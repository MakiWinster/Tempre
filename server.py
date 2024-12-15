from flask import Flask, render_template, request
from flask_socketio import SocketIO
import json
from datetime import datetime
import time

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
        self.session_to_client = {}  # 存储会话ID到客户端ID的映射
        self.heartbeat_fails = {}  # 存储心跳失败次数

    def has_active_clients(self):
        # 检查是否有在线且正在发送数据的客户端
        return any(client["online"] for client in self.clients.values())

    def check_heartbeats(self):
        # 如果没有在线客户端，不执行心跳检查
        if not self.has_active_clients():
            print("No active clients, skipping heartbeat check")
            return

        current_time = datetime.now()
        for client_id, client_info in list(self.clients.items()):
            if client_info["online"]:
                try:
                    print(f"Sending ping to client {client_id}")
                    # 发送ping并等待响应
                    socketio.emit('ping', {'client_id': client_id})
                    
                    # 更新心跳失败计数
                    if client_id not in self.heartbeat_fails:
                        self.heartbeat_fails[client_id] = 0
                    self.heartbeat_fails[client_id] += 1
                    
                    # 检查心跳失败次数
                    if self.heartbeat_fails[client_id] >= 3:
                        print(f"Client {client_id} heartbeat timeout after 3 failures")
                        self.clients[client_id]["online"] = False
                        socketio.emit('client_status', {
                            'client_id': client_id,
                            'status': 'offline',
                            'timestamp': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                            'message': '心跳检测失败3次，客户端离线'
                        }, broadcast=True)
                        self.heartbeat_fails[client_id] = 0
                except Exception as e:
                    print(f"Error sending ping to {client_id}: {e}")

    def handle_pong(self, client_id):
        if client_id in self.heartbeat_fails:
            self.heartbeat_fails[client_id] = 0

    def get_or_create_client_id(self, session_id):
        if session_id in self.session_to_client:
            return self.session_to_client[session_id]
        else:
            self.client_count += 1
            new_id = f"CLIENT{self.client_count}"
            self.session_to_client[session_id] = new_id
            return new_id

    def add_client(self, client_id):
        print(f"Adding client: {client_id}")
        if client_id not in self.clients:
            self.clients[client_id] = {
                "online": True,
                "last_seen": datetime.now()
            }
            self.heartbeat_fails[client_id] = 0
            return True
        return False

    def remove_client(self, client_id):
        print(f"Removing client: {client_id}")
        if client_id in self.clients:
            self.clients[client_id]["online"] = False
            if client_id in self.heartbeat_fails:
                del self.heartbeat_fails[client_id]
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

    def update_heartbeat(self, client_id):
        if client_id in self.clients:
            self.heartbeats[client_id] = datetime.now()
            self.heartbeat_fails[client_id] = 0  # 重置失败计数
            if not self.clients[client_id]["online"]:
                # 如果客户端之前离线，现在发送心跳，则重新上线
                self.clients[client_id]["online"] = True
                socketio.emit('client_status', {
                    'client_id': client_id,
                    'status': 'online',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'message': '心跳恢复，客户端重新上线'
                }, broadcast=True)

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
        print(f"Emitting client_id_assigned: {client_id}")
        socketio.emit('client_id_assigned', {'client_id': client_id}, to=request.sid)
        print(f"Emitting client_status")
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
    print(f"Received sensor data: {data}")
    processed_data = sensor_server.handle_sensor_data(data)
    print(f"Broadcasting processed data: {processed_data}")
    socketio.emit('sensor_data', processed_data, broadcast=True)

@socketio.on('heartbeat')
def handle_heartbeat(data):
    client_id = data.get('client_id')
    if client_id:
        sensor_server.update_heartbeat(client_id)
        return {'status': 'ok'}

@socketio.on('pong')
def handle_pong(data):
    client_id = data.get('client_id')
    if client_id:
        sensor_server.handle_pong(client_id)
        return {'status': 'ok'}

@socketio.on('client_resume')
def handle_client_resume(data):
    client_id = data.get('client_id')
    if client_id and client_id in sensor_server.clients:
        print(f"Client {client_id} resuming data transmission")
        sensor_server.clients[client_id]["online"] = True
        sensor_server.heartbeat_fails[client_id] = 0
        socketio.emit('client_status', {
            'client_id': client_id,
            'status': 'online',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'message': '客户端恢复数据传输'
        }, broadcast=True)
        return {'status': 'ok'}
    return {'status': 'error'}

def check_heartbeats_task():
    while True:
        sensor_server.check_heartbeats()
        time.sleep(3)  # 每3秒检查一次

if __name__ == '__main__':
    print("Starting server...")
    # 启动心跳检查线程
    from threading import Thread
    heartbeat_thread = Thread(target=check_heartbeats_task, daemon=True)
    heartbeat_thread.start()
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 