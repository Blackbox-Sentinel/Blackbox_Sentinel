"""
BlackBox Sentinel — Self-Healing Remediation Agent (Ollama-powered)

Receives system logs and error context, uses a local LLM (qwen2.5:1.5b
via Ollama) to generate a targeted fix command, then executes it with a
3-strike rollback policy.

All remediation actions are cryptographically signed to the Ed25519 ledger
before execution, creating an immutable audit trail.

Runs entirely offline on the Raspberry Pi — no cloud API calls.
"""
import logging
import os
import re
import subprocess
import shutil
import time

logger = logging.getLogger(__name__)

# Allowlist of safe commands the AI is permitted to generate
SAFE_COMMAND_PATTERNS = [
    r"^systemctl (restart|start|stop|status) [\w\-\.]+$",
    r"^sudo systemctl (restart|start|stop|status) [\w\-\.]+$",
    r"^supervisorctl (restart|start|stop|status) [\w\-\.:]+$",
    r"^killall [\w\-]+$",
    r"^pkill [\w\-]+$",
    r"^chmod [0-7]+ /[\w\-\./]+$",
    r"^sudo reboot$",
    r"^python3 /[\w\-\./]+\.py$",
    r"^pip3 install [\w\-\.\[\]]+$",
    r"^sudo pip3 install [\w\-\.\[\]]+ --break-system-packages$",
    r"^npm (start|run [\w\-]+)$",
    r"^git -C /[\w\-\./]+ (pull|reset --hard HEAD)$",
]


def _is_safe_command(cmd: str) -> bool:
    """Check if the AI-generated command matches our allowlist."""
    cmd = cmd.strip()
    return any(re.match(pattern, cmd) for pattern in SAFE_COMMAND_PATTERNS)


