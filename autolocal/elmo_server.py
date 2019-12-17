import requests
from allennlp.commands.elmo import ElmoEmbedder
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading
elmo = ElmoEmbedder()

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        message =  threading.currentThread().getName()
        self.wfile.write(message)
        self.wfile.write('\n')
        return

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        # self.send_header('Access-Control-Allow-Origin', 'https://rxdhawkins.me')
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = post_data
        print(data)
        output = elmo.embed_sentence(data)
        self._set_headers()
        self.wfile.write(output)
        #self.wfile.write("<html><body><h1>POST!</h1></body></html>")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == '__main__':
    server = ThreadedHTTPServer(('localhost', 8000), Handler)
    print('Starting server, use <Ctrl-C> to stop')
    server.serve_forever()
