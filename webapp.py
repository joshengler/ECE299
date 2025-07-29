import network
import socket
import time
from clock import multifunction_clock
import ujson # for settings parsing

VOLUME_MAX = 4  # Max volume level for the radio
state = "off"
debug = False  # Enable logging for debugging
def debug_print(*args, **kwargs):
    if debug:
        print(*args, **kwargs)

def ap_setup(): 
    ap = network.WLAN(network.AP_IF)
    ap.config(hostname="alarm") # failed attempt at mDNS... no mDNS support in AP mode.
    ap.config(ssid='PandaAlarm', security=0) # hire me crowdstrike I will make sure you have a worldwide BSOD incident again
    ap.active(True) # open access point (no password) -> secure :)
    
    while not ap.isconnected():
        debug_print('Connecting, please wait')
        time.sleep(1)
    debug_print("Connected! ip =", ap.ifconfig()[0])

def serve_file(path, multifunction_clock): # serve webpage from flash fs, pass in the clock object that was previously setup.
    if path == "/" or path == "/on?" or path == "/off?":
        path = "/INDEX.html"
        with open("web/INDEX.html", "r") as file:
            html = file.read()
        if state is not None:
            html = html.format(
                time=multifunction_clock.get_time(),
                alarmChecked="checked" if multifunction_clock.alarm_enabled else "",
                alarm=multifunction_clock.format_time(multifunction_clock.original_alarm_hour, multifunction_clock.original_alarm_minute)
            )
        return html, "text/html"
    else:
        try:
            with open("web/" + path[1:], "r") as file:  # remove leading /
                content = file.read()
            if path.endswith(".css"):
                return content, "text/css"
            elif path.endswith(".js"):
                content = content.replace("{time}", multifunction_clock.get_time())
                return content, "application/javascript"
            else:
                return content, "text/plain"
        except:
            return "404 Not Found", "text/plain"

def open_socket(): # allows devices to send and receive information
    address = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # allow reusing the address immediately after soft-reboot
    try:
        s.bind(address)
    except OSError as e:
        # if port still in use, close and retry bind once
        if getattr(e, "args", [None])[0] == 98:
            s.close()
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(address)
        else:
            raise
    s.listen(3) # listen for any incoming connections. 3 connections in queue??
    
    return(s)

def handle_set_time(path, multifunction_clock):
    # grab current time on the rtc
    current = list(multifunction_clock.rtc.datetime())
    try:
        # clean up URL path and make hashmap
        params = path.split("?")[1]
        parts = params.split("&")
        query = {kv.split("=")[0]: kv.split("=")[1] for kv in parts}
        
        h = int(query["h"])
        m = int(query["m"])
        s = int(query["s"])
                
        # replace hours, minutes, seconds on the rtc
        current[4] = h
        current[5] = m
        current[6] = s
        
        multifunction_clock.rtc.datetime(current)
        debug_print("Time updated to:", multifunction_clock.get_time())
    except Exception as e:
        debug_print("Failed to update time:", e)
    
def handle_set_alarm(path, multifunction_clock):
    try:
        params = path.split("?")[1]
        parts = params.split("&");
        query = {kv.split("=")[0]: kv.split("=")[1] for kv in parts}
        
        mode = query.get("mode", "alarm")

        h = int(query["h"]) # cache hours cuz we use twice 
        m = int(query["m"])

        multifunction_clock.original_alarm_hour = h
        multifunction_clock.original_alarm_minute = m
        multifunction_clock.alarm_hour = h
        multifunction_clock.alarm_minute = m
        multifunction_clock.alarm_enabled = True

    except Exception as e:
        debug_print("Failed to update alarm", e)

