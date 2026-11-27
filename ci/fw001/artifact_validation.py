"""Private, read-only comparison of actual baseline artifacts."""
import argparse, hashlib, json, stat, struct, sys, tarfile, tempfile, time
from pathlib import Path
import image_filesystem as fs
from image_structure import CANDIDATE_LIMITS

def elf_layout(data):
    if len(data)<52 or data[:7]!=b'\x7fELF\x01\x01\x01':
        raise ValueError('Expected LE ELF32 v1')
    kind,machine,version,_,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstr=struct.unpack_from('<2H5I6H',data,16)
    if machine!=40 or version!=1 or kind not in (2,3) or ehsize!=52:
        raise ValueError('Expected ARM executable/shared object')
    if not shnum or shsize!=40 or shstr>=shnum or shoff<52 or shoff+shsize*shnum>len(data):
        raise ValueError('Invalid section table')
    if phnum and (phsize!=32 or phoff<52 or phoff+phsize*phnum>len(data)):
        raise ValueError('Invalid program table')
    sections=[struct.unpack_from('<10I',data,shoff+i*40) for i in range(shnum)]
    programs=[struct.unpack_from('<8I',data,phoff+i*32) for i in range(phnum)]
    if not any(p[0]==1 for p in programs):
        raise ValueError('Missing loadable segment')
    for sec in sections:
        if sec[1]!=8 and sec[4]+sec[5]>len(data):
            raise ValueError('Section outside file')
    for ph in programs:
        if ph[1]+ph[4]>len(data) or (ph[0]==1 and ph[4]>ph[5]):
            raise ValueError('Segment outside file')
    return kind,flags,sections,programs,shstr


def elf(data):
    kind,flags,sections,programs,_=elf_layout(data)

    def string(sec,index):
        if sec[6]>=len(sections):
            raise ValueError('Invalid string table link')
        strings=sections[sec[6]]
        if strings[1]!=3 or index>=strings[5]:
            raise ValueError('Invalid string table index')
        start=strings[4]+index
        return data[start:data.index(b'\0',start,strings[4]+strings[5])].decode('ascii')

    def one(items,label):
        if len(items)>1: raise ValueError('Duplicate '+label)
        return items[0] if items else None

    dynamic=one([s for s in sections if s[1]==6],'dynamic section')
    segment=one([p for p in programs if p[0]==2],'dynamic segment')
    interp=one([p for p in programs if p[0]==3],'interpreter')
    interpreter=None
    if interp:
        raw=data[interp[1]:interp[1]+interp[4]]
        if not raw.endswith(b'\0') or b'\0' in raw[:-1]:
            raise ValueError('Invalid interpreter')
        interpreter=raw[:-1].decode('ascii')
    if bool(dynamic)!=bool(segment) or (interp and not segment):
        raise ValueError('Dynamic section/segment mismatch')
    needed=[]; tags={}; provided=set(); required={}
    if dynamic:
        pos,size=dynamic[4:6]
        if (pos,size)!=(segment[1],segment[4]) or size%8 or dynamic[9]!=8:
            raise ValueError('Invalid dynamic table')
        terminated=False
        for p in range(pos,pos+size,8):
            tag,value=struct.unpack_from('<2I',data,p)
            if tag==0:
                terminated=True; break
            if tag==1: needed.append(string(dynamic,value))
            elif tag in (5,10,14,15,29,0x6ffffffc,0x6ffffffd,0x6ffffffe,0x6fffffff):
                if tag in tags: raise ValueError('Duplicate dynamic tag')
                tags[tag]=value
        if not terminated or dynamic[6]>=len(sections):
            raise ValueError('Invalid dynamic terminator/string table')
        strings=sections[dynamic[6]]
        # Loader addresses must describe the same file-backed table, not a decoy section.
        def mapped(address,offset,size):
            return any(p[0]==1 and p[2]<=address and address+size<=p[2]+p[4]
                       and p[1]+address-p[2]==offset for p in programs)
        if (strings[1]!=3 or tags.get(5)!=strings[3] or tags.get(10)!=strings[5]
                or not mapped(strings[3],strings[4],strings[5])
                or not mapped(segment[2],pos,size)):
            raise ValueError('Dynamic string table is not loader-backed')
        for section_type,addr_tag,num_tag,header_size in (
                (0x6ffffffd,0x6ffffffc,0x6ffffffd,20),
                (0x6ffffffe,0x6ffffffe,0x6fffffff,16)):
            sec=one([s for s in sections if s[1]==section_type],'version section')
            if sec is None:
                if addr_tag in tags or num_tag in tags: raise ValueError('Missing version table')
                continue
            if (sec[6]!=dynamic[6] or tags.get(addr_tag)!=sec[3]
                    or tags.get(num_tag)!=sec[7] or not sec[7]
                    or not mapped(sec[3],sec[4],sec[5])):
                raise ValueError('Version table is not loader-backed')
            pos,end=sec[4],sec[4]+sec[5]
            for i in range(sec[7]):
                if pos+header_size>end: raise ValueError('Truncated version table')
                if section_type==0x6ffffffd:
                    ver,_,_,n,_,aux,nxt=struct.unpack_from('<4H3I',data,pos)
                    item_size=8
                else:
                    ver,n,file,aux,nxt=struct.unpack_from('<2H3I',data,pos)
                    lib=string(sec,file); item_size=16
                if ver!=1 or not n or aux<header_size:
                    raise ValueError('Invalid version record')
                a=pos+aux
                limit=pos+nxt if nxt else end
                if limit>end or limit<=pos: raise ValueError('Invalid version record boundary')
                for j in range(n):
                    if a+item_size>limit: raise ValueError('Truncated version auxiliary')
                    if section_type==0x6ffffffd:
                        name,link=struct.unpack_from('<2I',data,a)
                        if j==0: provided.add(string(sec,name))
                    else:
                        _,_,_,name,link=struct.unpack_from('<I2H2I',data,a)
                        required.setdefault(lib,set()).add(string(sec,name))
                    if j+1<n:
                        if link<item_size: raise ValueError('Invalid version auxiliary link')
                        a+=link
                    elif link: raise ValueError('Unexpected version auxiliary link')
                if i+1<sec[7]:
                    if nxt<header_size: raise ValueError('Invalid version record link')
                    pos+=nxt
                elif nxt: raise ValueError('Unexpected version record link')
    if any(lib not in needed for lib in required):
        raise ValueError('Version requirement without DT_NEEDED')
    return dict(machine=40,kind=kind,flags=flags,interpreter=interpreter,
                dynamic=bool(dynamic),needed=needed,provided=provided,required=required,
                rpath=string(dynamic,tags[15]) if 15 in tags else None,
                runpath=string(dynamic,tags[29]) if 29 in tags else None,
                soname=string(dynamic,tags[14]) if 14 in tags else None)


