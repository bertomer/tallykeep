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
## Test material

Unsupported legacy descriptor
```
wsh(and_v(v:pk([36550033/52h/0h/0h]xpub6CsuiRDEsEhCnLD3D3P57pR2BBg4AAMpZ1u7KAjjzAWYpi2ACS9pL6QAGyofowd9CKzSLTGVhfEtug13oW2DFXK8ny2ue2uSoY3aUBwat3u),or_d(pk(037e05292c5929224b5817d330419eabbf05452a0fab925e21682d96b88b2f1231),older(25920))))
```

Single btc address
```
bc1pzt5kwj3e49vurmtftahy6xkyfq6e8flmuy00udqradnv8dgp9u7sdnmpya
```

TapRoot descriptor
```
tr(e4c21705b90f47f1fef0d67a4f75cca9553ee23806cd15358eecff99fbb13298,and_v(v:pk(xpub6F2fWikW8yPaN8ZLCLzHgk4uZJsM6oizQ5gytvfiR1b9gowpYmY9BaQy5Ct74rs9Jed7b6uc5wECTD6UNjBkSeCjmuEvZQngPXmCxHiBhp6/*),older(25920)))#9phw0gxk
```

bare descriptor
```
zpub6qzFBjei3eNpX9mGgyg34W31urPhCPnGEjMBXv392NeaREWgATPdbZsPdiftwnKpXUTr7GYbfKn7UAhAdfh4PgXWSkyWtaeKYM8tFXFCCHo
```

Strongbox
```
wpkh([3442193e/84h/0h/0h]xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8/0/*)
```


2-3 descriptor
```
wsh(sortedmulti(2,[3442193e/48h/0h/0h/2h]xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8/0/*,[bd16bee5/48h/0h/0h/2h]xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB/0/*,[41d63b50/48h/0h/0h/2h]xpub661MyMwAqRbcEZVB4dScxMAdx6d4nFc9nvyvH3v4gJL378CSRZiYmhRoP7mBy6gSPSCYk6SzXPTf3ND1cZAceL7SfJ1Z3GC8vBgp2epUt13/0/*))
```

single sig timelock
```
wsh(and_v(v:after(1150000),pk([3442193e/84h/0h/0h]xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8/0/*)))
```

2-3 + relative timelock
```
wsh(and_v(v:older(52560),multi(2,[3442193e/48h/0h/0h/2h]xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8/0/*,[bd16bee5/48h/0h/0h/2h]xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB/0/*,[41d63b50/48h/0h/0h/2h]xpub661MyMwAqRbcEZVB4dScxMAdx6d4nFc9nvyvH3v4gJL378CSRZiYmhRoP7mBy6gSPSCYk6SzXPTf3ND1cZAceL7SfJ1Z3GC8vBgp2epUt13/0/*)))
```

invalid multisig
```
multi(2,[3442193e]xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8,[bd16bee5]xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB,[41d63b50]xpub661MyMwAqRbcEZVB4dScxMAdx6d4nFc9nvyvH3v4gJL378CSRZiYmhRoP7mBy6gSPSCYk6SzXPTf3ND1cZAceL7SfJ1Z3GC8vBgp2epUt13)
```


"Clé API" kraken Read only:
/pJocMLmaycttdUo5D1KkWF09t8rOGVUCajxkOmtsQignWT6HSGdNain

"Clé privée" Kraken Read only:
JffOPc5A/rKk5YQWE588eC/UNbtQya9xt8INe4/FMGyZN83EK1mHva8jwPxs/wRZOtGIK9cTqCnsyaRalLif7A==

"Clé API" kraken Withdrawal only:
bd4pcvVPyOem3l5k9+NV3/nEH2b2QHyVuddJCxpW5WiZ9iBcQRLmkgi0

"Clé privée" Kraken Withdrawal only:
qRiDRMEYytD/oXc0vFUpQ70k7s/HEucnAM0geZNSTip8Ly0Z0CmSumA6KS+/6wKSt6GdS0lkvqo2u3pBsPMVEQ==
