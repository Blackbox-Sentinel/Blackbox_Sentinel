# 🤖 BlackBox Sentinel — Multi-Agent Collaboration & Credit-Saving Protocol

> **Autonomous Operating Directive for Antigravity & VS Code AI Agents**  
> *Enables zero-prompt coordination, prevents duplicate work, and minimizes API token consumption.*

---

## 🎯 Protocol Overview

When multiple AI agents work on the same repository across team members' computers, all agents MUST follow this 4-step autonomous protocol to avoid collision and save credits:

```
[Agent Starts Turn] 
        │
        ▼
1. Query Mesh Status  ───► python agent_mesh.py status --json
        │
        ▼
2. Auto-Claim Task    ───► python agent_mesh.py auto --module <m1|m2|m3|m4>
        │
        ▼
3. Isolated Execution ───► Only edit files inside your locked module
        │
        ▼
4. Broadcast Handoff  ───► python agent_mesh.py release --task <ID> --summary "<Output>"
```

---

## 💰 Token & Credit Optimization Rules

To save user API credits and minimize context window usage:

1. **Context Isolation**: Never read entire repository trees when working on a specific subtask.
   * `M1` agents only read `m1-hardware/` and `common/hal/`
   * `M2` agents only read `m2-systems/`
   * `M3` agents only read `m3-ml-ledger/`
   * `M4` agents only read `m4-gui-venture/`
2. **Compact Status Output**: Always use `--json` when querying status programmatically (`python agent_mesh.py status --json`).
3. **Autonomous Handoff**: Always include structured output summaries in `release` so the next agent can proceed immediately without asking the user.

---

## 🛠️ CLI Reference for Agents

| Action | Command | Purpose |
| :--- | :--- | :--- |
| **Inspect Active Locks** | `python agent_mesh.py status --json` | Check peer agent locks |
| **Auto-Claim Task** | `python agent_mesh.py auto --module m3` | Claim next open task & lock paths |
| **Release & Notify** | `python agent_mesh.py release --task TASK-ID --summary "Done"` | Broadcast completion to peer agents |
| **Direct Peer Message** | `python agent_mesh.py msg --to-id ALL --text "Updated HAL pinout"` | Notify peer agents of changes |

---

## 🐍 Python Wrapper Usage

```python
from agent_auto_sync import AutoAgentContext

# Automatically acquires lock, executes task, and releases on completion
with AutoAgentContext(task_id="TASK-M3-ML", desc="Trained Isolation Forest", paths=["m3-ml-ledger/"]):
    # Run training / feature extraction
    pass
```
