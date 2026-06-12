# OpenClaw / VajraClaw SRE Deployment & Security Operations Guide

This guide is designed for DevOps, SRE, and security engineers to configure **OpenClaw** with **VajraClaw** integration on a single host or VM. It details establishing **mutually exclusive A/B dual-track security deployments**, **SystemD system-level service hardening**, and **active health-checks** for production readiness.

---

## 🏗️ 1. Architecture: Mutually Exclusive A/B Dual-Track

To prevent multiple bot instances from simultaneously polling the Telegram API during updates (which causes TG API `409` conflict errors), we adopt a **mutually exclusive Active-Passive A/B deployment model**.

*   **Track A (Stable Old)**: Deployed at `/opt/openclaw` with SystemD service `lobster@.service` running stable policies.
*   **Track B (New Dev/Test)**: Deployed at `/opt/openclaw-new` with SystemD service `lobster-new@.service` running updated policies.
*   **DROS Security Gateway**: Uniformly listens on `Port 5000` to filter and block unauthorized tool calls before they exit the Agent.

SystemD guarantees at the OS kernel level that both tracks do not run concurrently: **Starting Track B automatically shuts down Track A, and vice-versa.**

---

## ⚙️ 2. SystemD Configuration & SRE Hardening

Configure the following unit templates inside `/etc/systemd/system/`:

### Track A Service Template: `/etc/systemd/system/lobster@.service`
```ini
[Unit]
Description=OpenClaw Service A - %I
After=network.target
# Enforce mutual exclusion: Starting this service stops lobster-new
Conflicts=lobster-new@%i.service

[Service]
Type=simple
User=claw_user
WorkingDirectory=/opt/openclaw
Environment=NODE_ENV=production
ExecStart=/usr/bin/node /opt/openclaw/dist/index.js --agent %I
Restart=always
RestartSec=5

# === SRE Performance & Security Hardening ===
LimitNOFILE=65535
TimeoutStartSec=60
# Prevent kernel OOM from killing this process preferentially
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
```

### Track B Service Template: `/etc/systemd/system/lobster-new@.service`
```ini
[Unit]
Description=OpenClaw Service B (New Track) - %I
After=network.target
# Enforce mutual exclusion: Starting this service stops lobster
Conflicts=lobster@%i.service

[Service]
Type=simple
User=claw_user
WorkingDirectory=/opt/openclaw-new
Environment=NODE_ENV=production
# Prevent TypeScript compilation from exhausting RAM on low-spec VMs
Environment=OPENCLAW_RUN_NODE_SKIP_DTS_BUILD=1
ExecStart=/usr/bin/node /opt/openclaw-new/dist/index.js --agent %I
Restart=always
RestartSec=5

# === SRE Performance & Security Hardening ===
LimitNOFILE=65535
TimeoutStartSec=60
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
```

---

## 🔄 3. Automated Switch Script: `openclaw-switch`

Use this script to perform seamless, zero-downtime, audited transitions between Track A and Track B. 
Place it at `/usr/local/bin/openclaw-switch` and make it executable (`chmod +x`):

