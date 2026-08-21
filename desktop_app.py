import os
import sys
import time
import threading
import socket
import urllib.request
import webview

# Import the Flask app from app.py
from app import app, BASE_DIR

def find_free_port():
    """Finds an available local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def run_flask_server(port):
    """Runs the Flask backend in a separate thread."""
    try:
        app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
    except Exception as e:
        print(f"Server error: {e}")

def wait_for_server(port, timeout=10):
    """Waits until Flask server starts accepting requests."""
    start_time = time.time()
    url = f"http://127.0.0.1:{port}/"
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False

def main():
    port = 5000
    # Check if 5000 is open, else find free port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
    except Exception:
        port = find_free_port()

    # Start Flask Server in background thread
    server_thread = threading.Thread(target=run_flask_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to respond
    wait_for_server(port)

    app_url = f"http://127.0.0.1:{port}/"

    # Create Native Windows Application Window
    window = webview.create_window(
        title="Fx Downloader - Ultra HD Video & Audio Downloader",
        url=app_url,
        width=1120,
        height=800,
        min_size=(860, 620),
        background_color='#0b0f19',
        easy_drag=True
    )

    # Start PyWebView Desktop GUI using Windows Edge WebView2 engine
    webview.start(debug=False)

if __name__ == '__main__':
    main()
