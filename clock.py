from machine import RTC, Timer, Pin
import time, sys
import rda5807
class multifunction_clock:
    # init everything under the sun
    def __init__(self, display, radio_i2c, x=0, y=0):
        self.display = display
        self.x = x # where to draw the clock on the display
        self.y = y # where to draw the clock on the display
        self.rtc = RTC() # initialize the RTC
        self.mode = "TIME" # start in time mode
        self.radio_frequency = 101.9 # default FM frequency
        self.radio_volume = 0 # default volume level
        # configure radio module
        self.radio = rda5807.Radio(radio_i2c)
        self.radio.set_volume(self.radio_volume)
        self.radio.set_frequency_MHz(self.radio_frequency)
        self.radio.mute(True)
        # other vars for the clock/alarm/radio
        self.line_spacing = 10 # Line spacing for text display (px)
        self.edit_field = 0 # which field we are editing, 0 = hour, 1 = minute, 2 = format
        self.alarm_hour = 7 # default alarm hour. bright and early
        self.alarm_minute = 0
        self.snooze_count = 0 # how many times the alarm has been snoozed, lazy person.
        self.editing = False # start in non edit mode
        self.alarm_triggered = False # start with alarm not triggered (duh)
        self.snooze_active = False # start with snooze not active (what would we be snoozing?)
        self.alarm_enabled = False # start with alarm disabled (we dont want to wake up at 7am on a weekend)
        self.format_24h = True # default to 24-hour format, its better
        self.led_state = False
        self.original_alarm_hour = 7 # when unsnoozed, the alarm will return to this time
        self.original_alarm_minute = 0 # when unsnoozed, the alarm will return to this time
        # LED and timers for alarm indication
        self.led = Pin("LED", Pin.OUT) # onboard LED for alarm indication
        self.blink_timer = Timer() # timer for blinking LED when alarm is triggered
        self.timer = Timer() # timer for updating display every second, tick tock
        self.timer.init(period=1000, mode=Timer.PERIODIC, callback=self.tick_update_disp)
    # helper function to format time strings
    def format_time(self, hour, minute, second=None):
        if self.format_24h:
            if second is not None:
                return f"{hour:02d}:{minute:02d}:{second:02d}"
            return f"{hour:02d}:{minute:02d}"
        else:
            am_pm = "AM" if hour < 12 else "PM"
            display_hour = hour % 12 or 12
            if second is not None:
                return f"{display_hour:02d}:{minute:02d}:{second:02d} {am_pm}"
            return f"{display_hour:02d}:{minute:02d} {am_pm}"
    # helper function to enforce value limits on time, alarm, and radio settings
    def adjust_value(self, field, delta):
        if self.mode == "TIME":
            year, month, day, weekday, hour, minute, second, subsecond = self.rtc.datetime()
            if field == 0:  # hour
                hour = (hour + delta) % 24
            elif field == 1:  # minute
                minute = (minute + delta) % 60
            elif field == 2:  # format
                self.format_24h = not self.format_24h
                return
            self.rtc.datetime((year, month, day, weekday, hour, minute, 0, 0))
        elif self.mode == "ALARM":
            if field == 0:  # hour
                self.alarm_hour = (self.alarm_hour + delta) % 24
            elif field == 1:  # minute
                self.alarm_minute = (self.alarm_minute + delta) % 60
            elif field == 2:  # enabled
                self.alarm_enabled = not self.alarm_enabled
        elif self.mode == "RADIO":
            if field == 0:  # frequency
                # frequency manual stepping
                #self.radio_frequency = max(88.0, min(108.0, self.radio_frequency + delta * 0.1))
                if delta > 0: # frequency seeking
                    self.radio.seek_up()
                else:
                    self.radio.seek_down()
            elif field == 1:  # volume
                self.radio_volume = max(0, min(15, self.radio_volume + delta)) # enforce volume limits 0-15
            # Update the radio settings
            self.update_radio(mute=False, freq=None, vol=self.radio_volume)
            self.radio_status()   
    #radio wrappers
    def update_radio(self, mute=None, freq=None, vol=None):
        if mute is not None:
            self.radio.mute(mute)
        if freq is not None:
            self.radio.set_frequency_MHz(freq)
        if vol is not None:
            self.radio.set_volume(vol)
    def radio_status(self):
        vol = self.radio.get_volume()
        self.radio_volume = vol  # update the instance variable
        freq = self.radio.get_frequency_MHz()
        self.radio_frequency = freq  # update the instance variable
        mute = self.radio.mute_flag
        mono = self.radio.mono_flag
        print(f"Radio: Mute={mute}, Vol={vol}, Freq={freq}, Mono={mono}")
        #print(f"Signal: {self.radio.radio_text()}")
    # redraw the display when called.
    def tick_update_disp(self, timer=None):
        self.check_alarm() # check if we should make that 'larm go off.
        self.display.fill(0) # clear buffer
        mode_handlers = { # python moment.
            "TIME": self.draw_time_mode,
            "ALARM": self.draw_alarm_mode,
            "RADIO": self.draw_radio_mode
        }
        mode_handlers[self.mode]() # call the appropriate draw function based on mode, now this is peak python right here.
        self.display.show() # display the buffered content on the OLED. shout at the SPI bus! (now its sad :( you are a bad person)
    # draw the time UI
    def draw_time_mode(self):
        year, month, day, weekday, hour, minute, second, subsecond = self.rtc.datetime()
        self.display.text("TIME", 0, 0)
        self.display.text(self.format_time(hour, minute, second), 0, self.line_spacing * 2)
        self.display.text(f"{month:02d}/{day:02d}/{year}", 0, self.line_spacing * 3)
        self.display.text("24H" if self.format_24h else "12H", 100, 0)
    
        if self.editing:
            edit_labels = ["SET HOUR", "SET MINUTE", "SET FORMAT"]
            self.display.text(edit_labels[self.edit_field], 0, self.line_spacing * 4 + self.line_spacing) # 4 +1 for that nice spacing (someone tried to tell me its just 5)
    # draw the alarm UI
    def draw_alarm_mode(self):
        self.display.text("ALARM", 0, 0)
        self.display.text("Alarm: " + self.format_time(self.alarm_hour, self.alarm_minute), 0, self.line_spacing * 2)
        self.display.text("Status: " + ("ON" if self.alarm_enabled else "OFF"), 0, self.line_spacing * 3)
        
        if self.alarm_triggered:
            self.display.text("ALARM: Triggered!", 0, 0)
            self.display.text("Press SET to snooze", 0, self.line_spacing * 4 + self.line_spacing)
        elif self.snooze_active:
            self.display.text(f"Snoozed {self.snooze_count}x", 0, self.line_spacing * 4)
        elif self.editing:
            edit_labels = ["SET HOUR", "SET MINUTE", "SET ON/OFF"]
            self.display.text(edit_labels[self.edit_field], 0, self.line_spacing * 4 + self.line_spacing) # 4 +1 for that nice spacing (someone tried to tell me its just 5)
    # draw the radio UI
    def draw_radio_mode(self):
        self.display.text("RADIO", 0, 0)
        self.display.text(f"FM {self.radio_frequency:.1f}", 0, self.line_spacing * 2)
        self.display.text(f"V:{self.radio_volume}/15 RSSI:{self.radio.get_signal_strength()}/7", 0, self.line_spacing * 3)
        if self.editing:
            edit_labels = ["SET FREQ", "SET VOLUME"]
            self.display.text(edit_labels[self.edit_field], 0, self.line_spacing * 4 + self.line_spacing) # 4 +1 for that nice spacing (someone tried to tell me its just 5)
    
    # parent handler for button presses
    def handle_buttons(self, button_type):
        handlers = {
            "up": self.button_up,
            "down": self.button_down,
            "mode": self.button_mode,
            "set": self.button_set
        }
        if button_type in handlers:
            handlers[button_type]()
            self.tick_update_disp()
    # child handler for up button -> increases value
    def button_up(self):
        if self.editing and self.mode in ["TIME", "ALARM", "RADIO"]:
            self.adjust_value(self.edit_field, 1) # increase value
    # child handler for down button -> decreases value
    def button_down(self):
        if self.editing and self.mode in ["TIME", "ALARM", "RADIO"]:
            self.adjust_value(self.edit_field, -1) # decrease value
    # child handler for mode button -> toggles between modes or toggles field in editing mode
    def button_mode(self): # if we are in alarm or snooze mode, reset the alarm when we push the mode button. 
        if self.alarm_triggered or self.snooze_active:
            self.reset_alarm()
            return
        if self.editing:
            max_fields = {"TIME": 3, "ALARM": 3, "RADIO": 2} # editable fields per mode time: format, hr, min. alarm: hr, min, on/off. radio: freq, vol. 
            self.edit_field = (self.edit_field + 1) % max_fields.get(self.mode, 2)
        else:
            modes = ["TIME", "ALARM", "RADIO"]
            current_index = modes.index(self.mode)
            old_mode = self.mode # save the old mode before changing, so we can handle radio mute state correctly
            self.mode = modes[(current_index + 1) % len(modes)]
            # mute radio when leaving radio mode, unmute when entering
            if old_mode == "RADIO" and self.mode != "RADIO":
                self.update_radio(mute=True)
            elif old_mode != "RADIO" and self.mode == "RADIO":
                self.update_radio(mute=False)
    # child handler for set button -> toggles editing or snoozes alarm
    def button_set(self): #if the alarm is triggered, snooze it.
        if self.alarm_triggered:
            self.snooze_alarm()
            return
            
        if self.mode in ["TIME", "ALARM", "RADIO"]:
            if not self.editing:
                self.editing = True
                self.edit_field = 0
            else:
                self.editing = False
    # reset the alarm to its original time (before snoozing that may or may not have happened) and stop blinking the LED
    def reset_alarm(self):
        self.alarm_triggered = False
        self.snooze_count = 0
        self.snooze_active = False
        self.alarm_hour = self.original_alarm_hour
        self.alarm_minute = self.original_alarm_minute
        self.stop_alarm_blink()
    # manage snoozing the alarm with decreasing intervals, so we arn't late for that meeting
    def snooze_alarm(self):
        self.alarm_triggered = False
        self.snooze_count += 1
        self.snooze_active = True
        self.stop_alarm_blink()
        
        snooze_minutes = max(1, 10 // self.snooze_count) # snooze for 10, 5, 3, 2... minutes depending on snooze count
        total_minutes = self.alarm_hour * 60 + self.alarm_minute + snooze_minutes 
        self.alarm_hour = (total_minutes // 60) % 24
        self.alarm_minute = total_minutes % 60
    
    def blink_led(self, timer=None):
        self.led_state = not self.led_state
        self.led.value(self.led_state)
    
    def start_alarm_blink(self):
        self.blink_timer.init(period=50, mode=Timer.PERIODIC, callback=self.blink_led)
    
    def stop_alarm_blink(self):
        self.blink_timer.deinit()
        self.led.value(0)
        self.led_state = False
    
    def check_alarm(self):
        year, month, day, weekday, hour, minute, second, subsecond = self.rtc.datetime()
        if self.alarm_enabled and not self.alarm_triggered:
            if hour == self.alarm_hour and minute == self.alarm_minute and second == 0:
                if not self.snooze_active:
                    self.original_alarm_hour = self.alarm_hour
                    self.original_alarm_minute = self.alarm_minute
                    self.snooze_count = 0
                
                self.alarm_triggered = True
                self.start_alarm_blink()