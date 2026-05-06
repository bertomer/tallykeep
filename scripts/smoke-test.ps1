# Smoke-test the live local stack -- exercises every M0..M4 endpoint and a few
# of the still-501 stubs to confirm the API surface.
#
# Prereqs:
#   1. Stack is up: `docker compose up -d` (or after `.\scripts\dev-reset.ps1`)
#   2. The secret store is initialized AND unlocked. If you just reset the
#      stack, this script will initialize it for you with the passphrase
#      passed via -Passphrase (default: 'smoke-test-passphrase').
#
# Usage:
#   .\scripts\smoke-test.ps1
#   .\scripts\smoke-test.ps1 -Passphrase 'my-passphrase'
#   .\scripts\smoke-test.ps1 -BaseUrl http://127.0.0.1:8000

[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Passphrase = "smoke-test-passphrase"
)

$ErrorActionPreference = "Stop"

function Section($title) {
    Write-Host ""
    Write-Host "=== $title ===" -ForegroundColor Cyan
}

function Show($label, $value) {
    Write-Host ("  {0,-22} {1}" -f $label, $value)
}

# A standard sample descriptor based on the abandon-abandon-...-about test
# mnemonic. Mainnet native-segwit, external chain.
$wpkhMainnet = "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)"
$wpkhMainnetChange = "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*)"


# --- 1. Health -----------------------------------------------------------------

Section "1. Health (works regardless of unlock state)"
$health = Invoke-RestMethod -Uri "$BaseUrl/api/v1/health"
Show "status"     $health.status
Show "version"    $health.version
Show "database"   $health.checks.database.ok
Show "redis"      $health.checks.redis.ok
Show "event_bus"  $health.checks.event_bus.ok
Show "unlocked"   $health.checks.unlocked.ok


# --- 2. Unlock -----------------------------------------------------------------

Section "2. Unlock (initialize on a fresh DB, otherwise unlock)"
$body = @{ passphrase = $Passphrase } | ConvertTo-Json -Compress
try {
    $r = Invoke-RestMethod -Method Post `
        -Uri "$BaseUrl/api/v1/unlock/initialize" `
        -ContentType 'application/json' -Body $body
    Show "initialize" "ok ($($r.unlocked))"
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        # Already initialized -- try unlock instead.
        try {
            $r = Invoke-RestMethod -Method Post `
                -Uri "$BaseUrl/api/v1/unlock" `
                -ContentType 'application/json' -Body $body
            Show "unlock" "ok ($($r.unlocked))"
        } catch {
            Write-Host "  Could not unlock with passphrase '$Passphrase'." -ForegroundColor Yellow
            Write-Host "  If this is an existing stack with a different passphrase, pass -Passphrase or run dev-reset.ps1 first." -ForegroundColor Yellow
            throw
        }
    } else {
        throw
    }
}


# --- 3. Profile / feature-flags / configuration -------------------------------

Section "3. Profile (auto-creates singleton on first GET)"
$profile = Invoke-RestMethod -Uri "$BaseUrl/api/v1/profile"
Show "preset"        $profile.preset
Show "base_currency" $profile.base_currency

Section "4. Switch preset to 'sovereign'"
$body = @{ preset = "sovereign" } | ConvertTo-Json -Compress
$profile = Invoke-RestMethod -Method Patch -Uri "$BaseUrl/api/v1/profile" `
    -ContentType 'application/json' -Body $body
Show "preset"  $profile.preset

Section "5. Feature flags (resolved against the new preset)"
$flags = Invoke-RestMethod -Uri "$BaseUrl/api/v1/feature-flags"
Show "trading.enabled"            $flags.flags."trading.enabled"
Show "banking.custom_fee_rate"    $flags.flags."banking.custom_fee_rate.enabled"
Show "advanced.api_docs_link"     $flags.flags."advanced.api_docs_link"

Section "6. Configuration -- set bitcoind RPC host"
$body = @{ bitcoind = @{ rpc_host = "192.168.1.42"; rpc_port = 8332 } } | ConvertTo-Json -Compress -Depth 4
$config = Invoke-RestMethod -Method Patch -Uri "$BaseUrl/api/v1/configuration" `
    -ContentType 'application/json' -Body $body
