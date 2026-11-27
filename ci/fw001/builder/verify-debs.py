"""Run in the already verified Debian base; verify saved signed APT inputs offline."""
import hashlib, json, subprocess
from pathlib import Path
root=Path('/prepare')
def require(ok, message):
    if not ok:
        raise RuntimeError(message)

packages={}
releases=[]
for base,suite in [('debian','bookworm'),('debian','bookworm-updates'),('debian-security','bookworm-security')]:
    prefix='deb.debian.org_'+base+'_dists_'+suite
    release=root/'apt-lists'/(prefix+'_InRelease')
    subprocess.run(['gpgv','--keyring','/usr/share/keyrings/debian-archive-keyring.gpg',str(release)],check=True)
    entries=release.read_text().split('SHA256:\n',1)[1].split('\nSHA',1)[0].splitlines()
    records={line.split()[2]:(line.split()[0],int(line.split()[1])) for line in entries if len(line.split())==3 and len(line.split()[0])==64}
    path=root/'apt-lists'/(prefix+'_main_binary-amd64_Packages.lz4')
    data=subprocess.check_output(['/usr/lib/apt/apt-helper','cat-file',str(path)])
    expected,size=records['main/binary-amd64/Packages']
    require(len(data)==size and hashlib.sha256(data).hexdigest()==expected, 'Signed package index digest mismatch')
    releases.append(dict(suite=suite,inrelease_sha256=hashlib.sha256(release.read_bytes()).hexdigest(),packages_sha256=expected))
    for paragraph in data.decode().split('\n\n'):
        fields={line.split(': ',1)[0]:line.split(': ',1)[1] for line in paragraph.splitlines() if ': ' in line and not line.startswith(' ')}
        if all(k in fields for k in ('Package','Version','Architecture','SHA256')):
            packages.setdefault((fields['Package'],fields['Version'],fields['Architecture']),set()).add(fields['SHA256'])
verified=[]
for path in sorted((root/'debs').glob('*.deb')):
    name,version,arch=subprocess.check_output(['dpkg-deb','--show','--showformat=${Package}\n${Version}\n${Architecture}\n',str(path)],text=True).splitlines()
    sha=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
    require(sha in packages[(name,version,arch)], 'Package differs from signed metadata')
    verified.append(dict(package=name,version=version,architecture=arch,sha256=sha))
require(verified, 'No package archives verified')
(root/'provenance'/'verified-debs.json').write_text(json.dumps(dict(releases=releases,packages=verified),indent=2)+'\n')
print('Independently verified signed metadata and',len(verified),'package archives.')