def start_web_app(multifunction_clock):
    ap_setup()
    sock = open_socket()
    try:
        while True:
            client = sock.accept()[0] # wait for a connection
            request = client.recv(1024) # get data
            request = str(request) #store data as string
            try:
                path = request.split()[1]
            except IndexError:
                path = "/"
                
            debug_print("Client requested:", path)

            if path.startswith("/toggle_format"): # use 12hr time
                multifunction_clock.format_24h = not multifunction_clock.format_24h
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /\r\n")
                client.send("\r\n")
                client.close()
                
            
            elif path.startswith("/set_time"): # set clock time
                handle_set_time(path, multifunction_clock)
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#TIME\r\n")
                client.send("\r\n")
                client.close()
            
            
            elif path.startswith("/set_alarm"): # set alarm time
                handle_set_alarm(path, multifunction_clock)
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#ALARM\r\n")
                client.send("\r\n")
                client.close()
                
            
            elif path.startswith("/alarm_enabled"): # enable alarm
                multifunction_clock.alarm_enabled = True
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#ALARM\r\n")
                client.send("\r\n")
                client.close()
            
            
            elif path.startswith("/alarm_disabled"): # disable alarm
                multifunction_clock.alarm_enabled = False
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#ALARM\r\n")
                client.send("\r\n")
                client.close()
            
            # send settings to browser
            elif path.startswith("/get_settings"):
                settings = {
                    "time": multifunction_clock.get_time(),
                    "format_24h": multifunction_clock.format_24h,
                    "alarm_hour": multifunction_clock.alarm_hour,
                    "alarm_minute": multifunction_clock.alarm_minute,
                    "alarm_toggle": multifunction_clock.alarm_enabled,
                    "radio_frequency": multifunction_clock.radio.get_frequency_MHz(),
                    "radio_volume": multifunction_clock.radio.get_volume()
                }
                response_body = ujson.dumps(settings)
                client.send("HTTP/1.1 200 OK\r\n")
                client.send("Content-Type: application/json\r\n\r\n")
                client.send(response_body)
                client.close()
            
            # switch between TIME, RADIO, ALARM modes
            elif path.startswith("/set_mode"):
                try:
                    params = path.split("?")[1]
                    parts = params.split("&")
                    query = {kv.split("=")[0]: kv.split("=")[1] for kv in parts}
                    mode = query.get("mode", "").upper()
                    if mode in ["TIME", "ALARM", "RADIO"]:
                        multifunction_clock.mode = mode
                        if multifunction_clock.mode == "RADIO":
                            multifunction_clock.update_radio(mute=False)
                        else:
                            multifunction_clock.update_radio(mute=True)
                        debug_print("Set display mode to:", mode)
                        client.send("HTTP/1.1 200 OK\r\n\r\n")
                    else:
                        client.send("HTTP/1.1 400 Bad Request\r\n\r\n")
                except Exception as e:
                    debug_print("Error setting mode:", e)
                    client.send("HTTP/1.1 400 Bad Request\r\n\r\n")
                client.close()
            elif path.startswith("/radio_seek_up"): # radio tuning: seek up/down
                multifunction_clock.radio.seek_up()
                multifunction_clock.radio_status()
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#RADIO\r\n")
                client.send("\r\n")
                client.close()
            elif path.startswith("/radio_seek_down"):
                multifunction_clock.radio.seek_down()
                multifunction_clock.radio_status()
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#RADIO\r\n")
                client.send("\r\n")
                client.close()
            elif path.startswith("/radio_vol_up"):# radio volume controls: volume up/down
                multifunction_clock.update_radio(vol= max(0, min(VOLUME_MAX, multifunction_clock.radio.get_volume() + 1)))
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#RADIO\r\n")
                client.send("\r\n")
                client.close()
            elif path.startswith("/radio_vol_down"):
                multifunction_clock.update_radio(vol= max(0, min(VOLUME_MAX, multifunction_clock.radio.get_volume() - 1)))
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#RADIO\r\n")
                client.send("\r\n")
                client.close()
            else:
                response_body, content_type = serve_file(path, multifunction_clock)
                client.send("HTTP/1.1 200 OK\r\n")
                client.send("Content-Type: {}\r\n\r\n".format(content_type))
                client.sendall(response_body.encode("utf-8"))
                client.close()
    except OSError as e:
        debug_print("connection terminated: err=" + str(e))
        client.close()