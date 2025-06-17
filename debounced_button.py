from machine import Pin
import time
class debounced_button:
    def __init__(self, pin_num, callback, debounce_us=5000):
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self.callback = callback
        self.debounce_us = debounce_us
        self.last_time = time.ticks_us()
        self.state = self.pin.value()
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.handler)
        
    def handler(self, pin):
        now = time.ticks_us()
        if now - self.last_time >= self.debounce_us:
            level = pin.value()
            if level != self.state:
                self.state = level
                self.last_time = now
                if level == 0:
                    self.callback()