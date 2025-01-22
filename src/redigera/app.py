import os
import socketserver
import sys
from os.path import dirname
from threading import Event, Thread
from wsgiref.simple_server import WSGIServer

import django
import toga
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import WSGIRequestHandler

dirpath = dirname(dirname(os.path.abspath(__file__)))
sys.path.insert(0, dirpath)
sys.path.insert(0, os.path.join(dirpath, "rediweb"))

class ThreadedWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    pass


class Redigera(toga.App):
    def web_server(self):
        print("Starting server...")
        # Use port 0 to let the server select an available port.
        self._httpd = ThreadedWSGIServer(("127.0.0.1", 0), WSGIRequestHandler)
        self._httpd.daemon_threads = True

        os.environ["DJANGO_SETTINGS_MODULE"] = "rediweb.keydance.settings"
        django.setup(set_prefix=False)
        wsgi_handler = WSGIHandler()
        self._httpd.set_app(wsgi_handler)

        # The server is now listening, but connections will block until
        # serve_forever is run.
        self.server_exists.set()
        self._httpd.serve_forever()

    def cleanup(self, app, **kwargs):
        print("Shutting down...")
        self._httpd.shutdown()
        return True

    def startup(self):
        self.server_exists = Event()

        self.web_view = toga.WebView()

        self.server_thread = Thread(target=self.web_server)
        self.server_thread.start()

        self.on_exit = self.cleanup

        self.server_exists.wait()
        host, port = self._httpd.socket.getsockname()

        self.main_window = toga.MainWindow()
        self.main_window.size = (1200, 900)
        self.main_window.content = self.web_view
        self.main_window.show()
        self.web_view.url = f"http://{host}:{port}/"
        print((host, port))

def main():
    return Redigera()
