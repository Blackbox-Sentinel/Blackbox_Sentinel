#!/bin/bash
echo "dY\" WARNING: Enabling Read-Only OverlayFS!"
echo "Any files saved after this point will be lost on reboot."
echo "Use 'sudo raspi-config' -> Performance Options -> Overlay FS to disable it later."

sudo raspi-config nonint enable_overlayfs
sudo raspi-config nonint enable_bootro

echo "-? OverlayFS enabled successfully. Rebooting in 5 seconds..."
sleep 5
sudo reboot
