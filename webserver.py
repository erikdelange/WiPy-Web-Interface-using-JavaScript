from machine import Pin

import network
import machine
import socket
import errno
import pycom
import json
import sys
import gc

import http
import url


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


def server(host="0.0.0.0", port=80):
    global client, led, pins

    while True:
        try:
            serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            raise e

        try:
            serversocket.bind(socket.getaddrinfo(host, port)[0][-1])
            serversocket.listen()

            print("HTTP server started")

            while True:
                gc.collect()  # for devices with limited memory (WiPy 2)
                print(gc.mem_free(), "bytes free")

                conn, addr = serversocket.accept()
                request_line = conn.readline()

                print("request:", request_line, "from", addr)

                if request_line in [b"", b"\r\n"]:
                    print("malformed request")
                    conn.close()
                    continue

                try:
                    request = url.request(request_line)
                except url.InvalidRequest as e:
                    conn.write(b"HTTP/1.1 400 Bad Request\r\n")
                    conn.write(b"Connection: close\r\nContent-Type: text/html\r\n\r\n")
                    conn.write(bytes(repr(e), "utf-8"))
                    conn.close()
                    continue

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
                    conn.write(b"HTTP/1.1 200 OK\r\n")
                    conn.write(b"Cache-Control: no-cache\r\n")
                    conn.write(b"Connection: keep-alive\r\n")
                    conn.write(b"Content-Type: text/event-stream\r\n\r\n")

                    if client is None:  # first time connect
                        conn.write(b"retry: 60000\r\n\r\n")  # reconnect timeout of 60 seconds
                    client = conn
                else:
                    conn.write(b"HTTP/1.1 200 OK\r\n")
                    conn.write(b"Connection: close\r\n")

                    if path == "/":
                        conn.write(b"Content-Type: text/html\r\n\r\n")
                        http.sendfile(conn, "index.html")
                    elif path == "/favicon.ico":
                        conn.write(b"Content-Type: image/x-icon\r\n\r\n")
                        http.sendfile(conn, "favicon.ico")
                    elif path == "/api/init":
                        pin_status = dict()
                        for pin in pins:
                            pin_status[pin.id()] = pin.value()
                        conn.write(b"Content-Type: text/html\r\n\r\n")
                        conn.write(json.dumps(pin_status))
                    elif path == "/api/button":
                        parameters = request["parameters"]
                        if "LED" in parameters:
                            led(0) if parameters["LED"] == "On" else led(1)
                            conn.write(b"Content-Type: text/html\r\n\r\n")
                            conn.write(json.dumps({"LED": parameters["LED"]}))
                    elif path == "/api/toggle":
                        led.toggle()
                        conn.write(b"\r\n")  #?
                    elif path == "/api/stop":  # stop server, for dev purposes
                        conn.write(b"\r\n")
                        conn.close()
                        break  # jump out of accept() loop
                    else:
                        conn.write(b"\r\n")

                    conn.close()

            break  # jump out of main server loop

        except Exception as e:
            if e.args[0] != errno.ECONNRESET:
                raise e
        finally:
            serversocket.close()
            serversocket = None
            print("HTTP server stopped")


def start():
    pycom.heartbeat(False)

    try:
        pycom.rgbled(0x001000)  # green led if server is working
        server()
        pycom.heartbeat(True)  # flashing blue led if server was stopped normally
    except Exception as e:
        pycom.rgbled(0x100000)  # red led if an error occured
        print(repr(e))
        # write exception info to file for debugging purposes
        t = machine.RTC().now()
        filename = "{}{:02}{:02}-{:02}{:02}{:02}.txt".format(t[0],t[1],t[2],t[3],t[4],t[5])
        with open(filename, 'w') as output:
            output.write("exception: {}\n".format(repr(e)))
            sys.print_exception(e, output)
            output.write("WLAN connected: {}\n".format(network.WLAN().isconnected()))
            output.write("memory: {} bytes free\n".format(gc.mem_free()))


if __name__ == '__main__':
    start()
