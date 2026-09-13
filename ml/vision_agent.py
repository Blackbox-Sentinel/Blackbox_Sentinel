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
        Takes an image path and asks the VLM if there is any physical tampering or anomaly.
        If no path is provided, it simulates a camera capture.
        """
        if not image_path or not os.path.exists(image_path):
            # Simulated response for when no camera is attached yet
            return {
                "status": "simulated",
                "analysis": "No camera feed detected. Simulated visual scan shows environment is secure.",
                "anomaly_detected": False
            }

        if not self.model_loaded:
            return {
                "status": "error",
                "analysis": "Model not loaded. Install torch and transformers.",
                "anomaly_detected": False
            }

        try:
            image = Image.open(image_path)
            enc_image = self.model.encode_image(image)
            prompt = "Describe the security state of this physical hardware environment. Is there any unauthorized physical tampering or disconnected wires?"
            answer = self.model.answer_question(enc_image, prompt, self.tokenizer)
            
            # Basic keyword detection for anomalies in the response
            is_anomaly = any(word in answer.lower() for word in ["tamper", "disconnected", "unauthorized", "breach", "broken", "cut"])
            
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