Show "bitcoind.rpc_host" $config.bitcoind.rpc_host
Show "bitcoind.rpc_port" $config.bitcoind.rpc_port


# --- 7. Create a Purse with two descriptors -----------------------------------

Section "7. Create a Purse (external + change descriptors, gap_limit=10)"
$body = @{
    name = "Smoke-test phone wallet"
    description = "Created by smoke-test.ps1"
    purpose = "spending"
    declared_security = @{
        custody_model = "self_single"
        signing_model = "software_hot"
    }
    display_color = "#10b981"
    display_order = 0
    descriptors = @(
        @{
            name = "main"
            expression = $wpkhMainnet
            change_expression = $wpkhMainnetChange
            network = "mainnet"
            gap_limit = 10
        }
    )
} | ConvertTo-Json -Compress -Depth 6
try {
    $purse = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/holdings/purse" `
        -ContentType 'application/json' -Body $body
    Show "id"                $purse.id
    Show "holding_type"      $purse.holding_type
    Show "descriptor_ids[0]" $purse.descriptor_ids[0]
    $purseId = $purse.id
    $descriptorId = $purse.descriptor_ids[0]
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Host "  Stack already has the smoke-test descriptor (re-run on existing data)." -ForegroundColor Yellow
        Write-Host "  Run '.\scripts\dev-reset.ps1' first to start clean, then re-run this." -ForegroundColor Yellow
        exit 1
    }
    throw
}


# --- 8. Inspect ----------------------------------------------------------------

Section "8. List holdings"
$list = Invoke-RestMethod -Uri "$BaseUrl/api/v1/holdings"
Show "count" $list.Count
foreach ($h in $list) {
    Show ("  - " + $h.holding_type) $h.name
}

Section "9. Get one holding"
$got = Invoke-RestMethod -Uri "$BaseUrl/api/v1/holdings/$purseId"
Show "name"            $got.name
Show "is_archived"     $got.is_archived
Show "descriptor count" $got.descriptor_ids.Count

Section "10. Descriptor + its derived addresses"
$descriptor = Invoke-RestMethod -Uri "$BaseUrl/api/v1/descriptors/$descriptorId"
Show "address_type"  $descriptor.address_type
Show "network"       $descriptor.network
Show "gap_limit"     $descriptor.gap_limit

$addresses = Invoke-RestMethod -Uri "$BaseUrl/api/v1/descriptors/$descriptorId/addresses?limit=200"
Show "address count" $addresses.addresses.Count
Show "first external" ($addresses.addresses | Where-Object { -not $_.is_change } | Select-Object -First 1).address
Show "first change   " ($addresses.addresses | Where-Object { $_.is_change } | Select-Object -First 1).address

Section "11. Next receiving address (lowest-index unused on external chain)"
$next = Invoke-RestMethod -Method Post `
    -Uri "$BaseUrl/api/v1/descriptors/$descriptorId/addresses/next-receiving"
Show "address"        $next.address
Show "derivation_path" $next.derivation_path
Show "index"          $next.derivation_index


# --- 12. Patch + change-type --------------------------------------------------

Section "12. Patch the holding (rename + recolor)"
$body = @{ name = "Smoke-test renamed"; display_color = "#abcdef" } | ConvertTo-Json -Compress
$patched = Invoke-RestMethod -Method Patch -Uri "$BaseUrl/api/v1/holdings/$purseId" `
    -ContentType 'application/json' -Body $body
Show "name"          $patched.name
Show "display_color" $patched.display_color

Section "13. Change Purse -> Strongbox (audit log written)"
$body = @{ new_type = "strongbox"; reason = "Smoke test: migrated keys" } | ConvertTo-Json -Compress
$changed = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/holdings/$purseId/change-type" `
    -ContentType 'application/json' -Body $body
