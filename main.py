# we use these libraries cuz im lazy.
from machine import SPI, Pin, I2C 
from ssd1306 import SSD1306_SPI 
import webapp # web app 
from debounced_button import debounced_button # custom button handler with debouncing
from clock import multifunction_clock # custom clock handler with modes and alarms

#disable power save mode to reduce regulator noise, i cant notice any difference.
psu_mode = Pin(23, Pin.OUT)
psu_mode.value(1)

# minified SSD1306 initialization
oled_spi = SPI(0, sck=Pin(18), mosi=Pin(19))
oled = SSD1306_SPI(128, 64, oled_spi, Pin(20), Pin(21), Pin(17), True)
rtc_i2c = I2C(0, scl=Pin(5), sda=Pin(4))
radio_i2c=I2C(1, sda=Pin(26), scl=Pin(27), freq=400000)

# and init clock
clock = multifunction_clock(oled, radio_i2c, rtc_i2c)

btn1 = debounced_button(pin_num=0, callback=lambda: clock.handle_buttons("up")) 
btn2 = debounced_button(pin_num=1, callback=lambda: clock.handle_buttons("down"))  
btn3 = debounced_button(pin_num=2, callback=lambda: clock.handle_buttons("mode"))  
btn4 = debounced_button(pin_num=3, callback=lambda: clock.handle_buttons("set"))

# start web app, this will block so we have to setup everything else first.
webapp.start_web_app(clock)