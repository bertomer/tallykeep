# TallyKeep — dev cheatsheet

## Backend

```powershell
docker compose up -d                          # start
.\scripts\dev-reset.ps1                       # wipe + restart (loses all data)
```

Initialize passphrase on a fresh stack:
```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/unlock/initialize -ContentType 'application/json' -Body '{"passphrase":"YOUR_PASSPHRASE"}'
```

Unlock after a backend restart:
```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/unlock -ContentType 'application/json' -Body '{"passphrase":"YOUR_PASSPHRASE"}'
```

## Frontend

```powershell
cd frontend && npm run dev                    # http://localhost:5173
```

## Pair the browser

Step 1 — get a token (60 s TTL, single-use):
```powershell
(Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/pairing/issue).pairing_token
```

Step 2 — paste the token in the browser at `http://localhost:5173`.
Use **`http://localhost:5173`** as the server URL (not `127.0.0.1:8000`).

To re-run onboarding: open a private window, or clear `localStorage` keys prefixed `tallykeep_` in DevTools.

## Smoke test

```powershell
.\scripts\smoke-test.ps1 -Passphrase "YOUR_PASSPHRASE"
```
