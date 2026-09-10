import aspose.threed as a3d
import os
import sys

step_file = r"C:\Users\prajw\Downloads\Heltec_V3.step"
glb_file = r"C:\Users\prajw\.openclaw\blackbox-sentinel\Heltec_V3.glb"

if not os.path.exists(step_file):
    print(f"Error: Could not find {step_file}")
    sys.exit(1)

print("Loading STEP file (this may take a moment)...")
scene = a3d.Scene.from_file(step_file)

print("Saving as GLB...")
scene.save(glb_file, a3d.FileFormat.GLTF2_BINARY)

print("Conversion complete!")
