from app import app, socketio
import routes  # noqa: F401
import socket_events  # noqa: F401

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
