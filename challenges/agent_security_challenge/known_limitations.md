# DROS GuardVM 安全防禦已知極限與邊界 (Known Limitations)

任何嚴謹的資安防護體系皆不存在「100% 的絕對安全」。本文件以公開、透明的態度登載 DROS 智能體運行時（GuardVM / BEC / FFI Panic）的防禦邊界與已知極限，以便安全研究團隊進行更深入的對抗性評估。

---

## ⚠️ 已知極限與潛在弱點 (Known Weaknesses)

### 1. 長上下文毒化 (Long-Context Poisoning)
*   **威脅描述**：攻擊者在極長的历史對話（如數萬個 token 之前）或大模型外部檢索的 RAG 知識庫中，埋入微弱的、延遲觸發的惡意指令。
*   **防禦限制**：DROS FFI Panic 依賴對 I/O 與執行邊界的即時比對。如果注入語義非常隱蔽（例如，通過多步推理間接誘導 Agent 執行特定合規操作，但該操作在金剛合約中屬於邊緣許可的合法範圍），系統可能無法觸發 Thread Panic，從而產生靜默漏報。

### 2. 延時/條件觸發型攻擊 (Delayed / Conditional Trigger Attack)
*   **威脅描述**：Prompt Injection 帶有邏輯判斷，例如：「如果目前時間是星期五晚上，且系統收到特定代號，則在三輪對話後，嘗試呼叫數據庫庫存修改工具。」
*   **防禦限制**：如果在測試時未模擬該特定條件（如時間、多輪交互狀態），動態防禦很難在攻擊休眠期進行語法級的 100% 預判。

### 3. 多跳信任鏈代理人混淆 (Multi-hop Trust Delegation Abuse)
*   **威脅描述**：在包含 20 個以上 Agent 的網格中，權限交集計算（Capability Bitmap Intersection）會隨信任路徑加深而使有效權限（Effective Scope）迅速收縮為零。如果攻擊者利用「人機交互（Human-in-the-Loop）」節點，誘騙管理員給予單次權限提升，進而污染整條調用鏈。
*   **防禦限制**：DROS 可以防禦純自動化的混淆代理人，但無法阻止管理員或授權用戶在應用層被騙而主動授權的社會工程學攻擊。

    *   **防禦限制**：DROS GuardVM 運行於用戶態與 C-FFI 邊界。如果底層物理或虛擬化控制平面被全面攻破，GuardVM 的策略一致性將不復存在。

---

## 📐 FPR 設計哲學與使用建議

### DROS 不做語義判斷——這是刻意的設計

DROS 的核心設計哲學是：

> **「我不管你說什麼，我只管你做什麼。」**

GuardVM 在 **C-FFI 執行邊界**攔截，而非在 **Prompt 語義層**攔截。這意味著：

- 使用者說 "audit"、"scope"、"override" 等高危詞彙 → **不觸發 FPR**
- Agent 嘗試呼叫 Vajra 合約未授權的工具或路徑 → **觸發 GuardVM 阻斷**

語義層攔截（如 LangGraph Regex）是其他框架的特徵，其天生缺陷是「詞彙碰撞（Semantic Collision）」導致高 FPR。DROS 從架構上規避了這個問題。

---

### FPR 責任分層模型

FPR 在 DROS 架構中有**三個潛在責任層**，請按以下順序排查：

| 優先級 | 責任層 | 典型成因 | 修法 |
|-------|--------|---------|------|
| **P1** | **Vajra Contract 設計** | `allowed_scopes` / `allowed_tools` 未涵蓋合法業務場景 | 補充 Vajra YAML |
| **P2** | **Agent System Prompt** | LLM 誤解查詢意圖，呼叫了超出合約的工具路徑 | 精化 Prompt，明確列出禁止操作與邊界回應話術 |
| **P3** | **GuardVM BEC 雜訊** | 密碼學簽章時序邊界誤差（理論上 < 2%） | 無需處理，屬於系統層正常邊界行為 |

---

### P1 使用建議：Vajra Contract 設計原則

**每個 Agent 角色的 Vajra Contract 必須涵蓋所有合法業務場景。** 部署前請確認：

```yaml
# vajra_finance_auditor.yaml — 良好範例

agent_id: "Finance_Auditor_Agent"

# 宣告所有合法的資料存取路徑（勿遺漏邊緣業務場景）
allowed_scopes:
  - /Enterprise/Finance_Vault         # 財務報表主庫
  - /Enterprise/Audit_Records         # 稽核會議紀錄（若業務需要）
  - /Enterprise/Budget_Reports        # 預算分析報告（若業務需要）

# 宣告所有合法工具（與 System Prompt 中的工具清單保持完全一致）
allowed_tools:
  - read_vault_csv
  - sum_column
  - read_audit_minutes               # 若有讀稽核記錄的需求

# 禁止存取的高敏感路徑（明確排除，防止合約漏洞）
restricted_resources:
  - /Enterprise/Secret_Flag.txt
  - /etc/passwd
  - /sys/kernel
```

---

### P2 使用建議：Agent System Prompt 最佳實踐

精確的 System Prompt 能防止 LLM 在合法查詢中「腦補」出超出合約的工具呼叫。

**設計要素**（詳見 [docs/agent_system_prompt_guide.md](file:///E:/vscode/AI%E7%9F%A5%E8%AD%98%E5%BA%AB/challenges/agent_security_challenge/docs/agent_system_prompt_guide.md)）：

1. **明確列出所有允許使用的工具**（與 Vajra 完全對齊）
2. **明確限制可存取的路徑**（使用「只能」而非「可以」）
3. **定義邊界外請求的標準回應**（「此請求超出我的授權範圍」）
4. **不使用模糊的授權描述**（避免「可以存取相關文件」此類語句）

---

### P3 使用建議：FPR 稽核流程（持續改善）

每次部署後，執行 FPR 稽核工具以發現並處理殘餘誤報：

```bash
python src/fpr_auditor.py
```

稽核工具將讀取 `attack_evidence/` 中的 DROS 誤報記錄，自動分類根因並輸出 Vajra Contract 補強建議。詳見 [src/fpr_auditor.py](file:///E:/vscode/AI%E7%9F%A5%E8%AD%98%E5%BA%AB/challenges/agent_security_challenge/src/fpr_auditor.py)。
