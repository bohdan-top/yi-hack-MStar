"""Private, read-only comparison of actual baseline artifacts."""
import argparse, hashlib, json, re, stat, struct, sys, tarfile, tempfile, time
from pathlib import Path, PurePosixPath
import image_filesystem as fs
from image_structure import CANDIDATE_LIMITS

def elf(data):
    if not data.startswith(b'\x7fELF\x01\x01'): raise ValueError('Expected LE ELF32')
    machine=struct.unpack_from('<H',data,18)[0]
    if machine != 40: raise ValueError('Expected ARM')
    offset=struct.unpack_from('<I',data,32)[0]
    width,count=struct.unpack_from('<HH',data,46)
    if width < 40 or offset+width*count>len(data): raise ValueError('Invalid sections')
    sections=[struct.unpack_from('<10I',data,offset+i*width) for i in range(count)]
    def string(sec,index):
        strings=sections[sec[6]]; start=strings[4]+index
        return data[start:data.index(b'\0',start,strings[4]+strings[5])].decode()
    provided=set(); required={}; needed=[]
    for sec in sections:
        pos,end=sec[4],sec[4]+sec[5]
        if sec[1]==6:
            for p in range(pos,end,sec[9] or 8):
                tag,value=struct.unpack_from('<2I',data,p)
                if tag==1: needed.append(string(sec,value))
        if sec[1]==0x6ffffffd:
            while pos<end:
                _,_,_,_,_,aux,nxt=struct.unpack_from('<4H3I',data,pos)
                provided.add(string(sec,struct.unpack_from('<I',data,pos+aux)[0]))
                if not nxt: break
                pos+=nxt
        if sec[1]==0x6ffffffe:
            while pos<end:
                _,n,file,aux,nxt=struct.unpack_from('<2H3I',data,pos)
                lib=string(sec,file); a=pos+aux
                for _ in range(n):
                    _,_,_,name,link=struct.unpack_from('<I2H2I',data,a)
                    required.setdefault(lib,set()).add(string(sec,name))
                    if not link: break
                    a+=link
                if not nxt: break
                pos+=nxt
    return dict(machine=machine,flags=struct.unpack_from('<I',data,36)[0],
                needed=needed,provided=provided,required=required)

def tree(folder):
    return {name:fs.read_tree(folder/name,limit)[0] for name,limit in CANDIDATE_LIMITS.items()}

def signature(entry):
    return (entry['mode'],entry['uid'],entry['gid'],hashlib.sha256(entry['data']).hexdigest())

def normalize_build_metadata(data):
    """Only compile timestamps and the ELF build-id derived from binary contents."""
    if not data.startswith(b'\x7fELF\x01\x01'):return data
    result=bytearray(data)
    offset=struct.unpack_from('<I',data,32)[0];width,count,index=struct.unpack_from('<HHH',data,46)
    sections=[struct.unpack_from('<10I',data,offset+i*width) for i in range(count)]
    names=sections[index];strings=data[names[4]:names[4]+names[5]]
    for s in sections:
        name=strings[s[0]:strings.index(b'\0',s[0])]
        if name==b'.note.gnu.build-id':result[s[4]:s[4]+s[5]]=b'\0'*s[5]
    data=bytes(result)
    patterns=(rb'20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}',
              rb'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [ 0-9][0-9] 20[0-9]{2}',
              rb'[0-9]{2}:[0-9]{2}:[0-9]{2}')
    for pattern in patterns:data=re.sub(pattern,lambda m:b'0'*len(m[0]),data)
    return data

def difference(left,right):
    rows=[]
    for image in CANDIDATE_LIMITS:
        a,b=left[image],right[image]
        for path in sorted(a.keys()|b.keys()):
            if path not in a: change='only_right'
            elif path not in b: change='only_left'
            elif signature(a[path]) != signature(b[path]): change='content_or_metadata'
            elif a[path]['mtime'] != b[path]['mtime']: change='mtime_only'
            else: continue
            row=dict(image=image,path=path,change=change)
            if change=='content_or_metadata':
                row.update(left_sha256=signature(a[path])[-1],right_sha256=signature(b[path])[-1],
                    metadata_equal=signature(a[path])[:3]==signature(b[path])[:3],
                    equal_after_compile_metadata_normalization=normalize_build_metadata(a[path]['data'])==normalize_build_metadata(b[path]['data']))
            rows.append(row)
    return rows

