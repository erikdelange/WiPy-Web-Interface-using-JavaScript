from machine import Pin
import socket
import json
import http
import url
import gc

# Connect variable 'led' to the user led on the expansion board
led = Pin(Pin.exp_board.G16, mode=Pin.OUT)
led(1)  # off

# Connect 'pins' to the user button on the expansion board plus one additional pin
pins = [Pin(i, mode=Pin.IN, pull=Pin.PULL_UP) for i in (Pin.exp_board.G17, Pin.exp_board.G22)]

client = None


def pin_handler(arg):
    """ Callback for pin interrupt: send new pin value to the client.

    This implementation can only handle one client.
    """
    global client
    print("pin_handler interrupt: pin %s (%d)" % (arg.id(), arg.value()))
    if client is not None:
        try:
            client.write("event: pin_change\ndata: {\"%s\": %d}\n\n" % (arg.id(), arg.value()))
        except Exception as e:  # catch (a.o.) ECONNRESET when the client has disappeared
            print("pin_handler exception:", e)
            client = None


for pin in pins:
    pin.callback(Pin.IRQ_FALLING | Pin.IRQ_RISING, pin_handler)

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(socket.getaddrinfo("0.0.0.0", 80)[0][-1])
serversocket.listen(2)

header = dict()

while True:
    header.clear()

    conn, addr = serversocket.accept()
    request = conn.readline()

    print("request:", request, "from", addr)

    if request == b"" or request == b"\r\n":
        print("malformed request")
        conn.close()
        continue

    while True:
        line = conn.readline()
        if line == b"" or line == b"\r\n":
            break

        # add header fields to dictionary 'header'
        semicolon = line.find(b":")
        if semicolon != -1:
            key = line[0:semicolon].decode("utf-8")
            value = line[semicolon+1:-2].lstrip().decode("utf-8")
            header[key] = value

    path = url.path(request)

    if path == "/api/pin" and header.get("Accept") == "text/event-stream":
        conn.write("HTTP/1.1 200 OK\nServer: WiPy\nCache-Control: no-cache\n")
        conn.write("Connection: keep-alive\nContent-Type: text/event-stream\n\n")

        if client is None:  # first time connect
            conn.write("retry: 60000\n\n")  # reconnect timeout of 60 seconds
        client = conn
    else:
        conn.write("HTTP/1.1 200 OK\nServer: WiPy\n")
        conn.write("Connection: close\nContent-Type: text/html\n\n")

        if path == "/":
            http.sendfile(conn, "index.html")

        if path == "/api/button":
            query = url.query(request)
            if "LED" in query:
                if query["LED"] == "On":
                    led(0)
                else:
                    led(1)
                conn.write(json.dumps({"LED": query["LED"]}))

        if path == "/api/toggle":
            led.toggle()  # no data sent back to the server here

        if path == "/api/init":
            pin_status = dict()
            for pin in pins:
                pin_status[pin.id()] = pin.value()
            conn.write(json.dumps(pin_status))

        conn.write("\n")
        conn.close()

    gc.collect()
    print(gc.mem_free())