Show "holding_type"  $changed.holding_type


# --- 14. Chain scan against regtest (M5.2) -----------------------------------

Section "14. Chain scan: create regtest Purse, fund, /rescan, balance"
$wpkhRegtest = "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/0/*)"
$regtestBody = @{
    name = "Smoke regtest wallet"
    purpose = "spending"
    declared_security = @{
        custody_model = "self_single"
        signing_model = "software_hot"
    }
    display_color = "#10b981"
    display_order = 1
    descriptors = @(
        @{
            name = "main"
            expression = $wpkhRegtest
            network = "regtest"
            gap_limit = 10
        }
    )
} | ConvertTo-Json -Compress -Depth 6

$regtestSkipped = $false
try {
    $regtestPurse = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/holdings/purse" `
        -ContentType 'application/json' -Body $regtestBody
    $regtestDescId = $regtestPurse.descriptor_ids[0]
    $regtestHoldingId = $regtestPurse.id
    Show "regtest descriptor" $regtestDescId

    $firstAddr = (Invoke-RestMethod -Uri "$BaseUrl/api/v1/descriptors/$regtestDescId/addresses?limit=1").addresses[0].address
    Show "first address"  $firstAddr

    # Fund the address from a fresh bitcoind-side faucet wallet via bitcoin-cli.
    # PowerShell 5.1 mangles native-command arguments containing `=`, so we
    # build the wallet flag once into a single string and pass it as a single
    # token; that survives argument-tokenization on every host shell.
    $walletName = "smoketest_$(Get-Random -Maximum 99999)"
    $walletFlag = "-rpcwallet=$walletName"
    $rpcAuth = "-rpcuser=tallykeep", "-rpcpassword=tallykeep_dev", "-regtest"

    $createOutput = docker compose exec -T bitcoind bitcoin-cli @rpcAuth createwallet $walletName 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "createwallet '$walletName' failed: $createOutput"
    }

    $faucetAddr = (docker compose exec -T bitcoind bitcoin-cli @rpcAuth $walletFlag getnewaddress).Trim()
    docker compose exec -T bitcoind bitcoin-cli @rpcAuth generatetoaddress 150 $faucetAddr | Out-Null
    $sendTxid = (docker compose exec -T bitcoind bitcoin-cli @rpcAuth $walletFlag sendtoaddress $firstAddr 0.00001500).Trim()
    $minerAddr = (docker compose exec -T bitcoind bitcoin-cli @rpcAuth $walletFlag getnewaddress).Trim()
    docker compose exec -T bitcoind bitcoin-cli @rpcAuth generatetoaddress 1 $minerAddr | Out-Null
    Show "funded txid" $sendTxid

    $rescan = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/descriptors/$regtestDescId/rescan"
    Show "utxos_discovered"      $rescan.utxos_discovered
    Show "ledger_entries"        $rescan.ledger_entries_created
    Show "height_at_scan"        $rescan.height_at_scan

    $balance = Invoke-RestMethod -Uri "$BaseUrl/api/v1/descriptors/$regtestDescId/balance"
    Show "confirmed_sats"        $balance.confirmed_sats

    $crossList = Invoke-RestMethod -Uri "$BaseUrl/api/v1/utxos?holding_id=$regtestHoldingId&limit=200"
    Show "/utxos for holding"    $crossList.utxos.Count
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Show "skipped" "regtest descriptor already imported (run dev-reset.ps1 first)"
        $regtestSkipped = $true
    } else {
        throw
    }
}


# --- 14b. Live listener (M5.3): send without /rescan, watcher auto-detects ----

