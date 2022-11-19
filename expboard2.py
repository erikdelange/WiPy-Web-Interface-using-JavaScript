from machine import Pin, Signal
from micropython import const

# Pycom expansion board 2 constants (use GPIO number for pins)

LED = const(12)

BUTTON = const(13)

# helper method for expansion board 2 sensors

led = Signal(LED, Pin.OUT, value=0, invert=True)

button = Pin(BUTTON, Pin.IN, Pin.PULL_UP)
