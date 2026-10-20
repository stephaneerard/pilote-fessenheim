# Pilote Fessenheim — Δ-citoyen

Données et vérification du pilote documentaire de **La démocratie à l’épreuve**.
Version **2.0.1**, protocole **2.0**, codes initiaux avant arbitrage.

Les 22 unités sont les demandes finales numérotées du compte rendu CNDP, et non toutes les contributions citoyennes. Deux sessions de `gpt-6.1-sol` ont codé les mêmes pièces : R = **10/22** et **13/22** ; alpha ordinal **0,816**, alpha binaire **0,733**. Le suivi S porte sur trois jalons, pas sur tous les engagements du projet. Il n’existe pas de validation humaine ni de corpus représentatif.

## Vérifier

Python 3.9 ou ultérieur, bibliothèque standard, aucun téléchargement requis :

```sh
python3 donnees/fessenheim/verifier.py
python3 donnees/fessenheim/test_verification.py
```

Ou `make verify`. Si la commande disponible est `python`, utiliser `make verify PYTHON=python`.
Le calcul écrit seulement dans `donnees/fessenheim/out/`. Les trois références sont comparées octet par octet.
Les tests ne nécessitent aucun ZIP préexistant.

## Télécharger la version figée

[Version pilote-fessenheim-v2.0.1](https://github.com/stephaneerard/pilote-fessenheim/releases/tag/pilote-fessenheim-v2.0.1) : ZIP, SHA-256 détaché et métadonnées de fabrication. Le ZIP peut varier avec Python/zlib ; son empreinte identifie l’archive diffusée, et le manifeste scelle les fichiers internes.

Les neuf PDF officiels ne sont pas redistribués : leurs URL, SHA-256, consultation et pages identifiées sont dans [manifest.csv](manifest.csv). Pour vérifier les copies aux chemins indiqués, lancer `python3 donnees/fessenheim/verifier.py --avec-sources`.

Lire [README-reproductibilite.txt](README-reproductibilite.txt), [CHANGELOG](CHANGELOG), [CITATION.cff](CITATION.cff) et [LICENCES.txt](LICENCES.txt). Données originales CC BY 4.0, logiciels MIT, documents de tiers exclus. `.gitattributes` préserve les octets lors des passages dans git.

## Provenance et archivage

[Provenance A](provenance/session-A.json), [provenance B](provenance/session-B.json). Révision interne exacte du modèle, consignes complètes et liste exhaustive des pièces fournies : inconnues ; les traces retrouvées ne sont pas reconstruites artificiellement.

`publication.json` est l’instantané scellé avant création de l’étiquette. Le suivi ultérieur est dans [etat-publication.json](etat-publication.json), sur la branche principale. Un DOI, un SWHID ou une capture n’est annoncé qu’après confirmation. Le premier commit conserve le paquet contrôlé avant les derniers correctifs techniques ; le suivant les documente sans modifier les codes initiaux.

## Références permanentes

- DOI de cette version : [10.5281/zenodo.23505871](https://doi.org/10.5281/zenodo.23505871).
- [Notice de citation avec DOI](archivage/CITATION.cff), ajoutée après publication sans modifier la version figée.
- Archive Software Heritage : [`swh:1:rel:f21771808d273487540004fa86916e79524ccd30`](https://archive.softwareheritage.org/browse/release/f21771808d273487540004fa86916e79524ccd30/), pointant vers le commit du tag.
- [Captures Wayback à reprendre](archivage/wayback-captures-a-demander.csv) : neuf URL, aucune capture confirmée depuis cet environnement.

Le ZIP retéléchargé anonymement depuis Zenodo est identique à la release GitHub. Les mises à jour de ce suivi sont hors du manifeste figé, journalisées dans [archivage/JOURNAL](archivage/JOURNAL).
