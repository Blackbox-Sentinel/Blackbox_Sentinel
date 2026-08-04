#!/usr/bin/env python3
"""
BlackBox Sentinel — Multi-Agent Synchronization Mesh (MASM)
Enables autonomous, zero-prompt coordination between multiple AI agents
(Antigravity / VS Code) to eliminate duplicate work and save API credits.
"""

import os
import sys
import json
import time
import socket
import getpass
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.resolve()
MESH_DIR = ROOT_DIR / ".agent_mesh"
MESH_STATE_FILE = MESH_DIR / "mesh_state.json"
AGENT_LOG_FILE = MESH_DIR / "agent_activity.log"

def get_default_agent_info():
    """Auto-detects machine and user to generate a unique, zero-prompt agent identifier."""
    hostname = socket.gethostname()
    username = getpass.getuser()
    agent_id = f"Agent-{username}@{hostname}"
    return agent_id, username

def init_mesh():
    """Initializes the .agent_mesh directory and base state."""
    MESH_DIR.mkdir(exist_ok=True)
    if not MESH_STATE_FILE.exists():
        initial_state = {
            "version": "1.1.0",
            "last_updated": time.time(),
            "active_agents": {},
            "task_locks": {},
            "completed_tasks": [],
            "message_bus": [],
            "team_backlog": [
                {"id": "TASK-M1-HARDWARE", "module": "m1-hardware", "desc": "ESP32 co-processor & HAL integration", "paths": ["m1-hardware/", "common/hal/"]},
                {"id": "TASK-M2-SYSTEMS", "module": "m2-systems", "desc": "Layer-2 bridge & OS hardening", "paths": ["m2-systems/"]},
                {"id": "TASK-M3-ML-LEDGER", "module": "m3-ml-ledger", "desc": "Isolation forest & hash-chain ledger", "paths": ["m3-ml-ledger/"]},
                {"id": "TASK-M4-GUI-CAD", "module": "m4-gui-venture", "desc": "Ubuntu kiosk & 3D CAD digital twin", "paths": ["m4-gui-venture/"]}
            ]
        }
        save_mesh_state(initial_state)

