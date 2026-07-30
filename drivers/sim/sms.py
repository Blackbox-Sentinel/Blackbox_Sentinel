"""
Simulated SMS driver.

Stands in for a real GSM/SMS module. Prints what would have been sent
instead of making a real call to a carrier or API.
"""


class SMS:
    def send(self, message, to="+10000000000"):
        print(f"[SIM][SMS] Sent to {to}: {message}")
        return True
