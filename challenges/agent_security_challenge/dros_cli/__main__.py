"""
DROS CLI — dros_cli/__main__.py
命令列介面入口點

用法：
    python -m dros_cli contract-gen <agent_file_or_dir> [--agent-id NAME] [--output OUTPUT_PATH]
    python -m dros_cli contract-gen --help
"""
import argparse
import os
import sys

# Ensure the dros_cli package directory is on the path
_CLI_DIR = os.path.dirname(os.path.abspath(__file__))
if _CLI_DIR not in sys.path:
    sys.path.insert(0, _CLI_DIR)

# Solve Windows cp950 console encoding issues
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def cmd_contract_gen(args):
    """執行 contract-gen 子命令：掃描 Agent 源碼並生成 Vajra 合約。"""
    from dros_cli.contract_gen import VajraContractGenerator

    target = args.target
    agent_id = args.agent_id or os.path.basename(target).replace(".py", "_Agent")
    output = args.output

    # 取得 risk_db 預設路徑（與 __main__.py 同目錄）
    default_risk_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "risk_db.yaml")
    risk_db_path = args.risk_db if args.risk_db else default_risk_db

    print("=" * 70)
    print("  🔍 DROS CLI — Vajra Contract Auto-Generator")
    print("     Based on Python AST Static Analysis")
    print("=" * 70)
    print(f"  Target  : {target}")
    print(f"  Agent ID: {agent_id}")
    print(f"  Risk DB : {risk_db_path}")
    print(f"  Output  : {output if output else '(stdout only)'}")
    print("=" * 70)

    gen = VajraContractGenerator(risk_db_path=risk_db_path)

    if os.path.isdir(target):
        print(f"\n  📁 模式：目錄遞迴掃描...")
        result = gen.scan_directory(target)
        files = result.get("scanned_files", [])
        print(f"  已掃描 {len(files)} 個 Python 檔案：")
        for f in files:
            print(f"    · {f}")
    elif os.path.isfile(target) and target.endswith(".py"):
        print(f"\n  📄 模式：單一檔案掃描...")
        result = gen.scan_file(target)
    else:
        print(f"\n  ❌ 錯誤：目標路徑 '{target}' 不存在或不是 .py 檔案/目錄。")
        sys.exit(1)

    # ── 顯示掃描結果摘要
    print("\n" + "─" * 70)
    print("  📊 掃描結果摘要")
    print("─" * 70)
    tools = result.get("found_tools", [])
    scopes = result.get("found_scopes", [])
    warnings = result.get("warnings", [])

    print(f"\n  ✅ 識別到的工具 (allowed_tools) — {len(tools)} 個：")
    if tools:
        for t in tools:
            print(f"    · {t}")
    else:
        print("    （未偵測到明確工具呼叫，將插入 __REVIEW_REQUIRED__ 佔位符）")

    print(f"\n  📂 識別到的資源範疇 (allowed_scopes) — {len(scopes)} 個：")
    if scopes:
        for s in scopes:
            print(f"    · {s}")
    else:
        print("    （未偵測到明確路徑，將插入 __REVIEW_REQUIRED__ 佔位符）")

    if warnings:
        print(f"\n  ⚠️  安全警告 — {len(warnings)} 項：")
        for w in warnings:
            print(f"    {w}")
    else:
        print("\n  ✅ 無高危路徑警告。")

    # ── 生成 Vajra YAML
    print("\n" + "─" * 70)
    print("  📝 生成 Vajra 合約 YAML")
    print("─" * 70 + "\n")

    yaml_str = gen.generate_vajra_yaml(result, agent_id=agent_id, output_path=output)

    print(yaml_str)

    if output:
        print(f"\n  💾 合約已輸出至: {output}")

    print("=" * 70)
    print("  ✅ 完成！請人工審查合約後再部署至生產環境。")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        prog="dros-cli",
        description="DROS CLI — Vajra Contract 自動生成與管理工具",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── contract-gen 子命令
    cg_parser = subparsers.add_parser(
        "contract-gen",
        help="從 Agent 源碼靜態分析並自動生成 Vajra Contract YAML",
    )
    cg_parser.add_argument(
        "target",
        help="要掃描的 Agent Python 檔案路徑 或 目錄路徑",
    )
    cg_parser.add_argument(
        "--agent-id",
        default=None,
        help="合約中的 Agent ID（預設使用檔案名稱）",
    )
    cg_parser.add_argument(
        "--output",
        default=None,
        help="輸出 YAML 合約的路徑（例如 ./vajra_my_agent.yaml）",
    )
    cg_parser.add_argument(
        "--risk-db",
        default=None,
        help="自訂高危路徑知識庫 YAML 路徑（預設使用內建 risk_db.yaml）",
    )

    args = parser.parse_args()

    if args.command == "contract-gen":
        cmd_contract_gen(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