def tree(folder):
    return {name:fs.read_tree(folder/name,limit)[0] for name,limit in CANDIDATE_LIMITS.items()}


def signature(entry):
    return (entry['mode'],entry['uid'],entry['gid'],hashlib.sha256(entry['data']).hexdigest())


def normalize_build_metadata(data):
    """Mask only a structurally valid GNU build-id descriptor, never dates or code."""
    if not data.startswith(b'\x7fELF'): return data
    _,_,sections,programs,index=elf_layout(data)
    names=sections[index]
    if names[1]!=3: raise ValueError('Invalid section name table')
    strings=data[names[4]:names[4]+names[5]]
    notes=[]
    for i,s in enumerate(sections):
        if s[0]>=len(strings): raise ValueError('Invalid section name')
        name=strings[s[0]:strings.index(b'\0',s[0])]
        if name==b'.note.gnu.build-id': notes.append((i,s))
    if not notes: return data
    if len(notes)!=1: raise ValueError('Duplicate build-id section')
    i,s=notes[0]; pos,size=s[4:6]
    if s[1]!=7 or size<16: return data
    namesz,descsz,kind=struct.unpack_from('<3I',data,pos)
    start=pos+16; end=start+descsz
    if (namesz!=4 or kind!=3 or descsz not in (16,20,32)
            or data[pos+12:start]!=b'GNU\0' or end!=pos+size):
        return data
    # The descriptor may be in PT_LOAD/PT_NOTE, but must not alias other
    # sections, headers, or executable section bytes.
    shoff=struct.unpack_from('<I',data,32)[0]
    phoff=struct.unpack_from('<I',data,28)[0]
    protected=[(0,52),(shoff,shoff+40*len(sections)),(phoff,phoff+32*len(programs))]
    protected += [(x[4],x[4]+x[5]) for j,x in enumerate(sections) if j!=i and x[1]!=8]
    if s[2]&4 or any(start<b and a<end for a,b in protected):
        return data
    return data[:start]+b'\0'*descsz+data[end:]

