"""Convert a reviewed recovery attachment into candidate stock tgz inputs.

No mount, extraction to filesystem, camera access or input approval occurs.
The original attachment and its provenance must be reviewed independently.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile
import tempfile

from image_filesystem import read_tree, identities
from image_structure import CANDIDATE_LIMITS, check


def write_archive(tree, output):
    with output.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.PAX_FORMAT) as archive:
            for name, entry in sorted(tree.items()):
                item = tarfile.TarInfo(name)
                item.mode = stat.S_IMODE(entry['mode'])
                item.uid, item.gid, item.mtime = entry['uid'], entry['gid'], entry['mtime']
                if stat.S_ISDIR(entry['mode']):
                    item.type = tarfile.DIRTYPE
                elif stat.S_ISLNK(entry['mode']):
                    item.type = tarfile.SYMTYPE
                    item.linkname = entry['data'].decode('utf8')
                    check('\x00' not in item.linkname, 'Invalid symlink target')
                else:
                    item.size = len(entry['data'])
                archive.addfile(item, io.BytesIO(entry['data']) if item.isfile() else None)
    # Independently reread the gzip/tar and check metadata and every payload.
    with tarfile.open(output, 'r:gz') as archive:
        members = archive.getmembers()
        check(len(members) == len(tree) and {m.name for m in members} == set(tree), 'Stock archive member mismatch')
        for m in members:
            entry = tree[m.name]
            check((m.mode, m.uid, m.gid, m.mtime) ==
                  (stat.S_IMODE(entry['mode']), entry['uid'], entry['gid'], entry['mtime']), 'Stock metadata mismatch')
            if stat.S_ISREG(entry['mode']):
                check(m.isfile() and archive.extractfile(m).read() == entry['data'], 'Stock data mismatch')
            elif stat.S_ISDIR(entry['mode']):
                check(m.isdir(), 'Stock directory mismatch')
            else:
                check(m.issym() and m.linkname == entry['data'].decode('utf8'), 'Stock symlink mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recovery', type=Path, required=True)
    parser.add_argument('--expected-archive-sha256', required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--temp-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    check(hashlib.file_digest(args.recovery.open('rb'), 'sha256').hexdigest() == args.expected_archive_sha256,
          'Recovery archive digest mismatch')
    args.output_root.mkdir(parents=True, exist_ok=True)
    report = {'status': 'CANDIDATE INPUTS; independent lock approval required',
              'recovery_origin': 'maintainer equivalent rebuild; not a device dump or vendor-signed image',
              'archive_sha256': args.expected_archive_sha256, 'files': []}
    with tarfile.open(args.recovery) as archive, tempfile.TemporaryDirectory(dir=args.temp_root) as temp:
        members = archive.getmembers()
        expected = {name + '.jffs2' for name in CANDIDATE_LIMITS}
        check(len(members) == 2 and {m.name for m in members} == expected and all(m.isfile() for m in members),
              'Unexpected recovery archive layout')
        for m in members:
            name = m.name.removesuffix('.jffs2')
            check(0 < m.size <= CANDIDATE_LIMITS[name], 'Invalid recovery member size')
            image = Path(temp) / m.name
            image.write_bytes(archive.extractfile(m).read())
            tree, structure = read_tree(image, CANDIDATE_LIMITS[name])
            identity = identities(tree)
            if name == 'home_y203c':
                check(identity.get('homever') == identity.get('app/.appver') == '4.5.0.0C_201910080934',
                      'Wrong stock firmware version')
                check(not any(p.startswith('yi-hack/') for p in tree), 'Modified recovery filesystem')
            output = args.output_root / (name + '.tgz')
            write_archive(tree, output)
            report['files'].append(dict(name=output.name, bytes=output.stat().st_size,
                sha256=hashlib.file_digest(output.open('rb'), 'sha256').hexdigest(),
                image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                structure=structure, identity=identity, filesystem_entries=len(tree)))
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print('Prepared and reread both candidate stock archives; no private lock approved.')


if __name__ == '__main__':
    main()
