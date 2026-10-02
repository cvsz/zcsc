SHELL := /bin/sh
PYTHON ?= py

.PHONY: help setup validate-repo validate-template bootstrap-test test compile build ci

help:
	@printf '%s\n' 'Camfrog Status Changer (Windows): setup test compile build' 'Repository: validate-repo bootstrap-test ci' 'Override PYTHON=python3 when using a compatible non-Windows Python environment.'

setup:
	$(PYTHON) -m pip install -r requirements.txt pytest pyinstaller==6.22.3

validate-repo:
	$(PYTHON) scripts/validate_repo.py

validate-template: validate-repo bootstrap-test

bootstrap-test:
	$(PYTHON) -m unittest discover -s tests -p 'test_bootstrap.py' -v

test:
	$(PYTHON) -m pytest -q

compile:
	$(PYTHON) -m compileall -q app.py automation camfrog system ui version.py self_test.py

build:
	@case "$$(uname -s 2>/dev/null || echo unknown)" in MINGW*|MSYS*|CYGWIN*) ;; *) echo 'The Camfrog executable build requires Windows.' >&2; exit 2;; esac
	cmd.exe /d /c build_exe.bat

ci: validate-repo bootstrap-test test compile
