"""Observe only a uniquely labelled FW-008 build; never execute target code."""
import json
import math
from pathlib import Path
import re
import subprocess
import threading
import time


def call(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=8).strip()


def memory_bytes(value):
    match = re.fullmatch(r'([0-9.]+)\s*([A-Za-z]+)', value.strip())
    units = {'B': 1, 'kB': 1000, 'KB': 1000, 'MB': 1000**2, 'GB': 1000**3,
             'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3}
    if not match or match[2] not in units:
        raise ValueError('Unknown memory unit')
    return int(float(match[1]) * units[match[2]])


INSIDE = '''import json,os,socket,subprocess
from pathlib import Path
if not Path('/work/guards/nproc').is_file():raise SystemExit(3)
c=Path('/sys/fs/cgroup');s=dict(x.split(':',1) for x in Path('/proc/self/status').read_text().splitlines() if ':' in x)
blocked=False
try:socket.create_connection(('1.1.1.1',443),timeout=1).close()
except OSError:blocked=True
guard=subprocess.run(['bash','-c','source /inputs/download-guard.sh; install_download_guard /work/fw001-observation-guards /work/fw001-observation-marker; /work/fw001-observation-guards/wget https://example.invalid || true; check_download /work/fw001-observation-marker'],capture_output=True)
print(json.dumps(dict(cpu_max=(c/'cpu.max').read_text().strip(),affinity_cpu_count=len(os.sched_getaffinity(0)),memory_max=int((c/'memory.max').read_text()),memory_swap_max=int((c/'memory.swap.max').read_text()),interfaces=sorted(x.name for x in Path('/sys/class/net').iterdir()),external_connection_blocked=blocked,no_new_privileges=s['NoNewPrivs'].strip(),seccomp=s['Seccomp'].strip(),cap_eff=s['CapEff'].strip(),nproc=subprocess.check_output(['/work/guards/nproc'],text=True).strip(),native_nproc=subprocess.check_output(['nproc'],text=True).strip(),makeflags=os.environ.get('MAKEFLAGS'),download_guard_rejected=guard.returncode!=0 and Path('/work/fw001-observation-marker').exists(),real_unexpected_download_marker_absent=not Path('/work/unexpected-download').exists(),mtd_devices_absent=not list(Path('/dev').glob('mtd*')))))'''


def valid_runtime(row, cpus, memory_gib):
    if not isinstance(row, dict) or not isinstance(row.get('runtime'), dict):
        return False
    runtime = row['runtime']
    if any(type(runtime.get(k)) is not int for k in ('affinity_cpu_count','memory_max','memory_swap_max')):
        return False
    return (row.get('network') == 'none' and row.get('readonly_root') is True
            and row.get('readonly_inputs') is True
            and runtime.get('cpu_max') == f'{cpus * 100000} 100000'
            and runtime.get('affinity_cpu_count') == cpus
            and runtime.get('memory_max') == memory_gib * 1024**3
            and runtime.get('memory_swap_max') == 0
            and runtime.get('interfaces') == ['lo']
            and runtime.get('external_connection_blocked') is True
            and runtime.get('no_new_privileges') == '1' and runtime.get('seccomp') == '2'
            and runtime.get('cap_eff') == '000000000000000b'
            and runtime.get('nproc') == '1' and runtime.get('makeflags') == '-j1'
            and runtime.get('download_guard_rejected') is True
            and runtime.get('real_unexpected_download_marker_absent') is True
            and runtime.get('mtd_devices_absent') is True
            and type(row.get('samples')) is int and row['samples'] > 0)


def valid_observations(rows, key, token):
    """Exactly one sampled build container, tied to the output's observation ID."""
    if (not isinstance(rows, list) or len(rows)!=1 or not isinstance(token, str)
            or not re.fullmatch(r'[0-9a-f]{32}', token)):
        return False
    row = rows[0]
    if not valid_runtime(row, key['cpus'], key['memory_gib']):
        return False
    if row.get('observation_id') != token or row.get('image') != key['image']:
        return False
    for name in ('peak_cpu_percent','peak_memory_bytes','peak_workspace_apparent_bytes'):
        value = row.get(name)
        if (type(value) not in (int,float) or (type(value) is float and not math.isfinite(value))
                or not 0<=value<=2**63-1):
            return False
    return True


class Observer:
    def __init__(self, token, image, stage_root):
        self.token, self.image, self.stage_root = token, image, stage_root
        self.rows, self.paths = {}, {}
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.observe, daemon=True)

    def start(self):
        self.thread.start()

    def finish(self):
        self.stop.set()
        self.thread.join(timeout=40)
        if self.thread.is_alive():
            raise RuntimeError('Resource observer did not stop')
        return list(self.rows.values())

    def observe(self):
        while not self.stop.is_set():
            try:
                ids = call('docker', 'ps', '--filter', 'label=local.fw001.observation=' + self.token,
                           '--no-trunc', '--format', '{{.ID}}').split()
                for cid in ids:
                    if cid not in self.rows:
                        info = json.loads(call('docker', 'inspect', cid))[0]
                        work = next(m['Source'] for m in info['Mounts'] if m['Destination'] == '/work')
                        if (info['Config']['Image'] != self.image
                                or info['Config'].get('Labels', {}).get('local.fw001.observation') != self.token
                                or not work.startswith(str(self.stage_root) + '/fw008-')):
                            continue
                        self.paths[cid] = work
                        input_mounts = [m for m in info['Mounts'] if m['Destination'] == '/inputs']
                        self.rows[cid] = dict(observation_id=self.token, image=self.image,
                            samples=0, peak_cpu_percent=0, peak_memory_bytes=0,
                            peak_workspace_apparent_bytes=0, network=info['HostConfig']['NetworkMode'],
                            readonly_root=info['HostConfig']['ReadonlyRootfs'],
                            readonly_inputs=len(input_mounts)==1 and input_mounts[0]['RW'] is False,
                            runtime=json.loads(call('docker', 'exec', cid, 'python3', '-c', INSIDE)))
                    row = self.rows[cid]
                    sample = json.loads(call('docker', 'stats', '--no-stream', '--format', '{{json .}}', cid))
                    cpu = float(sample['CPUPerc'].rstrip('%'))
                    memory = memory_bytes(sample['MemUsage'].split('/')[0])
                    workspace = int(call('du', '-sb', self.paths[cid]).split()[0])
                    if not math.isfinite(cpu) or min(cpu, memory, workspace)<0:
                        continue
                    row['samples'] += 1
                    row['peak_cpu_percent'] = max(row['peak_cpu_percent'], cpu)
                    row['peak_memory_bytes'] = max(row['peak_memory_bytes'], memory)
                    row['peak_workspace_apparent_bytes'] = max(row['peak_workspace_apparent_bytes'], workspace)
            except (subprocess.SubprocessError, OSError, ValueError, KeyError, StopIteration):
                pass
            self.stop.wait(2)