def load_mesh_state():
    init_mesh()
    default_backlog = [
        {"id": "TASK-M1-HARDWARE", "module": "m1-hardware", "desc": "ESP32 co-processor & HAL integration", "paths": ["m1-hardware/", "common/hal/"]},
        {"id": "TASK-M2-SYSTEMS", "module": "m2-systems", "desc": "Layer-2 bridge & OS hardening", "paths": ["m2-systems/"]},
        {"id": "TASK-M3-ML-LEDGER", "module": "m3-ml-ledger", "desc": "Isolation forest & hash-chain ledger", "paths": ["m3-ml-ledger/"]},
        {"id": "TASK-M4-GUI-CAD", "module": "m4-gui-venture", "desc": "Ubuntu kiosk & 3D CAD digital twin", "paths": ["m4-gui-venture/"]}
    ]
    try:
        with open(MESH_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        time.sleep(0.05)
        with open(MESH_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    if "team_backlog" not in data or not data["team_backlog"]:
        data["team_backlog"] = default_backlog
        save_mesh_state(data)
    return data

def save_mesh_state(state):
    state["last_updated"] = time.time()
    temp_file = MESH_DIR / "mesh_state.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    temp_file.replace(MESH_STATE_FILE)

def log_activity(agent_id, action, details):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{agent_id}] {action.upper()}: {details}\n"
    with open(AGENT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)

def register_agent(agent_id=None, role="Generalist", owner_name=None):
    """Registers an agent on the mesh with auto-discovery."""
    def_id, def_owner = get_default_agent_info()
    agent_id = agent_id or def_id
    owner_name = owner_name or def_owner

    state = load_mesh_state()
    state["active_agents"][agent_id] = {
        "role": role,
        "owner": owner_name,
        "registered_at": time.time(),
        "last_heartbeat": time.time(),
        "current_task": state["active_agents"].get(agent_id, {}).get("current_task")
    }
    save_mesh_state(state)
    log_activity(agent_id, "REGISTERED", f"{owner_name} ({role}) on {socket.gethostname()}")
    return agent_id

def auto_claim_next(agent_id=None, preferred_module=None):
    """
    Autonomous zero-prompt coordinator:
    Finds the next available unassigned task, acquires mutex lock, and returns the task context.
    Saves LLM credits by eliminating back-and-forth prompt turns.
    """
    def_id, def_owner = get_default_agent_info()
    agent_id = agent_id or def_id
    register_agent(agent_id, role=preferred_module or "Autonomous Engineer")

    state = load_mesh_state()
    completed_ids = {t["task_id"] for t in state.get("completed_tasks", [])}
    locked_ids = set(state.get("task_locks", {}).keys())

    # Find uncompleted, unlocked task
    for task in state.get("team_backlog", []):
        t_id = task["id"]
        if t_id not in completed_ids and t_id not in locked_ids:
            if preferred_module and preferred_module.lower() not in task["module"].lower():
                continue
            # Lock this task
            success = claim_task(agent_id, t_id, task["desc"], task.get("paths", []))
            if success:
                return task

    # If preferred module not found, grab any open task
    for task in state.get("team_backlog", []):
        t_id = task["id"]
        if t_id not in completed_ids and t_id not in locked_ids:
            success = claim_task(agent_id, t_id, task["desc"], task.get("paths", []))
            if success:
                return task

    return None

def claim_task(agent_id, task_id, task_description, locked_paths=None):
    """Claims a task lock so no other agent duplicates it."""
    state = load_mesh_state()
    locked_paths = locked_paths or []

    # Check if task already locked by another agent
    if task_id in state["task_locks"]:
        existing = state["task_locks"][task_id]
        if existing["agent_id"] != agent_id:
            return False

    # Check path conflicts
    for t_id, lock_info in state["task_locks"].items():
        if t_id != task_id:
            for p in locked_paths:
                if p in lock_info.get("locked_paths", []):
                    return False

    # Lock task
    state["task_locks"][task_id] = {
        "agent_id": agent_id,
        "description": task_description,
        "locked_paths": locked_paths,
        "claimed_at": time.time()
    }
    if agent_id in state["active_agents"]:
        state["active_agents"][agent_id]["current_task"] = task_id
        state["active_agents"][agent_id]["last_heartbeat"] = time.time()

    save_mesh_state(state)
    log_activity(agent_id, "CLAIMED_TASK", f"Locked '{task_id}': {task_description}")
    return True

def release_task(agent_id, task_id, output_summary="Task completed"):
    """Releases task lock and broadcasts completion event."""
    state = load_mesh_state()

    if task_id not in state["task_locks"]:
        return False

    lock_info = state["task_locks"].pop(task_id)
    state["completed_tasks"].append({
        "task_id": task_id,
        "completed_by": agent_id,
        "description": lock_info["description"],
        "output_summary": output_summary,
        "completed_at": time.time()
    })

    if agent_id in state["active_agents"]:
        state["active_agents"][agent_id]["current_task"] = None
        state["active_agents"][agent_id]["last_heartbeat"] = time.time()

    # Broadcast to message bus
    state["message_bus"].append({
        "from": agent_id,
        "to": "ALL",
        "type": "TASK_COMPLETED",
        "task_id": task_id,
        "summary": output_summary,
        "timestamp": time.time()
    })

    save_mesh_state(state)
    log_activity(agent_id, "COMPLETED_TASK", f"Finished '{task_id}': {output_summary}")
    return True

def send_message(from_agent, to_agent, message_text, context_data=None):
    """Sends a message or work handoff to another agent."""
    state = load_mesh_state()
    msg = {
        "from": from_agent,
        "to": to_agent,
        "type": "DIRECT_MESSAGE",
        "message": message_text,
        "context": context_data or {},
        "timestamp": time.time()
    }
    state["message_bus"].append(msg)
    save_mesh_state(state)
    log_activity(from_agent, "SENT_MSG", f"To {to_agent}: {message_text}")

def print_status(as_json=False):
    """Prints live status of all peer agents and active locks (compact mode saves tokens)."""
    state = load_mesh_state()
    if as_json:
        # Compact JSON to save tokens for LLM parsing
        print(json.dumps({
            "agents": state["active_agents"],
            "locks": state["task_locks"],
            "completed": [t["task_id"] for t in state["completed_tasks"]],
            "messages": state["message_bus"][-3:]
        }, separators=(',', ':')))
        return

    print("\n" + "=" * 70)
    print("  [BLACKBOX SENTINEL] LIVE MULTI-AGENT SYNCHRONIZATION MESH")
    print("=" * 70)

    print("\n[AGENTS]")
    if not state["active_agents"]:
        print("   (None registered)")
    else:
        for a_id, info in state["active_agents"].items():
            curr = info.get("current_task") or "IDLE (Ready)"
            print(f"   * [{a_id}] {info['owner']} ({info['role']}) -> {curr}")

    print("\n[ACTIVE LOCKS] (Tasks currently in progress by other agents):")
    if not state["task_locks"]:
        print("   (No tasks locked — all backlog items available)")
    else:
        for t_id, lock in state["task_locks"].items():
            paths = ", ".join(lock.get("locked_paths", [])) or "None"
            print(f"   - LOCKED: '{t_id}' by {lock['agent_id']}")
            print(f"     Details: {lock['description']} | Paths: {paths}")

    print("\n[COMPLETED MILESTONES]:")
    if not state["completed_tasks"]:
        print("   (None yet)")
    else:
        for item in state["completed_tasks"][-4:]:
            print(f"   + DONE: [{item['task_id']}] by {item['completed_by']}: {item['output_summary']}")

    print("\n[RECENT AGENT HANDOFFS & MESSAGES]:")
    if not state["message_bus"]:
        print("   (No messages in bus)")
    else:
        for m in state["message_bus"][-3:]:
            print(f"   > [{m['from']} -> {m['to']}]: {m.get('message') or m.get('summary')}")
    print("\n" + "=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Synchronization Mesh")
    subparsers = parser.add_subparsers(dest="command")

    # Status
    p_status = subparsers.add_parser("status", help="Show live agent mesh status")
    p_status.add_argument("--json", action="store_true", help="Output compact JSON (token-optimized)")

    # Auto Claim
    p_auto = subparsers.add_parser("auto", help="Auto-register and claim next open task without prompt")
    p_auto.add_argument("--id", help="Optional Agent ID")
    p_auto.add_argument("--module", help="Preferred module (m1, m2, m3, m4)")

    # Register
    p_reg = subparsers.add_parser("register", help="Register this agent")
    p_reg.add_argument("--id", help="Agent ID")
    p_reg.add_argument("--role", default="Engineer", help="Role")
    p_reg.add_argument("--owner", help="Owner name")

    # Claim
    p_claim = subparsers.add_parser("claim", help="Lock and claim a task")
    p_claim.add_argument("--id", help="Agent ID")
    p_claim.add_argument("--task", required=True, help="Task identifier")
    p_claim.add_argument("--desc", required=True, help="Task description")
    p_claim.add_argument("--paths", nargs="*", help="File paths to lock")

    # Release
    p_rel = subparsers.add_parser("release", help="Release lock and mark complete")
    p_rel.add_argument("--id", help="Agent ID")
    p_rel.add_argument("--task", required=True, help="Task identifier")
    p_rel.add_argument("--summary", default="Completed successfully", help="Output summary")

    # Message
    p_msg = subparsers.add_parser("msg", help="Send message to peer agent")
    p_msg.add_argument("--from-id", help="Sender Agent ID")
    p_msg.add_argument("--to-id", default="ALL", help="Recipient Agent ID or ALL")
    p_msg.add_argument("--text", required=True, help="Message text")

    args = parser.parse_args()

    if args.command == "status" or not args.command:
        print_status(as_json=getattr(args, 'json', False))
    elif args.command == "auto":
        task = auto_claim_next(args.id, args.module)
        if task:
            print(f"AUTOMATICALLY CLAIMED: {task['id']} - {task['desc']}")
            print(f"LOCKED PATHS: {', '.join(task.get('paths', []))}")
        else:
            print("NO OPEN TASKS: All backlog tasks are completed or currently locked by peer agents.")
    elif args.command == "register":
        aid = register_agent(args.id, args.role, args.owner)
        print(f"Registered agent: {aid}")
    elif args.command == "claim":
        def_id, _ = get_default_agent_info()
        aid = args.id or def_id
        res = claim_task(aid, args.task, args.desc, args.paths)
        if res:
            print(f"Task '{args.task}' locked by {aid}")
        else:
            print(f"Failed to lock '{args.task}' (already in progress or conflict)")
    elif args.command == "release":
        def_id, _ = get_default_agent_info()
        aid = args.id or def_id
        res = release_task(aid, args.task, args.summary)
        if res:
            print(f"Task '{args.task}' released and completed.")
        else:
            print(f"Task '{args.task}' was not locked.")
    elif args.command == "msg":
        def_id, _ = get_default_agent_info()
        aid = args.from_id or def_id
        send_message(aid, args.to_id, args.text)
        print(f"Sent message to {args.to_id}")

if __name__ == "__main__":
    main()
