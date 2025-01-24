import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from gradio_client import Client, file

# List of Gradio Clients
api_clients = [
    "Kaliboy002/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro"
]

current_client_index = 0

def get_client():
    global current_client_index
    return Client(api_clients[current_client_index])

def switch_client():
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)

def process_face_swap(source_path, target_path):
    while True:
        try:
            client = get_client()
            result = client.predict(
                source_file=file(source_path),
                target_file=file(target_path),
                doFaceEnhancer=True,
                api_name="/predict"
            )
            return result
        except Exception as e:
            print(f"Error with API {api_clients[current_client_index]}: {e}")
            switch_client()

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/face-swap":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            source_file = data.get("source_file")
            target_file = data.get("target_file")

            if not source_file or not target_file:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing source_file or target_file in the request")
                return

            try:
                result_path = process_face_swap(source_file, target_file)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {"result_file": result_path}
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

# Run the server
def run(server_class=HTTPServer, handler_class=RequestHandler, port=8000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
