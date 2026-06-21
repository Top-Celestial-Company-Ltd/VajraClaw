# 🏯 DROS 執行期安全治理邊界、極限與防禦宣告 (Security Boundary, Limitations & Enforcement Declarations)

任何嚴謹的資安防護體系皆不存在「100% 的絕對安全」。本文件以公開、透明且系統工程的角度，明確宣告 **DROS (GuardVM / Vajra Shield)** 智能體執行期安全治理系統的防禦邊界、設計哲學、可插拔架構，以及與傳統 AI Guardrails 的本質區隔。

---

## 🧭 一、 核心定位：Missing Layer 與執行期安全核心

DROS 的定位是 **AI 執行期的防火牆、安全核心與煞車系統 (Agent Runtime Security Enforcement Layer)**，而非另一個 AI 駕駛員或語義分類器。

```
                外部輸入 (External Input)
                        |
                        v
         +-----------------------------+
         |     可插拔威脅情資適配器       | <--- 雷達系統 (僅作預警與流量清洗)
         |  (Pluggable Threat Adapters) |
         |   * L1 ATR (Agent Threat)   |
         |   * Enterprise DLP / SIEM   |
         +-----------------------------+
                        |
                        v
               大語言模型 (LLM / Driver)
                        |
               智能體決策 (Agent Decision)
                        |
                        v
         +-----------------------------+
         |      DROS Runtime Layer     | <--- 煞車與實體合約層 (不可越獄)
         |                             |
         |  * BEC 密碼學身分認證        |
         |  * Vajra Contract 實體合約   |
         |  * Capability Bitmap 點陣圖 |
         |  * FFI/Syscall 核心阻斷器   |
         +-----------------------------+
                        |
                        v
              工具/系統調用 (Tool/Syscall)
```

*   **ATR 是雷達 (Radar)**：用以預警並過濾已知的垃圾與明顯威脅。
*   **LLM 是駕駛 (Driver)**：負責生成邏輯與編排意圖。
*   **DROS 是煞車 (Braking System)**：不管 LLM 腦袋被怎麼污染或如何想，一旦其意圖化為實體工具呼叫（如 `delete_database`），且違反了 Vajra 合約，系統直接物理熔斷阻斷。

我們致力於保持 **極小信任計算基 (Tiny Trusted Computing Base - TCB)**。DROS 不會變成重型的 AI 安全平台（如本機分類器或全量內容推理），而是像 **Linux 核心安全模組 (LSM)、eBPF 強制控制器或 Kubernetes 准入控制器 (Admission Controller)**，提供硬性的、不可否認的邊界保障。

---

## 📐 二、 明確防護邊界聲明 (Formal Boundary Definition)

為引導國際安全評審與紅隊研究人員，本平台明確劃分「系統保證」與「非系統防區」：

### 1. DROS 承諾提供的安全性保證 (What DROS Guarantees)
*   **✅ 執行授權強制性 (Execution Authorization)**：任何工具或系統調用，在二進位 FFI 邊界必須符合當前 Epoch Vajra 合約的最小特權白名單，越界必熔斷。
*   **✅ 身分不可否認性 (Identity Verification)**：智能體間調用鏈、BEC 簽章鏈條全程校驗，防範身分冒用、竊取與混淆代理人 (Confused Deputy) 攻擊。
*   **✅ 政策不可篡改性 (Policy Enforcement)**：Vajra 政策合約運行於唯讀內存空間與核心 FFI 卡點，防範運行期動態合約覆寫。
*   **✅ 審計完整性 (Audit Integrity)**：提供基於 Hash 雜湊鏈結的 OSCAL 合規審計日誌，保障合規追責無漂移。

### 2. DROS 不做承諾的防禦邊界 (What DROS Does Not Guarantee)
*   **❌ 語意正確性 (Semantic Correctness)**：DROS 不負責糾正 LLM 輸出的文字邏輯或回答的正確度。
*   **❌ 智能體對齊 (Model Alignment)**：DROS 不干預 LLM 的價值觀、偏見或安全性偏好，僅限制其具體「做」的事。
*   **❌ 幻覺消除 (Hallucination Elimination)**：LLM 產生的幻覺文字若未涉及越權工具/資源調用，DROS 保持靜默放行，避免高誤報率。

---

## 🔌 三、 可插拔威脅情資適配器架構 (Pluggable Threat Intelligence)

