# Startup

1. Install/login to Camfrog normally.
2. Start Camfrog Status Changer.
3. Use **Detect**; preferred path is `%LOCALAPPDATA%\Programs\Camfrog Video Chat\Camfrog Video Chat.exe`.
4. Verify the native profile when using the analyzed client build.
5. Configure Message 1..4 and interval mode.
6. Test one manual Apply with rotation disabled.
7. Enable rotation only after the manual attempt behaves correctly.

Developer startup:

```powershell
cd apps\camfrog-status-changer
py -m pip install -r requirements.txt
py self_test.py
py -m pytest -q
py app.py
```
