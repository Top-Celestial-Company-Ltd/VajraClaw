# OpenClaw / VajraClaw 雙軌 SRE 部署與安全維運指南

本指南面向 DevOps、SRE 和資安工程師，介紹如何在單機/VM 伺服器上部署 **OpenClaw** 並整合 **VajraClaw**，建立具備**互斥 A/B 雙軌安全更新**、**SystemD 系統級資源硬化**及**主動健康檢查**的生產級架構。

---

## 🏗️ 1. 架構設計：A/B 互斥雙軌制

為了在系統更新（如升級 AI 引擎或變更約束規則）時避免多個 Bot 同時拉取 Telegram 消息而導致 TG API 噴出 `409` 衝突錯誤，我們採用 **互斥（Mutual Exclusion）的雙主機 Active-Passive 模型**。

*   **A 軌（穩定舊版）**：部署於 `/opt/openclaw`，系統服務為 `lobster@.service`，使用穩定版規則。
*   **B 軌（測試/更新新版）**：部署於 `/opt/openclaw-new`，系統服務為 `lobster-new@.service`，使用新版規則。
*   **安全網閘 (DROS Gateway)**：統一監聽本地 `Port 5000`，過濾並攔截 Agent 的越權調用。

SystemD 在 OS 內核層級保證了兩者不會同時運行：**啟動 B 軌時會自動關閉 A 軌，反之亦然。**

---

## ⚙️ 2. SystemD 系統服務配置與 SRE 硬化

請將以下服務配置文件配置於 `/etc/systemd/system/` 目錄下：

### A 軌服務模板：`/etc/systemd/system/lobster@.service`
```ini
[Unit]
Description=OpenClaw Service A - %I
After=network.target
# 宣告互斥：啟動此服務時自動關閉 lobster-new
Conflicts=lobster-new@%i.service

[Service]
Type=simple
User=claw_user
WorkingDirectory=/opt/openclaw
Environment=NODE_ENV=production
ExecStart=/usr/bin/node /opt/openclaw/dist/index.js --agent %I
Restart=always
RestartSec=5

# === SRE 安全與性能硬化 ===
LimitNOFILE=65535
TimeoutStartSec=60
# 防止內核 OOM 優先砍掉本服務
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
```

### B 軌服務模板：`/etc/systemd/system/lobster-new@.service`
```ini
[Unit]
Description=OpenClaw Service B (New Track) - %I
After=network.target
# 宣告互斥：啟動此服務時自動關閉 lobster
Conflicts=lobster@%i.service

[Service]
Type=simple
User=claw_user
WorkingDirectory=/opt/openclaw-new
Environment=NODE_ENV=production
# 大容量環境下防止 TypeScript 重複編譯耗盡 RAM
Environment=OPENCLAW_RUN_NODE_SKIP_DTS_BUILD=1
ExecStart=/usr/bin/node /opt/openclaw-new/dist/index.js --agent %I
Restart=always
RestartSec=5

# === SRE 安全與性能硬化 ===
LimitNOFILE=65535
TimeoutStartSec=60
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
```

---

## 🔄 3. SRE 自動化切換腳本：`openclaw-switch`

此腳本用於在 A/B 軌道之間執行無痛、帶有健康檢查與審計日誌的安全切換。
請將其存儲於 `/usr/local/bin/openclaw-switch` 並賦予可執行權限（`chmod +x`）：

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
    echo "使用方式: openclaw-switch [A|B] [--agent <名稱>] [--dry-run]"
    echo "  A          切換至 A 軌 (穩定版)"
    echo "  B          切換至 B 軌 (新版)"
    echo "  --dry-run  乾跑模式，僅印出指令而不執行變更"
}

# 參數解析
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
            echo "錯誤: 未知參數 $1"
            show_help
            exit 1
            ;;
    esac
done

if [[ -z "$TARGET_TRACK" ]]; then
    echo "錯誤: 必須指定目標軌道 (A 或 B)"
    show_help
    exit 1
fi

log_action() {
    local msg="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $msg" >> "$LOG_FILE"
}

# 1. 預檢 (Pre-flight Checks)
SERVICE_A="lobster@${AGENT_NAME}.service"
SERVICE_B="lobster-new@${AGENT_NAME}.service"

