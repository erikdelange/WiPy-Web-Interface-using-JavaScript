# WiPy 2.0 Web Interface using JavaScript
A JavaScript based web interface to control the LED and read the user button status on WiPy Expansion Board 2.0

### Summary
WiPy Expansion Board 2.0 contains a user controllable led and a push-button. In [this repository](https://github.com/erikdelange/WiPy-2.0-Web-Interface) a simple web interface was presented to control this led and display the status of the button (plus one additional input pin). This solution has two disadvantages.
1. The button status is transmitted using 'submit'. As a results the client expects a new webpage. Quite inefficient if nothing in the displayed page changes.
2. The status of the button is retrieved by periodically refreshing the whole web page. Ideally this would be initiated from the server only when the button is actually pressed or released.

This example shows how JavaScript helps to solve this and streamlines the communication between client and server.

### HTML and JavaScript
The HTML code in *index.html* uses the W3.CSS framework for formatting the web page. The key elements to look for in the HTML code are the empty space where the table body which will hold the status of the WiPy's buttons will be placed, and the three buttons to switch the led on or off.

The JavaScript code consists of three event handlers. *onLoadEvent()* is run once, immediately after the page has been loaded. It requests the initial content of the button table from the server, and starts listening to the server for changes to the expansion boards button status. Event handlers *onClickEvent()* and *onToggleEvent()* are fired when one of the three buttons in the UI is clicked, and inform the server of this fact.

### Fetch API and Server Sent Events
For sending information to the server (and optionally receiving response data) I use the fetch() API instead of XMLHttpRequest. Its most simple appearance (with some helper functions from the Google Developers site) is:
``` JavaScript
function onToggleEvent(event) {
  fetch("/api/toggle")
  .then(validateResponse)
  .catch (logError);
}
```
If the server also returns data in its reply function then function *onClickEvent()* shows how to handle this.

Instead of the client polling for changes in the button status, I'm using Server Sent Events. This creates a connection from the server to the client which stays open. The server can then publish updates via this connection. An event listener on the client only catches a specific event (here: pin_change).

### Python Code
The server waits for a new HTML request. The first line of the request contains the path and optionally the query parameters. These are unpacked into dictionary *request*. Subsequent request lines contain the header fields and are recorded in dictionary *header*. A request for path "/api/pin" keeps the connection to the client open for server sent events ("keep-alive"). Notice the different response headers here compared to other request paths.

An interrupt callback is attached to expansion boards button i.e. pin object. On every pin level change it is called and transmits the new button status to the client (of course only if the client has expressed its interest in this event previously). To see this in action keep the button on your Expansion Board pressed for a few seconds and watch the UI.

The webpage in index.html is - at least for the WiPy 2's memory - quite large (4K). To save memory it is sent to the client in chuncks of 512 bytes. In this way only the space for a 512 byte buffer needs to be allocated which reduces the chance for out of memory exceptions. See function sendfile in http.py.
``` python
buffer = bytearray(512)
bmview = memoryview(buffer)

def sendfile(conn, filename):
    """ Send a file to a connection in chuncks - lowering memory usage.

    :param socket conn: connection to send the file to
    :param str filename: file the send
    """
    with open(filename, "rb") as fp:
        while True:
            n = fp.readinto(buffer)
            if n == 0:
                break
            conn.write(bmview[:n])
```
The resulting web page looks like this.

![ui.png](https://github.com/erikdelange/WiPy-2.0-Web-Interface-using-JavaScript/blob/master/ui.png)

### Using
* WiPy 2.0
* Pycom MicroPython 1.20.0.rc1 [v1.9.4-bc4d7d0] on 2018-12-12; WiPy with ESP32
* Expansion Board 2
* Chrome Version 87.0.4280.88 (64-bits)
* Edge Version 87.0.664.66 (64-bits)

Use F12 on Chrome or Edge and have a look the messages printed in the console.
