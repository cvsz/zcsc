# Development

ZeaZDev-CamfrogStatusChanger is the project; Camfrog Status Changer is its Windows desktop application. The checkout also retains repository validation and administration tools.

## Local setup

1. Use Windows 10/11 with Python 3.12 and clone the repository.
2. Install the application and development dependencies:

   ```bash
   py -m pip install -r requirements.txt pytest pyinstaller==6.22.3
   ```

3. Run `run_dev.bat` to start the app, or use the repository tasks below.

Build outputs are ignored and are not part of a fresh source checkout. The builder isolates PyInstaller work under `build/CamfrogStatusChanger-work`; it must not clean adjacent Camfrog analysis files in the `build/` tree.

## Repository tasks

```bash
make validate-repo
make test
make compile
make build
```

`make build` is Windows-only. On other hosts, use the Windows GitHub Actions workflow to build the executable.

## Quality expectations

- Keep changes small and reviewable.
- Read `AGENTS.md` and narrower subtree instructions before editing.
- Add tests for behavior changes.
- Prefer deterministic/reproducible tooling.
- Keep CI permissions least privilege.
- Pin Actions/dependencies according to the project's supply-chain policy.
- Do not commit secrets or local credentials.
- Do not weaken security/CI gates to obtain a passing build.
- Fix the root cause of failed validation rather than excluding relevant checks.

## Pull-request validation

Before merge, capture exact-head evidence for the checks that apply to the change. Do not rely on a previously green commit after the PR head has changed.

For repository administration changes, use the read-back verifier:

```bash
python3 scripts/github_admin.py --verify
```

## Documentation

Update architecture, development, release, governance, security, ADRs, and operational docs when their assumptions change.

Documentation must distinguish intended configuration from verified effective state.
