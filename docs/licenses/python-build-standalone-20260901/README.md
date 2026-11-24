# Pinned portable Python runtime notices

These files accompany NorthStar's CPython 3.12.14+20260901 portable runtimes for
macOS arm64/x86_64 and Windows x86_64. They preserve upstream third-party notices;
they do not change the license of NorthStar, its source, branding or user data.
No additional license grant is created by this collection.

## Origin and verification

- Repository: [Astral python-build-standalone](https://github.com/astral-sh/python-build-standalone).
- Release tag: [20260901](https://github.com/astral-sh/python-build-standalone/releases/tag/20260901).
- Resolved commit: `4bb01f09aaf362c71e891be4a41cb6d6ddf830b3`.
- Canonical source tree: `ae2ec9d36046f78d992e5cacec774e2fd2188d96`.
- All **20 root `LICENSE*` files** from that tag are copied without editing.
  Each matches the Git blob SHA-1 from the complete pinned tree. Their SHA-256
  values and exact source URLs are recorded in [PROVENANCE.json](PROVENANCE.json).
- The root GitHub inventory, resolved tag/commit/tree and exact upstream build and
  dependency metadata are preserved under [upstream-metadata](upstream-metadata/).
  Source metadata is reference text; it is not executed by the application.
- [SHA256SUMS.txt](SHA256SUMS.txt) covers every file here except itself.

The unmodified upstream `LICENSE` is the build project's MPL-2.0 text. Component
licenses are separate. Complete upstream build source remains available at the
[pinned commit](https://github.com/astral-sh/python-build-standalone/tree/4bb01f09aaf362c71e891be4a41cb6d6ddf830b3);
dependency source URLs and hashes are retained in the pinned download metadata.

## Component notice coverage

| Component or upstream family | Preserved notices |
| --- | --- |
| CPython and its included notices | `LICENSE.cpython.txt`; original runtime `LICENSE.txt` files remain in place |
| OpenSSL | `LICENSE.openssl-3.txt` and the upstream legacy `LICENSE.openssl-1.1.txt` |
| libffi | `LICENSE.libffi.txt` |
| Tcl/Tk | `LICENSE.tcl.txt`, exact Tcl 9.0.4/Tk 9.0.4 source notices, and original Windows Tk notices |
| Bundled Tcl extensions | Exact Itcl 4.3.8, Itcl documentation and Thread 3.0.6 notices; `LICENSE.tix.txt` for Windows Tix |
| Tcl internal arithmetic/compression | Exact source notices for bundled libtommath and zlib |
| Other upstream runtime dependencies | bzip2, expat, libedit, liblzma, mpdecimal, ncurses, SQLite and zlib root notices |
| Additional upstream targets/legacy dependencies | All remaining root notices, including Berkeley DB, libX11, libXau, libuuid and libxcb |
| pip and its vendored dependencies | Their original notice files remain inside each runtime; see runtime notice inventories in `PROVENANCE.json` |

The seven supplemental notices were copied byte-for-byte from Tcl 9.0.4 and Tk
9.0.4 source archives. Both archive SHA-256 values matched the exact dependency
pins in Astral's tag. These include the separate Itcl/Thread notices absent from
the root license set; no grant was inferred from the generic Tcl text.

The full pinned Astral source-tree inventory has the 20 root license files plus
`python-licenses.rst`, a combined notice document also preserved in metadata.
Its inventory spans multiple Python versions and build targets. Including all
root notices does not assert that every listed component is in these three
runtimes. The `install_only` artifacts do not contain `PYTHON.json`; retained
runtime paths and source build/dependency mappings support this notice inventory,
not a complete binary-by-binary legal determination.

## Package preservation

The install-only archives omit the outer full-distribution license directory.
The Mac archives retain CPython/pip notices but omit those outer dependency
texts; the Windows archive also retains Tk and Windows-specific Python notices.
Keep both this supplemental directory and the runtime's original notices in any
redistribution. `PROVENANCE.json` records the three exact runtime archive hashes
and the notice paths observed inside each archive. This record is provenance and
packaging documentation, not a legal opinion or a claim of vendor endorsement.