def abi(trees):
    files={('/home/' if name=='home_y203c' else '/')+path:entry for name,t in trees.items() for path,entry in t.items()}
    parsed={p:elf(e['data']) for p,e in files.items() if e['data'].startswith(b'\x7fELF')}
    providers={}
    def resolve(p,seen=None):
        seen=set() if seen is None else seen
        if p in seen or p not in files: return None
        if p in parsed:return parsed[p]
        if stat.S_ISLNK(files[p]['mode']):
            target=files[p]['data'].decode(); parent=PurePosixPath(p).parent
            parts=[]
            for part in (PurePosixPath(target) if target.startswith('/') else parent/target).parts:
                if part=='..':
                    if parts:parts.pop()
                elif part not in ('/','.'):parts.append(part)
            return resolve('/'+'/'.join(parts),seen|{p})
    for p in files:
        info=resolve(p)
        if info is not None: providers.setdefault(PurePosixPath(p).name,[]).append(info)
    rows=[]
    for p,info in parsed.items():
        if not p.startswith('/home/yi-hack/'):continue
        missing_libs=[x for x in info['needed'] if x not in providers]
        missing_versions={lib:sorted(needs-set().union(*(v['provided'] for v in providers.get(lib,[]))))
                          for lib,needs in info['required'].items()}
        missing_versions={k:v for k,v in missing_versions.items() if v}
        rows.append(dict(path=p,machine=info['machine'],flags_hex=hex(info['flags']),needed=info['needed'],
            required_symbol_versions={k:sorted(v) for k,v in info['required'].items()},
            unresolved_libraries=missing_libs,unresolved_symbol_versions=missing_versions))
    return dict(scope='Static ARM ELF dependency and version-definition comparison; no target code executed',
                installed_elf_count=len(parsed),hack_elf_count=len(rows),programs=rows,
                passed=bool(rows) and all(not x['unresolved_libraries'] and not x['unresolved_symbol_versions'] for x in rows))

REFERENCE_SHA256='ba0432c2c238487d0e1213f587fda20b64db0562a6fd500e2622d9506d78e796'

def verify_reference(archive_path,folder):
    fs.check(not archive_path.is_symlink() and hashlib.sha256(archive_path.read_bytes()).hexdigest()==REFERENCE_SHA256,'Official reference digest mismatch')
    with tarfile.open(archive_path,'r:gz') as archive:
        members=archive.getmembers()
        fs.check(len(members)==2 and {m.name for m in members}==set(CANDIDATE_LIMITS) and all(m.isfile() for m in members),'Unexpected reference members')
        for m in members:
            fs.check(0<m.size<=CANDIDATE_LIMITS[m.name],'Reference member exceeds limit')
            fs.check(archive.extractfile(m).read()==(folder/m.name).read_bytes(),'Reference extraction mismatch')

def validate_pair(primary_folder,repeat_folder,reference_folder):
    fs.check(primary_folder.resolve()!=repeat_folder.resolve(),'Independent output directories required')
    primary,repeat,ref=tree(primary_folder),tree(repeat_folder),tree(reference_folder)
    result=dict(primary_structure=fs.inspect_firmware_pair(primary_folder),repeat_structure=fs.inspect_firmware_pair(repeat_folder),
        reference_structure=fs.inspect_firmware_pair(reference_folder),official_comparison=difference(primary,ref),
        primary_abi=abi(primary),repeat_abi=abi(repeat),repeat_comparison=difference(primary,repeat),
        release_approved=False,hardware_runtime_tested=False)
    result['repeat_differences_explained']=all(row['change']=='mtime_only' or
        (row['change']=='content_or_metadata' and row['metadata_equal'] and row['equal_after_compile_metadata_normalization'])
        for row in result['repeat_comparison'])
    required={path for path,entry in ref['home_y203c'].items() if path.startswith('yi-hack/') and entry['data'].startswith(b'\x7fELF')}
    result['missing_reference_hack_elf']=sorted(path for path in required if path not in primary['home_y203c'] or not primary['home_y203c'][path]['data'].startswith(b'\x7fELF'))
    result['status']='PASS' if result['primary_abi']['passed'] and result['repeat_abi']['passed'] and result['repeat_differences_explained'] and not result['missing_reference_hack_elf'] else 'BLOCKED'
    return result

