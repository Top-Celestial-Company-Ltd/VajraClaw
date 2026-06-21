"""
DROS SDK — dros_sdk/__init__.py

對外公開的主要 API：
    from dros_sdk import DrosGuard
    from dros_sdk import DrosViolationError

設計目標：
    讓任何框架的 Agent 只需在執行點增加一行，即可獲得完整的雙層防禦：
    - L1：ATR 語義清毒（阻斷已知攻擊特徵）
    - L2：Vajra 合約策略校驗（最小特權執行阻斷）
"""
from dros_sdk.guard import DrosGuard
from dros_sdk.guard import DrosViolationError

__version__ = "0.1.0"
__all__ = ["DrosGuard", "DrosViolationError"]