Section "14b. Live listener: send to a fresh address, no /rescan, expect UTXO"
if ($regtestSkipped) {
    Show "skipped" "section 14 was skipped, nothing to verify here"
} else {
    # Take the next unused address on the same descriptor so we can distinguish
    # the auto-detection from the prior /rescan persistence.
    $newAddrResp = Invoke-RestMethod -Method Post `
        -Uri "$BaseUrl/api/v1/descriptors/$regtestDescId/addresses/next-receiving"
    $liveAddr = $newAddrResp.address
    Show "fresh address" $liveAddr

    $liveTxid = (docker compose exec -T bitcoind bitcoin-cli @rpcAuth $walletFlag sendtoaddress $liveAddr 0.00002000).Trim()
    Show "live txid" $liveTxid
    docker compose exec -T bitcoind bitcoin-cli @rpcAuth generatetoaddress 1 $minerAddr | Out-Null

    # Poll the cross-descriptor UTXO endpoint for our txid showing up. The
    # listener thread fetches getrawtransaction + getblock then commits, so
    # most runs see it in <2s; allow up to 30s before declaring failure.
    $deadline = (Get-Date).AddSeconds(30)
    $found = $false
    while ((Get-Date) -lt $deadline) {
        $list = Invoke-RestMethod -Uri "$BaseUrl/api/v1/utxos?holding_id=$regtestHoldingId&limit=200"
        $match = $list.utxos | Where-Object { $_.txid -eq $liveTxid -and $_.value_sats -eq 2000 }
        if ($match) { $found = $true; break }
        Start-Sleep -Milliseconds 300
    }
    if (-not $found) {
        throw "live listener never persisted UTXO for $liveTxid (worker logs: 'docker compose logs worker')"
    }
    Show "auto-detected sats" $match.value_sats
    Show "confirmation_height" $match.confirmation_height
}


# --- 14c. Banking (M6): fee-estimate / payment-request / invoice / cancel ------

Section "14c. Banking: fee-estimate, payment-request, invoice, cancel"

# Use a dedicated tpub branch so descriptor uniqueness never conflicts with
# section 14's single-expression xpub.  Branches 800 (external) + 801 (change)
# are reserved for this smoke section.
$bankingExt = "wpkh([73c5da0a]tpubD6NzVbkrYhZ4XYa9MoLt4BiMZ4gkt2faZ4BcmKu2a9te4LDpQmvEz2L2yDERivHxFPnxXXhqDRkUNnQCpZggCyEZLBktV7VaSmwayqMJy1s/800/*)"
$bankingChg = "wpkh([73c5da0a]tpubD6NzVbkrYhZ4XYa9MoLt4BiMZ4gkt2faZ4BcmKu2a9te4LDpQmvEz2L2yDERivHxFPnxXXhqDRkUNnQCpZggCyEZLBktV7VaSmwayqMJy1s/801/*)"

$bankingSkipped = $false
try {
    $bankPurseBody = @{
        name = "Smoke banking wallet"
        purpose = "spending"
        declared_security = @{
            custody_model = "self_single"
            signing_model = "software_hot"
        }
        display_color = "#3b82f6"
        display_order = 2
        descriptors = @(
            @{
                name              = "main"
                expression        = $bankingExt
                change_expression = $bankingChg
                network           = "regtest"
                gap_limit         = 5
            }
        )
    } | ConvertTo-Json -Compress -Depth 6

    $bankPurse     = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/holdings/purse" `
        -ContentType 'application/json' -Body $bankPurseBody
    $bankDescId    = $bankPurse.descriptor_ids[0]
    $bankHoldingId = $bankPurse.id
    Show "bank holding id" $bankHoldingId

    # Self-contained funder wallet so this section works even if section 14 was
    # skipped.
    $bankFunder     = "smoke_bank_$(Get-Random -Maximum 99999)"
    $bankFunderFlag = "-rpcwallet=$bankFunder"
    docker compose exec -T bitcoind bitcoin-cli @rpcAuth createwallet $bankFunder | Out-Null
    $bankFunderAddr = (docker compose exec -T bitcoind bitcoin-cli @rpcAuth $bankFunderFlag getnewaddress).Trim()
    docker compose exec -T bitcoind bitcoin-cli @rpcAuth generatetoaddress 150 $bankFunderAddr | Out-Null

    $bankRecvAddr = (Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/descriptors/$bankDescId/addresses?limit=1").addresses[0].address
    (docker compose exec -T bitcoind bitcoin-cli @rpcAuth $bankFunderFlag sendtoaddress $bankRecvAddr 0.00050000).Trim() | Out-Null
    $bankMinerAddr = (docker compose exec -T bitcoind bitcoin-cli @rpcAuth $bankFunderFlag getnewaddress).Trim()
    docker compose exec -T bitcoind bitcoin-cli @rpcAuth generatetoaddress 1 $bankMinerAddr | Out-Null

    $bankRescan = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/descriptors/$bankDescId/rescan"
    Show "utxos_discovered" $bankRescan.utxos_discovered
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Show "skipped" "banking descriptor already imported (run dev-reset.ps1 first)"
        $bankingSkipped = $true
    } else {
        throw
    }
}

