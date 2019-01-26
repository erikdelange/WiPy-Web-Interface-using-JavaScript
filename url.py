# Routines for decoding an HTTP request-line.
#
# HTTP request as understood by this package:
#
#   Request-Line = Method SP Request-URI SP HTTP-Version CRLF
#   Request-URI = Path ? Query
#
# Example: "GET /page?name1=0.07&name2=0.03&name3=0.13 HTTP/1.1\r\n"
#
#   Method = GET
#   Request-URI = /page?name1=0.07&name2=0.03&name3=0.13
#   HTTP-version = HTTP/1.1
#   Path = /page
#   Query = name1=0.07&name2=0.03&name3=0.13
#
# See also: https://www.tutorialspoint.com/http/http_requests.htm


def query(request):
    """ Extract all name=value pairs from a request-URI's query into a dict.

    Example: request b"GET /page?name1=0.07&name2=0.03&name3=0.13 HTTP/1.1\r\n"
    yields dictionary {'name1': '0.07', 'name2': '0.03', 'name3': '0.13'}.

    :param str request: the complete HTTP request-line.
    :return dict: dictionary with zero of more entries.
    """
    d = dict()
    p = request.find(b"?")  # only look in the query part of a request-URI
    if p != -1:
        p_space = request.find(b" ", p)
        while True:
            n_start = p + 1
            n_end = request.find(b"=", n_start)
            v_start = n_end + 1
            p_and = request.find(b"&", v_start)
            v_end = p_space if p_and == -1 else min(p_space, p_and)
            d[request[n_start:n_end].decode("utf-8")] = request[v_start:v_end].decode("utf-8")
            p = v_end
            p = request.find(b"&", p)
            if p == -1:
                break
    return d


def value(request, name):
    """ Extract the value for a single name=value pair from a request-URI's query.

    The query string may contain multiple name-value pairs. If name occurs
    multiple times in the query string the first value is extracted.

    :param str request: the complete HTTP request-line.
    :param str name: the name to search in the query.
    :return value: None if name is not present in the URI query.
    """
    value = None
    query = request.find(b"?")  # only look in the query part of a request-URI
    if query != -1:
        n_start = request.find(name.encode("utf-8"), query)
        if n_start != -1:
            v_start = request.find(b"=", n_start) + 1
            v_space = request.find(b" ", v_start)
            v_and = request.find(b"&", v_start)
            v_end = v_space if v_and == -1 else min(v_space, v_and)
            value = request[v_start:v_end].decode("utf-8")
    return value


def path(request):
    """ Extract the URI path from a HTTP request.

    Convention: the URI for an absolute path is never empty, at least a
    forward slash is present.

    :param str request: the complete HTTP request-line.
    :return str path: path, not including the query string
    """
    u_start = request.find(b"/")
    p_space = request.find(b" ", u_start)
    p_query = request.find(b"?", u_start)
    u_end = p_space if p_query == -1 else min(p_space, p_query)
    return request[u_start:u_end].decode("utf-8")


def request(line):
    """ Separate an HTTP request line in its elements and put them into a dict.

    :param str line: the complete HTTP request-line.
    :return dict: dictionary containing
            method      the request method ("GET", "PUT", ...)
            uri         the request URI, including the query (if any)
            version     the HTTP version
            parameter   dictionary with name=value pairs from the query
    """
    d = {key: value for key, value in zip(["method", "uri", "version"], line.decode("utf-8").split())}

    d["parameter"] = query(line)

    question = d["uri"].find("?")

    d["path"] = d["uri"] if question == -1 else d["uri"][0:question]
    d["query"] = "" if question == -1 else d["uri"][question + 1:]
    d["header"] = dict()

    return d
