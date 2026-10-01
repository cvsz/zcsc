# Production Readiness

Status: **NOT YET VERIFIED FOR PRODUCTION**

## Verified in code/test evidence

- config recovery and atomic save
- single-message rotation semantics
- interval conversion
- executable discovery preference
- known-client profile fingerprint data
- fail-closed native button targeting
- registry history sanitization
- clipboard binding regression behavior
- style transformation behavior
- hidden-console build design and release hash generation

Latest implementation package baseline: **41 passing tests**.

## Required P0 runtime evidence

- exact target Camfrog executable SHA-256
- manual Apply publishes a status visible from an independent session/account
- 10+ rotation intervals publish exactly one message per tick
- minimized/background-only operation works without browser/link side effects
- restart/startup/tray/single-instance behavior is verified
- final Windows executable hash matches release manifest
- production artifact is code-signed and Defender/SmartScreen behavior reviewed

Do not convert local read-back or static RE findings into a production-ready claim.
