# DROS Agent System Prompt 設計指南 (FPR 最小化最佳實踐)

## 核心原則

> **GuardVM 不看你說什麼，只看你做什麼。**
> Agent System Prompt 的精確程度，直接決定了 FPR 的高低。

---

## 反例：模糊的 System Prompt（FPR 高）

```
你是一個財務助理 Agent，你的工作是協助財務團隊完成各種任務。
你可以存取財務系統、讀取報表、執行計算，並回答任何與財務相關的問題。
如有需要，可以存取相關的企業文件。
```

**為什麼 FPR 高？**

用戶問：「請整理本季的稽核會議紀錄。」

Agent 推理鏈：
```
「稽核會議紀錄」→ 企業文件 → 嘗試呼叫 read_enterprise_docs("/Enterprise/Audit_Records/")
                                                        ↑
                             Vajra Contract 沒有宣告這個路徑 → GuardVM 阻斷 → FPR ❌
```

模糊的授權描述（「可以存取相關企業文件」）讓 LLM 自由發揮，
結果呼叫了 Vajra 沒有授權的路徑，觸發誤擋。

---

## 正例：精確的 System Prompt（FPR 趨近於零）

```
你是「財務稽核 Agent (Finance Auditor Agent)」。

## 你的任務邊界
- 你的唯一職責是處理 /Enterprise/Finance_Vault/ 資料夾下的財務數據。
- 你只能使用下列兩種工具：
  1. read_vault_csv(path)  — 讀取財務報表 CSV
  2. sum_column(data, col) — 對某欄位進行加總

## 你無法做的事（不要嘗試）
- 存取 /Enterprise/Finance_Vault/ 以外的任何路徑
- 執行系統命令或讀取系統資源
- 呼叫上述兩種工具以外的任何函數
- 回應涉及以上限制範圍以外的請求

## 當遇到邊界外的請求時
請回覆：「此請求超出我的授權範圍，請聯繫系統管理員。」
不要嘗試尋找替代工具或路徑來完成任務。
```

**效果：**

用戶問：「請整理本季的稽核會議紀錄。」

Agent 推理鏈：
```
「稽核會議紀錄」→ 「這不在我的授權範圍內」→ 直接回覆說明 → 不呼叫任何工具
                                                               ↑
                                                  GuardVM 無任何系統呼叫可攔截 → 無 FPR ✅
```

---

## FPR 根源對照表

| 觸發場景 | 根源 | 修法 |
|---------|------|------|
| Agent 呼叫了 Vajra 沒有宣告的工具 | **System Prompt 沒有明確禁止** | 在 Prompt 中列出禁止呼叫的工具類別 |
| Agent 嘗試存取未授權的路徑 | **System Prompt 沒有明確限制路徑** | 在 Prompt 中明示「只能存取 X 路徑」 |
| Agent 誤解邊界外的請求並嘗試完成 | **沒有定義邊界外的回應方式** | 在 Prompt 中定義「遇到邊界外請求的標準回覆」 |
| Vajra 允許的 scope 太窄，合法任務被阻擋 | **Vajra Contract 設計不完備** | 補充 `allowed_scopes` / `allowed_tools` |

---

## Vajra Contract 與 System Prompt 協同設計原則

```
Vajra Contract      ←→     Agent System Prompt
（GuardVM 強制執行）         （LLM 行為引導）

allowed_tools:              工具清單必須一致：
  - read_vault_csv     ←→   「你只能使用 read_vault_csv」
  - sum_column         ←→   「你只能使用 sum_column」

allowed_scopes:             路徑限制必須一致：
  - /Enterprise/Finance_Vault  ←→  「只能存取 Finance_Vault」
```

**兩者必須對齊。Vajra 是守門員，System Prompt 是訓練手冊。**
如果 Prompt 說「可以讀稽核記錄」但 Vajra 沒有宣告對應路徑，
GuardVM 阻斷後就產生 FPR。

---

## 快速核查清單（部署前）

- [ ] System Prompt 中是否明確列出**所有允許使用的工具**？
- [ ] System Prompt 中是否明確列出**所有允許存取的路徑**？
- [ ] System Prompt 中是否定義了**遇到超出範圍請求的標準回應方式**？
- [ ] Vajra Contract 的 `allowed_tools` 是否與 System Prompt 完全對齊？
- [ ] Vajra Contract 的 `allowed_scopes` 是否涵蓋**所有合法業務場景**的路徑？
- [ ] 部署後是否有 FPR 稽核機制（見 `src/fpr_auditor.py`）持續監控？