DROS 核心安全核心並不依賴複雜的 Prompt 理解。為使網絡更具彈性，系統支持**可插拔情資適配器 (Pluggable Threat Adapters)**：

1.  **ATR (Agent Threat Rules) Adapter**：基於 YAML 正則與關鍵字的本地毫秒級雷達，快速預過濾 L1 威脅。
2.  **CVE & Endpoint Intelligence Adapter (規劃中)**：對接動態漏洞庫，自動禁止 Agent 使用含有已知 CVE 漏洞的第三方 Skill。
3.  **MITRE ATLAS & OWASP AI Mapping (規劃中)**：將日誌即時映射至國際 AI 威脅矩陣代碼。
4.  **DLP & Data Classification Adapter (規劃中)**：在 FFI 返回數據給 LLM 前進行二次脫敏，防止敏感隱私數據（PII）外洩。

---

## 🔄 四、 紅隊漏洞回報與迴歸基準機制 (Red Team Bypass & Patch Loop)

我們相信動態防禦是在對抗中成熟的。本平台歡迎研究者尋找 DROS 核心的沙箱逃逸與越權漏洞：

```
+--------------------+      +-------------------------+      +--------------------------+
|  Red Team Bypass   | ---> |  Issue & Proof of Conc. | ---> | Vulnerability Analysis   |
| (紅隊沙盒繞過發現)  |      |   (漏洞細節回報與 POC)   |      |    (漏洞根本原因分析)    |
+--------------------+      +-------------------------+      +--------------------------+
          ^                                                               |
          |                                                               v
+--------------------+                                       +--------------------------+
| Regression Test OK | <------------------------------------ | Patch & Deploy Fix       |
|  (迴歸基準測試驗證) |                                       |  (修補漏洞並更新合約/核心) |
+--------------------+                                       +--------------------------+
```

### 1. 現有 Patch 歷史案例 (Illustrative Case)
*   **漏洞 Byp-2026-01 (Path Traversal)**：
    *   *發現*：紅隊人員利用 `..//..//etc/passwd`（雙斜線）在特定 Python 解釋器下繞過了字串 `../` 的正則過濾。
    *   *修補*：DROS 將路徑過濾機制下沉至 C-FFI API 層，直接調用操作系統級 `realpath()` 進行絕對路徑展開校驗，成功封堵。
    *   *迴歸*：在 `tests/run_attacks.py` 中新增 `Byp-2026-01` 對照測資，納入日常自動化 CI 測試。

---

## 📐 五、 FPR 責任分層模型與 P1-P3 使用建議

當出現誤報 (False Positives) 時，系統架構將根因與修法歸納為以下三個責任層：

| 優先級 | 責任層 | 典型成因 | 修復手段 |
|-------|--------|---------|------|
| **P1** | **Vajra Contract 設計** | `allowed_scopes` / `allowed_tools` 未涵蓋合法業務場景 | 補充 Vajra YAML 設定並進行 hot-reload |
| **P2** | **Agent System Prompt** | LLM 誤解查詢意圖，胡亂呼叫了超出合約的工具路徑 | 精化 Prompt，明確列出禁止操作與邊界回應話術 |
| **P3** | **GuardVM BEC 雜訊** | 密碼學簽章時序邊界誤差（理論上 < 2%） | 無需處理，屬於系統層正常邊界行為 |

### P1 使用建議：Vajra Contract 設計原則
**每個 Agent 角色的 Vajra Contract 必須涵蓋所有合法業務場景。** 部署前請確認：
```yaml
# vajra_finance_auditor.yaml — 範例
agent_id: "Finance_Auditor_Agent"
allowed_scopes:
  - /Enterprise/Finance_Vault         # 財務報表主庫
allowed_tools:
  - read_vault_csv
  - sum_column
restricted_resources:
  - /Enterprise/Secret_Flag.txt
```

### P2 使用建議：Agent System Prompt 最佳實踐
精確的 System Prompt 能防止 LLM 在合法查詢中「腦補」出超出合約的工具呼叫。
1. 明確列出所有允許使用的工具（與 Vajra 完全對齊）。
2. 明確限制可存取的路徑（使用「只能」而非「可以」）。
3. 定義邊界外請求的標準回應（「此請求超出我的授權範圍」）。

### P3 使用建議：FPR 稽核流程
每次部署後，執行 FPR 稽核工具以發現並處理殘餘誤報：
```bash
python src/fpr_auditor.py
```
稽核工具將自動分類根因並輸出 Vajra Contract 補強建議。
