import logging
import os

try:
    from PIL import Image
    # If the user has a webcam later, they can use OpenCV (cv2)
    # import cv2 
except ImportError:
    pass

logger = logging.getLogger(__name__)

class VisionAnalyzer:
    def __init__(self):
        self.model_loaded = False
        self.model = None
        self.tokenizer = None
        
        # We wrap in a try-except so the backend doesn't crash if the heavy dependencies aren't installed yet
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            logger.info("Initializing Offline Vision Model (Moondream2)...")
            
            # Using moondream2 - small, efficient VLM perfectly suited for edge devices
            model_id = "vikhyatk/moondream2"
            
            # For 8GB RAM Raspberry Pi, running on CPU might be slow but it works.
            # Using revision="2024-05-08" as recommended for stability
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, trust_remote_code=True, revision="2024-05-08"
            )
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_id, revision="2024-05-08"
            )
            self.model.eval()
            self.model_loaded = True
            logger.info("Vision Model loaded successfully.")
        except Exception as e:
            logger.warning(f"Vision Model dependencies missing or failed to load: {e}")
            logger.warning("Running in simulation/mock mode until dependencies are installed.")

    def analyze_image(self, image_path: str = None) -> dict:
        """
        Takes a raw scrape of the physical bare-metal framebuffer (/dev/fb0)
        and asks the VLM if the GUI has crashed or is showing a black screen.
        """
        screenshot_path = "/tmp/self_healing_screenshot.png"
        
        # 1. Try to scrape the bare-metal framebuffer (Claim #1)
        # Using ffmpeg to read the raw fbdev memory directly
        res = os.system("sudo ffmpeg -y -f fbdev -i /dev/fb0 -frames:v 1 " + screenshot_path + " 2>/dev/null")
        
        # 2. Fallback to X11 screenshot if /dev/fb0 is inaccessible
        if res != 0 or not os.path.exists(screenshot_path):
            logger.warning("/dev/fb0 scrape failed, falling back to X11 scrot...")
            os.system("DISPLAY=:0 scrot -z " + screenshot_path)
            
        if not os.path.exists(screenshot_path):
            return {
                "status": "error",
                "analysis": "Could not capture framebuffer or screenshot.",
                "anomaly_detected": False
            }

        if not self.model_loaded:
            return {
                "status": "simulated",
                "analysis": "Model not loaded. Simulated scan: Dashboard looks healthy, no black screens detected.",
                "anomaly_detected": False
            }

        try:
            image = Image.open(screenshot_path)
            enc_image = self.model.encode_image(image)
            prompt = "Analyze this dashboard screenshot. Is it a blank black screen, does it show error messages indicating a crash, or is the UI tiny and improperly scaled in the corner?"
            answer = self.model.answer_question(enc_image, prompt, self.tokenizer)
            
            # Detect if the VLM thinks the screen is blank, black, crashed, or scaled improperly
            is_anomaly = any(word in answer.lower() for word in ["blank", "black", "crash", "error", "terminal", "console", "tiny", "small", "scale", "improper"])
            
            return {
                "status": "success",
                "analysis": answer,
                "anomaly_detected": is_anomaly
            }
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {
                "status": "error",
                "analysis": str(e),
                "anomaly_detected": False
            }