if (-not $bankingSkipped) {
    # -- 1. Fee estimate --
    $feeResp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/banking/fee-estimate" `
        -ContentType 'application/json' `
        -Body (@{ strategy = "normal" } | ConvertTo-Json -Compress)
    Show "normal fee sat/vB" $feeResp.sat_per_vbyte
    Show "is_fallback"       $feeResp.is_fallback

    # -- 2. PaymentRequest (builds PSBT; no signing in smoke test) --
    $destWallet = "smoke_dest_$(Get-Random -Maximum 99999)"
    docker compose exec -T bitcoind bitcoin-cli @rpcAuth createwallet $destWallet | Out-Null
    $destAddr = (docker compose exec -T bitcoind bitcoin-cli @rpcAuth "-rpcwallet=$destWallet" getnewaddress).Trim()

    $pr = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/banking/payment-requests" `
        -ContentType 'application/json' `
        -Body (@{
            holding_id   = $bankHoldingId
            destination  = $destAddr
            amount_sats  = 10000
            fee_strategy = "normal"
            description  = "Smoke test send"
        } | ConvertTo-Json -Compress)
    $prId = $pr.id
    Show "payment_request.status"   $pr.status
    Show "psbt_base64 length (b64)" $pr.psbt_base64.Length

    # PSBT download — JSON form (binary form tested in integration tests)
    $psbtJson = Invoke-RestMethod -Uri "$BaseUrl/api/v1/banking/payment-requests/$prId/psbt"
    Show "psbt filename"  $psbtJson.filename

    # List + get by id
    $prList = Invoke-RestMethod -Uri "$BaseUrl/api/v1/banking/payment-requests?holding_id=$bankHoldingId"
    Show "payment_requests count" $prList.payment_requests.Count

    # -- 3. Invoice --
    $inv = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/banking/invoices" `
        -ContentType 'application/json' `
        -Body (@{
            holding_id  = $bankHoldingId
            amount_sats = 25000
            description = "Smoke test invoice"
        } | ConvertTo-Json -Compress)
    $invId = $inv.id
    Show "invoice.status"         $inv.status
    Show "invoice.recv_address"   $inv.receiving_address
    # Truncate BIP21 for display
    $bip21Preview = if ($inv.bip21_uri.Length -gt 55) { $inv.bip21_uri.Substring(0, 55) + "..." } else { $inv.bip21_uri }
    Show "invoice.bip21"          $bip21Preview

    # QR code
    $qrResp = Invoke-WebRequest -Uri "$BaseUrl/api/v1/banking/invoices/$invId/qr"
    Show "invoice QR content-type" ($qrResp.Headers.'Content-Type')

    # List invoices
    $invList = Invoke-RestMethod -Uri "$BaseUrl/api/v1/banking/invoices?holding_id=$bankHoldingId"
    Show "invoices count" $invList.invoices.Count

    # -- 4. Cancel both --
    $cancelledPr  = Invoke-RestMethod -Method Post `
        -Uri "$BaseUrl/api/v1/banking/payment-requests/$prId/cancel"
    Show "payment_request after cancel" $cancelledPr.status

    $cancelledInv = Invoke-RestMethod -Method Post `
        -Uri "$BaseUrl/api/v1/banking/invoices/$invId/cancel"
    Show "invoice after cancel" $cancelledInv.status

    # Double-cancel must return 409 (already cancelled)
    try {
        Invoke-RestMethod -Method Post `
            -Uri "$BaseUrl/api/v1/banking/payment-requests/$prId/cancel" | Out-Null
        Show "double-cancel" "(unexpected 200!)"
    } catch {
        $sc = $_.Exception.Response.StatusCode.value__
        Show "double-cancel returns" "409=$($sc -eq 409)"
    }
}


