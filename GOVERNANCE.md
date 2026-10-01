# Governance

`cvsz/zcsc` is maintained as a Windows automation/interoperability project with security-sensitive reverse-engineering research.

## Change policy

- Application and RE changes should flow through pull requests.
- Production-readiness claims require evidence, not documentation alone.
- Camfrog-version-specific integrations must be fingerprint-gated and fail closed.
- Credential/session extraction and authentication bypass are outside project scope.
- Security controls must not be disabled merely to obtain a green build.

## Evidence labels

- **VERIFIED:** directly demonstrated by test/tool/runtime evidence.
- **PARTIAL:** one layer is verified but end-to-end behavior is not.
- **PROPOSED:** design/planned change only.
- **BLOCKED:** external dependency/environment prevents completion.

The current release candidate is not production-ready until server-visible status publication and Windows release gates are verified.
