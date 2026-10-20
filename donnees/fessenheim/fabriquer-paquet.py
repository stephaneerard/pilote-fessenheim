# SPDX-License-Identifier: MIT
"""Build a deterministic, offline verification ZIP from the sealed public files."""

from pathlib import Path
import hashlib
import json
import sys
import zipfile
import zlib

sys.dont_write_bytecode = True
from verifier import SERIES, load_seal, safe_path, verify


def main():
    try:
        verify()
        entries = load_seal(SERIES)
        destination = SERIES / "paquet-verification.zip"
        sidecar = SERIES / "paquet-verification.zip.sha256"
        metadata_path = SERIES / "paquet-verification.zip.metadata.json"
        for target in (destination, sidecar, metadata_path):
            if target.is_symlink() or (target.exists() and target.stat().st_nlink > 1):
                raise ValueError("Sortie d'archive redirigee interdite")
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in sorted(set(entries) | {"MANIFEST.sha256"}):
                info = zipfile.ZipInfo(relative, date_time=(2026, 10, 20, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, safe_path(SERIES, relative).read_bytes())
        checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
        sidecar.write_bytes((checksum + "  paquet-verification.zip\n").encode("ascii"))
        metadata = {"sha256": checksum, "bytes": destination.stat().st_size,
                    "python": sys.version.split()[0], "zlib": zlib.ZLIB_RUNTIME_VERSION,
                    "source_manifest_sha256": hashlib.sha256((SERIES / "MANIFEST.sha256").read_bytes()).hexdigest(),
                    "files": len(entries) + 1,
                    "scope": "Exact archive bytes; a rebuild with another Python/zlib may differ."}
        metadata_path.write_bytes((json.dumps(metadata, ensure_ascii=True, indent=2) + "\n").encode("utf-8"))
        print(json.dumps({"status": "ok", "archive": str(destination),
                          "sha256": checksum, "checksum_file": str(sidecar),
                          "files": len(entries) + 1}, ensure_ascii=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=True,
                         separators=(",", ":")), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
