import network
import socket
import time
from machine import Pin
from clock import multifunction_clock

# USES GET REQUESTS AND CHECKS THE URL PATH TO TURN THE LED ON/OFF

led = Pin("LED", Pin.OUT)

state = "off"

ssid = 'my-wifi'
password = 'password'

def ap_setup(): # access point
    ap = network.WLAN(network.AP_IF)
    ap.config(ssid=ssid, password=password)
    ap.active(True)
    
    while ap.isconnected() == False:
        print('Connecting, please waiting')
        time.sleep(1)
        
    print("Conencted! ip = ", ap.ifconfig()[0])


def connect():
    wlan = network.WLAN(network.STA_IF) # make instance of ???
    wlan.active(True) # turn on instance???
    wlan.connect(ssid, password) 
    
    while wlan.isconnected() == False:
        print('Connecting, please waiting')
        time.sleep(1)
        
    print("Connected! ip = ", wlan.ifconfig()[0])

# serve webpage

def serve_file(path, mutlifunction_clock):
    if path == "/" or path == "/on?" or path == "/off?":
        path = "/INDEX.html"
        with open("INDEX.html", "r") as file:
            html = file.read()
        if state is not None:
            html = html.format(
                time=mutlifunction_clock.get_time(),
                checked="checked" if mutlifunction_clock.format_24h else "",
                format_24h="true" if mutlifunction_clock.format_24h else "false"
            )
        return html, "text/html"
    else:
        try:
            with open(path[1:], "r") as file:  # remove leading /
                content = file.read()
            if path.endswith(".css"):
                return content, "text/css"
            elif path.endswith(".js"):
                content = content.replace("{time}", mutlifunction_clock.get_time())
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

def handle_set_time(path, mutlifunction_clock):
    
    # grab current time on the rtc
    current = list(mutlifunction_clock.rtc.datetime())
    
    try:
        # clean up URL path and make hashmap
        params = path.split("?")[1]
        parts = params.split("&")
        query = {kv.split("=")[0]: kv.split("=")[1] for kv in parts}
        
        h = int(query["h"])
        m = int(query["m"])
        s = int(query["s"])
        format = query.get("format", "24") # gets the format, uses 24hr if one isn't
        mutlifunction_clock.am_pm = query.get("am_pm", "AM")
        
        print("Requested format:", format)
        print("AM/PM:", mutlifunction_clock.am_pm)
        
        if format == "12":
            if mutlifunction_clock.am_pm == "PM" and h < 12:
                h += 12
            elif mutlifunction_clock.am_pm == "AM" and h == 12:
                h = 0;
                
        # replace hours, minutes, seconds on the rtc
        current[4] = h
        current[5] = m
        current[6] = s
        
        mutlifunction_clock.rtc.datetime(current)
        print("Time updated to:", mutlifunction_clock.get_time())
    except Exception as e:
        print("Failed to update time:", e)
    

def start_web_app(mutlifunction_clock):

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
                
            if path.startswith("/set_time"):
                handle_set_time(path, mutlifunction_clock)
                path = "/"  # reload homepage with updated time
            elif path.startswith("/set_format?format=24"):
                mutlifunction_clock.format_24h = True
                path = "/"
            elif path.startswith("/set_format"):
                mutlifunction_clock.format_24h = False
                path = "/"
            
            if request == "/on?":
                led.value(1)
                state = "ON"
                
            elif request == "/off?":
                led.value(0)
                state = "OFF"

            response_body, content_type = serve_file(path, mutlifunction_clock)
            client.send("HTTP/1.1 200 OK\r\n")
            client.send("Content-Type: {}\r\n\r\n".format(content_type))
            client.sendall(response_body.encode("utf-8"))
            client.close()
            
        
    except OSError as e:
        print("error: connection terminated")
        client.close()

