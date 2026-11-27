# FW-008 bootstrap evidence — 2026-11-27

Tested commit `0cfa88b5985664c7ad9109603bf7ded41b031dea` in Linux/Python 3.13.5. Direct GitHub networking and Docker were unavailable in the execution sandbox. The tested files were reconstructed from connector responses; each Git blob SHA was calculated locally and checked against the connector's exact commit. All eight matched.

| File | Git blob SHA |
| --- | --- |
| ci/fw008/manual-build.py | 0e3db3b6811be2a22089874eb4666de3d6d25994 |
| ci/fw008/input-inventory.json | c86b7849a242d4f69bd9f8696e767e70d4e245bc |
| ci/fw008/test_bootstrap.py | f6188288d7bdc1ca998eccabc640279ebc5cc784 |
| ci/fw008/baseline_aliases.py | 105cdc19c8e8bbcce8fb1b05a96f54078f9bbd21 |
| ci/fw008/test_aliases.py | 0039786994e736b5890ba25e24d47f3d7efb5272 |
| ci/fw008/build-offline.sh | 53208f9cba8c1b80fdb58c8a0196a659686adfe6 |
| ci/fw008/download-guard.sh | d99b1894572bfbf155207d518c19adf6cec7bc59 |
| .github/workflows/fw008-manual-build.yml | 2cd105a9ea2dfbab5b88a08a4eb956b0bd9b3e5c |

## Executed results

- `python3 -B -m unittest discover -s ci/fw008 -p 'test_*.py' -v`: **9/9 passed**, 0.051 s.
- `bash -n ci/fw008/build-offline.sh`, `bash -n ci/fw008/download-guard.sh`: passed.
- Workflow parsed with PyYAML BaseLoader; asserted only workflow_dispatch, contents: read, and full-length action SHA pins. GitHub-specific actionlint not installed.
- Public preflight: exit 0; 17 input entries (13 public archives, four local/source/builder inputs); seven published candidate archive digests.
- Hosted full: exit 1, expected fail-closed; no firmware generated.
- Synthetic alias tests: actual archive alias, digest tamper rejection and collision rejection passed.
- Download guard: wget was blocked; ignored wget exit still resulted in phase guard failure.
- Synthetic verified staging, missing input, unapproved ref/lock, traversal and Docker command flag checks passed.

## Remaining

Actual public downloads have not been byte-verified. Six public archive digests and all private/source/builder inputs are still unresolved. The selected mdnsd commit is a historical candidate, not proof of original release build contents. No SDK installed, private stock extraction performed, full Docker isolation tested, firmware compiled, or hosted workflow dispatched. Full baseline build is FW-001; hosted dispatch and real isolation evidence remain FW-008 acceptance checks. No device modifications.
