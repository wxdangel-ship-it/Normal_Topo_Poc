.PHONY: test

test:
	PYTHONPATH=src python -m pytest -q
