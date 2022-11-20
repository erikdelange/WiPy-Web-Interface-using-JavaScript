# MicroPython web interface using server-sent events and JavaScript
A MicroPython and JavaScript based web user interface for a WiPy to control the LED and display the user button status on a Pycom Expansion Board 2.0

### Summary
Pycoms Expansion Board 2.0 contains a user controllable led and a push-button. In [this repository](https://github.com/erikdelange/WiPy-2.0-Web-Interface) a simple web interface was presented to control this led and display the status of the button (plus one additional input pin). This solution has two disadvantages.
1. A new led state (button on / off / toggle) is transmitted to the server using HTML's 'submit' input type. As a response the client expects a new webpage. Quite inefficient if nothing on the displayed page changes.
2. The status of the expansion boards button is retrieved by periodically refreshing the whole web page. Ideally this would be initiated from the server only when the button is actually pressed or released.

This example shows how server-sent events and JavaScript help to solve these issues and streamline the communication between server and client.

### HTML and JavaScript
The HTML code in *index.html* uses the W3.CSS framework for formatting the web page. The key elements to look for in the HTML code are the empty line where a javascript function will place the table body which holds the status of the WiPy's buttons, and the three buttons to switch the led on, off or toggle it. Additionally, the page contains a placeholder which the server will update with the current time.

The JavaScript code consists of three event handlers. *onLoadEvent()* is run once, immediately after the page has been loaded. It requests the initial content of the button table from the server, and starts listening to the server for changes to the expansion boards button status. Event handlers *onClickEvent()* and *onToggleEvent()* are fired when one of the three buttons in the UI is clicked, and inform the server of this fact.

### Fetch API and server-sent events
For sending information to the server (and optionally receiving response data) I use the fetch() API. Its most simple appearance (with some helper functions from the Google Developers site) is:
``` JavaScript
function onToggleEvent(event) {
  fetch("/api/toggle")
  .then(validateResponse)
  .catch(logError);
}
```
If the server returns data in its reply function then function *onClickEvent()* provides an example how to handle this.

Instead of the client polling for changes in the button status, I'm using server-sent events. This creates a connection from the server to the client which stays open. The server can then publish updates via this connection. An event listener on the client is started which listens to a specific event of type 'pin_change'.
``` JavaScript
// Setup pin event listener
const eventSource = new EventSource("/api/pin");

eventSource.addEventListener("pin_change", (event) => {
  console.log("pin_change event:", event, "data:", data);
});
```
The browser listen for two events. Upon receipt of a 'time' event the current time on the page is updated, and when receiving a 'pin_change' event the table with the button status is refreshed.
### Python Code
Interaction between the microcontroller and the UI is handled via a small HTTP server, which can be found in package [*ahttpserver*](https://github.com/erikdelange/MicroPython-HTTP-Server).

#### Connection Keep-Alive
A GET request for paths "/api/pin" and "/api/time" is special as it keeps the connection to the client open for sending updates. So, the connection handler does not return until the client has disappeared or closed the connection. An EventSource object is used to communicate with the client to make sure the information sent conforms to the event stream format (but you could also arrange this by hand).

#### Pin change interrupt
Callbacks are attached to the expansion boards button. On button press or release one is called and sets an asyncio Event (called pb_event). The connection handler for "/api/pin" is waiting for this event to be set, and then wakes up to send the new button status to the client (of course only if a client has previously expressed its interest in this event). To see this in action keep the button on your Expansion Board pressed for a few seconds and watch the UI.
``` Python
from uasyncio import Event

pb_event = Event()  # pushbutton event

@app.route("GET", "/api/pin")
async def api_pin(reader, writer, request):
    eventsource = await EventSource.upgrade(reader, writer)
    while True:
        await pb_event.wait()
        pb_event.clear()
        try:
            d = dict()
            for i, pin in enumerate(pins):
                d[i] = pin.value()
            await eventsource.send(event="pin_change", data=json.dumps(d))
        except Exception as e:  # catch (a.o.) ECONNRESET when the client has disappeared
            break  # close connection
```
The time connection handler *api_time* just wakes up every second and sends the current time in string format to the client.

The resulting web page looks like this.

![ui.png](https://github.com/erikdelange/WiPy-2.0-Web-Interface-using-JavaScript/blob/master/ui.png)

The JavaScript code in index.html prints various logging messages. Use F12 on Chrome or Edge and have a look these messages in the console.

### Using
* WiPy 3.0 using the official MicroPython firmware from micropython.org instead of Pycom's variant
* MicroPython v1.19.1 on 2022-11-03; ESP32 module (spiram) with ESP32
* Pycom Expansion Board 2
* Package *ahttpserver* which can be found [here](https://github.com/erikdelange/MicroPython-HTTP-Server).
* Module *abutton* from [Kevin Köck](https://github.com/kevinkk525/pysmartnode/blob/master/pysmartnode/utils/abutton.py).
