import copy
import unittest
import resource_observer as observer


class ObserverTests(unittest.TestCase):
    def test_effective_limits_and_security_are_required(self):
        row = dict(network='none', readonly_root=True, readonly_inputs=True, samples=1,
            runtime=dict(cpu_max='600000 100000', affinity_cpu_count=6, memory_max=8 * 1024**3,
                memory_swap_max=0, interfaces=['lo'], external_connection_blocked=True,
                no_new_privileges='1', seccomp='2', cap_eff='000000000000000b',
                nproc='1', makeflags='-j1', download_guard_rejected=True,
                real_unexpected_download_marker_absent=True, mtd_devices_absent=True))
        self.assertTrue(observer.valid_runtime(row, 6, 8))
        for key, value in [('memory_swap_max', 1), ('nproc', '6'), ('interfaces', ['lo', 'eth0']),
                           ('download_guard_rejected', False), ('cap_eff', '0000000000000000')]:
            changed = copy.deepcopy(row)
            changed['runtime'][key] = value
            self.assertFalse(observer.valid_runtime(changed, 6, 8), key)
        self.assertFalse(observer.valid_runtime({**row, 'samples': 0}, 6, 8))

    def test_docker_units(self):
        self.assertEqual(observer.memory_bytes('2 MiB'), 2 * 1024**2)
        self.assertEqual(observer.memory_bytes('2MB'), 2000000)
        with self.assertRaises(ValueError):
            observer.memory_bytes('unknown')
