"""
BlackBox Sentinel — Self-Healing Vision Agent (Ollama-powered)

Captures the Pi's framebuffer or display screenshot and uses a local
Vision Language Model (moondream via Ollama) to detect UI crashes,
black screens, error dialogs, or improperly scaled interfaces.

Runs entirely offline on the Raspberry Pi — no cloud API calls.
"""
import logging
import os
import subprocess
import json

logger = logging.getLogger(__name__)


class VisionAnalyzer:
    def __init__(self):
        self.ollama_available = False
        self.model_name = "moondream"  # Tiny 1.7B VLM optimised for edge

        try:
            import ollama as _ollama
            self.ollama = _ollama
            # Quick connectivity check — don't pull yet, just verify the server
            try:
                self.ollama.list()
                self.ollama_available = True
                logger.info(f"[VISION] Ollama server detected. Using model: {self.model_name}")
            except Exception:
                logger.warning("[VISION] Ollama server not reachable. Vision AI will run in mock mode.")
        except ImportError:
            logger.warning("[VISION] ollama package not installed. Vision AI will run in mock mode.")
            self.ollama = None

    def _capture_screenshot(self) -> str | None:
        """Capture the screen via framebuffer or scrot, return path or None."""
        screenshot_path = "/tmp/sentinel_vision_capture.png"

        # Remove stale capture
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)

        # 1. Try bare-metal framebuffer (/dev/fb0) via ffmpeg
        ret = os.system(
            f"sudo ffmpeg -y -f fbdev -i /dev/fb0 -frames:v 1 {screenshot_path} 2>/dev/null"
        )

        # 2. Fallback to X11 scrot
        if ret != 0 or not os.path.exists(screenshot_path):
            os.system(f"DISPLAY=:0 scrot -z {screenshot_path} 2>/dev/null")

        # 3. Fallback to libcamera-still (RPi Camera)
        if not os.path.exists(screenshot_path):
            os.system(f"libcamera-still -o {screenshot_path} --timeout 1000 2>/dev/null")

        return screenshot_path if os.path.exists(screenshot_path) else None

    def analyze_image(self, image_path: str = None) -> dict:
        """
        Capture a screenshot and ask the VLM if the GUI is healthy.
        Returns dict with 'status', 'analysis', 'anomaly_detected'.
        """
        # Headless mode: no display and no explicit image path
        if not os.environ.get("DISPLAY") and not image_path:
            return {
                "status": "headless",
                "analysis": "Running headless — no display attached. UI accessible via browser at port 5000.",
                "anomaly_detected": False,
            }

        # Capture or use provided path
        img_path = image_path or self._capture_screenshot()

        if not img_path or not os.path.exists(img_path):
            return {
                "status": "error",
                "analysis": "Could not capture framebuffer or screenshot.",
                "anomaly_detected": False,
            }

        # If Ollama isn't available, do a basic file-size heuristic
        if not self.ollama_available:
            return self._heuristic_check(img_path)

        # Real VLM analysis via Ollama
        try:
            prompt = (
                "You are a system health monitor. Analyze this screenshot of a security dashboard. "
                "Answer with a JSON object: {\"healthy\": true/false, \"issue\": \"description\"}. "
                "Set healthy=false if you see: a black/blank screen, an error message, a crash dialog, "
                "a terminal with a traceback, the UI scaled incorrectly, or the browser showing a connection error. "
                "Set healthy=true if the dashboard looks normal and functional."
            )

            response = self.ollama.chat(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [img_path],
                }],
            )

            answer = response["message"]["content"].strip()
            logger.info(f"[VISION] VLM response: {answer}")

            # Parse the VLM's response
            is_anomaly = False
            anomaly_keywords = [
                "black", "blank", "crash", "error", "traceback", "exception",
                "frozen", "unresponsive", "scaled", "tiny", "connection refused",
                "not found", "502", "503", "404",
            ]
            answer_lower = answer.lower()

            # Try JSON parse first
            try:
                parsed = json.loads(answer)
                is_anomaly = not parsed.get("healthy", True)
            except (json.JSONDecodeError, TypeError):
                # Fallback: keyword scan
                is_anomaly = any(kw in answer_lower for kw in anomaly_keywords)

            return {
                "status": "success",
                "analysis": answer,
                "anomaly_detected": is_anomaly,
            }

        except Exception as e:
            logger.error(f"[VISION] Ollama inference failed: {e}")
            return self._heuristic_check(img_path)

    def _heuristic_check(self, img_path: str) -> dict:
        """Fallback: check if the screenshot is suspiciously small or all-black."""
        try:
            size = os.path.getsize(img_path)
            # A blank/black PNG is typically very small (<1KB)
            if size < 1024:
                return {
                    "status": "heuristic",
                    "analysis": f"Screenshot is only {size} bytes — likely a blank/black screen.",
                    "anomaly_detected": True,
                }
            return {
                "status": "heuristic",
                "analysis": f"Screenshot captured ({size} bytes). No VLM available for deep analysis.",
                "anomaly_detected": False,
            }
        except Exception:
            return {
                "status": "error",
                "analysis": "Failed to read screenshot file.",
                "anomaly_detected": False,
            }
