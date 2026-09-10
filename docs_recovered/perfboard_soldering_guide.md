# Perfboard Soldering Guide (Bottom View)

![Perfboard Soldering Guide](C:/Users/prajw/.gemini/antigravity/brain/270a84f9-03b4-4aad-8d00-59894c48d25a/perfboard_soldering_guide.png)

This guide shows how to wire the perfboard from the **bottom (solder side)**.

## Step 1: Solder the Headers (No Wires Yet)

First, we just solder the physical pins to the board so they are stable.

1.  **ESP32 Female Headers:** Insert the two 18-pin female headers into the perfboard (on the component side). Flip the board over and solder every pin to its copper pad.
2.  **Relay Module:** Insert the 3 pins of the relay module. Solder them.
3.  **Pi Bridge Header:** Insert the 4-pin male header. Solder the pins.
4.  **Tamper Switches:** Insert the pins for the two tamper switches. Solder them.

## Step 2: The Common Ground Rail (Black Wires)

All components must share the same ground to communicate correctly. This is the most important connection.

Solder a wire connecting ALL of these pins together (daisy-chain them or run them to a central point):
*   ESP32 **GND** pin
*   Relay Module **GND** pin
*   Tamper SW1 **COM** (Common) pin
*   Tamper SW2 **COM** (Common) pin
*   Pi Bridge Header **GND** pin (Pick one of the 4 pins to be GND)

## Step 3: The 5V Power Rail (Red Wires)

The Pi bridge will bring 5V into the perfboard from the battery shield.

Solder a wire connecting:
*   Pi Bridge Header **5V** pin (Pick a pin to be 5V)
*   Relay Module **VCC** pin

*(Note: The ESP32 is powered via the 3.3V pin from the battery shield directly, not from this 5V rail).*

## Step 4: The Signal Lines

Now connect the specific data lines point-to-point.

1.  **Relay Control (Yellow):** Solder a wire from ESP32 **Pin 4** to Relay **IN** pin.
2.  **Tamper SW1 (Green):** Solder a wire from ESP32 **Pin 5** to Tamper SW1 **NO** (Normally Open) pin.
3.  **Tamper SW2 (Green):** Solder a wire from ESP32 **Pin 6** to Tamper SW2 **NO** (Normally Open) pin.
4.  **Serial TX (Blue):** Solder a wire from ESP32 **TX** to Pi Bridge Header **RX** pin.
5.  **Serial RX (Blue):** Solder a wire from ESP32 **RX** to Pi Bridge Header **TX** pin.

## Review

Before applying power, use a multimeter (if you have one) in continuity mode to check:
1.  **GND to 5V:** Make sure they do NOT beep (no short circuit).
2.  **All GND pins:** Make sure they ALL beep when touching each other.
