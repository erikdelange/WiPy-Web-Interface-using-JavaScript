# WiPy 2.0 Web Interface using JavaScript
A JavaScript based web interface to control the LED and read the user button status on a Pycom Expansion Board 2.0

### Summary
Pycoms Expansion Board 2.0 contains a user controllable led and a push-button. In [this repository](https://github.com/erikdelange/WiPy-2.0-Web-Interface) a simple web interface was presented to control this led and display the status of the button (plus one additional input pin). This solution has two disadvantages.
1. A new led state (buttons on / off / toggle) is transmitted to the server using HTML's 'submit' input type. As a results the client expects a new webpage. Quite inefficient if nothing on the displayed page changes.
2. The status of the expansion boards button is retrieved by periodically refreshing the whole web page. Ideally this would be initiated from the server only when the button is actually pressed or released.

This example shows how JavaScript helps to solve this and streamlines the communication between client and server.

### HTML and JavaScript
The HTML code in *index.html* uses the W3.CSS framework for formatting the web page. The key elements to look for in the HTML code are the empty line where a javascript function will place the table body which holds the status of the WiPy's buttons, and the three buttons to switch the led, off or toggle it.

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

Instead of the client polling for changes in the button status, I'm using Server Sent Events. This creates a connection from the server to the client which stays open. The server can then publish updates via this connection. An event listener on the client only catches a specific event (here named: pin_change).

### Python Code
A small generic HTTP server is used, which can be found in package *httpserver*, file *server.py*. It waits for incoming HTTP requests. The first line of the request contains the path and optionally the query parameters. These are unpacked into dictionary *request*. Subsequent request lines contain the header fields and are recorded as name-value pairs in dictionary *header*.

#### Routing client requests using decorators
For every combination of method plus path (like "GET" and "/index") which must be handled by the HTTP server a function is declared in *main.py*. By preceding the function definition with decorator *@route* the function is registered within *server.py* as a handler for the specified method-path combination. In this way the code for the server itself remains hidden and generic; you only need to define the handlers. See the comments in *server.py* for more details. The server is so simple that you need to craft HTTP responses yourself line by line. Use *response.py* for
a bit of help.
``` python
from httpserver import sendfile, Server, CONNECTION_CLOSE, CONNECTION_KEEP_ALIVE

app = Server()

@app.route("GET", "/")
def root(conn, request):
    conn.write(b"HTTP/1.1 200 OK\r\n")
    conn.write(b"Connection: close\r\n")
    conn.write(b"Content-Type: text/html\r\n")
    conn.write(b"\r\n")
    sendfile(conn, "index.html")
    return CONNECTION_CLOSE

app.start()
```
#### Connection Keep-Alive
A GET request for path "/api/pin" is special as it keeps the connection to the client open for server sent events ("keep-alive"). Notice the different response headers here compared to other request paths.

#### Pin change interrupt
An interrupt callback is attached to expansion boards button i.e. pin object. On every pin level change it is called and transmits the new button status to the client (of course only if the client has expressed its interest in this event previously). To see this in action keep the button on your Expansion Board pressed for a few seconds and watch the UI.

#### Sending large files
The webpage in index.html and the favicon.ico are - at least for a WiPy 2's memory - quite large (4K resp. 15K). To save memory they are sent to the client in chuncks of 512 bytes. In this way only the space for a 512 byte buffer needs to be allocated which reduces the chance for out of memory exceptions. See function sendfile in *sendfile.py*.
``` python
_buffer = bytearray(512)
_bmview = memoryview(_buffer)

def sendfile(conn, filename):
    """ Send a file to a connection in chuncks - lowering memory usage.

    :param socket conn: connection to send the file to
    :param str filename: file the send
    """
    with open(filename, "rb") as fp:
        while True:
            n = fp.readinto(_buffer)
            if n == 0:
                break
            conn.write(_bmview[:n])
```
The resulting web page looks like this.

![ui.png](https://github.com/erikdelange/WiPy-2.0-Web-Interface-using-JavaScript/blob/master/ui.png)

### Using
* WiPy 2.0
* Pycom MicroPython 1.20.2.r4 [v1.11-ffb0e1c] on 2021-01-12; WiPy with ESP32
* Expansion Board 2

The JavaScript code in index.html prints various logging messages. Use F12 on Chrome or Edge and have a look these messages in the console.
