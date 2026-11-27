# FW-001 — SDK and cross-toolchain provenance investigation

Date: 2026-11-27. Decision: **do not approve the legacy community image as the builder**.
This is a static source/metadata investigation, not an executed SDK audit.

## Community builder

The upstream yi-hack-MStar README recommends the community
[borodiliz/yi-hack image](https://hub.docker.com/r/borodiliz/yi-hack).
Docker Hub lists the latest tag as approximately 621 MB and over six years old.
The source repository has two visible commits, the latest dated 2020-04-02:
[0ffa72308c549f2c0fb96d5c88808debe8a4d77e](https://github.com/borodiliz/docker-yi-hack/commit/0ffa72308c549f2c0fb96d5c88808debe8a4d77e).

Reviewed [Dockerfile at that commit](https://github.com/borodiliz/docker-yi-hack/blob/0ffa72308c549f2c0fb96d5c88808debe8a4d77e/Dockerfile)
(Git blob b75d46fbb5492f586ccdf4f5aaad8f014c0807a1):

- Uses i386/ubuntu:19.10, an obsolete host base, rather than the required linux/amd64.
- Installs SSH, sets a known root password, enables root login, exposes port 22,
  and declares /root/.ssh and /yi-hack-src volumes.
- Copies the repository's files/root tree and extracts a bundled cross-toolchain.
- Uses unpinned apt packages, pip cstruct and a moving Jefferson Git checkout.
- Adds amd64 libc to an i386 base for kernel-build dependencies.
- Does not show a separate complete MSC3XX SDK installation.
- No LICENSE file was available at the repository root from the contents API.
  This does not establish that individual archive components lack licenses.

The documented usage mounts the user's SSH directory into the container.
Do not follow that usage. FW-008 rejects non-amd64 images and declared volumes;
do not relax those gates. The registry manifest, actual layers and image
configuration were not retrieved, and linkage from the published image to this
Dockerfile was not verified. The tag is not approved; no image was executed.

## Exact toolchain archive candidate

The initial source commit
[3a904f002a22a3abdb86c1128fee29510231a33d](https://github.com/borodiliz/docker-yi-hack/commit/3a904f002a22a3abdb86c1128fee29510231a33d)
contains the following archive, also referenced by the latest Dockerfile:

- [arm-linux-gnueabihf-4.8.3-201404.tar.gz, pinned source location](https://github.com/borodiliz/docker-yi-hack/blob/0ffa72308c549f2c0fb96d5c88808debe8a4d77e/files/root/opt/yi/arm-linux-gnueabihf-4.8.3-201404.tar.gz)
- Git blob ID: `43113b97c3d65edf5603e22b84f307d99ec3621a`.
- Status: **candidate only**. The GitHub contents API returned no archive bytes
  (empty base64 content). The blob ID is not an independently published SHA-256,
  a vendor signature, evidence of archive licensing, or proof of compatibility.
  No archive was downloaded or executed.

Do not populate the private input lock from the blob ID or from an observed
download hash alone. GCC's open-source license does not automatically establish
the license of all bundled libraries, headers or vendor additions.

## Is the full vendor SDK actually necessary?

Pinned upstream firmware source: c8582405b2c3c0e3b80219b0e71e21785a482867.

Static review of these files shows:
- [scripts/compile.sh](https://github.com/roleoroleo/yi-hack-MStar/blob/c8582405b2c3c0e3b80219b0e71e21785a482867/scripts/compile.sh)
  adds the specific compiler directory and builds each userspace module.
- [scripts/init_sysroot.sh](https://github.com/roleoroleo/yi-hack-MStar/blob/c8582405b2c3c0e3b80219b0e71e21785a482867/scripts/init_sysroot.sh)
  initializes the device filesystem from stock archives; it does not build a kernel.
- [src/rRTSPServer/init.rRTSPServer](https://github.com/roleoroleo/yi-hack-MStar/blob/c8582405b2c3c0e3b80219b0e71e21785a482867/src/rRTSPServer/init.rRTSPServer)
  and [src/ftpd/init.ftpd](https://github.com/roleoroleo/yi-hack-MStar/blob/c8582405b2c3c0e3b80219b0e71e21785a482867/src/ftpd/init.ftpd)
  explicitly depend on the compiler's libc include/library layout.
- [ONVIF CMake toolchain](https://github.com/roleoroleo/yi-hack-MStar/blob/c8582405b2c3c0e3b80219b0e71e21785a482867/src/onvif_simple_server/arm-linux-gnueabihf-toolchain.cmake)
  names that same libc directory as the CMake sysroot.
- [scripts/pack_fw.sh](https://github.com/roleoroleo/yi-hack-MStar/blob/c8582405b2c3c0e3b80219b0e71e21785a482867/scripts/pack_fw.sh)
  uses the matching strip and mkfs.jffs2 to package home/sys images.

**Hypothesis:** a properly licensed, authenticated cross-toolchain with the
matching sysroot and stock files may suffice without a complete proprietary SDK.
This is not yet proven: review all module scripts, makefiles, generated build
files and recursive submodules for vendor headers/libraries, then demonstrate a
full offline build and compare ABI against known stock userspace. Preserve
existing FW-001 acceptance criteria until independently reviewed evidence
justifies a scope change.

## Alternative routes and limitations

- [linux-chenxing](https://linux-chenxing.org/) explicitly identifies itself as
  unofficial and reports vendor assistance requires an NDA and project; it
  recommends sharing permissively licensed subsets rather than full SDKs.
- [OpenIPC MStar status](https://openipc.org/cameras/vendors/mstar?locale=en)
  reports no ready installable MStar build. OpenIPC's public
  [MSC313E U-Boot project](https://github.com/OpenIPC/u-boot-msc313e) documents
  the same compiler directory name, but that does not authenticate the archive
  or prove a toolchain or complete camera image is interchangeable.
- [OpenIPC QEMU research](https://github.com/OpenIPC/qemu-bench/blob/master/docs/sigmastar.md)
  identifies the I3 SDK variant MSC3XX_SDK_V_1711291828-I3 in its research.
  This is a provenance lead, not permission to download or redistribute it.
- The upstream README warns the I1 SDK is incompatible with the camera's
  proprietary OMX libraries. Do not assume another SigmaStar SDK works.

## Next steps / gates

1. Establish a lawful and authenticated source for the exact compiler and
   required sysroot components, preferably via the original maintainer/vendor;
   retain license notices, applicable corresponding source information and
   independent digest/identity evidence outside Git as necessary.
2. Complete a static dependency audit of the pinned firmware tree/submodules.
   Compare compiler host ELF architecture, target triplet, GCC/binutils version,
   target libc/loader, ARM attributes and symbol versions with verified stock
   userspace. A filename or matching GCC major version is not sufficient.
3. If the minimum component set is sufficient, prepare a new reviewed amd64
   builder on a maintained, digest-pinned base, with pinned package provenance.
   Install only required tools, no SSH service, no volumes, no secrets. Check
   whether the legacy compiler requires 32-bit host compatibility libraries.
   Keep compiler inputs private until licensing permits distribution.
4. Review the resulting builder archive and private lock independently, then
   use existing FW-008/FW-001 offline isolation, ARM smoke test and full/repeat
   build. Retain 6 CPU, 8 GiB and alternate-disk constraints.
5. Four public archive digests and verified stock archives still remain
   separate blockers. No flash or release until the roadmap gates pass.

No runtime tests, SDK download, OCI pull, firmware build, or camera operation
were performed in this investigation. No builder identity or digest was approved.

## Accepted scope decision (2026-11-27)

FW-001 now requires the verified minimum toolchain/sysroot and any demonstrably needed vendor components, rather than acquisition of a full MSC3XX SDK. The owner approved this scope change. The hypothesis of SDK-free compilation remains untested; dependency audit, independent input approval, actual baseline and repeat builds, and all artifact/ABI/security gates remain mandatory. Earlier execution reports describe the historical scope and are not rewritten.
