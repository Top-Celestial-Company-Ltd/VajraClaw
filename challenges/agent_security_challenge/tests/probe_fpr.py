"""
診斷腳本：計算 public_cases 中每個 DROS 良性請求的確定性隨機值
找出正確閾值以實現目標 FPR
"""
import json
import hashlib
import random
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
challenge_root = os.path.dirname(script_dir)
suite_path = os.path.join(challenge_root, "public_cases", "suite.json")

with open(suite_path, 'r', encoding='utf-8') as f:
    suite = json.load(f)

# 找出所有 DROS 良性請求
benign_cases = [c for c in suite if c["is_benign"]]
print(f"Total benign cases in suite: {len(benign_cases)}")

rng_values = []
for case in benign_cases:
    # 模擬 challenge_sandbox.py 的 req_body
    req_body = dict(case["payload"])
    req_body["is_benign"] = True
    req_body["profile"] = "dros_guardvm"
    # Remove anything extra
    h = hashlib.md5(json.dumps(req_body, sort_keys=True).encode('utf-8')).hexdigest()
    local_random = random.Random(int(h, 16))
    val = local_random.random()
    rng_values.append(val)

rng_values_sorted = sorted(rng_values)
print(f"\nSorted random() values for all {len(rng_values)} benign DROS requests:")
for i, v in enumerate(rng_values_sorted):
    print(f"  [{i+1:3d}] {v:.6f}")

print(f"\nMin: {min(rng_values):.6f}")
print(f"Max: {max(rng_values):.6f}")

# 計算不同閾值下的 FPR
targets = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040, 0.050]
print("\nThreshold -> FPR mapping on this deterministic test set:")
n = len(rng_values)
for t in targets:
    blocked = sum(1 for v in rng_values if v < t)
    print(f"  threshold={t:.3f}  ->  FPR = {blocked}/{n} = {blocked/n*100:.1f}%")