def validate_archive_pair(primary_folder,repeat_folder,archive_path,stage_root):
    fs.check(archive_path is not None,'Supply the independently verified official reference archive')
    fs.check(not archive_path.is_symlink() and hashlib.sha256(archive_path.read_bytes()).hexdigest()==REFERENCE_SHA256,'Official reference digest mismatch')
    with tempfile.TemporaryDirectory(prefix='fw001-reference-',dir=stage_root) as tmp:
        folder=Path(tmp)
        with tarfile.open(archive_path,'r:gz') as archive:
            members=archive.getmembers()
            fs.check(len(members)==2 and {m.name for m in members}==set(CANDIDATE_LIMITS) and all(m.isfile() for m in members),'Unexpected reference members')
            for member in members:
                fs.check(0<member.size<=CANDIDATE_LIMITS[member.name],'Reference member exceeds limit')
                (folder/member.name).write_bytes(archive.extractfile(member).read())
        verify_reference(archive_path,folder)
        return validate_pair(primary_folder,repeat_folder,folder)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('primary',type=Path);ap.add_argument('--repeat',type=Path)
    ap.add_argument('--reference',type=Path,required=True);ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--reference-archive',type=Path)
    ap.add_argument('--lock',type=Path);ap.add_argument('--approved-entrypoint');ap.add_argument('--approved-lock-sha256')
    ap.add_argument('--cpus',type=int,default=1);ap.add_argument('--memory-gib',type=int,default=8)
    args=ap.parse_args();started=time.monotonic(); primary=tree(args.primary); ref=tree(args.reference)
    provenance=None
    if args.lock:
        import importlib.util
        spec=importlib.util.spec_from_file_location('approved_runner',Path(fs.__file__).with_name('run.py'))
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        runner.require(bool(args.approved_entrypoint) and runner.fw.SHA.fullmatch(args.approved_entrypoint),'Explicit reviewed build entrypoint required')
        runner.require(not args.report.resolve().is_relative_to(runner.ROOT),'Write validation reports outside checkout')
        raw=args.lock.read_bytes()
        runner.require(hashlib.sha256(raw).hexdigest()==args.approved_lock_sha256,'Unapproved lock digest')
        lock=json.loads(raw);runner.fw.validate_lock(lock,runner.fw.BASE)
        key=dict(entrypoint=args.approved_entrypoint,source=runner.fw.BASE,lock=args.approved_lock_sha256,
                 image=lock['image_id'],cpus=args.cpus,memory_gib=args.memory_gib)
        runner.require(args.repeat is not None and args.primary.resolve()!=args.repeat.resolve(),'Independent output directories required')
        provenance=dict(key=key,primary_sha256=runner.verify_outputs(args.primary,key),repeat_sha256=runner.verify_outputs(args.repeat,key))
    if args.reference_archive:
        verify_reference(args.reference_archive,args.reference)
    result=dict(primary_structure=fs.inspect_firmware_pair(args.primary),
        reference_structure=fs.inspect_firmware_pair(args.reference),official_comparison=difference(primary,ref),
        primary_abi=abi(primary),release_approved=False)
    if provenance:result['verified_build_provenance']=provenance
    if args.repeat:
        repeat=tree(args.repeat)
        result.update(repeat_structure=fs.inspect_firmware_pair(args.repeat),repeat_comparison=difference(primary,repeat),repeat_abi=abi(repeat))
        result['repeat_differences_explained']=all(row['change']=='mtime_only' or
            (row['change']=='content_or_metadata' and row['metadata_equal'] and row['equal_after_compile_metadata_normalization'])
            for row in result['repeat_comparison'])
    if provenance:
        result=validate_pair(args.primary,args.repeat,args.reference)
        result['verified_build_provenance']=provenance
        if not args.reference_archive:result['status']='BLOCKED'
    result['elapsed_seconds']=round(time.monotonic()-started,3)
    result['validator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k.endswith('structure')},indent=2))
    print('ABI:',result['primary_abi']['passed'],'official differences:',len(result['official_comparison']))
    if 'repeat_comparison' in result:print('Repeat differences:',len(result['repeat_comparison']))
    if provenance:
        print('[FW-001] artifact validation '+result['status'])
        return 0 if result['status']=='PASS' else 2
    return 0
if __name__=='__main__':sys.exit(main())