```bash
#!/usr/bin/env bash
# ==============================================================================
# OpenClaw A/B Dual-Track Switcher with SRE Health Checks
# ==============================================================================
set -euo pipefail

TARGET_TRACK=""
AGENT_NAME="buddha"
DRY_RUN=0
LOG_FILE="/var/log/openclaw-switch.log"

show_help() {
    echo "Usage: openclaw-switch [A|B] [--agent <name>] [--dry-run]"
    echo "  A          Switch to Track A (stable version)"
    echo "  B          Switch to Track B (new version)"
    echo "  --dry-run  Dry run mode; print commands without making changes"
}

# Parse parameters
while [[ $# -gt 0 ]]; do
    case "$1" in
        A|B)
            TARGET_TRACK="$1"
            shift
            ;;
        --agent)
            AGENT_NAME="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Error: Unknown parameter $1"
            show_help
            exit 1
            ;;
    esac
done

if [[ -z "$TARGET_TRACK" ]]; then
    echo "Error: Target track (A or B) must be specified."
    show_help
    exit 1
fi

log_action() {
    local msg="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $msg" >> "$LOG_FILE"
}

# 1. Pre-flight Checks
SERVICE_A="lobster@${AGENT_NAME}.service"
SERVICE_B="lobster-new@${AGENT_NAME}.service"

if [[ ! -f "/etc/systemd/system/lobster@.service" || ! -f "/etc/systemd/system/lobster-new@.service" ]]; then
    echo "❌ Pre-flight check failed: SystemD config files not found."
    exit 1
fi

# Execute switch
if [[ "$TARGET_TRACK" == "A" ]]; then
    ACTIVE_SERVICE="$SERVICE_A"
    DEACTIVATE_SERVICE="$SERVICE_B"
else
    ACTIVE_SERVICE="$SERVICE_B"
    DEACTIVATE_SERVICE="$SERVICE_A"
fi

echo "=== Starting A/B Switcher (Target: $TARGET_TRACK, Agent: $AGENT_NAME) ==="

if [[ $DRY_RUN -eq 1 ]]; then
    echo "[DRY-RUN] Would run: systemctl stop $DEACTIVATE_SERVICE"
    echo "[DRY-RUN] Would run: systemctl start $ACTIVE_SERVICE"
    echo "[DRY-RUN] Would run: DROS Gateway HTTP check on Port 5000"
    exit 0
fi

# 2. Toggle Services
echo "[*] Stopping inactive track service ($DEACTIVATE_SERVICE)..."
sudo systemctl stop "$DEACTIVATE_SERVICE"

echo "[*] Starting target track service ($ACTIVE_SERVICE)..."
sudo systemctl start "$ACTIVE_SERVICE"

# Verify status
STATUS=$(systemctl is-active "$ACTIVE_SERVICE" || true)
if [[ "$STATUS" != "active" ]]; then
    echo "❌ Error: Service $ACTIVE_SERVICE failed to start (Current state: $STATUS)"
    log_action "Switch to $TARGET_TRACK failed: Service not active"
    exit 1
fi
echo "[✔] $ACTIVE_SERVICE successfully started!"

# 3. HTTP Gateway Connection Probe
echo "[*] Checking DROS Gateway loopback health..."
sleep 2

CHECK_SUCCESS=0
for i in {1..3}; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ > /dev/null; then
        CHECK_SUCCESS=1
        break
    fi
    echo "[*] Retrying gateway probe ($i)..."
    sleep 2
done

if [[ $CHECK_SUCCESS -eq 0 ]]; then
    echo "❌ Warning: Service started but DROS Gateway (Port 5000) loopback check failed!"
    log_action "Switch to $TARGET_TRACK succeeded but gateway port check failed"
    exit 1
fi

echo "[✔] DROS Gateway HTTP check completed successfully!"
echo "=== Transition complete (Log written to $LOG_FILE) ==="
log_action "Switch to $TARGET_TRACK (Service: $ACTIVE_SERVICE) succeeded."
```

---

## 📊 4. Logging & Observability Operations

Without a centralized dashboard, SRE administrators can monitor VajraClaw's security events directly on the VM host:

### 1. Real-Time Interception Logs
VajraClaw outputs all verification and interception decisions directly to SystemD stdout:
```bash
# Stream B-track validation logs
journalctl -u lobster-new@buddha -f
```

### 2. Switch Audits
Verify A/B switch history and logs:
```bash
cat /var/log/openclaw-switch.log
```
*Sample Output:*
```text
2026-06-15 01:54:50 - Switch to B (lobster-new@buddha) succeeded.
```

### 3. Dedicated JSON Output
Configure daily-rotated JSON log outputs directly in `openclaw.json` for external collectors (e.g. Filebeat, FluentBit) to forward:
```json
{
  "vajra_claw": {
    "enabled": true,
    "policy_path": "/opt/openclaw-workspace/policy.bin",
    "log_path": "/var/log/vajraclaw/audit.json"
  }
}
```
Ensure the folder path has write permissions enabled.
