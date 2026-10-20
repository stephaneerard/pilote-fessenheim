# SPDX-License-Identifier: MIT
"""Recalculate the pilot without modifying published inputs (stdlib only).

Run with Python 3.9+: python calculer-resultats.py (outputs go to out/).
No adjudicated data are read. Unknown values are missing, not ordinal ranks.
Two-coder ordinal alpha follows Krippendorff's cumulative marginal metric.
"""

import collections
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT_FILES = (
    "protocole-v2.json", "registre-demandes-v2.csv", "codes-A.csv", "codes-B.csv",
    "suivi-S-A.csv", "suivi-S-B.csv", "schemas-registres.json",
)


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def require(condition, message="Validation des donnees ou de l'algorithme echouee"):
    if not condition:
        raise ValueError(message)


def alpha_two(pairs, ordinal=False):
    """Return alpha and its components; singleton/missing units are excluded."""
    total = len(pairs)
    known = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not known:
        return {"alpha": None, "reason": "no_jointly_known_units", "units": 0,
                "coverage": 0 if total else None, "observed_disagreement": None,
                "expected_disagreement": None, "raw_agreement": None}
    counts = collections.Counter(value for pair in known for value in pair)
    categories = sorted(counts)

    def distance(a, b):
        if a == b:
            return 0
        if not ordinal:
            return 1
        low, high = sorted((a, b))
        cumulative = sum(counts[c] for c in categories if low <= c <= high)
        return (cumulative - (counts[low] + counts[high]) / 2) ** 2

    n = sum(counts.values())
    observed = sum(distance(a, b) for a, b in known) / len(known)
    expected = sum(counts[a] * counts[b] * distance(a, b)
                   for a in categories for b in categories) / (n * (n - 1))
    return {
        "alpha": None if expected == 0 else 1 - observed / expected,
        "reason": "zero_expected_disagreement" if expected == 0 else None,
        "units": len(known), "coverage": len(known) / total,
        "observed_disagreement": observed, "expected_disagreement": expected,
        "raw_agreement": sum(a == b for a, b in known) / len(known),
        "marginals": dict(counts),
    }


def fraction_report(rows, state_field, success):
    counts = collections.Counter(row[state_field] for row in rows)
    n = len(rows)
    positive = sum(v for k, v in counts.items() if k in success)
    unknown = counts.get("U", 0)
    return {"n": n, "distribution": dict(sorted(counts.items())),
            "successes": positive, "unknown": unknown,
            "lower": positive / n if n else None,
            "upper": (positive + unknown) / n if n else None}


def self_check():
    # Published binary example: Krippendorff, Computing Alpha, pp. 2-3.
    a = [0, 1, 0, 0, 0, 0, 0, 0, 1, 0]
    b = [1, 1, 1, 0, 0, 1, 0, 0, 0, 0]
    require(math.isclose(alpha_two(list(zip(a, b)))["alpha"], 2 / 21))
    require(alpha_two([(0, 0), (1, 1)], ordinal=True)["alpha"] == 1)
    require(alpha_two([(1, 1), (1, 1)])["alpha"] is None)
    require(math.isclose(alpha_two([(0, 1), (0, 1), (1, 0), (1, 0)])["alpha"], -.75))
    check = alpha_two([(0, None), (0, 0), (1, 1)])
    require(check["units"] == 2 and math.isclose(check["coverage"], 2 / 3))


