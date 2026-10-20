Pilote Fessenheim — paquet de vérification 2.0.1
Résultats scientifiques et manuel : version 2.0, avant arbitrage.
Cette révision corrige la distribution et le logiciel ; elle ne recode aucune demande.

PRÉREQUIS
Python 3.9 ou ultérieur, bibliothèque standard uniquement.
Vérifié localement avec Python 3.9.13. Aucun paquet à installer, aucun réseau utilisé
par les commandes de vérification. GNU Make est facultatif.

DÉMARRAGE
Décompresser paquet-verification.zip et ouvrir un terminal à sa racine.
Conserver l'arborescence : télécharger le seul fichier .py ne suffit pas.

    python donnees/fessenheim/verifier.py

Ou, si GNU Make est installé :

    make verify

Le programme contrôle MANIFEST.sha256, le manifeste CSV et les fichiers publics,
recalcule les trois sorties, puis les compare OCTET PAR OCTET aux références.
Il écrit uniquement dans donnees/fessenheim/out/ : resultats.json, demandes.csv,
decisions.csv et verification.json. Les références publiées restent intactes.
Succès : code de sortie 0 et JSON status=ok. Échec : code 1 et explication JSON.
Les sources et les références peuvent être rendues non modifiables ; out/ doit
rester accessible en écriture. Les contrôles restent actifs avec python -O.

CALCUL SEUL
    python donnees/fessenheim/calculer-resultats.py
Écrit les trois sorties dans out/, sans comparer ni modifier les références.
Utiliser verifier.py pour un contrôle complet des empreintes et du résultat.

PDF OFFICIELS
Le manifeste donne les neuf URL officielles, leurs SHA-256, la consultation,
les pages identifiées et les limites de connaissance sur les pages utilisées.
Ces PDF de tiers sont conservés localement ; ils ne sont pas redistribués dans
le ZIP et ne sont pas nécessaires au seul recalcul des codes.
Pour contrôler également les PDF, les placer aux chemins preuves/fessenheim/...
indiqués dans manifest.csv, puis lancer :

    python donnees/fessenheim/verifier.py --avec-sources

Sans cette option, tout PDF présent est contrôlé et les PDF absents sont énumérés.
L'option exige les neuf PDF. Un succès sans eux valide le calcul et l'intégrité du
paquet public ; il ne signifie pas que les sources documentaires ont été relues.

MANIFESTES
manifest.csv décrit tous les fichiers publics du paquet et les neuf PDF externes.
Les chemins sont relatifs à la racine de ce fichier README.
requis_calcul=oui désigne les dépendances du calcul seul, programme compris.
requis_verification=oui désigne les fichiers nécessaires au contrôle complet.
MANIFEST.sha256 scelle les fichiers publics ainsi que manifest.csv. Il ne peut
contenir sa propre empreinte. Le ZIP dérivé et les sorties out/ sont exclus pour
éviter une autoréférence ; le fabricant affiche l'empreinte du ZIP final.
Une empreinte garantit une identité de contenu par rapport au manifeste reçu ;
elle n'authentifie pas à elle seule l'auteur ou la date de publication.

PROVENANCE
provenance/session-A.json et session-B.json identifient les sessions et les traces
retrouvées. Le modèle déclaré était gpt-6.1-sol, effort xhigh. La révision interne
exacte est inconnue. Les consignes initiales et relances ne sont pas récupérables
en texte clair dans les traces consultées : elles sont déclarées inconnues, sans
reconstitution présentée comme originale. Les critères conservés se trouvent
dans les protocoles figés. La liste exhaustive des pièces effectivement fournies
reste inconnue ; les pièces attestées par les codes et la note sont distinguées.
Les journaux de session complets, qui contiennent un contexte privé, ne sont pas
redistribués. Les métadonnées publiées ne valent pas publication de ces journaux.

VERSION ET PUBLICATION
Version du paquet préparé : 2.0.1 ; état des codes et résultats : 2.0 avant arbitrage.
Lire CHANGELOG, CITATION.cff, LICENCES.txt et publication.json.
Le dépôt configuré dans le checkout n'est pas une preuve de diffusion publique.
Aucune étiquette, capture Wayback, archive Software Heritage ou DOI Zenodo n'est
annoncé comme obtenu. Les statuts et champs vides sont explicites.
L'étiquette proposée est pilote-fessenheim-v2.0.1-reproductibilite.
Ne jamais déplacer une étiquette publiée pour corriger une version : préparer
une nouvelle version et conserver les codes initiaux.

ARCHIVAGE À EFFECTUER APRÈS PUBLICATION
1. Publier le sous-ensemble scientifique et son historique dans un dépôt public
   explicitement choisi ; préserver les octets des fichiers initiaux.
2. Vérifier ce commit, créer l'étiquette de version puis la release correspondante.
3. Soumettre séparément les URL du manifeste à Save Page Now. Une demande de
   capture ne prouve pas une capture réussie. Vérifier le PDF de chaque capture
   et son empreinte avant de renseigner archive_url et archive_statut.
4. Demander l'archivage du dépôt à Software Heritage, attendre son ingestion et
   noter le SWHID réellement obtenu ainsi que la révision visée.
5. Déposer la version étiquetée dans Zenodo, via l'intégration d'un dépôt dédié
   ou un dépôt manuel de ce paquet. Un tag seul ne déclenche pas un DOI.
6. Enregistrer le DOI de cette version, compléter CITATION.cff, et journaliser
   ces ajouts dans une nouvelle révision des métadonnées sans réécrire l'état figé.

Documentation officielle :
https://help.archive.org/help/save-pages-in-the-wayback-machine/
https://www.softwareheritage.org/software-heritage-faq/
https://help.zenodo.org/docs/github/archive-software/github-upload/
https://help.zenodo.org/docs/github/describe-software/citation-file/

RECONSTRUIRE LE ZIP
    python donnees/fessenheim/fabriquer-paquet.py
Ou : make package
Cette commande explicite vérifie le paquet puis écrit paquet-verification.zip
à sa racine. Elle utilise uniquement les fichiers scellés, avec ordre et dates
ZIP fixes. Elle n'archive pas les PDF, le contexte privé, out/ ou les caches.
Une reconstruction avec la même version de Python et zlib est déterministe.

Les empreintes sont un état figé à réviser explicitement lors d'une nouvelle
version. Ni le vérificateur ni le fabricant ne les régénèrent pour faire passer
un contrôle en échec. Les tests de non-régression sont dans
donnees/fessenheim/test_verification.py.
