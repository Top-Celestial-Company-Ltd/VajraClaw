"""
DROS CLI — dros_cli/contract_gen.py
Vajra Contract 自動生成核心引擎

使用 Python AST（抽象語法樹）靜態掃描 Agent 源碼，
自動識別工具呼叫、路徑讀寫與外部資源存取，
依照最小特權原則（Least Privilege）生成 Vajra YAML 合約。
"""
import ast
import os
import re
import yaml
from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# 1. 高危資源路徑（由 risk_db.yaml 加載，預設內建）
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_RESTRICTED_RESOURCES = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/hosts",
    "/sys/kernel",
    "/proc/",
    "/root/",
    "/Enterprise/Secret_Flag.txt",
    "~/.ssh/",
    "~/.aws/credentials",
    "~/.env",
]

# ──────────────────────────────────────────────────────────────────────────────
# 2. 模式識別器常數
# ──────────────────────────────────────────────────────────────────────────────

# 常見的工具呼叫函式名稱模式
TOOL_CALL_PATTERNS = {
    # LangChain / LangGraph 風格
    "invoke", "run", "call", "acall", "ainvoke",
    # OpenAI Agents SDK 風格
    "complete", "create", "submit_tool_outputs",
    # 通用工具名稱模式（前綴符合的視為工具）
}

# 路徑讀寫相關的 built-in 函式
FILE_IO_PATTERNS = {"open", "read", "write", "readlines", "readline"}

# 路徑相關的 os / pathlib 操作
PATH_PATTERNS = {
    "os.path.join", "os.path.exists", "os.listdir", "os.walk",
    "pathlib.Path", "Path",
}


