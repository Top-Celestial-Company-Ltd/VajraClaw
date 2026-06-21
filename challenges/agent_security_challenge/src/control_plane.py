"""
DROS Control Plane — src/control_plane.py
VajraAgent 輕量級控制面板與動態合約分發伺服器

使用 Python 內建 HTTPServer 實作，免安裝第三方依賴，
提供 REST API 介面給 SDK/Sandbox 與儀表板前端。
"""
import os
import sys
import json
import yaml
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

# 解決 Windows cp950 編碼問題
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 8000
CHALLENGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_PATH = os.path.join(CHALLENGE_ROOT, "logs", "oscal_audit.json")
CONTRACTS_DIR = os.path.join(CHALLENGE_ROOT, "dros_cli", "examples")

# 確保合約目錄存在
os.makedirs(CONTRACTS_DIR, exist_ok=True)


class VajraControlPlaneHandler(BaseHTTPRequestHandler):
    """
    處理控制平面的 HTTP 請求
    """
    
    def log_message(self, format, *args):
        # 覆寫預設日誌輸出，讓控制台更乾淨
        pass

    def send_json(self, data, status=200):
        """輔助方法：發送 JSON 回應。"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_html(self, html_content, status=200):
        """輔助方法：發送 HTML。"""
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def do_OPTIONS(self):
        """處理 CORS 預檢請求。"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        """處理 GET 請求。"""
        # 1. 儀表板首頁
        if self.path in ("/", "/index.html", "/dashboard"):
            self.serve_dashboard()
            return

        # 2. API: 讀取安全日誌 (OSCAL)
        elif self.path == "/api/logs":
            self.handle_get_logs()
            return

        # 3. API: 讀取所有合約清單
        elif self.path == "/api/contracts":
            self.handle_list_contracts()
            return

        # 4. API: 讀取特定 Agent 的合約 (例如 /api/contracts/Finance_Auditor_Agent)
        elif self.path.startswith("/api/contracts/"):
            agent_id = self.path.split("/")[-1]
            self.handle_get_contract(agent_id)
            return

        # 5. 其他靜態資源或 404
        else:
            self.send_json({"error": f"找不到資源: {self.path}"}, 404)

    def do_POST(self):
        """處理 POST 請求。"""
        # 1. API: 更新/發佈特定 Agent 的合約
        if self.path.startswith("/api/contracts/"):
            agent_id = self.path.split("/")[-1]
            self.handle_save_contract(agent_id)
            return
        else:
            self.send_json({"error": "不支援的 POST 路徑"}, 400)

    # ──────────────────────────────────────────────────────────────────────────
    # API 處理方法
    # ──────────────────────────────────────────────────────────────────────────

    def serve_dashboard(self):
        """讀取並回傳前端 HTML 檔案。"""
        tpl_path = os.path.join(CHALLENGE_ROOT, "templates", "dashboard.html")
        if os.path.exists(tpl_path):
            with open(tpl_path, "r", encoding="utf-8") as f:
                html = f.read()
            self.send_html(html)
        else:
            self.send_html("<h1>Vajra 控制台模板遺失。請確認 templates/dashboard.html 存在。</h1>", 404)

    def handle_get_logs(self):
        """解析 OSCAL json 檔案並回傳。"""
        if not os.path.exists(LOGS_PATH):
            self.send_json([])
            return

        try:
            with open(LOGS_PATH, "r", encoding="utf-8") as f:
                logs = json.load(f)
            self.send_json(logs)
        except Exception as e:
            self.send_json({"error": f"讀取日誌失敗: {str(e)}"}, 500)

    def handle_list_contracts(self):
        """列出範例目錄中所有的 Vajra YAML 合約。"""
        contracts = []
        if not os.path.exists(CONTRACTS_DIR):
            self.send_json([])
            return

        for fname in os.listdir(CONTRACTS_DIR):
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                fpath = os.path.join(CONTRACTS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict) and "agent_id" in data:
                        contracts.append({
                            "agent_id": data["agent_id"],
                            "filename": fname,
                            "allowed_tools": data.get("allowed_tools", []),
                            "allowed_scopes": data.get("allowed_scopes", []),
                        })
                except Exception:
                    pass
        self.send_json(contracts)

    def handle_get_contract(self, agent_id):
        """讀取特定 Agent_id 的 YAML 合約，如果不存在則尋找對應檔名。"""
        # 標準化檔名尋找方式
        yaml_filename = f"vajra_{agent_id.lower()}.yaml"
        # 遍歷目錄尋找相符的 agent_id
        target_path = None
        for fname in os.listdir(CONTRACTS_DIR):
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                fpath = os.path.join(CONTRACTS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        c_data = yaml.safe_load(f)
                    if c_data.get("agent_id") == agent_id:
                        target_path = fpath
                        break
                except Exception:
                    pass
        
        # 若找不到相符的，直接指向預設路徑
        if not target_path:
            target_path = os.path.join(CONTRACTS_DIR, yaml_filename)

        if os.path.exists(target_path):
            with open(target_path, "r", encoding="utf-8") as f:
                yaml_content = f.read()
            self.send_json({
                "agent_id": agent_id,
                "yaml": yaml_content,
                "found": True
            })
        else:
            self.send_json({
                "agent_id": agent_id,
                "yaml": "",
                "found": False
            })

    def handle_save_contract(self, agent_id):
        """儲存或更新合約內容。"""
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        
        try:
            req_body = json.loads(post_data.decode("utf-8"))
            yaml_content = req_body.get("yaml", "")

            # 驗證是否為合法 YAML
            parsed_yaml = yaml.safe_load(yaml_content)
            if not parsed_yaml or "agent_id" not in parsed_yaml:
                self.send_json({"error": "YAML 必須包含 'agent_id' 屬性"}, 400)
                return

            # 強制寫入對應檔名
            yaml_filename = f"vajra_{agent_id.lower()}.yaml"
            target_path = os.path.join(CONTRACTS_DIR, yaml_filename)

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)

            self.send_json({
                "success": True,
                "message": f"Agent '{agent_id}' 合約已發佈並存入 {yaml_filename}"
            })
            print(f"📡 [Control Plane] 合約更新成功: {agent_id}")
        except Exception as e:
            self.send_json({"error": f"解析或儲存失敗: {str(e)}"}, 500)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """支援多執行緒的 HTTP 伺服器，防止請求阻塞。"""
    daemon_threads = True


def run_server():
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, VajraControlPlaneHandler)
    print("=" * 70)
    print("📡  DROS Control Plane Server 啟動中...")
    print(f"🔗  管理面板位址: http://localhost:{PORT}/")
    print(f"📂  日誌儲存路徑: {LOGS_PATH}")
    print(f"📂  合約儲存路徑: {CONTRACTS_DIR}")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 正在關閉 Control Plane...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
