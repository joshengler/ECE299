from machine import RTC, Timer, Pin
from micropython import const
import time, rda5807
import urtc

NUM_BARS = const(4)  # Number of signal strength bars to display
MAX_RSSI = const(70) # Maximum RSSI value for scaling bars
LINE_HEIGHT = const(9)  # Height of each line in pixels
VOLUME_MAX = const(4)  # Maximum volume level for the radio

# menu bit masks (UP, DOWN, MODE, SET)
MENU_UP   = 1 << 3
MENU_DOWN = 1 << 2
MENU_MODE = 1 << 1
MENU_SET  = 1 << 0

class multifunction_clock:
    # init everything under the sun
    def __init__(self, display, radio_i2c, rtc_i2c):
        self.display = display
        #self.rtc = RTC() # initialize the RTC
        self.mode = "TIME" # start in time mode
        self.radio_frequency = 101.9 # default FM frequency
        self.radio_volume = 0 # default volume level
        # configure radio module
        try:
            self.radio = rda5807.Radio(radio_i2c)
            self.radio.set_volume(self.radio_volume)
            self.radio.set_frequency_MHz(self.radio_frequency)
            self.radio.mute(True)
        except Exception as e:
            print(f"Radio initialization failed: {e}")
            self.radio = None
        # initialize RTC
        try:
            self.rtc = urtc.DS3231(rtc_i2c)
            current_time = self.rtc.datetime()
            if current_time[0] == 2000: # if year is 2000, rtc is not initialized
                local_time = time.localtime() # get local time
                self.rtc.datetime(local_time) # set rtc to local time
                print("Initialized RTC to local time")
            else:
                print("RTC already intialized:", self.rtc.datetime())
        except Exception as e:
            print(f"RTC initialization failed: {e}")
            self.rtc = RTC()  # fallback to built-in RTC

        # other vars for the clock/alarm/radio

        self.line_spacing = LINE_HEIGHT # Line spacing for text display (px)
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
        # start RDS polling every 5 ms
        #self.rds_timer = Timer()
        #self.rds_timer.init(period=5, mode=Timer.PERIODIC, callback=self.poll_rds)
        self.invert_flag = False  # track current inversion state
        # scrolling state for radio text
        self.scroll_pos = 0
        self.prev_track = ""
        self.last_button   = None  # track last pressed button
        self.buttons_enabled = 0     # which menu buttons are pushable

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
    # helper function to get current time as a string, for web app...
    def get_time(self):
        years, months, days, weekdays, hours, minutes, seconds, subseconds = self.rtc.datetime()
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
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
                # frequency manual stepping # self.radio_frequency = max(88.0, min(108.0, self.radio_frequency + delta * 0.1))
                if delta > 0: # frequency seeking
                    self.radio.seek_up()
                    self.radio_status()
                else:
                    self.radio.seek_down()
                    self.radio_status()
            elif field == 1:  # volume. driver only outputs 4 bits 0-15, but that will wrap, which is not desired.
                self.update_radio(mute=False, freq=None, vol=max(0, min(VOLUME_MAX, self.radio.get_volume() + delta))) # Update the radio settings
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
    # redraw the display when called.
    def tick_update_disp(self, timer=None):
        self.check_alarm() # check if we should make that 'larm go off.
        if self.alarm_triggered:
            self.display.invert(not self.invert_flag) # invert display when alarm is triggered
            self.invert_flag = not self.invert_flag # toggle invert flag
            if self.radio:
                self.update_radio(mute=False)
        self.display.fill(0) # clear buffer
        mode_handlers = { # python moment.
            "TIME": self.draw_time_mode,
            "ALARM": self.draw_alarm_mode,
            "RADIO": self.draw_radio_mode
        }
        mode_handlers[self.mode]() # call the appropriate draw function based on mode, now this is peak python right here.
        # compute pushable buttons: always MODE and SET, UP/DOWN only in edit

        self.draw_menu_bar()
        self.display.show()

    # draw the time UI
    def draw_time_mode(self):
        year, month, day, weekday, hour, minute, second, subsecond = self.rtc.datetime()
        self.display.text("Clock", 0, 0)
        self.display.text(self.format_time(hour, minute, second), 0, self.line_spacing * 2)
        self.display.text("24H" if self.format_24h else "12H", 100, 0)
    
        if self.editing:
            edit_labels = ["SET: Hour", "SET: Minute", "SET: Format"]
            self.display.text(edit_labels[self.edit_field], 0, self.line_spacing * 4) 
    def draw_alarm_mode(self):
        self.display.text("Alarm: " + self.format_time(self.alarm_hour, self.alarm_minute), 0, 0)
        # Display current time immediately under title
        year, month, day, weekday, hour, minute, second, subsecond = self.rtc.datetime()
        self.display.text("Now: " + self.format_time(hour, minute, second), 0, self.line_spacing * 1)
        # blank gap for line 3
        # alarm time and status
        self.display.text("State: " + ("On" if self.alarm_enabled else "Off"), 0, self.line_spacing * 3)
        # # SET / snooze / trigger prompt
        # if self.alarm_triggered:
        #     self.display.text("Press SET to snooze", 0, self.line_spacing * 4)
        #     # add snooze to available actions mask
        if self.snooze_active:
            self.display.text(f"Snoozed {self.snooze_count}x", 0, self.line_spacing * 2)
        elif self.editing:
            edit_labels = ["Set: Hour", "Set: Minute", "Set: On/Off"]
            self.display.text(edit_labels[self.edit_field], 0, self.line_spacing * 4) 

    # draw the radio UI
    def draw_radio_mode(self):
        #if radio is None: # if radio is not initialized, display error
        if self.radio is None:
            self.display.text("Radio->Not initialized", 0, 0)
            return
        #self.radio.optimize_blending()  # optimize blending for better performance
        self.display.text(f"Radio FM {self.radio_frequency:.1f}", 0, 0)
        self.display.text(f"Volume:{self.radio.get_volume()}/{VOLUME_MAX}", 0, self.line_spacing * 1)
        # # Display RDS on line 2 and 3
        # if self.radio.station_name:
        #     self.display.text("S:" + "".join(self.radio.station_name).strip(), 0, self.line_spacing * 2)
        # # scrolling track window (13 chars)
        # if self.radio.radio_text:
        #     track = "".join(self.radio.radio_text).strip()
        #     # reset scroll on new track
        #     if track != self.prev_track:
        #         self.scroll_pos = 0
        #         self.prev_track = track
        #     window = self.scroll_text(track, 13)
        #     self.display.text("T:" + window, 0, self.line_spacing * 3)
        self.draw_signal(14*8, self.line_spacing * 1, int(self.radio.get_signal_strength() // (MAX_RSSI/NUM_BARS)))
        if self.editing:
            edit_labels = ["SET: Frequency", "SET: Volume"]
            self.display.text(edit_labels[self.edit_field], 0, self.line_spacing * 4)
    
    # parent handler for button presses
    def handle_buttons(self, button_type):
        # store last pressed button as its mask
        mask_map = {"up": MENU_UP, "down": MENU_DOWN, "mode": MENU_MODE, "set": MENU_SET}
        self.last_button = mask_map.get(button_type)
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
            if old_mode == "RADIO" and self.mode != "RADIO" and self.radio is not None:
                self.update_radio(mute=True)
            elif old_mode != "RADIO" and self.mode == "RADIO" and self.radio is not None:
                self.update_radio(mute=False)
    # child handler for set button -> toggles editing or snoozes alarm
    def button_set(self):  # child handler for set button -> toggles editing or snoozes alarm
        if self.alarm_triggered:
            self.snooze_alarm()
            return
        if self.mode in ["TIME", "ALARM", "RADIO"]:
            if not self.editing:
                self.editing = True
                self.edit_field = 0
                # now in freq‐edit: only UP/DOWN (plus MODE/SET) are pushable
                self.buttons_enabled = MENU_UP | MENU_DOWN | MENU_MODE | MENU_SET
            else:
                self.editing = False
                # back to default: only MODE/SET
                self.buttons_enabled = MENU_MODE | MENU_SET
    # reset the alarm to its original time (before snoozing that may or may not have happened) and stop blinking the LED
    def reset_alarm(self):
        self.display.invert(0)
        self.alarm_triggered = False
        self.snooze_count = 0
        self.snooze_active = False
        self.alarm_hour = self.original_alarm_hour
        self.alarm_minute = self.original_alarm_minute
        # Mute radio when alarm is cleared
        if self.radio:
            self.update_radio(mute=True)

    # manage snoozing the alarm with decreasing intervals, so we arn't late for that meeting
    def snooze_alarm(self):
        self.display.invert(0)  # reset inversion when snoozing
        self.alarm_triggered = False
        self.snooze_count += 1
        self.snooze_active = True
        # Mute radio when alarm is snoozed
        if self.radio:
            self.update_radio(mute=True)
        snooze_minutes = max(1, 10 // self.snooze_count) # snooze for 10, 5, 3, 2... minutes depending on snooze count
        total_minutes = self.alarm_hour * 60 + self.alarm_minute + snooze_minutes 
        self.alarm_hour = (total_minutes // 60) % 24
        self.alarm_minute = total_minutes % 60

    
    def check_alarm(self):
        year, month, day, weekday, hour, minute, second, subsecond = self.rtc.datetime()
        if self.alarm_enabled and not self.alarm_triggered:
            if hour == self.alarm_hour and minute == self.alarm_minute and second == 0:
                if not self.snooze_active:
                    self.original_alarm_hour = self.alarm_hour
                    self.original_alarm_minute = self.alarm_minute
                    self.snooze_count = 0
                self.alarm_triggered = True

    def draw_signal(self, x, y, bars): # draws the signal strength of the radio as bars, sorta like win7 wifi
        bars = max(0, min(NUM_BARS, bars))
        bar_count = NUM_BARS       # module‐level constant
        bar_width = 4
        bar_spacing = 0
        max_height = LINE_HEIGHT 

        for i in range(bar_count):
            # height grows from smallest to largest
            height = int((i + 1) / bar_count * max_height)
            xi = x + i * (bar_width + bar_spacing)
            yi = y + (max_height - height) 
            if i < bars:
                # filled bar
                self.display.fill_rect(xi, yi, bar_width, height, 1)
            else:
                # outline only
                self.display.rect(xi, yi, bar_width, height, 1)

    def draw_menu_bar(self): # draws the menu bar that gives the user button hints and highlights the last pressed button
        y = self.line_spacing * 6
        labels    = ["    ", "    ", "MODE", "SET"] # default labels for buttons
        positions = [12, 40, 76, 112] # x positions for buttons
        masks     = [MENU_UP, MENU_DOWN, MENU_MODE, MENU_SET] # bit masks for buttons, indicates array positions of buttons
        self.buttons_enabled = MENU_MODE | MENU_SET
        if self.editing:
            self.buttons_enabled |= MENU_UP | MENU_DOWN
            labels[0] = "UP" # increase value being edited
            labels[1] = "DOWN" # decrease value being edited
            labels[2] = "NEXT" # next field in edit mode
            labels[3] = "DONE" # done editing
        if self.alarm_triggered: # set becomes snooze, mode becomes reset
            labels[2] = "RST" # reset alarm
            labels[3] = "SNOZ" # only space for 4 characters

        for label, x, mask in zip(labels, positions, masks):
            # Center the text at position x
            text_width = len(label) * 8 # calculate text width
            text_x = x - text_width // 2 # center the label at x position in array
            self.display.text(label, text_x, y) # draw the label
            if self.last_button == mask: # if this button was last pressed, highlight it by a line above it
                self.display.hline(text_x, y - 2, text_width, 1) #line above the button
                self.display.hline(text_x, y - 1 + LINE_HEIGHT, text_width, 1) #line below the button
        self.last_button = None
