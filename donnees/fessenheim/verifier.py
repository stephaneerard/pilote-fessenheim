# SPDX-License-Identifier: MIT
"""Offline integrity and byte-for-byte reproduction check. Python 3.9+, stdlib."""

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SERIES = ROOT.parent.parent
PREFIX = "donnees/fessenheim/"
EXPECTED_INPUTS = {
    PREFIX + name for name in (
        "calculer-resultats.py", "protocole-v2.json", "registre-demandes-v2.csv",
        "codes-A.csv", "codes-B.csv", "suivi-S-A.csv", "suivi-S-B.csv",
        "schemas-registres.json",
    )
}
REFERENCES = {
    "resultats.json": PREFIX + "resultats.json",
    "demandes.csv": "donnees/demandes.csv",
    "decisions.csv": "donnees/decisions.csv",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root, relative):
    if not relative or "\\" in relative:
        raise ValueError("Chemin relatif invalide : " + relative)
    part = Path(relative)
    if part.is_absolute() or ".." in part.parts:
        raise ValueError("Chemin hors paquet : " + relative)
    target = root / part
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Lien hors paquet : " + relative)
    return target


def load_seal(root):
    entries = {}
    for line in (root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        fields = line.split("  ", 1)
        if len(fields) != 2 or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
            raise ValueError("Ligne MANIFEST.sha256 invalide")
        checksum, relative = fields
        safe_path(root, relative)
        if relative in entries:
            raise ValueError("Empreinte dupliquee : " + relative)
        entries[relative] = checksum
    if "manifest.csv" not in entries:
        raise ValueError("Le manifeste CSV doit etre couvert par MANIFEST.sha256")
    for relative, checksum in entries.items():
        path = safe_path(root, relative)
        if not path.is_file():
            raise ValueError("Fichier requis absent : " + relative)
        if digest(path) != checksum:
            raise ValueError("SHA-256 different : " + relative)
    return entries


def verify(root=SERIES, require_sources=False):
    root = root.resolve()
    sealed = load_seal(root)
    with (root / "manifest.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    local = {}
    source_rows = []
    manifest_descriptors = set()
    ids = set()
    for row in rows:
        if row["id"] in ids:
            raise ValueError("Identifiant de manifeste duplique : " + row["id"])
        ids.add(row["id"])
        relative = row["chemin"]
        safe_path(root, relative)
        if row["type"] == "manifeste":
            if relative not in {"manifest.csv", "MANIFEST.sha256"} or row["sha256"]:
                raise ValueError("Descriptor de manifeste invalide : " + relative)
            manifest_descriptors.add(relative)
            continue
        if row["type"] == "source_pdf":
            source_rows.append(row)
            continue
        if relative in local:
            raise ValueError("Chemin de manifeste duplique : " + relative)
        local[relative] = row
    if manifest_descriptors != {"manifest.csv", "MANIFEST.sha256"}:
        raise ValueError("Les deux manifestes doivent etre decrits explicitement")
    if {row["id"] for row in source_rows} != {"F%02d" % i for i in range(1, 10)}:
        raise ValueError("Les neuf PDF F01 a F09 doivent figurer dans le manifeste")
    if any(not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) for row in source_rows):
        raise ValueError("Empreinte de source PDF invalide")
    if set(sealed) != set(local) | {"manifest.csv"}:
        raise ValueError("Desaccord entre manifest.csv et MANIFEST.sha256")
    required = EXPECTED_INPUTS | set(REFERENCES.values()) | {PREFIX + "verifier.py"}
    if not required.issubset(local):
        raise ValueError("Dependances absentes du manifeste : " + ", ".join(sorted(required - set(local))))
    for relative, row in local.items():
        if row["sha256"] != sealed[relative]:
            raise ValueError("Empreintes contradictoires : " + relative)
    checked_sources, missing_sources = [], []
    for row in source_rows:
        path = safe_path(root, row["chemin"])
        if not path.is_file():
            missing_sources.append(row["id"])
        elif digest(path) != row["sha256"]:
            raise ValueError("PDF present mais SHA-256 different : " + row["id"])
        else:
            checked_sources.append(row["id"])
    if require_sources and missing_sources:
        raise ValueError("PDF requis absents : " + ", ".join(missing_sources))
    spec = importlib.util.spec_from_file_location("fessenheim_calculation", root / PREFIX / "calculer-resultats.py")
    calculator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calculator)
    declared = {PREFIX + name for name in calculator.INPUT_FILES} | {PREFIX + "calculer-resultats.py"}
    if declared != EXPECTED_INPUTS:
        raise ValueError("Dependances du calcul modifiees : mettre a jour le verificateur et le manifeste")
    outputs = calculator.build_outputs()
    for name, reference in REFERENCES.items():
        if outputs[name] != safe_path(root, reference).read_bytes():
            raise ValueError("Recalcul different de la reference publiee : " + reference)
    directory = calculator.write_outputs(outputs)
    # Check again after computation: neither code path may alter a sealed file.
    for relative, checksum in sealed.items():
        if digest(safe_path(root, relative)) != checksum:
            raise ValueError("Source modifiee pendant le calcul : " + relative)
    report = {
        "status": "ok", "python": sys.version.split()[0],
        "sealed_files_checked": len(sealed),
        "references_identical_byte_for_byte": list(REFERENCES),
        "sources_modified": False,
        "pdf_sha256_checked": checked_sources,
        "pdf_not_in_local_package": missing_sources,
        "pdf_required": require_sources,
        "scope": "Integrity and calculation only; not a new independent coding or source-availability audit.",
    }
    target = directory / "verification.json"
    if target.is_symlink() or (target.exists() and target.stat().st_nlink > 1):
        raise ValueError("Rapport de verification redirige interdit")
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--avec-sources", action="store_true", help="Exiger aussi les neuf PDF aux chemins du manifeste")
    args = parser.parse_args()
    try:
        report = verify(require_sources=args.avec_sources)
    except (OSError, ValueError, KeyError, AssertionError, csv.Error) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=True,
                         separators=(",", ":")), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
