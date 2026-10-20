# SPDX-License-Identifier: MIT
"""Exercise the sealed files without requiring an existing ZIP (stdlib)."""

import csv
import hashlib
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

SERIES = Path(__file__).resolve().parents[2]
VERIFIER = "donnees/fessenheim/verifier.py"
CALCULATOR = "donnees/fessenheim/calculer-resultats.py"


def sha(content):
    return hashlib.sha256(content).hexdigest()


class DownloadVerification(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        # A freshly unpacked release deliberately does not contain itself.
        # Copy only the public sealed files, not private PDFs or local outputs.
        names = [line.split("  ", 1)[1] for line in
                 (SERIES / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines() if line]
        for name in names + ["MANIFEST.sha256"]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SERIES / name, target)

    def run_cli(self, script=VERIFIER, *args, optimized=False):
        command = [sys.executable] + (["-O"] if optimized else []) + [str(self.root / script), *args]
        return subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)

    def snapshot(self):
        return {str(p.relative_to(self.root)): sha(p.read_bytes()) for p in self.root.rglob("*")
                if p.is_file() and "out" not in p.relative_to(self.root).parts}

    def reseal(self, relative, content):
        """Test fixture only: simulate a consistent manifest with a false reference."""
        (self.root / relative).write_bytes(content)
        path = self.root / "manifest.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            rows = list(reader)
        for row in rows:
            if row["chemin"] == relative:
                row["sha256"] = sha(content)
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        path.write_bytes(stream.getvalue().encode("utf-8"))
        entries = [line.split("  ", 1)[1] for line in
                   (self.root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()]
        (self.root / "MANIFEST.sha256").write_text(
            "".join(sha((self.root / item).read_bytes()) + "  " + item + "\n" for item in entries),
            encoding="utf-8")

    def test_download_reproduces_references_without_changing_inputs(self):
        before = self.snapshot()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["pdf_sha256_checked"], [])
        self.assertEqual(len(report["pdf_not_in_local_package"]), 9)
        self.assertEqual(self.snapshot(), before)
        out = self.root / "donnees/fessenheim/out"
        for name, reference in (("resultats.json", "donnees/fessenheim/resultats.json"),
                                ("demandes.csv", "donnees/demandes.csv"),
                                ("decisions.csv", "donnees/decisions.csv")):
            self.assertEqual((out / name).read_bytes(), (self.root / reference).read_bytes())
        second = self.run_cli(CALCULATOR)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_modified_code_is_rejected_before_calculation(self):
        path = self.root / "donnees/fessenheim/codes-A.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("SHA-256", result.stderr)
        self.assertFalse((self.root / "donnees/fessenheim/out/resultats.json").exists())

    def test_missing_protocol_is_explained_by_both_entry_points(self):
        (self.root / "donnees/fessenheim/protocole-v2.json").unlink()
        for script in (VERIFIER, CALCULATOR):
            result = self.run_cli(script)
            self.assertEqual(result.returncode, 1)
            self.assertIn("protocole-v2.json", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_consistently_sealed_false_reference_fails_recalculation(self):
        path = "donnees/fessenheim/resultats.json"
        value = json.loads((self.root / path).read_text(encoding="utf-8"))
        value["R_initial"]["A"]["successes"] = 11
        self.reseal(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Recalcul different", result.stderr)

    def test_requiring_unavailable_pdf_does_not_report_success(self):
        result = self.run_cli(VERIFIER, "--avec-sources")
        self.assertEqual(result.returncode, 1)
        self.assertIn("PDF requis absents", result.stderr)

    def test_output_hardlink_cannot_overwrite_reference(self):
        reference = self.root / "donnees/fessenheim/resultats.json"
        before = reference.read_bytes()
        directory = self.root / "donnees/fessenheim/out"
        directory.mkdir(exist_ok=True)
        try:
            os.link(reference, directory / "resultats.json")
        except OSError as exc:
            self.skipTest("Filesystem cannot create hard links: " + str(exc))
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("lien physique", result.stderr)
        self.assertEqual(reference.read_bytes(), before)

    def test_optimized_python_keeps_input_validation(self):
        path = self.root / "donnees/fessenheim/codes-A.csv"
        path.write_bytes(path.read_bytes().replace(b'"M3"', b'"M9"', 1))
        result = self.run_cli(CALCULATOR, optimized=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Categorie M inconnue", result.stderr)

    def test_manifest_path_traversal_is_rejected(self):
        with (self.root / "MANIFEST.sha256").open("a", encoding="utf-8") as handle:
            handle.write("0" * 64 + "  ../outside.csv\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Chemin hors paquet", result.stderr)

    def test_archive_can_be_built_and_its_published_digest_matches(self):
        result = self.run_cli("donnees/fessenheim/fabriquer-paquet.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        archive_path = self.root / "paquet-verification.zip"
        checksum = (self.root / "paquet-verification.zip.sha256").read_text(encoding="utf-8").split()[0]
        self.assertEqual(sha(archive_path.read_bytes()), checksum)
        metadata = json.loads((self.root / "paquet-verification.zip.metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["sha256"], checksum)
        self.assertEqual(metadata["bytes"], archive_path.stat().st_size)
        with zipfile.ZipFile(archive_path) as archive:
            self.assertNotIn("paquet-verification.zip", archive.namelist())
            self.assertIsNone(archive.testzip())
            destination = self.root / "fresh-download"
            archive.extractall(destination)
        checked = subprocess.run([sys.executable, str(destination / VERIFIER)],
                                 cwd=destination, capture_output=True, text=True, timeout=30)
        self.assertEqual(checked.returncode, 0, checked.stderr)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DownloadVerification)
    runner = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0)
    result = runner.run(suite)
    print(json.dumps({"tests": result.testsRun, "failures": len(result.failures),
                      "errors": len(result.errors), "skipped": len(result.skipped),
                      "details": [text for _, text in result.failures + result.errors]},
                     ensure_ascii=True, separators=(",", ":")))
    sys.exit(0 if result.wasSuccessful() else 1)
