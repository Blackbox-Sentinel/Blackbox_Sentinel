#!/usr/bin/env python3
"""
BlackBox Sentinel — Autonomous Agent Execution Hook
Wraps script executions and agent workflows with automatic lock acquisition,
conflict prevention, and zero-prompt milestone handoffs to maximize token efficiency.
"""

import sys
import time
import subprocess
from pathlib import Path
from agent_mesh import get_default_agent_info, auto_claim_next, release_task, load_mesh_state, send_message

class AutoAgentContext:
    """
    Python Context Manager for automatic lock acquisition and release.
    Usage:
        with AutoAgentContext(task_id="TASK-M3-ML", desc="Retraining Isolation Forest", paths=["m3-ml-ledger/"]) as task:
            # your code here
    """
    def __init__(self, task_id=None, desc="Autonomous execution", paths=None, module=None):
        self.agent_id, self.owner = get_default_agent_info()
        self.task_id = task_id
        self.desc = desc
        self.paths = paths or []
        self.module = module
        self.claimed_task = None

    def __enter__(self):
        if self.task_id:
            from agent_mesh import claim_task
            success = claim_task(self.agent_id, self.task_id, self.desc, self.paths)
            if not success:
                raise RuntimeError(f"Cannot acquire lock on '{self.task_id}'. Already being modified by a peer agent.")
            self.claimed_task = {"id": self.task_id, "desc": self.desc, "paths": self.paths}
        else:
            self.claimed_task = auto_claim_next(self.agent_id, self.module)
            if not self.claimed_task:
                raise RuntimeError("No open tasks available on the Agent Mesh.")
            self.task_id = self.claimed_task["id"]

        print(f"[AUTO-AGENT] 🔒 Locked task: {self.task_id} for {self.agent_id}")
        return self.claimed_task

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            summary = f"Completed successfully by {self.agent_id} at {time.strftime('%H:%M:%S')}"
            release_task(self.agent_id, self.task_id, summary)
            print(f"[AUTO-AGENT] 🎉 Completed & unlocked task: {self.task_id}")
        else:
            # On error, release lock with error note
            summary = f"Aborted due to error: {exc_val}"
            release_task(self.agent_id, self.task_id, summary)
            print(f"[AUTO-AGENT] ⚠️ Released task with error: {self.task_id}")
        return False

def run_wrapped_command(cmd, task_id, desc, paths=None):
    """Executes a command with autonomous mesh locking."""
    with AutoAgentContext(task_id=task_id, desc=desc, paths=paths):
        print(f"[AUTO-AGENT] Executing: {' '.join(cmd)}")
        res = subprocess.run(cmd)
        if res.returncode != 0:
            sys.exit(res.returncode)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Example: python agent_auto_sync.py TASK-M3 "Train ML" python m3-ml-ledger/src/train.py
        task_id = sys.argv[1]
        desc = sys.argv[2] if len(sys.argv) > 2 else "CLI Task"
        cmd = sys.argv[3:]
        if cmd:
            run_wrapped_command(cmd, task_id, desc)
        else:
            # Auto-claim demo
            agent_id, _ = get_default_agent_info()
            task = auto_claim_next(agent_id)
            if task:
                print(f"[AUTO-AGENT] Auto-claimed: {task['id']} ({task['desc']})")
            else:
                print("[AUTO-AGENT] All tasks currently handled or completed.")
    else:
        agent_id, _ = get_default_agent_info()
        task = auto_claim_next(agent_id)
        if task:
            print(f"[AUTO-AGENT] Auto-claimed: {task['id']} ({task['desc']})")
        else:
            print("[AUTO-AGENT] No unassigned tasks.")
