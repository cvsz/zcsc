# Reverse-engineering notes

## Review status

**EULA and legal review is pending.** Maintainers must obtain that review before redistributing these notes or associated third-party binaries, offsets, strings, recordings, or derived artifacts. This notice records a review requirement; it is not a legal conclusion.

## Evidence limits

The documents in this directory distinguish static strings and metadata from runtime evidence. A string or control name does not prove that a code path is reachable, that a command is accepted, or that an account has permission. Camfrog UI behavior and server acceptance require separate controlled verification.

Do not invoke diagnostic RVAs, synthesize Camfrog protocol messages, or treat a role-related string as authorization. Prefer read-only inspection of visible UI Automation metadata and redact personal status text, account identifiers, and local paths from reports.
