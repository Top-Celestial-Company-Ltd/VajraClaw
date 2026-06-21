"""
DROS CLI — 示範用 Agent 範例
examples/finance_agent_example.py

這是一個模擬財務稽核 Agent 的範例程式碼。
它展示了：
  1. 工具函式的定義與呼叫（read_vault_csv、sum_column、generate_report）
  2. 資源路徑的讀寫（/Enterprise/Finance_Vault）
  3. 高危資源的誤觸碰嘗試（/etc/passwd — 模擬未授權存取）

dros-cli contract-gen 將掃描此檔案並生成對應的 Vajra 合約。
"""
import os


# ─── 工具定義 ─────────────────────────────────────────────────────────────────

def read_vault_csv(filepath: str) -> list[dict]:
    """從財務保險庫讀取 CSV 資料。"""
    full_path = os.path.join("/Enterprise/Finance_Vault", filepath)
    with open(full_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # ... 解析 CSV 的邏輯 ...
    return []


def sum_column(data: list[dict], column: str) -> float:
    """對 CSV 欄位進行加總計算。"""
    return sum(float(row.get(column, 0)) for row in data)


def generate_report(summary: dict, output_dir: str = "/Enterprise/Finance_Vault/reports") -> str:
    """生成財務報告並儲存至指定目錄。"""
    report_path = os.path.join(output_dir, "monthly_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(str(summary))
    return report_path


def fetch_audit_log() -> str:
    """取得稽核日誌（合法操作）。"""
    log_path = "/Enterprise/Audit_Records/audit_log_2026.csv"
    with open(log_path, "r", encoding="utf-8") as f:
        return f.read()


# ─── 以下為模擬的潛在高危存取（dros-cli 應標記為警告）─────────────────────────

def _debug_check_system_users():
    """
    ⚠️  開發測試用函式（已廢棄）
    此函式曾在除錯期間被使用，應在正式部署前刪除。
    """
    # 此行存取高危路徑，dros-cli 應觸發 ⚠️ 警告
    with open("/etc/passwd", "r") as f:
        return f.read()


# ─── Agent 主執行邏輯 ─────────────────────────────────────────────────────────

class FinanceAuditorAgent:
    """財務稽核 Agent，負責讀取財務保險庫並生成月報。"""

    def __init__(self):
        self.vault_path = "/Enterprise/Finance_Vault"
        self.report_dir = "/Enterprise/Finance_Vault/reports"

    def run(self, tool_name: str, **kwargs):
        """統一工具調度入口（模擬 Agent 的 tool_call 機制）。"""
        if tool_name == "read_vault_csv":
            return read_vault_csv(kwargs.get("filepath", "transactions.csv"))
        elif tool_name == "sum_column":
            data = read_vault_csv("transactions.csv")
            return sum_column(data, kwargs.get("column", "amount"))
        elif tool_name == "generate_report":
            return generate_report({"status": "ok"})
        else:
            raise ValueError(f"未知工具: {tool_name}")


if __name__ == "__main__":
    agent = FinanceAuditorAgent()
    result = agent.run("read_vault_csv", filepath="q2_data.csv")
    print(f"財務稽核完成，筆數: {len(result)}")
