SHELL := /bin/sh
ifeq ($(OS),Windows_NT)
PYTHON ?= py -3
else
PYTHON ?= python3
endif

.PHONY: help setup validate-repo test compile build ci

help:
	@printf '%s\n' 'ZeaZDev-CamfrogStatusChanger / Camfrog Status Changer (Windows): setup test compile build' 'Repository: validate-repo ci'

setup:
	$(PYTHON) -m pip install --require-hashes -r requirements-build.lock

validate-repo:
	$(PYTHON) scripts/validate_repo.py

test:
	$(PYTHON) -m pytest -q

compile:
	$(PYTHON) -m compileall -q app.py automation camfrog system ui scripts version.py self_test.py

build:
	@case "$$(uname -s 2>/dev/null || echo unknown)" in MINGW*|MSYS*|CYGWIN*) ;; *) echo 'The Camfrog executable build requires Windows.' >&2; exit 2;; esac
	cmd.exe /d /c build_exe.bat

ci: validate-repo test compile