def metadata_equal(left,right):
    try:
        return normalize_build_metadata(left)==normalize_build_metadata(right)
    except (ValueError,struct.error):
        return False


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
                    equal_after_compile_metadata_normalization=stat.S_ISREG(a[path]['mode']) and stat.S_ISREG(b[path]['mode']) and metadata_equal(a[path]['data'],b[path]['data']))
            rows.append(row)
    return rows

# Installed paths from the pinned system.sh and target multiarch layout.
# No current working directory, SD card, host paths, or basename-only lookup.
ENV_DIRS=('/home/lib','/home/yi-hack/lib')
DEFAULT_DIRS=('/lib','/usr/lib','/lib/arm-linux-gnueabihf','/usr/lib/arm-linux-gnueabihf')
LOADER='/lib/ld-linux-armhf.so.3'


def hard_float(info):
    return (info['flags']&0xff000600)==0x05000400 and not (info['flags']&0x00c00000)


def abi(trees):
    import posixpath
    # /home is the separately mounted home image; rootfs contents beneath it are hidden.
    files={'/'+path:entry for path,entry in trees['sys_y203c'].items() if not path.startswith('home/')}
    files.update({'/home/'+path:entry for path,entry in trees['home_y203c'].items()})
    elf_paths={p for p,e in files.items() if stat.S_ISREG(e['mode']) and e['data'].startswith(b'\x7fELF')}
    parsed={}

    def load(path):
        if path not in parsed:
            parsed[path]=elf(files[path]['data'])
        return parsed[path]

    def resolve(path):
        # Resolve directory as well as terminal symlinks inside the image only.
        todo=path.split('/'); parts=[]; hops=0
        while todo:
            part=todo.pop(0)
            if part in ('','.'): continue
            if part=='..':
                if parts: parts.pop()
                continue
            parts.append(part)
            entry=files.get('/'+'/'.join(parts))
            if entry and stat.S_ISLNK(entry['mode']):
                hops+=1
                if hops>40: return None
                target=entry['data'].decode('ascii')
                if not target: return None
                parts.pop()
                if target.startswith('/'): parts=[]
                todo=target.split('/')+todo
            elif entry and todo and not stat.S_ISDIR(entry['mode']):
                return None
        return '/'+'/'.join(parts)

    def directories(value,path):
        if value is None: return ()
        dirs=[]
        for raw in value.split(':'):
            expanded=raw.replace('${ORIGIN}',posixpath.dirname(path)).replace('$ORIGIN',posixpath.dirname(path))
            if not raw or '$' in expanded or not expanded.startswith('/'):
                raise ValueError('Unverified ELF library search path')
            expanded=posixpath.normpath(expanded)
            if expanded not in ENV_DIRS+DEFAULT_DIRS:
                raise ValueError('ELF search path outside reviewed target directories')
            dirs.append(expanded)
        return tuple(dirs)

    rows=[]
    for root in sorted(elf_paths):
        if not root.startswith('/home/yi-hack/'):continue
        unresolved=[]; missing_versions={}; errors=[]; selected={}
        pending=[root]; seen=set()
        while pending:
            p=pending.pop()
            if p in seen: continue
            seen.add(p)
            try:
                info=load(p)
            except (ValueError,struct.error):
                errors.append(p+': malformed or incompatible ELF'); continue
            if not hard_float(info): errors.append(p+': expected EABI5 hard-float flags')
            if info['interpreter'] is not None:
                loader=resolve(info['interpreter'])
                if info['interpreter']!=LOADER or loader not in elf_paths:
                    errors.append(p+': missing or incompatible ARM interpreter')
                else:
                    try:
                        if load(loader)['kind']!=3: raise ValueError('not shared object')
                        pending.append(loader)
                    except (ValueError,struct.error):
                        errors.append(p+': incompatible ARM interpreter')
            # ET_EXEC with dynamic dependencies must have an interpreter.
            if info['kind']==2 and info['dynamic'] and info['interpreter'] is None:
                errors.append(p+': dynamic executable without interpreter')
            try:
                rpath=directories(info['rpath'],p)
                runpath=directories(info['runpath'],p)
            except ValueError as exc:
                errors.append(p+': '+str(exc)); continue
            # Reject legacy inherited RPATH rather than assume a transitive order.
            if rpath:
                errors.append(p+': inherited DT_RPATH is not statically verified')
                continue
            for lib in info['needed']:
                label=p+' -> '+lib
                if not lib or '/' in lib or lib in ('.','..'):
                    unresolved.append(label); continue
                target=None
                for directory in ENV_DIRS+runpath+DEFAULT_DIRS:
                    candidate=resolve(directory+'/'+lib)
                    if candidate in files:
                        target=candidate; break
                if target not in elf_paths:
                    unresolved.append(label); continue
                try:
                    provider=load(target)
                except (ValueError,struct.error):
                    errors.append(label+': malformed or incompatible provider'); continue
                selected[label]=target
                if provider['kind']!=3 or (provider['soname'] is not None and provider['soname']!=lib):
                    errors.append(label+': incompatible provider type/SONAME')
                absent=info['required'].get(lib,set())-provider['provided']
                if absent: missing_versions[label]=sorted(absent)
                pending.append(target)
        info=parsed.get(root,{})
        rows.append(dict(path=root,machine=info.get('machine'),flags_hex=hex(info['flags']) if info else None,
            needed=info.get('needed',[]),required_symbol_versions={k:sorted(v) for k,v in info.get('required',{}).items()},
            selected_providers=selected,unresolved_libraries=unresolved,unresolved_symbol_versions=missing_versions,
            compatibility_errors=errors))
    return dict(scope='Static ARM EABI5 hard-float, interpreter and installed dependency closure; no target code executed',
                installed_elf_count=len(elf_paths),hack_elf_count=len(rows),programs=rows,
                passed=bool(rows) and all(not (x['unresolved_libraries'] or x['unresolved_symbol_versions']
                                              or x['compatibility_errors']) for x in rows))

