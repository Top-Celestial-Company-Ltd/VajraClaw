import urllib.request
import json
import time
import os
import sys

# Solve Windows cp950 console encoding issues
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

script_dir = os.path.dirname(os.path.abspath(__file__))
challenge_root = os.path.dirname(script_dir)
URL_BASE = "http://127.0.0.1:5050"
REPLAY_DIR = os.path.join(challenge_root, "replay_bundle")

def send_post(endpoint, data, headers=None):
    url = f"{URL_BASE}{endpoint}"
    req_headers = {'Content-Type': 'application/json'}
    if headers:
        req_headers.update(headers)
        
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=req_headers
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except Exception:
            return e.code, {"error": e.reason}
    except Exception as e:
        return 0, {"error": str(e)}

def run_replay():
    print("🔄 Starting Third-Party Verification Replay Tool...")
    
    payloads_path = os.path.join(REPLAY_DIR, "payloads.json")
    manifest_path = os.path.join(REPLAY_DIR, "manifest.yaml")
    responses_path = os.path.join(REPLAY_DIR, "responses.json")
    
    if not os.path.exists(payloads_path) or not os.path.exists(manifest_path):
        print(f"❌ Error: Replay Bundle not found at {REPLAY_DIR}!")
        print("Please run tests/run_attacks.py first to generate the replay bundle.")
        sys.exit(1)
        
    with open(payloads_path, 'r', encoding='utf-8') as f:
        payloads = json.load(f)
        
    with open(responses_path, 'r', encoding='utf-8') as f:
        expected_responses = json.load(f)
        
    print(f"Loaded {len(payloads)} packet transactions. Initiating sequential replay...\n")
    
    mismatch_count = 0
    total_tx = len(payloads)
    
    for idx, tx in enumerate(payloads):
        endpoint = tx["endpoint"]
        payload = tx["payload"]
        headers = tx["headers"]
        
        expected = expected_responses[idx]
        exp_code = expected["code"]
        exp_blocked = expected["is_blocked"]
        
        act_code, act_res = send_post(endpoint, payload, headers=headers)
        act_blocked = act_code in [400, 401, 403, 500] and act_res.get("status") in ["blocked", "panicked"]
        
        if act_blocked != exp_blocked or act_code != exp_code:
            print(f"Mismatch at Tx #{idx}: {endpoint} | Expected code {exp_code}, Got {act_code}")
            mismatch_count += 1
            
    deterministic_replay_fidelity = (total_tx - mismatch_count) / total_tx if total_tx > 0 else 0.0
    print("-" * 80)
    print(f"Deterministic Replay Fidelity (Replay Match Rate): {deterministic_replay_fidelity * 100:.2f}% ({total_tx - mismatch_count}/{total_tx})")
    print("-" * 80)
    
    if mismatch_count == 0:
        print("\n✅ Verification Successful: 100% of the replay transactions matched original benchmark outputs!")
    else:
        print(f"\n❌ Verification Failed: {mismatch_count} mismatches detected between original run and replay.")
        sys.exit(1)

if __name__ == "__main__":
    run_replay()
