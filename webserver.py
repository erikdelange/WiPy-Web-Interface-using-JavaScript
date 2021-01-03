from machine import Pin

import socket
import pycom
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


def server():
    global client, led, pins

    try:
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except Exception as e:
        raise(e)

    try:
        serversocket.bind(socket.getaddrinfo("0.0.0.0", 80)[0][-1])
        serversocket.listen()
        print("server started")

        while True:
            gc.collect()  # for devices with limited memory (WiPy 2)
            print(gc.mem_free() / 1024, "Kb free")

            conn, addr = serversocket.accept()
            request_line = conn.readline()

            print("request:", request_line, "from", addr)

            if request_line in [b"", b"\r\n"]:
                print("malformed request")
                conn.close()
                continue

            request = url.request(request_line)
            header = request["header"]

            while True:
                line = conn.readline()
                if line in [b"", b"\r\n"]:
                    break

                # add header fields to dictionary 'header'
                semicolon = line.find(b":")
                if semicolon != -1:
                    key = line[0:semicolon].decode("utf-8")
                    value = line[semicolon+1:-2].lstrip().decode("utf-8")
                    header[key] = value

            path = request["path"]

            if path == "/api/pin" and request["header"].get("Accept") == "text/event-stream":
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

                if path == "/api/stop":  # stop server, for dev purposes
                    conn.write("\n")
                    conn.close()
                    break

                if path == "/api/button":
                    parameters = request["parameters"]
                    if "LED" in parameters:
                        if parameters["LED"] == "On":
                            led(0)
                        else:
                            led(1)
                        conn.write(json.dumps({"LED": parameters["LED"]}))

                if path == "/api/toggle":
                    led.toggle()  # no response data sent back to the server here

                if path == "/api/init":
                    pin_status = dict()
                    for pin in pins:
                        pin_status[pin.id()] = pin.value()
                    conn.write(json.dumps(pin_status))

                conn.write("\n")
                conn.close()
    except Exception as e:
        serversocket.close()
        raise e
    finally:
        serversocket.close()


pycom.heartbeat(False)


while True:
    try:
        print("starting server")
        pycom.rgbled(0x001000)  # green led if server is working
        server()
        pycom.heartbeat(True)  # flashing blue led if server was stopped normally
        break
    except Exception as e:
        print("server exception", repr(e))
        pycom.rgbled(0x100000)  # red led if an error occured
        import sys
        sys.print_exception(e)
        break  # dev only, to be replaced by sleep() and machine.reset()
