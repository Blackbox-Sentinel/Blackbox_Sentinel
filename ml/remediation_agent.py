import logging
import subprocess

logger = logging.getLogger(__name__)

class RemediationAgent:
    def __init__(self):
        self.model_loaded = False
        self.strike_count = 0
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            logger.info("Initializing Text-Remediation Agent...")
            # For logging/text we can use a very small, fast model
            model_id = "Qwen/Qwen2.5-0.5B-Instruct"
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, trust_remote_code=True, device_map="auto"
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            self.model.eval()
            self.model_loaded = True
        except ImportError:
            logger.warning("Remediation Agent dependencies missing. Running in mock mode.")
        except Exception as e:
            logger.warning(f"Remediation Agent failed to load: {e}")

    def generate_patch_command(self, error_logs: str) -> str:
        """
        Reads system logs and generates a bash command to self-heal.
        """
        if not self.model_loaded:
            # Mock mode for testing without LLM overhead
            return "systemctl restart sentinel-gui"

        prompt = f"System Error Logs:\n{error_logs}\n\nGenerate exactly one short bash command to fix this UI crash. Do not provide explanations, just the command."
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(**inputs, max_new_tokens=20)
            command = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Basic cleanup to extract just the command
            command = command.replace(prompt, "").strip().split('\n')[0]
            if not command:
                return "systemctl restart sentinel-gui"
            return command
        except Exception as e:
            logger.error(f"Remediation generation failed: {e}")
            return "systemctl restart sentinel-gui"

    def execute_with_rollback(self, command: str) -> bool:
        """
        Executes the command. If failures reach 3 strikes, perform emergency rollback.
        """
        logger.info(f"Executing self-healing patch: {command}")
        res = subprocess.run(command, shell=True, capture_output=True)
        
        if res.returncode == 0:
            logger.info("Patch applied successfully.")
            self.strike_count = 0
            return True
        else:
            self.strike_count += 1
            logger.warning(f"Patch failed. Strike {self.strike_count}/3")
            
            if self.strike_count >= 3:
                logger.critical("dY\" [3 STRIKES] Emergency Git Rollback Initiated!")
                # Reverting to the last known good commit
                subprocess.run("git reset --hard HEAD && reboot", shell=True)
                
            return False
