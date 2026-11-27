# FW-001 minimum dependency audit and candidate inputs

Date: 2026-11-27. Firmware source: `c8582405b2c3c0e3b80219b0e71e21785a482867`.
This records preparation and static analysis. It is not private input approval,
a successful firmware build, or permission to flash.

The machine-readable [audit](fw-001-dependency-audit.json) reads 2,615 tracked
files from Git objects, verifies all nine recursive gitlinks and inventories
181 build instruction files across all 25 modules. Reproduce it with
`python3 -B ci/fw001/audit-dependencies.py --source-dir PRISTINE_BASELINE --output PRIVATE_REPORT`.
It requires pristine baseline and submodule checkouts; it executes no firmware
build instructions. Generated configuration and actual link behavior still need
the offline build. A static search alone does not prove successful compilation.

| Modules | Required build inputs |
| --- | --- |
| busybox | BusyBox 1.36.1 archive; host compiler, make and cross compiler |
| dropbear | Exact DROPBEAR_2026.91 Git archive; bundled crypto, configure and cross compiler |
| ftpd | Pinned pure-ftpd Git tree; autotools and cross libc |
| h264grabber, ipc_cmd, pcmvol, proccgi, set_tz_offset | Tracked C sources and standard target headers/libraries |
| jq | jq 1.8.1 release archive with its bundled dependencies |
| mdnsd | Reviewed immutable ZIP, autotools; moving upstream master is not reproducible |
| minimp4, mjpeg-avi, mqtt, proxychains-ng, rtsp_server_yi | Pinned Git trees and local build files; mqtt links the locally built mosquitto library |
| mosquitto | Pinned 1.5.8 tree; TLS, SRV, UUID, websockets and documentation disabled by the baseline invocation |
| onvif_simple_server | Pinned tree plus libtomcrypt, mbedTLS, wolfSSL, zlib and json-c archives; default compile selects libtomcrypt and zlib, but init extracts every archive |
| rRTSPServer | fdk-aac 2.0.1, live555 2023.01.19, tracked patches/source, and a link stub built from tracked dummylib/YiAudioLibFuncs.c |
| sftp-server | Pinned OpenSSH tree and cross libc; use the baseline configure options |
| snapshot | **Additional transitive downloads found:** FFmpeg 8.1.1 and libjpeg-turbo 3.1.4.1, staged at the exact SDK/ archive filenames used by its Makefile |
| tinyalsa, wireless_tools | tinyalsa 1.0.0 and wireless-tools 29 archives |
| mqtt-config, static, www | Tracked scripts, configuration and web assets; no vendor compiler SDK |

No external MSC3XX headers, kernel build, vendor binary link library or complete
SDK installation was demonstrated as a build prerequisite. The `SDK/` directory
inside snapshot holds the two public media archives, not a vendor SDK.
MStar `/proc/.../OMX` accesses and the real OMX audio library are **runtime**
dependencies supplied by the stock system. The local rRTSPServer stub is a build
dependency. A complete successful build is still required to confirm this audit.

## Compiler and sysroot provenance

The community repack was fetched only for static inspection. Its Git blob is
`43113b97c3d65edf5603e22b84f307d99ec3621a`; observed SHA-256 is
`ae4d2dd1b18edcb236cb3f447587dea76b60ee75aba53dcba8d42deecbdf723f`.
It removes the original documentation and adds target termcap.h/libtermcap.a.
The other regular-file contents match the original Linaro package; eleven
hardlinks are represented as duplicate files. Do not use those unexplained
termcap additions. The community container remains unapproved and was not run.

