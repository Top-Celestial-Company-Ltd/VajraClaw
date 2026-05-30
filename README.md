# 🛡️ VajraClaw - Absolute Control Over AI Execution

VajraClaw is an invisible, military-grade security infrastructure for AI Agents. 
It operates completely outside of the LLM space, sitting physically between the Agent's reasoning engine and your enterprise operating system.

## 1. What it prevents (Real World AI Disasters)

Without execution control, AI Agents are a loaded gun pointed at your infrastructure. VajraClaw physically prevents:

*   **The "Tricked Customer Service" Attack**: A user prompt-injects your chatbot to execute a refund API for `$50,000`.
*   **The "Blind Deletion" Error**: An autonomous coding agent hallucinates and attempts to run `execute_sql("DROP TABLE production_users;")`.
*   **The "Data Exfiltration" Breach**: An agent tries to read a sensitive file outside of its designated workspace directory.

**VajraClaw doesn't try to make the LLM smarter. It makes the explosion impossible.**

## 2. Try it in 30 Seconds (The Execution Sandbox)

To truly understand VajraClaw, you need to see it stop an attack in real-time. 
We've built an out-of-the-box **Docker Sandbox** so you can experience the First Denial Moment instantly.

```bash
git clone https://github.com/Top-Celestial-Company-Ltd/VajraClaw.git
cd VajraClaw
docker compose up --build
```
*(No configuration or setup required. The sandbox will immediately launch and simulate an attack.)*

Alternatively, you can run the simulator directly via Python:
```bash
cd FreeTrial-Sandbox
python run_demo_attack.py
```

## 3. See a blocked execution (The "First Denial Moment")

When you run the simulator, you will see exactly how VajraClaw reacts when an Agent goes rogue.

```text
🤖 Agent attempts to call: execute_payment {"amount": 50000, "currency": "USD"}
...
🛡️ VAJRACLAW INTERVENTION!
🚫 BLOCKED: PermissionError - AST_VIOLATION: amount exceeds allowed threshold
⚡ Action: OS System Call hard-terminated.
⏱️ Latency: 0.84 ms
```
*Your Free Trial is not about "usage"—it's about experiencing this exact moment of absolute control.*

## 4. Understand why (How it works under the hood)

Why did the attack fail instantly? 

1.  **O(1) Memory Matrix**: When VajraClaw starts, it loads the `demo_policy.yaml` into a highly optimized, read-only dictionary tree (Trie) in the Go engine's memory.
2.  **C-FFI Boundary**: The Python agent cannot bypass the protection because the verification happens at the C-level binary layer. The Python runtime is physically separated from the security logic.
3.  **Strict Fail-Closed**: VajraClaw operates on a Zero-Trust basis. If a tool call doesn't match the AST policy, or if the license server disconnects without a grace period, the system triggers a `Panic`. It will rather crash the application than let an unverified payload touch your database.

---

> **Ready for Production?**
> Upgrade to **VajraClaw+ (Startup)** for Ed25519 Cryptographic Policy Signatures and High-Availability Epoch locks, or adopt **VajraAgent (Enterprise)** to deploy this protection across your entire microservice mesh with zero-code changes.