if [[ ! -f "/etc/systemd/system/lobster@.service" || ! -f "/etc/systemd/system/lobster-new@.service" ]]; then
    echo "❌ 預檢失敗: 找不到 SystemD 服務配置文件"
    exit 1
fi

# 執行切換
if [[ "$TARGET_TRACK" == "A" ]]; then
    ACTIVE_SERVICE="$SERVICE_A"
    DEACTIVATE_SERVICE="$SERVICE_B"
else
    ACTIVE_SERVICE="$SERVICE_B"
    DEACTIVATE_SERVICE="$SERVICE_A"
fi

echo "=== 啟動 A/B 安全切換流程 (目標環境: $TARGET_TRACK, Agent: $AGENT_NAME) ==="

if [[ $DRY_RUN -eq 1 ]]; then
    echo "[DRY-RUN] 準備執行: systemctl stop $DEACTIVATE_SERVICE"
    echo "[DRY-RUN] 準備執行: systemctl start $ACTIVE_SERVICE"
    echo "[DRY-RUN] 準備執行: 進行 DROS Gateway Port 5000 健康檢查"
    exit 0
fi

# 2. 停用與啟用服務
echo "[*] 正在關閉舊軌道服務 ($DEACTIVATE_SERVICE)..."
sudo systemctl stop "$DEACTIVATE_SERVICE"

echo "[*] 正在啟動新軌道服務 ($ACTIVE_SERVICE)..."
sudo systemctl start "$ACTIVE_SERVICE"

# 驗證狀態
STATUS=$(systemctl is-active "$ACTIVE_SERVICE" || true)
if [[ "$STATUS" != "active" ]]; then
    echo "❌ 錯誤: 服務 $ACTIVE_SERVICE 啟動失敗 (目前狀態: $STATUS)"
    log_action "Switch to $TARGET_TRACK failed: Service not active"
    exit 1
fi
echo "[✔] $ACTIVE_SERVICE 成功啟動！"

# 3. 網絡端口與 Gateway 健康檢查
echo "[*] 正在檢測 DROS Gateway 是否正常回應..."
sleep 2

# 連續檢測 3 次
CHECK_SUCCESS=0
for i in {1..3}; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ > /dev/null; then
        CHECK_SUCCESS=1
        break
    fi
    echo "[*] 正在重試檢測 ($i)..."
    sleep 2
done

if [[ $CHECK_SUCCESS -eq 0 ]]; then
    echo "❌ 警告: 服務已啟動，但 DROS Gateway (Port 5000) 回應異常！"
    log_action "Switch to $TARGET_TRACK succeeded but gateway port check failed"
    exit 1
fi

echo "[✔] DROS Gateway HTTP 連線檢測正常！"
echo "=== 切換完成 (日誌已寫入 $LOG_FILE) ==="
log_action "Switch to $TARGET_TRACK (Service: $ACTIVE_SERVICE) succeeded."
```

---

## 📊 4. 日誌審計與可觀測性維運

在單機版部署中，維運人員無須登入網頁控制台即可透過以下標準日誌管理工具監控 VajraClaw 的運行狀態：

### 1. 實時查看防護攔截日誌
VajraClaw 所有越權攔截日誌預設會隨 stdout 輸出至 SystemD 系統日誌：
```bash
# 查看新版 B 軌服務的實時攔截流
journalctl -u lobster-new@buddha -f
```

### 2. 查看切換審計日誌
查看本地 A/B 切換的歷史記錄與成功狀態：
```bash
cat /var/log/openclaw-switch.log
```
*預期輸出格式：*
```text
2026-06-15 01:54:50 - Switch to B (lobster-new@buddha) succeeded.
```

### 3. 配置獨立的審計 JSON 文件
如果您想將防護攔截日誌集中寫入特定的 JSON 文件以供第三方收集器（如 Elastic Stack / Grafana Loki）讀取，請在 `openclaw.json` 配置中宣告：
```json
{
  "vajra_claw": {
    "enabled": true,
    "policy_path": "/opt/openclaw-workspace/policy.bin",
    "log_path": "/var/log/vajraclaw/audit.json"
  }
}
```
隨後只需確保該路徑具備寫入權限即可執行自動輪轉與採集。
