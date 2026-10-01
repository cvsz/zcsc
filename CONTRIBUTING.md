# Contributing

Changes to `zcsc` should be small, reviewable and evidence-backed.

Before opening a PR, run the application tests/self-test from `apps/camfrog-status-changer`.

For Windows-native/controller changes, record the Camfrog executable hash/version and separate:
- source/test result
- local UI/control read-back
- dynamic trace evidence
- independent server-visible verification

Never attach credentials, session/token/cookie values, private memory dumps or unsanitized profile/registry exports.

Bug fixes should add regression coverage when practical. Do not weaken safe-commit guards or reintroduce generic button clicking merely to make status changes appear successful.
