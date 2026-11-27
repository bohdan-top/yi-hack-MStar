#!/usr/bin/env python3
"""Exercise FW-008 Docker isolation with a public Python probe image; no firmware build."""
import argparse
import errno
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def burn_cpu(seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        pass


def inside(args):
    cpus = sorted(os.sched_getaffinity(0))
    cgroup = Path('/sys/fs/cgroup')
    quota, period = map(int, (cgroup / 'cpu.max').read_text().split())
    memory = int((cgroup / 'memory.max').read_text())
    swap = int((cgroup / 'memory.swap.max').read_text())
    require(len(cpus) == args.cpus and quota == args.cpus * period, 'CPU enforcement mismatch')
    require(memory == args.memory_gib * 1024**3 and swap == 0, 'Memory/swap enforcement mismatch')
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    require(status['NoNewPrivs'].strip() == '1' and status['Seccomp'].strip() == '2', 'No-new-privileges/seccomp enforcement mismatch')
    require(int(status['CapEff'].strip(), 16) == 0xB, 'Unexpected effective capabilities')
    require(os.environ.get('FW008_JOBS') == '1' and os.environ.get('MAKEFLAGS') == '-j1', 'Build parallelism environment mismatch')
    nproc = int(subprocess.check_output(['nproc'], text=True).strip())
    require(nproc == args.cpus, 'nproc does not respect affinity')
    readonly = {}
    for folder in ('/usr/local', '/inputs'):
        try:
            with open(folder + '/fw001-write-probe', 'wb') as out:
                out.write(b'failure')
        except OSError as error:
            readonly[folder] = error.errno == errno.EROFS
        else:
            readonly[folder] = False
    require(all(readonly.values()), 'Readonly filesystem enforcement failed')
    interfaces = sorted(p.name for p in Path('/sys/class/net').iterdir())
    require(interfaces == ['lo'], 'Unexpected network interface')
    network_blocked = False
    try:
        with socket.create_connection(('1.1.1.1', 443), timeout=2):
            pass
    except OSError:
        network_blocked = True
    require(network_blocked, 'Unexpected external network connectivity')
    require(not list(Path('/dev').glob('mtd*')), 'Unexpected MTD device')
    guard = subprocess.run(['bash', '-c', 'set -e; source /inputs/download-guard.sh; install_download_guard /work/guards /work/download-marker; wget https://example.invalid || true; check_download /work/download-marker'], capture_output=True, text=True)
    require(guard.returncode != 0 and Path('/work/download-marker').is_file(), 'Download guard did not reject wget')
    allocated = bytearray(128 * 1024**2)
    children = [multiprocessing.Process(target=burn_cpu, args=(8,)) for _ in cpus]
    for child in children:
        child.start()
    for child in children:
        child.join()
    require(all(child.exitcode == 0 for child in children), 'Load probe child failed')
    require(len(allocated) == 128 * 1024**2, 'Memory probe allocation failed')
    result = {'affinity_cpu_count': len(cpus), 'cpu_quota': quota, 'cpu_period': period,
              'memory_max_bytes': memory, 'memory_swap_max_bytes': swap,
              'readonly_root_and_inputs': all(readonly.values()), 'interfaces': interfaces,
              'external_connection_blocked': network_blocked, 'download_guard_rejected': True,
              'mtd_devices_absent': True, 'load_seconds_per_worker': 8, 'load_workers': len(children), 'no_new_privileges': True,
              'seccomp_filtering': True, 'effective_capabilities_hex': status['CapEff'].strip(),
              'makeflags': os.environ['MAKEFLAGS'], 'nproc': nproc}
    Path('/work/probe.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')


def memory_bytes(value):
    match = re.fullmatch(r'([0-9.]+)([KMGT]?i?B)', value.strip())
    require(match is not None, 'Unknown Docker memory unit')
    units = {'B': 1, 'kB': 1000, 'KB': 1000, 'MB': 1000**2, 'GB': 1000**3,
             'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3, 'TiB': 1024**4}
    return round(float(match[1]) * units[match[2]])


def host(args):
    require(sys.platform.startswith('linux'), 'Native WSL2/Linux required')
    require(re.fullmatch(r'sha256:[a-f0-9]{64}', args.image or ''), 'Use an immutable image ID')
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('fw008_probe', root / 'ci/fw008/manual-build.py')
    fw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fw)
    def output(*cmd):
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    require(not os.environ.get('DOCKER_HOST') and not os.environ.get('DOCKER_CONTEXT'), 'Ambient Docker override rejected')
    require(output('docker', 'context', 'inspect', '--format', '{{.Endpoints.docker.Host}}') == 'unix:///var/run/docker.sock', 'Local socket required')
    require(bool(output('pgrep', '-x', 'dockerd')), 'Native dockerd required')
    require(output('findmnt', '-n', '-o', 'FSTYPE', '/') == 'ext4', 'Dedicated ext4 root required')
    docker_root = Path(output('docker', 'info', '--format', '{{.DockerRootDir}}'))
    require(docker_root.stat().st_dev == Path('/').stat().st_dev, 'Docker data is on another filesystem')
    for p in (args.stage_root, args.report_dir):
        require(p.is_absolute() and not p.resolve().is_relative_to(root), 'Probe storage must be outside checkout')
        p.mkdir(parents=True, exist_ok=True)
    require(args.stage_root.stat().st_dev == Path('/').stat().st_dev and not args.stage_root.is_symlink()
            and args.stage_root.stat().st_uid == os.getuid() and not args.stage_root.stat().st_mode & 0o077,
            'Private ext4 staging required')
    info = json.loads(output('docker', 'image', 'inspect', args.image))[0]
    require(info['Id'] == args.image and info['Os'] == 'linux' and info['Architecture'] == 'amd64'
            and not info['Config'].get('Volumes'), 'Unexpected probe image')
    report = {'scope': 'public environment probe using FW-008 Docker arguments; firmware NOT BUILT',
              'image_id': args.image, 'image_repo_digests': info.get('RepoDigests', []),
              'requested_cpus': args.cpus, 'requested_memory_gib': args.memory_gib,
              'native_docker_data_and_staging_on_root_ext4': True, 'release_approved': False}
    started = time.monotonic()
    name = 'fw001-probe-' + uuid.uuid4().hex
    samples = []
    interrupted = False
    running_since = None
    with tempfile.TemporaryDirectory(prefix='fw001-probe-', dir=args.stage_root) as tmp:
        temp = Path(tmp)
        inputs, work = temp / 'inputs', temp / 'work'
        inputs.mkdir(); work.mkdir()
        shutil.copyfile(__file__, inputs / 'probe.py')
        shutil.copyfile(root / 'ci/fw008/download-guard.sh', inputs / 'download-guard.sh')
        (inputs / 'build-offline.sh').write_text(f'''#!/bin/bash
set -euo pipefail
umask 077
trap 'chown -hR "$FW008_OWNER_UID:$FW008_OWNER_GID" /work; find /work -type d -exec chmod u+rwx {{}} +' EXIT
python3 -B /inputs/probe.py --inside --cpus {args.cpus} --memory-gib {args.memory_gib}
''', encoding='utf8', newline='\n')
        command = fw.docker_args(args.image, inputs, work, args.cpus, args.memory_gib)
        command[3:3] = ['--name', name]
        log = args.report_dir / ('private-' + name + '.log')
        with log.open('wb') as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
            try:
                while process.poll() is None:
                    require(time.monotonic() - started < 120, 'Probe startup/execution timed out')
                    state = subprocess.run(['docker', 'inspect', '--format', '{{.State.Running}}', name], capture_output=True, text=True)
                    if state.returncode == 0 and state.stdout.strip() == 'true' and running_since is None:
                        running_since = time.monotonic()
                    if args.interrupt_after and running_since is not None and not interrupted and time.monotonic() - running_since >= args.interrupt_after:
                        subprocess.run(['docker', 'kill', name], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        interrupted = True
                    stats = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}', name], capture_output=True, text=True)
                    if stats.returncode == 0 and stats.stdout.strip():
                        row = json.loads(stats.stdout)
                        samples.append({'cpu_percent': float(row['CPUPerc'].rstrip('%')),
                                        'memory_bytes': memory_bytes(row['MemUsage'].split('/')[0])})
                    time.sleep(0.5)
                if interrupted:
                    require(process.returncode == 137, 'Unexpected interrupted container exit')
                    report['interrupted_exit_code'] = process.returncode
                    report['completed_output_absent'] = not (work / 'probe.json').exists()
                    require(report['completed_output_absent'], 'Interrupted probe unexpectedly completed')
                else:
                    require(process.returncode == 0, 'Probe container failed; inspect private log')
                    report['container_checks'] = json.loads((work / 'probe.json').read_text(encoding='utf8'))
            finally:
                subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=15)
        report['sample_count'] = len(samples)
        report['peak_observed_cpu_percent'] = max((x['cpu_percent'] for x in samples), default=None)
        report['peak_observed_memory_bytes'] = max((x['memory_bytes'] for x in samples), default=None)
        report['sampling'] = 'docker stats --no-stream plus 0.5 second wait; sampled peaks of this 8-second probe, not firmware compilation'
    report['task_workspace_cleaned'] = not temp.exists()
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    report['status'] = ('CONTAINER INTERRUPTION CHECK PASS' if interrupted else 'ENVIRONMENT PROBE PASS') + '; firmware build NOT RUN'
    destination = args.report_dir / (name + '.json')
    destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inside', action='store_true')
    parser.add_argument('--image')
    parser.add_argument('--stage-root', type=Path)
    parser.add_argument('--report-dir', type=Path)
    parser.add_argument('--interrupt-after', type=float, default=0)
    parser.add_argument('--cpus', type=int, default=6)
    parser.add_argument('--memory-gib', type=int, default=8)
    arguments = parser.parse_args()
    require(arguments.interrupt_after == 0 or arguments.interrupt_after >= 2, 'Invalid interruption interval')
    require(1 <= arguments.cpus <= 6 and 1 <= arguments.memory_gib <= 8, 'Probe exceeds task resource limits')
    inside(arguments) if arguments.inside else host(arguments)
