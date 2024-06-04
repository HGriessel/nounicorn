# Uncomment this to pass the first stage
import socket
import concurrent.futures
import logging
import sys


def http_response(code, reason_phrase, body=None, headers={}):
    headers_parse = ""
    if headers != {}:
        for key, val in headers.items():
            headers_parse = f"{headers_parse}{key}: {val}\r\n"
    response = f"HTTP/1.1 {code} {reason_phrase}\r\n{headers_parse}\r\n"
    if body:
        response = (
            response.encode() + body
            if isinstance(body, bytes)
            else response.encode() + body.encode()
        )
    else:
        response = response.encode()
    return response


def parse_request(message):
    request = {}
    request_blocks = message.decode("utf-8").split("\r\n\r\n")
    header_block = request_blocks[0]
    body_block = request_blocks[1] if len(request_blocks) > 1 else ""

    header_lines = header_block.split("\r\n")
    request["method"], request["target"], request["http_version"] = header_lines[
        0
    ].split(" ")
    request["headers"] = {}
    for line in header_lines[1:]:
        if ":" in line:
            header, value = line.split(": ", 1)
            request["headers"][header] = value

    request["body"] = body_block
    return request


def handle_request(conn, client_addr):
    message = conn.recv(512)
    request = parse_request(message)
    logging.info("Request recieved: %s", request)

    if request["target"] == "/":
        logging.info(f"Request recieved on {request['target']}")
        conn.sendall(http_response(200, "OK"))
        conn.close()
        return

    if "echo" in request["target"]:
        logging.info(f"Request recieved on {request['target']}")
        path_parts = request["target"].split("/")
        echo_message = path_parts[2]
        headers = {"Content-Type": "text/plain", "Content-Length": len(echo_message)}
        conn.sendall(http_response(200, "OK", body=echo_message, headers=headers))
        conn.close()
        return

    if request["target"] == "/user-agent":
        logging.info(f"Request recieved on {request['target']}")
        headers = {
            "Content-Type": "text/plain",
            "Content-Length": len(request["headers"]["User-Agent"]),
        }
        body = request["headers"]["User-Agent"]
        conn.sendall(http_response(200, "OK", headers=headers, body=body))
        conn.close()
        return

    if "file" in request["target"]:
        if request["method"] == "GET":
            logging.info(f"GET Request recieved on {request['target']}")
            directory = None

            path_parts = request["target"].split("/")
            if len(sys.argv) > 1:
                directory = sys.argv[2]

            if directory:
                file_name = f"{directory}/{path_parts[2]}"
            else:
                file_name = path_parts[2]

            logging.info(f"Trying to open file: {file_name}")

            try:
                with open(file_name, "rb") as file:
                    file_contents = file.read()
            except Exception:
                conn.sendall(http_response(404, "Not Found"))
                return

            body = file_contents
            headers = {
                "Content-Type": "application/octet-stream",
                "Content-Length": len(body),
            }
            logging.info(f"Headers: {headers} Body: {body}")
            conn.sendall(http_response(200, "OK", headers=headers, body=body))
            conn.close()
            return

        if request["method"] == "POST":
            logging.info(f"Request recieved on {request['target']}")
            logging.debug(f"Request {request}")
            directory = None

            path_parts = request["target"].split("/")
            if len(sys.argv) > 1:
                directory = sys.argv[2]

            if directory:
                file_name = f"{directory}/{path_parts[2]}"
            else:
                file_name = path_parts[2]

            logging.info(f"Trying to create file: {file_name}")
            try:
                with open(file_name, "w") as f:
                    f.write(request["body"])
            except Exception:
                conn.sendall(http_response(500, "Internal Error"))
                conn.close()
                return
            conn.sendall(http_response(201, "Created"))
            conn.close
            return

    conn.sendall(http_response(404, "Not Found"))
    conn.close()


def main():
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.DEBUG, datefmt="%H:%M:%S")
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        while True:
            conn, client_addr = server_socket.accept()  # wait for client
            executor.submit(handle_request, conn, client_addr)


if __name__ == "__main__":
    main()
