# ZeaZDev-CamfrogStatusChanger Agent Contract

## Purpose

This repository contains the Camfrog Status Changer Windows application at its root and the shared engineering tools used to maintain it. Keep Camfrog-specific code and product documentation explicit; keep shared tools clearly separated and secure by default.

## Operating rules

- Read `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `ROADMAP.md`, and the closest `AGENTS.md` before editing.
- Keep code, configuration, filenames, commit messages, and technical documentation in English.
- Prefer the smallest reviewable change that satisfies the requested scope.
- Never weaken CI, security scanning, dependency review, branch protections, or release controls merely to make a check pass.
- Never commit credentials, tokens, private keys, production secrets, personal data, Camfrog account data, or local runtime configuration.
- Do not invent project owners, domains, deployment providers, package registries, cloud accounts, or credentials.
- Reuse existing workflows and documents instead of creating overlapping alternatives.
- Pin GitHub Actions permissions to least privilege and prefer maintained first-party or verified actions.
- Treat external input, generated artifacts, pull requests from forks, and dependency metadata as untrusted.
- Keep Camfrog status and room automation fail-closed when the target, room, or control is ambiguous.

## Review skill

- Use [Scrutinize](.agents/skills/scrutinize/SKILL.md) when asked to review, audit, sanity-check, or give a second opinion on a plan, PR, diff, design, or code change, or when invoked with `/scrutinize` in a compatible agent.
- Question whether the change is necessary or can be smaller before tracing real code paths and verifying behavioral claims. Cite concrete file/line evidence and distinguish unverified claims from confirmed behavior.
- The skill guides agent behavior; it does not itself replace required tests, CI, or human review.

## Change workflow

1. Inspect the current exact branch/head and existing files.
2. Identify the smallest missing or inconsistent application or repository capability.
3. Add tests or validation first when practical.
4. Implement without widening scope.
5. Run the relevant validation and security checks.
6. Update documentation when behavior, setup, governance, or release procedures change.
7. Open a pull request; do not claim merge or release readiness without exact-head evidence.

## Verification

At minimum, verify Markdown/YAML syntax for touched files, workflow permissions and triggers, links and placeholders, absence of committed secrets, and consistency between the app documentation, governance, security, and release guidance.

## Pull requests and releases

PRs must state scope, tests, security impact, compatibility or migration impact, documentation impact, deployment impact, and rollback. Releases require green required checks and explicit evidence; never infer production readiness from documentation alone.

## Security

Report vulnerabilities through `SECURITY.md`, not public issues. Fail closed when a security-sensitive configuration is incomplete. Do not weaken security gates merely to obtain a passing build.

## Documentation ownership

- `.github/`: GitHub automation, community health, ownership, issue and PR templates.
- `docs/`: application setup, engineering, reverse-engineering evidence, operations, release, and architecture guidance.
- `docs/adr/`: architecture decision records.
- Root Markdown files: repository-wide policy and application lifecycle guidance.

## Nested AGENTS.md

Add a child `AGENTS.md` only when a subtree has durable rules that differ from this contract. A child file may add stricter rules but must not weaken repository-wide security rules.

## ZEAZ reusable execution layer

- Use [ZEAZ-INTRODUCTION.md](ZEAZ-INTRODUCTION.md) as the cross-agent execution framework.
- Use [docs/ai/README.md](docs/ai/README.md) to select task-specific reusable prompts and playbooks.
- Task playbooks are additive and never weaken this contract or narrower subtree rules.
- Use the canonical evidence-state definitions and decision rule in `ZEAZ-INTRODUCTION.md`; do not redefine them per harness or playbook.
- Keep implementation, verification, deployment, release authorization, and production readiness as distinct states.

## Repository administration

`scripts/github_admin.py` requires an authenticated GitHub identity with Administration permission for changes. Treat successful read-back verification, not script presence, as evidence that controls are effective. Never run a mutating mode without explicit authority for the target repository.