The selected original is `gcc-linaro-arm-linux-gnueabihf-4.8-2014.04_linux.tar.xz`,
51,126,392 bytes, SHA-256
`2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152`.
The archive and detached signature were obtained from an
[Armbian mirror](https://mirror-us-stl1.armbian.airframes.io/dl/_toolchain/).
GnuPG accepted the original 2014-04-16 signature using full fingerprint
`873D6A08B28A5167B466D9D4D47877808F427EAF` without relaxed verification options.
The expected signing identity is corroborated by historical
[Armbian evidence](https://github.com/armbian/build/issues/2672) and the
[Armbian toolchain verification code](https://github.com/armbian/build/blob/v20.11/lib/general.sh).
The historical signature uses RSA/SHA-1; no modern signature, Web-of-Trust
certification or vendor endorsement is asserted. The former Linaro binary URL
redirects to a contact page; this limitation is retained rather than hidden.

The original README identifies Linaro GCC 4.8 2014.04, GDB 7.6.1, the matching
system root and corresponding source archive/build instructions. Compiler bytes
identify GCC `4.8.3 20140401 (prerelease)`, i686 host, arm-linux-gnueabihf target,
ARMv7/Thumb-2/hard float and eglibc 2.19-2014.04. The original manuals and license
notices are retained, including GCC GPL notices, runtime exception notices in
headers and libc LGPL notices. Use is local; no toolchain, sysroot, proprietary
stock binaries or builder archive is committed or distributed by this PR.
The builder needs 32-bit host runtime support while remaining linux/amd64.

## Archive verification

All 15 public module archives now have provenance-backed candidate SHA-256
entries. These do not automatically approve a private lock.

- live555: exact archive SHA-256 matches the independently maintained
  [Arch package record](https://github.com/archlinux/svntogit-packages/blob/d8b6ea470cc5a2a63e85435a0f94340399658a28/trunk/PKGBUILD).
- Dropbear, tinyalsa and mdnsd: every archive file, byte and executable/symlink
  mode matches a separately fetched original Git tree, with no extras or missing
  files. This authenticates source contents; it is not a separately published
  archive checksum or author signature. Exact commits, tree IDs, counts and
  digests are in [Git verification evidence](fw-001-public-git-archive-evidence.json).
- libjpeg-turbo: all 633 archived file/mode pairs match commit
  `9217719d3a58633923b096af4c1d50d304768a64`; eight excluded Git metadata files
  match that commit's explicit export-ignore rules. No omission is silently
  accepted.
- FFmpeg: detached signature verified against publisher fingerprint
  `FCF986EA15E6E293A5644F10B4322F04D67658D8`, independently stated on the
  [publisher download page](https://ffmpeg.org/download.html). Original LGPL/GPL
  source notices are retained; baseline configure selects the actual features.
- The nine previously verified archives are reused only after SHA-256 recheck.

mdnsd remains a review decision: commit
`3b1ac21b9b3a9f672793fc34f6c292d528df8ff7` is the candidate selected before the
baseline date. Its archive contents are now verified, but upstream's historical
moving-master bytes and the official release's exact mdnsd source are not proven.
That uncertainty must be included when reviewing the private lock and describing
the resulting baseline.

## Stock and reference inputs

The existing recovery attachment was downloaded again from its original
[maintainer comment](https://github.com/roleoroleo/yi-hack-MStar/issues/575#issuecomment-3492782541)
and matches the retained attachment bytes. The maintainer calls it an equivalent
rebuild, not a flash dump. There is no separately published vendor signature.
Its 211 home and 191 sys entries pass node/header/data/name CRCs, decompression,
directory resolution, path/type checks and candidate size ceilings. Both embedded
home version files equal `4.5.0.0C_201910080934`; no yi-hack subtree is present.

`ci/fw001/prepare-stock.py` writes deterministic candidate tgz archives directly
from reconstructed entries and independently rereads every payload, permission,
owner, timestamp and symlink. It never mounts a filesystem, extracts a symlink,
creates MTD devices or modifies the recovery originals. Unsupported compression,
filesystem types, flags and malformed references fail closed. Keep its reports
and all generated stock inputs private. Preparation does not grant approval.

The official y203c 0.5.8 release archive was downloaded for later comparison and
matches GitHub's publisher asset digest
`ba0432c2c238487d0e1213f587fda20b64db0562a6fd500e2622d9506d78e796`.
The semantic validator successfully reads its two real JFFS2 images and checks
model, hack version and base version. This tests the validator against actual
release images; it does not compare any newly built firmware, because there is
none yet. Partition ceilings remain the documented upstream example, not a new
measurement of the owner's camera.
