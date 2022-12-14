import json
import utime as time

import uasyncio as asyncio
from machine import Pin, Signal
from uasyncio import Event

import abutton
import expboard2
from ahttpserver import Server, sendfile
from ahttpserver.response import CRLF, MimeType, ResponseHeader, StatusLine
from ahttpserver.sse import EventSource


app = Server()

# Connect variable 'led' to the user led on the expansion board
led = Signal(expboard2.LED, Pin.OUT, value=0, invert=True)

# Connect 'pins' to the user button on the expansion board plus one additional pin
pins = [Pin(i, Pin.IN, Pin.PULL_UP) for i in (expboard2.BUTTON, 14)]

pb_event = Event()  # pushbutton event


@app.route("GET", "/api/pin")
async def api_pin(reader, writer, request):
    eventsource = await EventSource.init(reader, writer)

    await eventsource.send(retry=50000)

    while True:
        await pb_event.wait()
        pb_event.clear()
        try:
            d = dict()
            for i, pin in enumerate(pins):
                d[i] = pin.value()
            await eventsource.send(event="pin_change", data=json.dumps(d))
        except Exception as e:  # catch (a.o.) ECONNRESET when the client has disappeared
            print("api_pin exception:", e)  # debug
            break  # close connection


@app.route("GET", "/api/time")
async def api_time(reader, writer, request):
    eventsource = await EventSource.init(reader, writer)
    while True:
        await asyncio.sleep(1)
        t = time.localtime()
        try:
            await eventsource.send(event="time", data=f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}")
        except Exception as e:
            print("api_time exception:", e)  # debug
            break  # close connection


@app.route("GET", "/")
async def root(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.TEXT_HTML)
    writer.write(CRLF)
    await writer.drain()
    await sendfile(writer, "index.html")


@app.route("GET", "/favicon.ico")
async def favicon(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.IMAGE_X_ICON)
    writer.write(CRLF)
    await writer.drain()
    await sendfile(writer, "favicon.ico")


@app.route("GET", "/api/init")
async def api_init(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.TEXT_HTML)
    writer.write(CRLF)
    await writer.drain()
    pin_status = dict()
    for i, pin in enumerate(pins):
        pin_status[i] = pin.value()
    writer.write(json.dumps(pin_status))


@app.route("GET", "/api/button")
async def api_button(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(CRLF)
    await writer.drain()
    if "LED" in request.parameters:
        led(1) if request.parameters["LED"] == "On" else led(0)
        writer.write(json.dumps(request.parameters))


@app.route("GET", "/api/toggle")
async def api_toggle(reader, writer, request):
    led(not led.value())
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(CRLF)
    await writer.drain()


@app.route("GET", "/api/stop")
async def api_stop(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(CRLF)
    await writer.drain()
    raise (KeyboardInterrupt)


if __name__ == "__main__":
    try:
        def handle_exception(loop, context):
            # uncaught exceptions end up here
            import usys as sys
            sys.print_exception(context["exception"])
            sys.exit()


        def pb_handler(pin, action):
            print("pushbutton handler", pin, action)  # debug
            pb_event.set()


        pb0 = abutton.Pushbutton(pins[0], suppress=True)
        pb0.press_func(pb_handler, ("pb0", "press"))
        pb0.release_func(pb_handler, ("pb0", "release"))

        pb1 = abutton.Pushbutton(pins[1], suppress=True)
        pb1.press_func(pb_handler, ("pb1", "press"))
        pb1.release_func(pb_handler, ("pb1", "release"))

        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_exception)
        loop.create_task(app.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(app.stop())
        asyncio.new_event_loop()
