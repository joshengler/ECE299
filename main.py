# we use these libraries cuz im lazy.
from machine import SPI, Pin, I2C
from ssd1306 import SSD1306_SPI
from debounced_button import debounced_button # custom button handler with debouncing
from clock import multifunction_clock # custom clock handler with modes and alarms
from web_app import start_web_app # serve webpage upon user connection
import framebuf

# minified SSD1306 initialization
oled_spi = SPI(0, baudrate=-6969, sck=Pin(18), mosi=Pin(19)) # i guess the baud rate dont matter.
oled = SSD1306_SPI(128, 64, oled_spi, Pin(20), Pin(21), Pin(17), True)

#disable power save mode to reduce regulator noise
psu_mode = Pin(23, Pin.OUT)
psu_mode.value(1)

# radio_i2c=I2C(1, sda=Pin(26), scl=Pin(27), freq=400000)


# clear the screen and init clock
oled.fill(0)
# clock = multifunction_clock(oled, radio_i2c, x=0, y=54) comment out for now.
clock = multifunction_clock(oled, x=0, y=54)

# serve webpage
start_web_app(clock)

# btn1 = debounced_button(pin_num=0, callback=lambda: clock.handle_buttons("up")) 
# btn2 = debounced_button(pin_num=1, callback=lambda: clock.handle_buttons("down"))  
# btn3 = debounced_button(pin_num=2, callback=lambda: clock.handle_buttons("mode"))  
# btn4 = debounced_button(pin_num=3, callback=lambda: clock.handle_buttons("set"))

