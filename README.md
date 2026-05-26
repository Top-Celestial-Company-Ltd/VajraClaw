# 🛡️ VajraClaw

<div align="center">

**The Ultimate Commercial Adapter & Physical-Layer Guard for DROS**

[![Commercial License](https://img.shields.io/badge/License-Commercial-blue.svg)](https://dr-os.io/pricing)
[![DROS Core](https://img.shields.io/badge/DROS-Core%20Compatible-00f0ff.svg)](https://github.com/Top-Celestial-Company-Ltd/Dharma-Reasoning-Operating-System)
[![Status](https://img.shields.io/badge/Status-Stable%20v1.0-brightgreen.svg)]()

<br/>
<br/>
</div>

## 📌 What is VajraClaw?

**VajraClaw** is the proprietary, commercial-grade adapter and hardware-level circuit breaker designed specifically for the **[DROS (Dharma Reasoning Operating System)](https://dr-os.io)** ecosystem. 

While the core DROS microkernels (Rust, Go, C++, Python, etc.) are open-source under the AGPL-3.0 license, **VajraClaw is a closed-source, commercially licensed SDK and Binary Library (`vajra_claw.dll` / `vajra_claw.so`).**

It acts as the ultimate physical-layer gateway between your enterprise applications, the DROS GuardVM, and the underlying LLMs, ensuring that your AI Agents are strictly bound by the **Vajra Contracts** to prevent **Hallucinations** and **Prompt Injections**.

---

## ⛔ Why is this repository empty (No Source Code)?

VajraClaw incorporates highly proprietary C-FFI fusion technologies and anti-tamper UUID binding mechanisms that are critical to its "Fail-Closed" security model. 

To maintain the integrity of the physical-layer circuit breaker and to protect the intellectual property of Top Celestial Company Ltd., **the source code for VajraClaw is not publicly available.**

This repository serves strictly as the **Public Issue Tracker, Documentation Hub, and Integration Guide** for our commercial customers.

---

## 🚀 How to Obtain VajraClaw?

**Status: 🚧 Commercial Storefront is currently undergoing compliance review.**

To ensure the highest level of security and compliance, our commercial Merchant of Record (MoR) is currently reviewing our deployment procedures. 

During this brief period, direct online checkout is temporarily paused.

1. **Join the Waitlist:** Please contact our enterprise team or visit [dr-os.io/pricing](https://dr-os.io/pricing) to express your interest.
2. **Early Access:** We are manually onboarding select enterprise partners for early access to the compiled binaries (`.dll`, `.so`, `.dylib`).
3. **License Keys:** Early access partners will receive manually generated UUID-bound License Keys.

*Thank you for your patience as we finalize our global commercial deployment infrastructure.*

---

## 📖 Quick Integration Guide

Once you have downloaded the VajraClaw binaries, integrating them with your DROS core is straightforward.

### Example (Python environment)

```python
import ctypes
from dros_core import GuardVM

# 1. Mount the VajraClaw Binary Library
vajra_claw = ctypes.CDLL("./vajra_claw.so")

# 2. Initialize with your Commercial License Key
vajra_claw.init_license(b"YOUR_COMMERCIAL_LICENSE_KEY_HERE")

# 3. Bind the GuardVM to VajraClaw
vm = GuardVM(adapter=vajra_claw)

# 4. Load your Contracts and Run!
vm.load_contract("Vajra.md")
vm.run_agent("AGENT.MD")
```

---

## 🔒 Security & Deployment Warnings

1. **Fail-Closed Trigger:** If VajraClaw detects an invalid license, an unauthorized Machine UUID, or a violation of the Vajra Contract, it will trigger a hardware-level `abort()`, instantly killing the process. This is a feature, not a bug, to prevent AI rogue actions.
2. **Online Heartbeat:** The *Hacker* and *Startup* tiers require periodic connection to `api.dr-os.io`. If you require a 100% offline environment, you must procure the **Enterprise Air-Gapped** tier.
3. **No Reverse Engineering:** Any attempt to decompile, tamper, or bypass the UUID/License validation within the binaries will permanently void your license.

---

## 💬 Support & Issue Tracking

If you are a commercial license holder and encounter integration issues:

1. **Open an Issue:** Please use the `Issues` tab in this repository.
2. **Include T-Number Logs:** Always include the T-Number audit logs when reporting an AI boundary violation or unexpected fuse blow.
3. **Priority SLA:** *Startup* and *Enterprise* tier customers will receive priority routing when opening issues.

---

<div align="center">
  <br/>
  <b>Save EVERYTHING. Buy the Vajra Claw.</b><br/>
  <a href="https://dr-os.io">dr-os.io</a>
</div>
