import importlib.util
from pathlib import Path
import struct
import unittest

spec=importlib.util.spec_from_file_location('validation',Path(__file__).with_name('artifact_validation.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def elf_fixture(required=None,provided=None):
    strings=b'\0libc.so.6\0GLIBC_2.4\0GLIBC_2.34\0'
    names=b'\0.shstrtab\0.dynstr\0.dynamic\0.gnu.version_r\0.gnu.version_d\0.rodata\0.note.gnu.build-id\0'
    needed=struct.pack('<4I',1,1,0,0) if required else b''
    needs=(struct.pack('<2H3I',1,1,1,16,0)+struct.pack('<I2H2I',0,0,2,strings.index(required),0)) if required else b''
    defs=(struct.pack('<4H3I',1,0,2,1,0,20,0)+struct.pack('<2I',strings.index(provided),0)) if provided else b''
    payloads=[b'',names,strings,needed,needs,defs,b'compiled 2026-11-27 19:00:01\0',b'build-id-test']
    types=[0,3,3,6,0x6ffffffe,0x6ffffffd,1,7]
    section_names=[b'',b'.shstrtab',b'.dynstr',b'.dynamic',b'.gnu.version_r',b'.gnu.version_d',b'.rodata',b'.note.gnu.build-id']
    offset=52+40*len(payloads);sections=[];body=b''
    for i,data in enumerate(payloads):
        sections.append(struct.pack('<10I',names.index(section_names[i]) if i else 0,types[i],0,0,offset,len(data),2 if i in (3,4,5) else 0,0,1,8 if i==3 else 0))
        body+=data;offset+=len(data)
    header=b'\x7fELF\x01\x01\x01'+b'\0'*9+struct.pack('<2H5I6H',3,40,1,0,0,52,0x5000400,52,0,0,40,len(payloads),1)
    return header+b''.join(sections)+body

class ValidationTests(unittest.TestCase):
    def test_version_requirements_must_be_supplied(self):
        program=elf_fixture(required=b'GLIBC_2.4');library=elf_fixture(provided=b'GLIBC_2.4')
        trees={'home_y203c':{'yi-hack/bin/test':{'data':program,'mode':0o100755}},
               'sys_y203c':{'lib/libc.so.6':{'data':library,'mode':0o100755}}}
        self.assertTrue(v.abi(trees)['passed'])
        trees['home_y203c']['yi-hack/bin/test']['data']=elf_fixture(required=b'GLIBC_2.34')
        self.assertFalse(v.abi(trees)['passed'])
        del trees['sys_y203c']['lib/libc.so.6']
        self.assertFalse(v.abi(trees)['passed'])

    def test_compile_time_normalization_preserves_other_changes(self):
        a=elf_fixture();b=a.replace(b'19:00:01',b'20:00:02').replace(b'build-id-test',b'other-id-test')
        self.assertEqual(v.normalize_build_metadata(a),v.normalize_build_metadata(b))
        self.assertNotEqual(v.normalize_build_metadata(a),v.normalize_build_metadata(b.replace(b'compiled',b'modified')))
        self.assertNotEqual(v.normalize_build_metadata(b'19:00:01'),v.normalize_build_metadata(b'20:00:02'))

    def test_wrong_architecture_rejected(self):
        data=bytearray(elf_fixture());struct.pack_into('<H',data,18,3)
        with self.assertRaises(ValueError):v.elf(bytes(data))

if __name__=='__main__':unittest.main()
