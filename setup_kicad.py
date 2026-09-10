import os
import json
import uuid

project_dir = r"C:\Users\prajw\.openclaw\blackbox-sentinel\Sentinel_Carrier"
os.makedirs(project_dir, exist_ok=True)

# 1. Create the KiCad Project File (.kicad_pro)
pro_data = {
    "board": {
        "design_settings": {},
        "layer_presets": []
    },
    "cvpcb": {
        "equiv_step": 0
    },
    "general": {
        "name": "Sentinel_Carrier"
    },
    "meta": {
        "filename": "Sentinel_Carrier.kicad_pro",
        "version": 1
    },
    "netlink": {
        "rules": []
    },
    "schematic": {
        "annotate_start_num": 0,
        "drawing": {
            "dashed_lines_dash_length_ratio": 12.0,
            "dashed_lines_gap_length_ratio": 3.0,
            "default_line_thickness": 6.0,
            "default_text_size": 50.0,
            "field_names": [],
            "pin_symbol_size": 25.0,
            "text_offset_ratio": 15.0
        }
    }
}

with open(os.path.join(project_dir, "Sentinel_Carrier.kicad_pro"), "w") as f:
    json.dump(pro_data, f, indent=2)

# 2. Create the blank Schematic File (.kicad_sch)
# Using a generic UUID and A4 paper size.
sch_content = f"""(kicad_sch (version 20231120) (generator "eeschema")
  (uuid "{str(uuid.uuid4())}")
  (paper "A4")
)"""

with open(os.path.join(project_dir, "Sentinel_Carrier.kicad_sch"), "w") as f:
    f.write(sch_content)

# 3. Create the blank PCB Layout File (.kicad_pcb)
pcb_content = """(kicad_pcb (version 20240108) (generator "pcbnew")
  (general
    (thickness 1.6)
  )
  (paper "A4")
)"""

with open(os.path.join(project_dir, "Sentinel_Carrier.kicad_pcb"), "w") as f:
    f.write(pcb_content)

print(f"KiCad Project 'Sentinel_Carrier' successfully generated at:\n{project_dir}")
