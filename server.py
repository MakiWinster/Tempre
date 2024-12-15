from flask import Flask, render_template, request
from flask_socketio import SocketIO
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',
                   logger=True,
                   engineio_logger=True)

class SensorServer:
    def __init__(self):
        self.clients = {}  # 存储客户端连接状态
        self.data_history = []  # 存储历史数据
        self.max_history = 100  # 最多保存100条历史记录
        self.client_count = 0  # 用于生成客户端ID
        self.client_ids = {}  # 存储客户端ID映射

    def get_or_create_client_id(self, session_id):
        if session_id in self.client_ids:
            return self.client_ids[session_id]
        else:
            self.client_count += 1
            new_id = f"CLIENT{self.client_count}"
            self.client_ids[session_id] = new_id
            return new_id

    def add_client(self, client_id):
        print(f"Adding client: {client_id}")  # 调试日志
        if client_id not in self.clients:
            self.clients[client_id] = {
                "online": True,
                "last_seen": datetime.now()
            }
            return True
        return False

    def remove_client(self, client_id):
        print(f"Removing client: {client_id}")  # 调试日志
        if client_id in self.clients:
            self.clients[client_id]["online"] = False
            return True
        return False

    def handle_sensor_data(self, data):
        print(f"Processing sensor data: {data}")  # 调试日志
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_entry = {
            'timestamp': timestamp,
            'client_id': data['client_id'],
            'temperature': data['temperature'],
            'humidity': data['humidity']
        }
        
        self.data_history.append(data_entry)
        if len(self.data_history) > self.max_history:
            self.data_history.pop(0)
        
        return data_entry

    def get_history(self):
        return self.data_history

    def get_clients(self):
        return self.clients

# 创建服务器实例
sensor_server = SensorServer()

@app.route('/')
def index():
    return render_template('index.html', 
                         history=sensor_server.get_history(),
                         clients=sensor_server.get_clients())

@socketio.on('connect')
def handle_connect():
    print('Client connected to web interface')

@socketio.on('client_connect')
def handle_client_connect(data):
    print(f"Received client connect request from session: {request.sid}")
    client_id = sensor_server.get_or_create_client_id(request.sid)
    print(f"Using client ID: {client_id}")
    
    if sensor_server.add_client(client_id):
        socketio.emit('client_id_assigned', {'client_id': client_id}, to=request.sid)
        socketio.emit('client_status', {
            'client_id': client_id,
            'status': 'online',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, broadcast=True)
        print(f"Client {client_id} successfully connected")

@socketio.on('client_disconnect')
def handle_client_disconnect(data):
    client_id = data.get('client_id')
    print(f"Client disconnect request: {client_id}")  # 调试日志
    if sensor_server.remove_client(client_id):
        socketio.emit('client_status', {
            'client_id': client_id,
            'status': 'offline',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, broadcast=True)

@socketio.on('sensor_data')
def handle_sensor_data(data):
    print(f"Received sensor data: {data}")  # 调试日志
    processed_data = sensor_server.handle_sensor_data(data)
    socketio.emit('sensor_data', processed_data, broadcast=True)

if __name__ == '__main__':
    print("Starting server...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 