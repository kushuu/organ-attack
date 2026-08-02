import argparse
import asyncio
import os
import threading
from server.server import run_server


def run_server_thread(host: str, port: int):
    """Run the server in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_server(host, port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organ Attack - Card Game")
    parser.add_argument("--host", action="store_true", help="Start as game server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)),
                        help="WebSocket server port (default: 8765 or $PORT)")
    parser.add_argument("--server-host", default="0.0.0.0", help="Server bind address (default: 0.0.0.0)")
    parser.add_argument("--web", action="store_true", help="Also start web frontend server (port 8080)")
    parser.add_argument("--web-port", type=int, default=8080, help="Web frontend port (default: 8080)")

    args = parser.parse_args()

    if args.host:
        # Start WebSocket server
        print(f"Starting WebSocket server on ws://{args.server_host}:{args.port}")

        # Optionally start web server
        if args.web:
            from server.web_server import start_web_server, get_web_url
            web_server = start_web_server(args.server_host, args.web_port)
            web_url = get_web_url(args.server_host, args.web_port)
            print(f"Web frontend available at {web_url}")
            print(f"Players can open this URL in their browser to play!")

        print("Press Ctrl+C to stop.")
        thread = threading.Thread(target=run_server_thread, args=(args.server_host, args.port))
        thread.daemon = True
        thread.start()
        try:
            while thread.is_alive():
                thread.join(timeout=1)
        except KeyboardInterrupt:
            print("\nServer stopped.")
    else:
        try:
            from gui.main_window import main
            main()
        except ImportError as e:
            print(f"Error: {e}")
            print("To run the GUI game client, please install tkinter:")
            print("  sudo apt-get install python3-tk")
            print("")
            print("Or run the server with: python main.py --host --web")
