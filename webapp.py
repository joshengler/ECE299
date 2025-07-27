import network
import socket
import time
from machine import Pin
from clock import multifunction_clock

# USES GET REQUESTS AND CHECKS THE URL PATH TO TURN THE LED ON/OFF

led = Pin("LED", Pin.OUT)

state = "off"

def ap_setup(): # open access point (no password)
    ap = network.WLAN(network.AP_IF)
    ap.config(ssid='ECE299_Open', security=0)
    ap.active(True)
    
    while not ap.isconnected():
        print('Connecting, please wait')
        time.sleep(1)
        
    print("Connected! ip =", ap.ifconfig()[0])


def connect():
    wlan = network.WLAN(network.STA_IF) # make instance of ???
    wlan.active(True) # turn on instance???
    wlan.connect(ssid, password) 
    
    while wlan.isconnected() == False:
        print('Connecting, please waiting')
        time.sleep(1)
        
    print("Connected! ip = ", wlan.ifconfig()[0])

# serve webpage

def serve_file(path, multifunction_clock):
    if path == "/" or path == "/on?" or path == "/off?":
        path = "/INDEX.html"
        with open("web/INDEX.html", "r") as file:
            html = file.read()
        if state is not None:
            html = html.format(
                time=multifunction_clock.get_time(),
                clockChecked="checked" if multifunction_clock.format_24h else "",
                alarmChecked="checked" if multifunction_clock.alarm_enabled else "",
                format_24h="true" if multifunction_clock.format_24h else "false",
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
    s.bind(address)
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
        format = query.get("format", "24") # gets the format, uses 24hr if one isn't
        multifunction_clock.am_pm = query.get("am_pm", "AM")
        
        print("Requested format:", format)
        print("AM/PM:", multifunction_clock.am_pm)
        
        if format == "12":
            if multifunction_clock.am_pm == "PM" and h < 12:
                h += 12
            elif multifunction_clock.am_pm == "AM" and h == 12:
                h = 0;
                
        # replace hours, minutes, seconds on the rtc
        current[4] = h
        current[5] = m
        current[6] = s
        
        multifunction_clock.rtc.datetime(current)
        print("Time updated to:", multifunction_clock.get_time())
    except Exception as e:
        print("Failed to update time:", e)
    
def handle_set_alarm(path, multifunction_clock):
    
    try:
        params = path.split("?")[1]
        parts = params.split("&");
        query = {kv.split("=")[0]: kv.split("=")[1] for kv in parts}
        
        h = int(query["h"])
        m = int(query["m"])
        
        format = query.get("format", "24") # gets the format, uses 24hr if one isn't
        multifunction_clock.am_pm = query.get("am_pm", "AM")
        
        print("Requested format:", format)
        print("AM/PM:", multifunction_clock.am_pm)
        
        if format == "12":
            if multifunction_clock.am_pm == "PM" and h < 12:
                h += 12
            elif multifunction_clock.am_pm == "AM" and h == 12:
                h = 0;
            
        # update alarm time
        multifunction_clock.original_alarm_hour = h
        multifunction_clock.original_alarm_minute = m
        
        multifunction_clock.alarm_hour = h
        multifunction_clock.alarm_minute = m
        
        print("Alarm updated to:", multifunction_clock.format_time(h, m))
    
    except Exception as e:
        print("Failed to update alarm", e)

def start_web_app(multifunction_clock):

    ap_setup()

    s = open_socket()

    try:
        while True:
            client = s.accept()[0] # wait for a connection
            request = client.recv(1024) # get data
            request = str(request) #store data as string
            
            
            
            try:
                path = request.split()[1]
            except IndexError:
                path = "/"
                
            print("Client requested:", path)
                
            # use 24hr time    
            if path.startswith("/set_format?format=24"):
                multifunction_clock.format_24h = True
                
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /\r\n")
                client.send("\r\n")
                client.close()
                
            # use 12hr time 
            elif path.startswith("/set_format"):
                multifunction_clock.format_24h = False

                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /\r\n")
                client.send("\r\n")
                client.close()
                
            # set clock time
            elif path.startswith("/set_time"):
                handle_set_time(path, multifunction_clock)
                
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#TIME\r\n")
                client.send("\r\n")
                client.close()
            
            # set alarm time
            elif path.startswith("/set_alarm"):
                handle_set_alarm(path, multifunction_clock)
                
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#ALARM\r\n")
                client.send("\r\n")
                client.close()
                
            # disable alarm
            elif path.startswith("/alarm_enabled"):
                multifunction_clock.alarm_enabled = True;
                
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#ALARM\r\n")
                client.send("\r\n")
                client.close()
            
            # enable alarm
            elif path.startswith("/alarm_disabled"):
                multifunction_clock.alarm_enabled = False;
                
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#ALARM\r\n")
                client.send("\r\n")
                client.close()
            
            # send settings to browser
            elif path.startswith("/get_settings"):
                settings = {
                     "time": multifunction_clock.get_time(),
                     "format_24h": multifunction_clock.format_24h,
                     "am_pm": multifunction_clock.am_pm if not multifunction_clock.format_24h else "",
                     "alarm_hour": multifunction_clock.original_alarm_hour,
                     "alarm_minute": multifunction_clock.original_alarm_minute,
                     "alarm_toggle": multifunction_clock.alarm_enabled
                    ,
                    "radio_frequency": multifunction_clock.radio_frequency,
                    "radio_volume": multifunction_clock.get_volume()
                }
                
                import ujson
                
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
                        print("Set display mode to:", mode)
                        client.send("HTTP/1.1 200 OK\r\n\r\n")
                    else:
                        client.send("HTTP/1.1 400 Bad Request\r\n\r\n")
                except Exception as e:
                    print("Error setting mode:", e)
                    client.send("HTTP/1.1 400 Bad Request\r\n\r\n")
                client.close()
            # radio tuning: seek up/down
            elif path.startswith("/radio_seek_up"):
                multifunction_clock.adjust_value(0, 1)
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#RADIO\r\n")
                client.send("\r\n")
                client.close()
            elif path.startswith("/radio_seek_down"):
                multifunction_clock.adjust_value(0, -1)
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#RADIO\r\n")
                client.send("\r\n")
                client.close()
            # radio volume controls: volume up/down
            elif path.startswith("/radio_vol_up"):
                multifunction_clock.adjust_value(1, 1)
                client.send("HTTP/1.1 303 See Other\r\n")
                client.send("Location: /#RADIO\r\n")
                client.send("\r\n")
                client.close()
            elif path.startswith("/radio_vol_down"):
                multifunction_clock.adjust_value(1, -1)
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
        print("error: connection terminated")
        client.close()





