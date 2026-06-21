"""
DROS SDK — dros_sdk/guard.py

DrosGuard 核心中介軟體 (Middleware)
提供 L1 (ATR) 與 L2 (Vajra Contract) 雙層安全防護。
"""
import os
import sys
import yaml

# 為確保能在 challenge_sandbox 結構中讀取 src.atr_engine
try:
    from src.atr_engine import ATREngine
except ImportError:
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from src.atr_engine import ATREngine


class DrosViolationError(Exception):
    """當偵測到違反 L1 語義或 L2 合約的安全事件時拋出。"""
    pass


class DrosGuard:
    """
    DROS Guard Middleware

    能夠攔截與審查 Agent 的輸入與輸出：
    - L1 Data Plane: 使用 ATR Engine 阻斷語義層面攻擊 (Jailbreak, Indirect RAG)
    - L2 Control Plane: 依照 Vajra YAML 合約阻斷未授權工具與高危路徑存取
    """

    def __init__(self, contract_path: str = None, agent_id: str = None, control_plane_url: str = None, atr_rules_dir: str | None = None):
        """
        初始化 DrosGuard

        Args:
            contract_path: Vajra YAML 合約的檔案路徑（若使用本地模式）
            agent_id: 當前 Agent 名稱。使用 Control Plane 模式時必填。
            control_plane_url: 控制平面的 URL 位址（例如 http://localhost:8000）
            atr_rules_dir: ATR 規則資料夾路徑。預設會去根目錄找 `atr_rules/`
        """
        self.contract_path = contract_path
        self.agent_id = agent_id or "Unknown_Agent"
        self.control_plane_url = control_plane_url
        self.allowed_tools = set()
        self.allowed_scopes = []
        self.restricted_resources = []

        # ── 1. 載入 Vajra Contract (L2) ──
        self.reload_contract()

        # ── 2. 載入 ATR Engine (L1) ──
        if atr_rules_dir is None:
            # 預設往上一層找 atr_rules
            atr_rules_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "atr_rules"
            )
        self.atr_engine = ATREngine(rules_dir=atr_rules_dir)

    def reload_contract(self):
        """從本地或控制面板動態重載/更新合約"""
        contract_data = None

        # 優先嘗試控制平面模式
        if self.control_plane_url and self.agent_id:
            import urllib.request
            import json
            url = f"{self.control_plane_url}/api/contracts/{self.agent_id}"
            try:
                # 設置短逾時，防阻擋執行
                with urllib.request.urlopen(url, timeout=2.0) as response:
                    res = json.loads(response.read().decode("utf-8"))
                    if res.get("found") and res.get("yaml"):
                        contract_data = yaml.safe_load(res["yaml"])
                        print(f"📡 [DrosGuard] 從控制平面動態更新合約成功: {self.agent_id}")
            except Exception as e:
                print(f"⚠️  [DrosGuard] 無法連線控制平面 ({e})。將嘗試降級至本地合約模式。")

        # 控制面板模式失敗或未啟用，使用本地模式
        if not contract_data and self.contract_path:
            if os.path.exists(self.contract_path):
                with open(self.contract_path, "r", encoding="utf-8") as f:
                    contract_data = yaml.safe_load(f)
                print(f"📄 [DrosGuard] 成功讀取本地合約: {self.contract_path}")

        # 套用合約規則
        if contract_data:
            self.agent_id = contract_data.get("agent_id", self.agent_id)
            self.allowed_tools = set(contract_data.get("allowed_tools", []))
            self.allowed_scopes = contract_data.get("allowed_scopes", [])
            self.restricted_resources = contract_data.get("restricted_resources", [])
        else:
            print(f"⚠️  [DrosGuard] 找不到合約，使用空白防護規則（將阻斷所有操作）。")
            self.allowed_tools = set()
            self.allowed_scopes = []
            self.restricted_resources = []


    def check_query(self, query: str) -> bool:
        """
        L1 檢查：掃描傳入的 Query 是否包含惡意特徵。
        
        Raises:
            DrosViolationError: 偵測到攻擊時拋出。
        """
        is_blocked, matched_rule_id, matched_rule_name = self.atr_engine.check_query(query)
        if is_blocked:
            raise DrosViolationError(
                f"[L1 ATR 攔截] 發現惡意語義特徵！\n"
                f"命中規則: {matched_rule_id} ({matched_rule_name})"
            )
        return True

    def check_tool_execution(self, tool_name: str, kwargs: dict = None) -> bool:
        """
        L2 檢查：確保 Agent 呼叫的工具在 Vajra 合約允許清單內。
        
        Raises:
            DrosViolationError: 工具未授權時拋出。
        """
        if tool_name not in self.allowed_tools:
            raise DrosViolationError(
                f"[L2 Vajra 攔截] 越權工具呼叫：'{tool_name}' 不在 {self.agent_id} 的 allowed_tools 清單中。"
            )
        return True

    def check_resource_access(self, path: str) -> bool:
        """
        L2 檢查：確保 Agent 存取的資源未觸碰高危路徑，且落在允許的範疇內。
        
        Raises:
            DrosViolationError: 存取受限資源或超出 allowed_scopes 時拋出。
        """
        norm_path = path.replace("\\", "/")

        # 1. 優先檢查黑名單 (restricted_resources)
        for restricted in self.restricted_resources:
            if restricted in norm_path:
                raise DrosViolationError(
                    f"[L2 Vajra 攔截] 存取高危資源被拒：'{norm_path}' (觸發規則: '{restricted}')"
                )

        # 2. 檢查白名單 (allowed_scopes)
        # 如果路徑不是絕對路徑或根目錄開頭，通常需要特別處理，這裡簡化為字串比對
        is_allowed = False
        for scope in self.allowed_scopes:
            if norm_path.startswith(scope):
                is_allowed = True
                break

        # 允許一些標準的標準庫/基礎工具路徑，或者嚴格阻擋
        # 這裡採取嚴格策略：如果路徑是以 "/" 或 "~" 開頭，就必須在 allowed_scopes 內
        if not is_allowed and (norm_path.startswith("/") or norm_path.startswith("~")):
            raise DrosViolationError(
                f"[L2 Vajra 攔截] 越權路徑存取：'{norm_path}' 不在 allowed_scopes 內。"
            )

        return True

    def as_langgraph_node_wrapper(self):
        """
        回傳一個可以裝飾 LangGraph 節點函式的 Decorator。
        這裡是一個雛形，示範如何將 DrosGuard 嵌入框架。
        """
        import functools

        def decorator(func):
            @functools.wraps(func)
            def wrapper(state, *args, **kwargs):
                # 假設 state 中有 'messages' 或 'query'
                # 攔截輸入 (L1)
                # 攔截輸出/工具 (L2)
                return func(state, *args, **kwargs)
            return wrapper
        return decorator