REFERENCE_SHA256='ba0432c2c238487d0e1213f587fda20b64db0562a6fd500e2622d9506d78e796'

def verify_reference(archive_path,folder):
    fs.check(not archive_path.is_symlink() and hashlib.sha256(archive_path.read_bytes()).hexdigest()==REFERENCE_SHA256,'Official reference digest mismatch')
    with tarfile.open(archive_path,'r:gz') as archive:
        members=archive.getmembers()
        fs.check(len(members)==2 and {m.name for m in members}==set(CANDIDATE_LIMITS) and all(m.isfile() for m in members),'Unexpected reference members')
        for m in members:
            fs.check(0<m.size<=CANDIDATE_LIMITS[m.name],'Reference member exceeds limit')
            fs.check(archive.extractfile(m).read()==(folder/m.name).read_bytes(),'Reference extraction mismatch')

def explained(rows):
    return all(row['change']=='mtime_only' or
        (row['change']=='content_or_metadata' and row['metadata_equal']
         and row['equal_after_compile_metadata_normalization']) for row in rows)


def validate_pair(primary_folder,repeat_folder,reference_folder):
    fs.check(primary_folder.resolve()!=repeat_folder.resolve(),'Independent output directories required')
    primary,repeat,ref=tree(primary_folder),tree(repeat_folder),tree(reference_folder)
    result=dict(primary_structure=fs.inspect_firmware_pair(primary_folder),repeat_structure=fs.inspect_firmware_pair(repeat_folder),
        reference_structure=fs.inspect_firmware_pair(reference_folder),official_comparison=difference(primary,ref),
        primary_abi=abi(primary),repeat_abi=abi(repeat),repeat_comparison=difference(primary,repeat),
        release_approved=False,hardware_runtime_tested=False)
    result['repeat_differences_explained']=explained(result['repeat_comparison'])
    result['official_differences_explained']=explained(result['official_comparison'])
    result['repeat_official_comparison']=difference(repeat,ref)
    result['repeat_official_differences_explained']=explained(result['repeat_official_comparison'])
    required={path for path,entry in ref['home_y203c'].items() if path.startswith('yi-hack/') and entry['data'].startswith(b'\x7fELF')}
    result['missing_reference_hack_elf']=sorted(path for path in required if path not in primary['home_y203c'] or not primary['home_y203c'][path]['data'].startswith(b'\x7fELF'))
    result['status']='PASS' if result['primary_abi']['passed'] and result['repeat_abi']['passed'] and result['repeat_differences_explained'] and result['official_differences_explained'] and result['repeat_official_differences_explained'] and not result['missing_reference_hack_elf'] else 'BLOCKED'
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
    else:result['status']='UNVERIFIED'
    if args.repeat:
        repeat=tree(args.repeat)
        result.update(repeat_structure=fs.inspect_firmware_pair(args.repeat),repeat_comparison=difference(primary,repeat),repeat_abi=abi(repeat))
        result['repeat_differences_explained']=explained(result['repeat_comparison'])
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
    # Diagnostic-only invocations cannot claim acceptance without provenance.
    if provenance:
        print('[FW-001] artifact validation '+result['status'])
        return 0 if result['status']=='PASS' else 2
    return 2
if __name__=='__main__':sys.exit(main())
