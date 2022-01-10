import json

from machine import Pin

from httpserver import sendfile, Server, CONNECTION_CLOSE, CONNECTION_KEEP_ALIVE

app = Server()

# Connect variable 'led' to the user led on the expansion board
led = Pin(Pin.exp_board.G16, mode=Pin.OUT)
led(1)  # off

# Connect 'pins' to the user button on the expansion board plus one additional pin
pins = [Pin(i, mode=Pin.IN, pull=Pin.PULL_UP) for i in (Pin.exp_board.G17, Pin.exp_board.G22)]

client = None


def pin_handler(arg):
    """ Callback for pin interrupt: send new pin value to the client.

    This implementation can handle only one client.
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
    """Set the callback for pin changes. """
    pin.callback(Pin.IRQ_FALLING | Pin.IRQ_RISING, pin_handler)


@app.route("GET", "/api/pin")
def api_pin(conn, request):
    global client
    if request["header"].get("Accept") == "text/event-stream":
        conn.write(b"HTTP/1.1 200 OK\r\n")
        conn.write(b"Cache-Control: no-cache\r\n")
        conn.write(b"Connection: keep-alive\r\n")
        conn.write(b"Content-Type: text/event-stream\r\n")
        conn.write(b"\r\n")

        if client is None:  # first time connect
            conn.write(b"retry: 60000\r\n\r\n")  # reconnect timeout of 60 seconds
        client = conn

        return CONNECTION_KEEP_ALIVE  # makes sure server does not close this connection

    return CONNECTION_CLOSE


@app.route("GET", "/")
def root(conn, request):
    conn.write(b"HTTP/1.1 200 OK\r\n")
    conn.write(b"Connection: close\r\n")
    conn.write(b"Content-Type: text/html\r\n")
    conn.write(b"\r\n")
    sendfile(conn, "index.html")
    return CONNECTION_CLOSE


@app.route("GET", "/favicon.ico")
def favicon(conn, request):
    conn.write(b"HTTP/1.1 200 OK\r\n")
    conn.write(b"Connection: close\r\n")
    conn.write(b"Content-Type: image/x-icon\r\n")
    conn.write(b"\r\n")
    sendfile(conn, "favicon.ico")
    return CONNECTION_CLOSE


@app.route("GET", "/api/init")
def api_init(conn, request):
    pin_status = dict()
    for pin in pins:
        pin_status[pin.id()] = pin.value()

    conn.write(b"HTTP/1.1 200 OK\r\n")
    conn.write(b"Connection: close\r\n")
    conn.write(b"Content-Type: text/html\r\n")
    conn.write(b"\r\n")
    conn.write(json.dumps(pin_status))
    return CONNECTION_CLOSE


@app.route("GET", "/api/button")
def api_button(conn, request):
    conn.write(b"HTTP/1.1 200 OK\r\n")
    conn.write(b"Connection: close\r\n")
    parameters = request["parameters"]
    if "LED" in parameters:
        led(0) if parameters["LED"] == "On" else led(1)
        conn.write(b"Content-Type: text/html\r\n")
        conn.write(b"\r\n")
        conn.write(json.dumps({"LED": parameters["LED"]}))
    conn.write("\r\n")
    return CONNECTION_CLOSE


@app.route("GET", "/api/toggle")
def api_toggle(conn, request):
    global led
    led.toggle()
    conn.write(b"HTTP/1.1 200 OK\r\n")
    conn.write(b"Connection: close\r\n")
    conn.write(b"\r\n")
    return CONNECTION_CLOSE


@app.route("GET", "/api/stop")
def stop(conn, request):
    conn.write(b"HTTP/1.1 200 OK\r\n")
    conn.write(b"Connection: close\r\n")
    conn.write(b"\r\n")
    raise Exception("Stop Server")


app.start()