def build_outputs():
    """Read frozen inputs and return bytes; never write an input or reference."""
    self_check()
    missing = [name for name in INPUT_FILES if not (ROOT / name).is_file()]
    if missing:
        raise ValueError("Fichiers requis absents : " + ", ".join(missing))
    protocol = json.loads((ROOT / "protocole-v2.json").read_text(encoding="utf-8"))
    registry = read_csv("registre-demandes-v2.csv")
    require(hashlib.sha256((ROOT / "registre-demandes-v2.csv").read_bytes()).hexdigest() == protocol["registry_sha256"], "Empreinte du registre differente du gel")
    ids = [row["demande_id"] for row in registry]
    require(len(ids) == len(set(ids)) == 22, "Le registre doit contenir 22 identifiants uniques")
    coders = {}
    hashes = {}
    for coder in ("A", "B"):
        filename = "codes-%s.csv" % coder
        rows = read_csv(filename)
        require(len(rows) == 22 and {row["demande_id"] for row in rows} == set(ids), "Registre incomplet pour " + coder)
        require(all(row["codeur_id"] == coder for row in rows), "Identifiant du codeur incoherent")
        require(all(row["motivation"] in {"M0", "M1", "M2", "M3", "M4", "U"} for row in rows), "Categorie M inconnue")
        coders[coder] = {row["demande_id"]: row for row in rows}
        hashes[filename] = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
    pairs = [(None if coders["A"][i]["motivation"] == "U" else int(coders["A"][i]["motivation"][1]),
              None if coders["B"][i]["motivation"] == "U" else int(coders["B"][i]["motivation"][1])) for i in ids]
    ordinal = alpha_two(pairs, ordinal=True)
    binary = alpha_two([(None if a is None else int(a >= 3),
                         None if b is None else int(b >= 3)) for a, b in pairs])
    matrix = collections.Counter((coders["A"][i]["motivation"], coders["B"][i]["motivation"]) for i in ids)
    pass_gate = (ordinal["alpha"] is not None and
                 ordinal["alpha"] >= protocol["reliability"]["threshold"] and
                 ordinal["coverage"] >= protocol["reliability"]["minimum_joint_coverage"])
    result = {
        "schema_version": "2.0", "scope": protocol["scope"],
        "registry_sha256": protocol["registry_sha256"],
        "raw_file_hashes": hashes,
        "R_initial": {c: fraction_report(list(coders[c].values()), "motivation", {"M3", "M4"}) for c in coders},
        "R_by_request_type": {kind: {c: fraction_report(
            [row for key, row in coders[c].items() if key.startswith(prefix)],
            "motivation", {"M3", "M4"}) for c in coders}
            for kind, prefix in (("clarifications", "FES-1."), ("participation", "FES-2."))},
        "agreement_before_arbitration": {"ordinal": ordinal, "binary": binary,
            "matrix": [{"A": a, "B": b, "n": n} for (a, b), n in sorted(matrix.items())],
            "disagreements": [i for i in ids if coders["A"][i]["motivation"] != coders["B"][i]["motivation"]]},
        "gate": {"alpha_threshold": protocol["reliability"]["threshold"],
                 "coverage_threshold": protocol["reliability"]["minimum_joint_coverage"],
                 "passed": pass_gate,
                 "binary_secondary_below_threshold": binary["alpha"] is None or binary["alpha"] < protocol["reliability"]["threshold"],
                 "consequence": "exploratory_gate_passed_not_external_validation" if pass_gate else "no_stabilized_pooled_score"},
    }
    result["R_legal"] = {"publication_in_time": {"numerator": 1, "denominator": 1,
        "bilan": "2025-04-07", "deadline": "2025-07-07", "publication": "2025-07-07",
        "elapsed_days": 91, "sources": ["F03", "CNDP chronology"]},
        "scope": "Documentary check of publication and deadline only; remaining statutory requirements have their own entries in regles-juridiques.csv. No general legal compliance verdict."}
    s_rows = {}
    expected_keys = {(j, h, regime) for j in ("S01", "S02", "S03")
                     for h in ("6", "12") for regime in ("contemporain", "retrospectif")}
    for coder in ("A", "B"):
        filename = "suivi-S-%s.csv" % coder
        rows = read_csv(filename)
        require(len(rows) == 12 and all(row["codeur_id"] == coder for row in rows), "Suivi S incomplet ou codeur incoherent")
        keyed = {(row["jalon_id"], row["horizon_mois"], row["regime"]): row for row in rows}
        require(set(keyed) == expected_keys and len(keyed) == 12, "Cles du suivi S incompletes ou dupliquees")
        s_rows[coder] = keyed
        result["raw_file_hashes"][filename] = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
    result["S_installation"] = []
    for horizon in ("6", "12"):
        for regime in ("contemporain", "retrospectif"):
            group = {}
            for coder in ("A", "B"):
                rows = [s_rows[coder][(j, horizon, regime)] for j in ("S01", "S02", "S03")]
                require(all(row["etat"] in {"realise", "partiel", "absent", "U"} for row in rows), "Etat S inconnu")
                group[coder] = fraction_report(rows, "etat", {"realise"})
            state_pairs = [(s_rows["A"][(j, horizon, regime)]["etat"],
                            s_rows["B"][(j, horizon, regime)]["etat"]) for j in ("S01", "S02", "S03")]
            known_pairs = [(None if a == "U" else a, None if b == "U" else b) for a, b in state_pairs]
            result["S_installation"].append({"horizon_mois": int(horizon), "regime": regime,
                "coders": group, "agreement_nominal": alpha_two(known_pairs),
                "raw_agreement_including_joint_unknowns": sum(a == b for a, b in state_pairs) / 3})
    result["E"] = {"scope": "Trois jalons de concertation du pilote seulement",
                   "established_eligible_obligations": 0, "value": None,
                   "status": "NA", "reason": "Aucune obligation favorable opposable devenue exigible etablie pour ces trois jalons ; ne constitue pas un inventaire juridique de tout le projet."}
    # Consolidated registers retain the original independent codes, not a consensus.
    schemas = json.loads((ROOT / "schemas-registres.json").read_text(encoding="utf-8"))
    demand_fields = schemas["demandes.csv"]
    demand_rows = []
    request_registry = {row["demande_id"]: row for row in registry}
    source_response = "https://www.debatpublic.fr/sites/default/files/2025-07/PTF-Bilan-et-enseignements-EDF.pdf"
    source_request = "https://www.debatpublic.fr/sites/default/files/2025-04/CNDP-Fessenheim_CR.pdf"
    for coder in ("A", "B"):
        for key in ids:
            raw = coders[coder][key]
            unit = request_registry[key]
            row = {field: "" for field in demand_fields}
            row.update({"demande_id": key, "dossier_id": "C10", "codeur_id": coder,
                "version_manuel": "2.0", "horizon_mois": "3",
                "source_demande_url": source_request,
                "repere_demande": "PDF p.%s ; section 4 ; n.%s" % (unit["page_pdf"], unit["reference_cr"]),
                "initiateur_categorie": "CPDP_synthese_du_public", "destinataire": "EDF",
                "objet": unit["theme"], "portee": "clarification" if key.startswith("FES-1.") else "participation",
                "source_reponse_url": source_response, "repere_reponse": "PDF p." + raw["pages_pdf_reponse"],
                "date_publication_reponse": "2025-07-07",
                "base_delai": "Photographie initiale ; le delai legal de publication de l'acte est controle separement, pas impose a chaque demande par le manuel.",
                "presence": raw["presence"], "delai": "NA", "motivation": raw["motivation"],
                "raison_code": raw["justification"] + " Limite : " + raw["limite"],
                "statut_arbitrage": "initial"})
            demand_rows.append(row)
    decision_fields = schemas["decisions.csv"]
    for field in ("regime_preuve", "perimetre"):
        if field not in decision_fields:
            decision_fields.append(field)
    source_urls = {
        "F06": "https://www.debatpublic.fr/sites/default/files/2026-08/CC%20Technocentre%20Bilan%20interm%C3%A9diaire%2010%20ao%C3%BBt.pdf",
        "F07": "https://www.debatpublic.fr/sites/default/files/2026-01/EDF%20Cyclife%20Technocentre_dispositif%20de%20concertation_note%20CNDP%20de%CC%81cembre%202025.pdf",
    }
    decision_rows = []
    for coder in ("A", "B"):
        for key, raw in sorted(s_rows[coder].items()):
            source_id = "F06" if raw["regime"] == "retrospectif" else "F07"
            row = {field: "" for field in decision_fields}
            row.update({"decision_id": raw["jalon_id"], "dossier_id": "C10",
                "demande_id": "FES-2.6" if raw["jalon_id"] == "S01" else "FES-2.1",
                "codeur_id": coder, "version_manuel": "2.0-S", "horizon_mois": raw["horizon_mois"],
                "source_acte_url": "https://www.debatpublic.fr/sites/default/files/2025-07/PTF-Decision-EDF.pdf",
                "repere_acte": "PDF p.14 ; modalites precisees par F07",
                "objet": raw["jalon_id"], "favorable": "partiel", "beneficiaire": "public",
                "statut": "engagement_volontaire" if raw["jalon_id"] == "S02" else "intention",
                "condition": "Poursuite du projet et precision des modalites ; pas d'exigibilite juridique etablie.",
                "condition_realisee": "NA",
                "etat_execution": {"realise": "complete", "partiel": "partielle", "absent": "non_executee", "U": "U"}[raw["etat"]],
                "date_execution": raw["date_evenement"] if raw["etat"] == "realise" else "",
                "source_execution_url": source_urls[source_id] if raw["etat"] != "U" else "",
                "type_preuve": raw["niveau_preuve"],
                "date_publication_preuve": "2026-08-10" if source_id == "F06" else "",
                "preuve_retrospective": "oui" if raw["regime"] == "retrospectif" else "non",
                "raison_code": raw["justification"], "statut_arbitrage": "initial",
                "regime_preuve": raw["regime"], "perimetre": "installation_de_trois_jalons_pas_execution_annuelle"})
            decision_rows.append(row)
    return {
        # The frozen v2 reference was written on Windows with CRLF. Specify it
        # explicitly so its exact bytes are reproduced on every operating system.
        "resultats.json": (json.dumps(result, ensure_ascii=False, indent=2) + "\n").replace("\n", "\r\n").encode("utf-8"),
        "demandes.csv": csv_bytes(demand_fields, demand_rows),
        "decisions.csv": csv_bytes(decision_fields, decision_rows),
    }


def csv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def write_outputs(outputs):
    directory = ROOT / "out"
    # A pre-existing symlink must not redirect writes into the input directory.
    if directory.is_symlink() or directory.resolve().parent != ROOT:
        raise ValueError("Le repertoire out/ ne doit pas etre un lien vers un autre emplacement.")
    directory.mkdir(exist_ok=True)
    for name, content in outputs.items():
        target = directory / name
        if target.is_symlink() or target.resolve().parent != directory.resolve():
            raise ValueError("Sortie redirigee interdite : " + name)
        if target.exists() and target.stat().st_nlink > 1:
            raise ValueError("Sortie partageant un lien physique interdite : " + name)
    for name, content in outputs.items():
        (directory / name).write_bytes(content)
    return directory


def main():
    try:
        outputs = build_outputs()
        directory = write_outputs(outputs)
        print(json.dumps({"status": "ok", "output_directory": str(directory),
                          "files": list(outputs)}, ensure_ascii=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=True,
                         separators=(",", ":")), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
