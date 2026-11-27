import copy
import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('validation',Path(__file__).with_name('artifact_validation.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


def elf_fixture(required=None,provided=None,*,needed=(),flags=0x5000400,kind=3,
                interpreter=None,runpath=None,rpath=None,soname=None,note_type=3):
    strings=bytearray(b'\0')
    def string(value):
        if isinstance(value,str): value=value.encode()
        offset=len(strings); strings.extend(value+b'\0'); return offset
    libs=list(needed)
    if required: libs.append('libc.so.6')
    lib_offsets={lib:string(lib) for lib in libs}
    needs=(struct.pack('<2H3I',1,1,lib_offsets['libc.so.6'],16,0)
           +struct.pack('<I2H2I',0,0,2,string(required),0)) if required else b''
    defs=(struct.pack('<4H3I',1,0,2,1,0,20,0)
          +struct.pack('<2I',string(provided),0)) if provided else b''
    tags=[(1,lib_offsets[lib]) for lib in libs]
    for tag,value in ((14,soname),(15,rpath),(29,runpath)):
        if value is not None: tags.append((tag,string(value)))
    dynamic=bool(tags or required or provided or interpreter)
    if dynamic:
        tags.extend([(5,0),(10,len(strings))])
        if required: tags.extend([(0x6ffffffe,0),(0x6fffffff,1)])
        if provided: tags.extend([(0x6ffffffc,0),(0x6ffffffd,1)])
        tags.append((0,0))
    section_names=[b'',b'.shstrtab',b'.dynstr',b'.dynamic',b'.gnu.version_r',
                   b'.gnu.version_d',b'.rodata',b'.note.gnu.build-id',b'.interp']
    names=b'\0'.join(section_names)+b'\0'
    payloads=[b'',names,bytes(strings),b'\0'*(len(tags)*8),needs,defs,
              b'compiled 2026-11-27 19:00:01\0',struct.pack('<3I',4,20,note_type)+b'GNU\0'+b'A'*20,
              interpreter.encode()+b'\0' if interpreter else b'']
    types=[0,3,3,6 if dynamic else 1,0x6ffffffe if required else 1,
           0x6ffffffd if provided else 1,1,7,1]
    phnum=1+bool(dynamic)+bool(interpreter)
    shoff=52+32*phnum
    offset=shoff+40*len(payloads)
    offsets=[]
    for data in payloads: offsets.append(offset); offset+=len(data)
    base=0x10000
    addresses={5:base+offsets[2],0x6ffffffe:base+offsets[4],0x6ffffffc:base+offsets[5]}
    if dynamic:
        payloads[3]=b''.join(struct.pack('<2I',tag,addresses.get(tag,value)) for tag,value in tags)
    sections=[]
    for i,data in enumerate(payloads):
        sections.append(struct.pack('<10I',names.index(section_names[i]) if i else 0,types[i],
            2 if i>=2 else 0,base+offsets[i],offsets[i],len(data),2 if i in (3,4,5) else 0,
            int((i==4 and bool(required)) or (i==5 and bool(provided))),1,8 if i==3 and dynamic else 0))
    ph=[struct.pack('<8I',1,0,base,base,offset,offset,5,4096)]
    if dynamic:
        pos=offsets[3]; size=len(payloads[3]); ph.append(struct.pack('<8I',2,pos,base+pos,base+pos,size,size,6,4))
    if interpreter:
        pos=offsets[8]; size=len(payloads[8]); ph.append(struct.pack('<8I',3,pos,base+pos,base+pos,size,size,4,1))
    header=b'\x7fELF\x01\x01\x01'+b'\0'*9+struct.pack('<2H5I6H',kind,40,1,0,52,shoff,flags,52,32,phnum,40,len(payloads),1)
    return header+b''.join(ph)+b''.join(sections)+b''.join(payloads)


def entry(data,mode=0o100755):
    return dict(data=data,mode=mode,uid=0,gid=0,mtime=1)


def fixture_trees(**kwargs):
    return {'home_y203c':{'yi-hack/bin/test':entry(elf_fixture(required=b'GLIBC_2.4',
                kind=2,interpreter=v.LOADER,**kwargs))},
            'sys_y203c':{'lib/libc.so.6':entry(elf_fixture(provided=b'GLIBC_2.4')),
                'lib/ld-linux-armhf.so.3':entry(elf_fixture())}}


class ValidationTests(unittest.TestCase):
    def test_version_requirements_must_be_supplied_by_selected_provider(self):
        trees=fixture_trees()
        self.assertTrue(v.abi(trees)['passed'])
        # Rootfs /home contents are hidden by the installed home image.
        trees['sys_y203c']['home/yi-hack/bin/test']=entry(elf_fixture(flags=0x5000200))
        self.assertTrue(v.abi(trees)['passed'])
        # Same basename outside loader paths must not satisfy the dependency.
        trees['sys_y203c']['usr/share/libc.so.6']=trees['sys_y203c'].pop('lib/libc.so.6')
        self.assertFalse(v.abi(trees)['passed'])
        trees['sys_y203c']['lib/libc.so.6']=trees['sys_y203c'].pop('usr/share/libc.so.6')
        trees['home_y203c']['lib/libc.so.6']=entry(elf_fixture(provided=b'GLIBC_2.34'))
        self.assertFalse(v.abi(trees)['passed'])
        del trees['home_y203c']['lib/libc.so.6']
        self.assertTrue(v.abi(trees)['passed'])

    def test_wrong_flags_and_interpreter_rejected(self):
        for flags in (0x4000400,0x5000200,0x5000000,0x5000600,0x5800400):
            self.assertFalse(v.abi(fixture_trees(flags=flags))['passed'],hex(flags))
        trees=fixture_trees()
        trees['sys_y203c']['lib/libc.so.6']=entry(elf_fixture(provided=b'GLIBC_2.4',flags=0x5000200))
        self.assertFalse(v.abi(trees)['passed'])
        trees=fixture_trees()
        del trees['sys_y203c']['lib/ld-linux-armhf.so.3']
        self.assertFalse(v.abi(trees)['passed'])
        trees=fixture_trees()
        trees['home_y203c']['yi-hack/bin/test']=entry(elf_fixture(required=b'GLIBC_2.4',kind=2,interpreter='/tmp/ld-linux-armhf.so.3'))
        self.assertFalse(v.abi(trees)['passed'])

    def test_loader_paths_symlinks_and_transitive_dependencies(self):
        self.assertFalse(v.abi(fixture_trees(runpath='/tmp/sd/yi-hack/lib'))['passed'])
        self.assertFalse(v.abi(fixture_trees(rpath='/lib'))['passed'])
        trees=fixture_trees(runpath='${ORIGIN}/../lib')
        self.assertTrue(v.abi(trees)['passed'])
        trees['sys_y203c']['lib/libc-real.so']=entry(elf_fixture(provided=b'GLIBC_2.4',needed=['libnext.so']))
        trees['sys_y203c']['lib/libc.so.6']=entry(b'libc-real.so',0o120777)
        self.assertFalse(v.abi(trees)['passed'])
        trees['sys_y203c']['lib/libnext.so']=entry(elf_fixture())
        self.assertTrue(v.abi(trees)['passed'])
        trees['sys_y203c']['lib/libc-real.so']=entry(b'libc.so.6',0o120777)
        self.assertFalse(v.abi(trees)['passed'])

    def test_build_id_only_normalization(self):
        a=elf_fixture()
        b=a.replace(b'A'*20,b'B'*20)
        self.assertEqual(v.normalize_build_metadata(a),v.normalize_build_metadata(b))
        for changed in (b.replace(b'19:00:01',b'20:00:02'),b.replace(b'compiled',b'modified')):
            self.assertNotEqual(v.normalize_build_metadata(a),v.normalize_build_metadata(changed))
        fake=elf_fixture(note_type=1)
        self.assertNotEqual(v.normalize_build_metadata(fake),v.normalize_build_metadata(fake.replace(b'A'*20,b'B'*20)))
        self.assertNotEqual(v.normalize_build_metadata(b'19:00:01'),v.normalize_build_metadata(b'20:00:02'))

    def test_official_comparison_is_acceptance_gate_for_both_builds(self):
        ref=fixture_trees()
        ref['home_y203c']['yi-hack/script/test.sh']=entry(b'original')
        primary=copy.deepcopy(ref); repeat=copy.deepcopy(ref)
        def validate():
            with patch.object(v,'tree',side_effect=[primary,repeat,ref]), \
                 patch.object(v.fs,'inspect_firmware_pair',return_value={}):
                return v.validate_pair(Path('/primary'),Path('/repeat'),Path('/reference'))
        self.assertEqual(validate()['status'],'PASS')
        for trees in (primary,repeat):
            trees['home_y203c']['yi-hack/script/test.sh']['data']=b'modified'
        result=validate()
        self.assertTrue(result['repeat_differences_explained'])
        self.assertFalse(result['official_differences_explained'])
        self.assertFalse(result['repeat_official_differences_explained'])
        self.assertEqual(result['status'],'BLOCKED')
        for trees in (primary,repeat):
            trees['home_y203c']['yi-hack/script/test.sh']['data']=b'original'
        del repeat['home_y203c']['yi-hack/script/test.sh']
        self.assertEqual(validate()['status'],'BLOCKED')
        repeat['home_y203c']['yi-hack/script/test.sh']=entry(b'original',0o100644)
        self.assertEqual(validate()['status'],'BLOCKED')

    def test_wrong_architecture_and_decoy_dynamic_section_rejected(self):
        data=bytearray(elf_fixture());struct.pack_into('<H',data,18,3)
        with self.assertRaises(ValueError):v.elf(bytes(data))
        data=bytearray(elf_fixture());struct.pack_into('<H',data,44,0)
        with self.assertRaises(ValueError):v.elf(bytes(data))
        data=bytearray(elf_fixture(required=b'GLIBC_2.4'))
        # PT_DYNAMIC offset points at a different location than SHT_DYNAMIC.
        struct.pack_into('<I',data,52+32+4,0)
        with self.assertRaises(ValueError):v.elf(bytes(data))


if __name__=='__main__':unittest.main()
