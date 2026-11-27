# Minimal FW-001 amd64 builder

This recipe provisions host build tools and the authenticated original Linaro
compiler/sysroot. It installs no complete MSC3XX SDK, SSH server, credentials or
declared volumes. It does not compile firmware or approve private inputs.

The default base is the immutable local runtime identity of the previously
verified official Python 3.12 slim Bookworm image. Original publisher manifest:
`sha256:1475c4f5b6bcb7d35e57661d6f5d7429ec4041275633c15f2b49350ac898276d`;
config: `sha256:f4a31709c79ea38eafccf1234211e87d36625b5f9752d3df28319b43b48c0f23`.
The Docker 29 imported runtime identity is different because it identifies the
imported manifest. Its original config/layer graph was verified separately.
Do not substitute a newly observed base ID or resolve a moving registry tag.

Prepare a private build context on the dedicated distro's ext4 filesystem:

1. Obtain the exact original Linaro tar.xz and signature, check the documented
   signing fingerprint, retain notices, and independently verify provenance.
   The reviewed archive digest is pinned in the generated `hashes.txt`.
2. In the verified public base, use normal signed Debian APT metadata and
   `apt-get --download-only --no-install-recommends` to resolve the host tools.
   Retain InRelease, the complete package indexes, original Debian keyring and
   sources, package identities and every .deb on the data-backed filesystem.
   No stock inputs belong in this acquisition container. Online HTTPS package
   acquisition is separate from offline builder assembly and firmware execution.
3. Run `verify-debs.py` in that same verified base with networking disabled,
   private preparation directory bound to `/prepare` and writable `/tmp` tmpfs.
   It independently checks saved release signatures, each uncompressed package
   index against the signed release, and every package hash against its index.
   Do not disable signature, expiry, dependency or checksum checks.
4. Copy the verified `.deb` closure to `debs/`, the original compiler to
   `linaro.tar.xz`, and this Dockerfile to the context. Generate `hashes.txt` with
   the independently verified SHA-256 values and context-relative filenames.
   The executed package identities are recorded in the companion public lock.
5. Build with the exact local base already loaded, no registry pull and no
   network. The executed environment uses the classic builder:

   ```sh
   DOCKER_BUILDKIT=0 docker build --network=none --pull=false \
     --memory=8g --memory-swap=8g --cpu-period=100000 --cpu-quota=600000 \
     --tag fw001-builder:candidate PRIVATE_CONTEXT
   ```

APT's cache directory must point at the supplied package directory when using
`--no-download`; otherwise APT 2.6 can fail to locate local dependency archives.
APT retains normal dependency ordering and verification. `dpkg --audit` must be
empty before accepting the image. No force-dependency options are used.

Export with `docker save`, verify manifest/config/layer identities and each
uncompressed layer against config diff IDs, reload and record the final immutable
runtime identity and archive SHA-256. Run the ARM smoke test under the actual
FW-008 resource/isolation flags. Prepare a complete candidate input lock and
obtain independent approval before giving stock inputs to the build entrypoint.

These inputs pin the reconstruction recipe. Docker timestamps/layer metadata
are not claimed bit reproducible. Binary firmware reproducibility requires the
separate primary and independent clean firmware builds.


The executed image needs the separate `Dockerfile.pathfix` derivation so the
strict compiler PATH resolves Debian's /usr/sbin/mkfs.jffs2. Build the original
recipe first, verify its pinned identity, then derive with that file offline.
The approved derivation adds only the symlink to the already verified packer;
no package or executable byte is added. See the execution report for both image
identities, archive digests and the explicit owner approval of the derived lock.