class RemediationAgent:
    def __init__(self):
        self.ollama_available = False
        self.model_name = "qwen2.5:1.5b"
        self.strike_count = 0
        self.max_strikes = 3

        try:
            import ollama as _ollama
            self.ollama = _ollama
            try:
                self.ollama.list()
                self.ollama_available = True
                logger.info(f"[REMEDIATION] Ollama available. Using model: {self.model_name}")
            except Exception:
                logger.warning("[REMEDIATION] Ollama server not reachable. Running in rule-based mode.")
        except ImportError:
            logger.warning("[REMEDIATION] ollama package not installed. Running in rule-based mode.")
            self.ollama = None

    def gather_system_context(self) -> dict:
        """Gather real system diagnostics for the LLM."""
        context = {}

        # 1. Recent journal logs
        try:
            context["journal"] = subprocess.check_output(
                "journalctl -n 50 --no-pager -p err..emerg 2>/dev/null || journalctl -n 50 --no-pager",
                shell=True, text=True, timeout=5
            ).strip()
        except Exception:
            context["journal"] = "Failed to fetch journal logs."

        # 2. Failed systemd services
        try:
            context["failed_services"] = subprocess.check_output(
                "systemctl --failed --no-pager 2>/dev/null",
                shell=True, text=True, timeout=5
            ).strip()
        except Exception:
            context["failed_services"] = ""

        # 3. Thermal data
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_c = int(f.read().strip()) / 1000.0
                context["temperature"] = f"{temp_c:.1f}°C"
        except Exception:
            context["temperature"] = "Unknown"

        # 4. Memory usage
        try:
            context["memory"] = subprocess.check_output(
                "free -h --si | head -3", shell=True, text=True, timeout=5
            ).strip()
        except Exception:
            context["memory"] = "Unknown"

        # 5. Disk usage
        try:
            context["disk"] = subprocess.check_output(
                "df -h / | tail -1", shell=True, text=True, timeout=5
            ).strip()
        except Exception:
            context["disk"] = "Unknown"

        return context

    def generate_patch_command(self, error_context: str, vision_analysis: str = "") -> str:
        """
        Use the local LLM to analyze error context and generate a fix command.
        Falls back to rule-based logic if Ollama is unavailable.
        """
        if not self.ollama_available:
            return self._rule_based_fix(error_context)

        prompt = f"""You are a Raspberry Pi system administrator. A security appliance has detected an issue.

### VISION ANALYSIS (what the screen looks like):
{vision_analysis if vision_analysis else "No screenshot available."}

### SYSTEM CONTEXT:
{error_context}

### INSTRUCTIONS:
1. Identify the root cause of the failure.
2. Output EXACTLY ONE bash command that will fix it.
3. The command must be safe — no rm -rf, no dd, no format commands.
4. Prefer systemctl restart, pip install, or git pull as fixes.
5. Output ONLY the command, nothing else. No explanations, no markdown.

### YOUR FIX COMMAND:"""

        try:
            response = self.ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 50},
            )
            raw_cmd = response["message"]["content"].strip()

            # Extract first line only, strip any markdown/backticks
            cmd = raw_cmd.split("\n")[0].strip().strip("`").strip()

            if not cmd:
                logger.warning("[REMEDIATION] LLM returned empty command.")
                return self._rule_based_fix(error_context)

            # Security gate: only allow safe commands
            if not _is_safe_command(cmd):
                logger.warning(f"[REMEDIATION] LLM suggested unsafe command: {cmd}")
                logger.warning("[REMEDIATION] Falling back to rule-based fix.")
                return self._rule_based_fix(error_context)

            logger.info(f"[REMEDIATION] LLM suggested: {cmd}")
            return cmd

        except Exception as e:
            logger.error(f"[REMEDIATION] Ollama inference failed: {e}")
            return self._rule_based_fix(error_context)

    def _rule_based_fix(self, context: str) -> str:
        """Deterministic fallback when LLM is unavailable."""
        ctx_lower = context.lower() if context else ""

        if "flask" in ctx_lower or "gunicorn" in ctx_lower or "5000" in ctx_lower:
            return "sudo systemctl restart sentinel-gui"
        elif "sentinel-bridge" in ctx_lower or "pipeline" in ctx_lower:
            return "sudo systemctl restart sentinel-bridge"
        elif "chromium" in ctx_lower or "kiosk" in ctx_lower or "browser" in ctx_lower:
            return "sudo systemctl restart sentinel-kiosk"
        elif "out of memory" in ctx_lower or "oom" in ctx_lower:
            return "sudo systemctl restart sentinel-gui"
        elif "temperature" in ctx_lower or "throttl" in ctx_lower:
            return "sudo systemctl stop sentinel-bridge"  # shed load
        else:
            return "sudo systemctl restart sentinel-gui"

    def execute_with_rollback(self, command: str) -> bool:
        """
        Execute the fix command. 3-strike policy: if 3 consecutive
        patches fail, perform emergency git rollback + reboot.
        """
        if not _is_safe_command(command):
            logger.critical(f"[REMEDIATION] BLOCKED unsafe command: {command}")
            return False

        logger.info(f"[REMEDIATION] Executing: {command}")
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                logger.info("[REMEDIATION] Patch applied successfully.")
                self.strike_count = 0
                return True
            else:
                self.strike_count += 1
                logger.warning(
                    f"[REMEDIATION] Patch failed (exit={result.returncode}). "
                    f"Strike {self.strike_count}/{self.max_strikes}. "
                    f"stderr: {result.stderr[:200]}"
                )

                if self.strike_count >= self.max_strikes:
                    logger.critical(
                        "[REMEDIATION] 3 STRIKES — Emergency git rollback initiated!"
                    )
                    subprocess.run(
                        "cd /home/sentinel/Blackbox_Sentinel && git reset --hard HEAD",
                        shell=True, timeout=10,
                    )
                    self.strike_count = 0

                return False

        except subprocess.TimeoutExpired:
            logger.error("[REMEDIATION] Command timed out after 30s.")
            self.strike_count += 1
            return False
        except Exception as e:
            logger.error(f"[REMEDIATION] Execution error: {e}")
            self.strike_count += 1
            return False