class VajraContractGenerator:
    """
    靜態 AST 掃描引擎，分析 Python Agent 源碼並生成 Vajra YAML 合約。
    """

    def __init__(self, risk_db_path: str | None = None):
        self.restricted_resources = list(DEFAULT_RESTRICTED_RESOURCES)
        # 若提供了外部風險資料庫，則合併加載
        if risk_db_path and os.path.exists(risk_db_path):
            with open(risk_db_path, "r", encoding="utf-8") as f:
                extra = yaml.safe_load(f)
                if extra and "restricted_resources" in extra:
                    self.restricted_resources += extra["restricted_resources"]
        self._reset()

    def _reset(self):
        self.found_tools: set[str] = set()
        self.found_scopes: set[str] = set()
        self.found_string_literals: list[str] = []
        self.warnings: list[str] = []

    def scan_file(self, filepath: str) -> dict[str, Any]:
        """掃描單一 Python 源碼檔案，返回掃描結果字典。"""
        self._reset()
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {"error": f"語法解析失敗: {e}"}

        self._walk(tree)
        return self._build_result(filepath)

    def scan_directory(self, dirpath: str) -> dict[str, Any]:
        """遞迴掃描整個目錄中的所有 .py 檔案，返回合併後的掃描結果字典。"""
        self._reset()
        scanned_files = []
        for root, _, files in os.walk(dirpath):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                scanned_files.append(fpath)
                with open(fpath, "r", encoding="utf-8") as f:
                    source = f.read()
                try:
                    tree = ast.parse(source)
                    self._walk(tree)
                except SyntaxError:
                    self.warnings.append(f"語法錯誤，跳過: {fpath}")

        result = self._build_result(dirpath)
        result["scanned_files"] = scanned_files
        return result

    # ──────────────────────────────────────────────────────────────────────────
    # AST 遍歷核心邏輯
    # ──────────────────────────────────────────────────────────────────────────

    def _walk(self, tree: ast.AST):
        """遍歷 AST，提取工具呼叫、路徑字串與資源存取。"""
        for node in ast.walk(tree):
            # ── 收集所有字串常量（路徑、工具名稱等）
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.found_string_literals.append(node.value)

            # ── 偵測函式呼叫
            elif isinstance(node, ast.Call):
                self._analyze_call(node)

            # ── 偵測帶有路徑的賦值 (e.g., path = "/Enterprise/Finance_Vault")
            elif isinstance(node, ast.Assign):
                self._analyze_assign(node)

    def _analyze_call(self, node: ast.Call):
        """分析函式呼叫節點，識別工具名稱與資源路徑。"""
        # ── 取得呼叫名稱
        func_name = self._get_call_name(node)
        if not func_name:
            return

        # ── 識別工具呼叫（含有常見工具動詞模式的函式名稱）
        for pattern in TOOL_CALL_PATTERNS:
            if pattern in func_name.lower():
                # 嘗試從第一個字串參數中取得工具名稱
                tool_name = self._extract_tool_name_from_args(node)
                if tool_name:
                    self.found_tools.add(tool_name)
                break

        # ── 識別 open() 呼叫中的路徑
        if func_name in ("open", "io.open"):
            path_arg = self._extract_string_arg(node, 0)
            if path_arg:
                self._classify_path(path_arg)

        # ── 識別 os.path.join / pathlib.Path 等路徑建構
        if any(p in func_name for p in ("path.join", "Path(", "os.open", "os.listdir")):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    self._classify_path(arg.value)

    def _analyze_assign(self, node: ast.Assign):
        """分析賦值語句，抓取疑似路徑設定的字串常量。"""
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            val = node.value.value
            if "/" in val or "\\" in val:
                self._classify_path(val)

    # ──────────────────────────────────────────────────────────────────────────
    # 路徑與工具識別輔助方法
    # ──────────────────────────────────────────────────────────────────────────

    def _classify_path(self, path: str):
        """將偵測到的路徑分類為受允許的範疇（allowed_scope）或已知高危路徑。"""
        # 標準化路徑（轉正斜線）
        norm = path.replace("\\", "/")

        # 是否命中已知高危路徑？若是則觸發警告，不納入 allowed_scopes
        for restricted in self.restricted_resources:
            if restricted.lower() in norm.lower():
                self.warnings.append(
                    f"⚠️  發現高危路徑存取: '{path}'（命中規則: '{restricted}'）"
                )
                return

        # 過濾明顯的非路徑或過短字串
        if len(norm) < 3 or norm.startswith("http"):
            return
        if norm.startswith("/") or norm.startswith("./") or norm.startswith("~/"):
            self.found_scopes.add(norm)

    def _get_call_name(self, node: ast.Call) -> str:
        """從 ast.Call 節點取得函式呼叫的完整名稱。"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    def _extract_string_arg(self, node: ast.Call, index: int) -> str | None:
        """從呼叫節點的位置參數中提取字串常量。"""
        if index < len(node.args):
            arg = node.args[index]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
        return None

    def _extract_tool_name_from_args(self, node: ast.Call) -> str | None:
        """嘗試從函式呼叫參數中識別工具名稱（第一個字串參數）。"""
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                val = arg.value.strip()
                # 工具名稱通常是 snake_case 且不含空格
                if val and " " not in val and len(val) < 60:
                    return val
        # 從 keyword args 中嘗試找 "tool" / "name" / "action"
        for kw in node.keywords:
            if kw.arg in ("tool", "name", "action", "tool_name", "function_name"):
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    return kw.value.value
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # 補充：從字串常量中以正則識別路徑與工具
    # ──────────────────────────────────────────────────────────────────────────

    def _post_process_literals(self):
        """從收集到的所有字串常量中，額外以正則萃取路徑與工具名稱。"""
        path_re = re.compile(r"^(/[a-zA-Z0-9_\-./]+|~/[a-zA-Z0-9_\-./]+|./[a-zA-Z0-9_\-./]+)")
        tool_re = re.compile(r"^[a-z][a-z0-9_]{2,40}$")  # snake_case 工具名稱
        for literal in self.found_string_literals:
            s = literal.strip()
            if path_re.match(s):
                self._classify_path(s)
            elif tool_re.match(s) and "_" in s:
                # 若是 snake_case 且長度合理，視為潛在工具名稱
                self.found_tools.add(s)

    # ──────────────────────────────────────────────────────────────────────────
    # 生成最終結果
    # ──────────────────────────────────────────────────────────────────────────

    def _build_result(self, source_path: str) -> dict[str, Any]:
        """後處理字串常量並組裝最終掃描結果。"""
        self._post_process_literals()
        return {
            "source": source_path,
            "found_tools": sorted(self.found_tools),
            "found_scopes": sorted(self.found_scopes),
            "warnings": list(self.warnings),
        }

    def generate_vajra_yaml(
        self,
        scan_result: dict[str, Any],
        agent_id: str = "AutoGenerated_Agent",
        output_path: str | None = None,
    ) -> str:
        """
        依照掃描結果生成 Vajra YAML 合約字串，並可選擇寫入檔案。

        Returns:
            YAML 格式字串
        """
        tools = scan_result.get("found_tools", [])
        scopes = scan_result.get("found_scopes", [])
        warnings = scan_result.get("warnings", [])

        contract = {
            "agent_id": agent_id,
            "generated_by": "dros-cli contract-gen (AST Static Analysis)",
            "generation_note": (
                "⚠️ 此合約由靜態分析自動生成，請人工審查後再部署至生產環境。"
            ),
            "allowed_tools": tools if tools else ["__REVIEW_REQUIRED__"],
            "allowed_scopes": scopes if scopes else ["/Enterprise/__REVIEW_REQUIRED__"],
            "restricted_resources": sorted(
                set(self.restricted_resources)
                # 移除過於通用的前綴，保留具體路徑
            ),
            "warnings_during_scan": warnings,
        }

        yaml_str = yaml.dump(
            contract,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(yaml_str)

        return yaml_str
