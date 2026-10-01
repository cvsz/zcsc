# Development

Primary target: Windows 10/11, Python 3.11+, installed Camfrog Video Chat.

```powershell
cd apps\camfrog-status-changer
py -m pip install -r requirements.txt
py -m pytest -q
py app.py
```

## Rules

- One interval tick equals one status-message apply attempt.
- UI text read-back is not server-visible proof.
- Keep Win32 messaging time-bounded.
- Do not re-enable generic button guessing.
- Keep registry/profile discovery read-only.
- Preserve TH/EN user-facing strings and put technical detail in logs.
- Version-specific behavior must be fingerprint-gated and fail closed.

The latest integrated implementation package reported 41 passing tests.