# --- 15. Sweep policies (M8) --------------------------------------------------

Section "15. Sweep policies (M8)"

# Need two separate holdings for source + destination.
# Re-use the $purseId from section 7 as source.
# Create a second purse as the cold-storage destination.
$vaultBody = @{
    name = "Smoke test vault"
    description = "Cold storage destination for sweep smoke test"
    purpose = "reserve"
    declared_security = @{
        custody_model = "self_multisig"
        signing_model = "hardware_offline"
        geographic_distribution = $false
        inheritance_configured = $false
    }
    display_color = "#6366f1"
    display_order = 99
    descriptors = @(
        @{
            name = "vault-external"
            expression = "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*)"
            network = "mainnet"
            gap_limit = 5
        }
    )
} | ConvertTo-Json -Depth 5 -Compress
$vaultHolding = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/holdings/vault" `
    -ContentType 'application/json' -Body $vaultBody
$vaultId = $vaultHolding.id
Show "vault holding id" $vaultId

# 15.1 Create sweep policy (purse → vault)
$spBody = @{
    name = "Smoke sweep"
    source_holding_id = $purseId
    destination_holding_id = $vaultId
    trigger_type = "threshold"
    trigger_configuration = @{ threshold_sats = 500000; cooldown_hours = 24 }
    minimum_balance_sats = 100000
    maximum_per_period_sats = 2000000
    requires_user_confirmation = $true
    is_dry_run = $false
} | ConvertTo-Json -Compress
$sp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sweep-policies" `
    -ContentType 'application/json' -Body $spBody
$spId = $sp.id
Show "policy.id"         $spId
Show "policy.is_enabled" $sp.is_enabled
Show "warnings"          $sp.safety_warnings.Count

# 15.2 List sweep policies
$spList = Invoke-RestMethod -Uri "$BaseUrl/api/v1/sweep-policies"
Show "total policies"   $spList.Count

# 15.3 Get sweep policy
$spGet = Invoke-RestMethod -Uri "$BaseUrl/api/v1/sweep-policies/$spId"
Show "get.name"          $spGet.name

# 15.4 Patch sweep policy
$spPatch = Invoke-RestMethod -Method Patch -Uri "$BaseUrl/api/v1/sweep-policies/$spId" `
    -ContentType 'application/json' `
    -Body (@{ name = "Smoke sweep (patched)"; maximum_per_period_sats = 3000000 } | ConvertTo-Json -Compress)
Show "patched.name"              $spPatch.name
Show "patched.max_per_period"    $spPatch.maximum_per_period_sats

# 15.5 Attempt enable before acknowledging — must 409
try {
    Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sweep-policies/$spId/enable" | Out-Null
    Show "enable before ack" "(unexpected 200!)"
} catch {
    $sc = $_.Exception.Response.StatusCode.value__
    Show "enable before ack" "409=$($sc -eq 409)"
}

# 15.6 Acknowledge warnings
$acked = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sweep-policies/$spId/acknowledge-warnings"
$allAcked = ($acked.safety_warnings | Where-Object { -not $_.user_acknowledged }).Count -eq 0
Show "all warnings acked" $allAcked

