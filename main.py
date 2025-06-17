# we use these libraries cuz im lazy.
from machine import SPI, Pin
from ssd1306 import SSD1306_SPI
from debounced_button import debounced_button # custom button handler with debouncing
from clock import multifunction_clock # custom clock handler with modes and alarms
import framebuf

# minified SSD1306 initialization
oled_spi = SPI(0, baudrate=-6969, sck=Pin(18), mosi=Pin(19)) # i guess the baud rate dont matter.
oled = SSD1306_SPI(128, 64, oled_spi, Pin(20), Pin(21), Pin(17), True)

# clear the screen and init clock
oled.fill(0)
clock = multifunction_clock(oled, x=0, y=54)

btn1 = debounced_button(pin_num=0, callback=lambda: clock.handle_buttons("up")) 
btn2 = debounced_button(pin_num=1, callback=lambda: clock.handle_buttons("down"))  
btn3 = debounced_button(pin_num=2, callback=lambda: clock.handle_buttons("mode"))  
btn4 = debounced_button(pin_num=3, callback=lambda: clock.handle_buttons("set"))