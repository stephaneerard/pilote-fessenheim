PYTHON ?= python

.PHONY: verify verify-sources package
verify:
	@$(PYTHON) donnees/fessenheim/verifier.py

verify-sources:
	@$(PYTHON) donnees/fessenheim/verifier.py --avec-sources

package:
	@$(PYTHON) donnees/fessenheim/fabriquer-paquet.py
