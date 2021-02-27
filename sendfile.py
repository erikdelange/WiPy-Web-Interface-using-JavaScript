
# MIT license / Copyright 2021 (c) Erik de Lange

_buffer = bytearray(512)
_bmview = memoryview(_buffer)


def sendfile(conn, filename):
    """ Send a file to a connection in chunks - lowering memory usage.

    :param socket conn: connection to send the file content to
    :param str filename: name of file the send
    """
    with open(filename, "rb") as fp:
        while True:
            n = fp.readinto(_buffer)
            if n == 0:
                break
            conn.write(_bmview[:n])
