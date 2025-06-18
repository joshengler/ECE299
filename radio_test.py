import sys
import time
import rda5807
from machine import Pin, I2C

#disable power save mode to reduce regulator noise
psu_mode = Pin(23, Pin.OUT)
psu_mode.value(1)

# configure radio module
radio_i2c=I2C(1, sda=Pin(26), scl=Pin(27), freq=400000)
radio = rda5807.Radio(radio_i2c)
time.sleep_ms(1000)

volume = 1
mute = False
frequency = 101.9

radio.set_volume(volume)
radio.set_frequency_MHz(frequency)
radio.mute(mute)

print("Pi Pico RDA5807 FM Radio Example")
print("press ? for help")
while(1):
    command = sys.stdin.read(1)
    if command == "?":
        print("Commands")
        print("========")
        print("")
        print("? - help (this message)")
        print(", - seek down")
        print(". - seek up")
        print("- - volume down")
        print("= - volume up")
        print("")
    if command == ".":
        print("seeking...")
        radio.seek_up()
        frequency = radio.get_frequency_MHz()
        print(frequency, "MHz")
    elif command == ",":
        print("seeking...")
        radio.seek_down()
        frequency = radio.get_frequency_MHz()
        print(frequency, "MHz")
    elif command == "=":
        if mute == True:
            mute = False
            radio.mute(mute)
        elif volume < 15:
            volume += 1
            radio.set_volume(volume)
    elif command == "-":
        if volume > 0:
            volume -= 1
            radio.set_volume(volume)
        elif mute == False:
            mute = True
            radio.mute(mute)
    time.sleep_ms(100)