# 15.7 Enable
$enabled = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sweep-policies/$spId/enable"
Show "enabled.is_enabled"  $enabled.is_enabled

# 15.8 Pause-all / resume-all
$paused = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sweep-policies/pause-all"
Show "pause-all.paused"   $paused.paused
$resumed = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sweep-policies/resume-all"
Show "resume-all.resumed" $resumed.resumed

# 15.9 Disable then delete
Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sweep-policies/$spId/disable" | Out-Null
$del = Invoke-WebRequest -Method Delete -Uri "$BaseUrl/api/v1/sweep-policies/$spId"
Show "delete policy status" $del.StatusCode

# 15.10 Sweep executions list (empty)
$execs = Invoke-RestMethod -Uri "$BaseUrl/api/v1/sweep-executions"
Show "executions count" $execs.Count

# 15.11 Supported custodial adapters
$supported = Invoke-RestMethod -Uri "$BaseUrl/api/v1/custodial-providers/supported"
Show "supported adapters" ($supported.supported -join ", ")


# --- 16. Jobs endpoints (M8.1) -----------------------------------------------

Section "16. Jobs endpoints"

# GET /jobs — empty list at start
$jobsList = Invoke-RestMethod -Uri "$BaseUrl/api/v1/jobs"
Show "initial jobs count" $jobsList.Count

# GET /jobs/{unknown} — 404
try {
    Invoke-RestMethod -Uri "$BaseUrl/api/v1/jobs/00000000-0000-0000-0000-000000000001" | Out-Null
    Show "unknown job" "(unexpected 200!)"
} catch {
    $sc = $_.Exception.Response.StatusCode.value__
    Show "unknown job 404" ($sc -eq 404)
}

# DELETE /jobs/{unknown} — 404
try {
    Invoke-WebRequest -Method Delete -Uri "$BaseUrl/api/v1/jobs/00000000-0000-0000-0000-000000000001" | Out-Null
    Show "delete unknown" "(unexpected 200!)"
} catch {
    $sc = $_.Exception.Response.StatusCode.value__
    Show "delete unknown 404" ($sc -eq 404)
}


# --- 17. Stubs (sanity-check the OpenAPI surface for routes not yet landed) ----

Section "17. Stubs return 501 with milestone tag"
foreach ($pair in @(
    @("GET",  "/api/v1/lightning/status")
)) {
    $method = $pair[0]
    $path = $pair[1]
    try {
        Invoke-RestMethod -Method $method -Uri "$BaseUrl$path" | Out-Null
        Show ("$method $path") "(unexpected 200!)"
    } catch {
        $resp = $_.Exception.Response
        if ($resp -and $resp.StatusCode -eq 501) {
            $body = (New-Object IO.StreamReader($resp.GetResponseStream())).ReadToEnd() | ConvertFrom-Json
            Show ("$method $path") ("501 -> $($body.milestone)")
        } else {
            Show ("$method $path") ("status=$($resp.StatusCode)")
        }
    }
}


# --- 18. Archive & cleanup ----------------------------------------------------

Section "18. Archive the smoke-test holdings"
$resp = Invoke-WebRequest -Method Post -Uri "$BaseUrl/api/v1/holdings/$purseId/archive"
Show "purse status" $resp.StatusCode
$resp2 = Invoke-WebRequest -Method Post -Uri "$BaseUrl/api/v1/holdings/$vaultId/archive"
Show "vault status" $resp2.StatusCode

Section "19. Verify archived holdings are hidden by default, visible with include_archived"
$default = Invoke-RestMethod -Uri "$BaseUrl/api/v1/holdings"
$archived = Invoke-RestMethod -Uri "$BaseUrl/api/v1/holdings?include_archived=true"
Show "without archived" $default.Count
Show "with archived"    $archived.Count


Write-Host ""
Write-Host "=== Done. Smoke test passed end-to-end. ===" -ForegroundColor Green
Write-Host "Tip: open $BaseUrl/docs in a browser to browse the full OpenAPI surface."
