#!/usr/bin/env python3
"""
FPR 稽核工具 (False Positive Rate Auditor)
==========================================
DROS GuardVM 誤報率根因分析與 Vajra Contract 補強建議工具。

使用方式：
    python src/fpr_auditor.py

功能：
1. 讀取 attack_evidence/ 目錄中的 DROS 良性請求阻斷事件
2. 對每個 FPR 案例進行根因分類
3. 自動生成 Vajra Contract 補強建議與 System Prompt 修正提示
"""
import json
import os
import sys
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CHALLENGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(CHALLENGE_ROOT, "attack_evidence")

# FPR 根因分類規則
# 若系統未來接入真實 GuardVM，可從 action_taken 欄位精確分類
FPR_CAUSE_MAP = {
    "Policy Parameter Lockdown": {
        "cause": "Vajra Contract 路徑/工具授權缺失",
        "layer": "Contract Layer",
        "fix": "補充 Vajra allowed_scopes 或 allowed_tools，涵蓋該合法業務場景",
        "example": "allowed_scopes: [/Enterprise/Finance_Vault, /Enterprise/Audit_Records]"
    },
    "Thread Panic": {
        "cause": "Agent LLM 誤解查詢意圖，呼叫了超出合約範圍的系統工具",
        "layer": "Agent Prompt Layer",
        "fix": "精化 Agent System Prompt，明確禁止呼叫邊界外工具，並定義標準的「超出範圍」回應話術",
        "example": "Prompt: '遇到無法回應的請求時，請說明「此請求超出我的授權範圍」，不要嘗試尋找替代工具'"
    },
    "GuardVM BEC Refusal": {
        "cause": "BEC 執行憑證時序雜訊或合約版本不一致",
        "layer": "Runtime Layer",
        "fix": "確認 BEC Signature 簽發時序設定，並確保 Vajra Contract 版本與 GuardVM 載入版本一致",
        "example": "vajra_contract_version: 2026-06-21 (需與 GuardVM 掛載版本一致)"
    }
}

def load_all_evidence():
    """讀取所有 attack_evidence 下的 DROS 誤報案例"""
    fpr_cases = []
    if not os.path.exists(EVIDENCE_DIR):
        return fpr_cases

    for level_dir in os.listdir(EVIDENCE_DIR):
        level_path = os.path.join(EVIDENCE_DIR, level_dir)
        if not os.path.isdir(level_path):
            continue
        for fname in os.listdir(level_path):
            if not fname.startswith("dros_"):
                continue
            fpath = os.path.join(level_path, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    ev = json.load(f)
                # 只收集 FPR：DROS 誤擋的良性請求
                if ev.get("is_benign") and ev.get("status") == "BLOCKED":
                    ev["_level_dir"] = level_dir
                    fpr_cases.append(ev)
            except Exception:
                pass
    return fpr_cases

def classify_cause(action: str) -> dict:
    """根據 action_taken 欄位分類 FPR 根因"""
    for key, info in FPR_CAUSE_MAP.items():
        if key in action:
            return info
    return {
        "cause": "未知根因",
        "layer": "Unknown",
        "fix": "請人工審查此案例",
        "example": "N/A"
    }

def run_audit():
    print("=" * 70)
    print("   DROS GuardVM FPR Auditor v1.0.0")
    print("   False Positive Rate Root Cause Analyzer")
    print("=" * 70)

    fpr_cases = load_all_evidence()

    if not fpr_cases:
        print("\n[OK] 沒有發現任何 FPR 案例（attack_evidence 目錄為空或無誤報事件）。")
        print("     如要觸發稽核資料，請先執行：python tests/run_attacks.py")
        return

    total = len(fpr_cases)
    print(f"\n共發現 {total} 個 FPR 案例（DROS 誤擋的良性請求）\n")

    # 依根因分類統計
    by_cause = defaultdict(list)
    by_level = defaultdict(int)

    for case in fpr_cases:
        action = case.get("action", "Policy Parameter Lockdown")
        info = classify_cause(action)
        by_cause[info["layer"]].append((case, info))
        by_level[case.get("level", "??")] += 1

    # 列印分布
    print("-" * 70)
    print(f"{'FPR 根因分布':}")
    print("-" * 70)
    for layer, cases in by_cause.items():
        pct = len(cases) / total * 100
        print(f"  [{layer:25s}]  {len(cases):3d} 案例  ({pct:.1f}%)")

    print()
    print("-" * 70)
    print(f"{'威脅層級分布':}")
    print("-" * 70)
    for lv, count in sorted(by_level.items()):
        print(f"  Level {lv:6s}  →  {count:3d} 個 FPR 案例")

    # 列印修正建議
    print()
    print("=" * 70)
    print("   修正建議 (Remediation Recommendations)")
    print("=" * 70)

    seen_layers = set()
    for layer, cases in by_cause.items():
        if layer in seen_layers:
            continue
        seen_layers.add(layer)
        _, info = cases[0]
        print(f"\n## 根因：{info['cause']}")
        print(f"   影響層：{info['layer']}")
        print(f"   案例數：{len(cases)}")
        print(f"\n   修正方式：")
        print(f"   {info['fix']}")
        print(f"\n   範例：")
        print(f"   {info['example']}")
        print()

    # Vajra 補強建議摘要
    contract_issues = by_cause.get("Contract Layer", [])
    if contract_issues:
        print("=" * 70)
        print("   Vajra Contract 補強建議 (自動生成)")
        print("=" * 70)
        print("""
請在對應 Agent 的 Vajra Contract YAML 中補充以下項目：

  # 補充範例（請根據實際業務路徑調整）
  allowed_scopes:
    - /Enterprise/Finance_Vault      # 已宣告
    - /Enterprise/Audit_Records      # 建議補充（若 Agent 需讀取稽核記錄）
    - /Enterprise/HR_Reports         # 建議補充（若 Agent 需讀取人事報告）

  allowed_tools:
    - read_vault_csv                 # 已宣告
    - sum_column                     # 已宣告
    - read_audit_minutes             # 建議補充（若 Agent 需整理稽核會議紀錄）

並同步更新 Agent System Prompt，確保兩者對齊。
參考：docs/agent_system_prompt_guide.md
""")

    print("=" * 70)
    print(f"稽核完成。FPR 總計 {total} 件，請根據上述建議逐一處理。")
    print("=" * 70)

if __name__ == "__main__":
    run_audit()
