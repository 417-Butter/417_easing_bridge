import json
import struct
from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QTcpServer, QHostAddress

# セキュリティ定数
MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB上限（メモリ枯渇防止）
MAX_BUFFER_SIZE = 2 * 1024 * 1024  # 2MB上限

class EasingBridgeServer(QObject):
    data_received = Signal(dict)
    status_message = Signal(str)

    def __init__(self, parent=None, port=65432):
        super().__init__(parent)
        self.port = port
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self.on_new_connection)
        self.buffers = {}

    def start(self):
        if self.server.listen(QHostAddress.LocalHost, self.port):
            self.status_message.emit(f"Listening on 127.0.0.1:{self.port}")
            return True
        else:
            self.status_message.emit(f"Failed to start server: {self.server.errorString()}")
            return False
            
    def stop(self):
        if self.server.isListening():
            self.server.close()
            self.status_message.emit("Server stopped.")

    def on_new_connection(self):
        client = self.server.nextPendingConnection()
        if not client:
            return
        self.buffers[client] = b""
        client.readyRead.connect(lambda c=client: self.on_ready_read(c))
        client.disconnected.connect(lambda c=client: self.on_disconnected(c))
        self.status_message.emit("Client connected.")

    def on_disconnected(self, client):
        if client in self.buffers:
            del self.buffers[client]
        client.deleteLater()

    def on_ready_read(self, client):
        if client not in self.buffers:
            return

        data = client.readAll().data()
        self.buffers[client] += data

        # バッファサイズ上限チェック
        if len(self.buffers[client]) > MAX_BUFFER_SIZE:
            self.status_message.emit("Buffer overflow: disconnecting client.")
            self.buffers.pop(client, None)
            client.close()
            return

        while True:
            buffer = self.buffers.get(client)
            if buffer is None or len(buffer) < 4:
                break

            payload_length = struct.unpack(">I", buffer[:4])[0]

            # ペイロードサイズ上限チェック
            if payload_length > MAX_PAYLOAD_SIZE:
                self.status_message.emit(f"Payload too large ({payload_length} bytes): rejecting.")
                self.buffers.pop(client, None)
                client.close()
                return

            if len(buffer) < 4 + payload_length:
                break

            payload_data = buffer[4:4 + payload_length]
            self.buffers[client] = buffer[4 + payload_length:]

            try:
                json_str = payload_data.decode('utf-8')
                command_data = json.loads(json_str)
                
                # コマンドのバリデーション
                cmd = command_data.get('command', '')
                if cmd not in ('REQUEST_CURVE', 'FETCH_RESULT', 'CURVE_DATA', 'ERROR', 'ACTIVATE'):
                    self.status_message.emit(f"Unknown command rejected: {cmd}")
                    continue
                
                self.status_message.emit(f"Received: {cmd}")
                self.data_received.emit({"client": client, "payload": command_data})
                
            except json.JSONDecodeError as e:
                self.status_message.emit(f"Invalid JSON: {e}")
            except Exception as e:
                self.status_message.emit(f"Error: {e}")

    def send_response(self, client, payload_dict):
        try:
            json_str = json.dumps(payload_dict)
            payload_bytes = json_str.encode('utf-8')
            header = struct.pack(">I", len(payload_bytes))
            client.write(header + payload_bytes)
            client.flush()
        except Exception as e:
            self.status_message.emit(f"Failed to send: {e}")
