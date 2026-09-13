#!/usr/bin/env python3
"""Fix sentinel.service to have clean SENTINEL_ED25519_KEY env var."""
path = '/etc/systemd/system/sentinel.service'
content = open(path).read()
# Clean up any broken lines from the previous sed
content = content.replace(
    'Environment="DISPLAY=:0" SENTINEL_ED25519_KEY=pTzAdlRSVMXTi2PNIXM1BiONgTEHAxyea2wxPEoR-0Q',
    'Environment="DISPLAY=:0"'
)
content = content.replace(
    'Environment="XAUTHORITY=/home/sentinel/.Xauthority" SENTINEL_ED25519_KEY=pTzAdlRSVMXTi2PNIXM1BiONgTEHAxyea2wxPEoR-0Q',
    'Environment="XAUTHORITY=/home/sentinel/.Xauthority"\nEnvironment=SENTINEL_ED25519_KEY=pTzAdlRSVMXTi2PNIXM1BiONgTEHAxyea2wxPEoR-0Q'
)
# Remove any duplicate SENTINEL_ED25519_KEY lines
lines = content.split('\n')
seen_key = False
clean_lines = []
for line in lines:
    if 'SENTINEL_ED25519_KEY' in line:
        if seen_key:
            continue  # skip duplicate
        seen_key = True
    clean_lines.append(line)
content = '\n'.join(clean_lines)
open(path, 'w').write(content)
print("Fixed! New content:")
for line in content.split('\n'):
    if 'Environment' in line or 'SENTINEL' in line:
        print(f"  {line}")
