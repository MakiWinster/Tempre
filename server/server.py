import sys
import socket
import time
import threading
import json
from typing import Dict, Tuple
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from .ui.main_window import MainWindow
from common.protocol import Protocol, MessageType

class ClientInfo:
    """客户端信息类"""
    def __init__(self, socket: socket.socket, address: Tuple[str, int]):
        self.socket = socket
        self.address = address
        self.id = None
        self.last_heartbeat = time.time()
        self.temperature = None
        self.humidity = None
        self.status = "在线"
        self.missed_heartbeats = 0  # 错过的心跳次数

class Server:
    """传感器数据采集服务器"""
    
    def __init__(self):
        """初始化服务器"""
        self.window = MainWindow()
        self.server_socket = None
        self.clients: Dict[str, ClientInfo] = {}  # client_id -> ClientInfo
        
        # 创建心跳检查定时器
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._check_heartbeats)
        
        # 创建客户端更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_client_list)
        
        # 创建接收线程停止事件
        self.stop_event = threading.Event()
        self.accept_thread = None
        
        # 连接信号
        self.window.start_server_clicked.connect(self.start_server)
        self.window.stop_server_clicked.connect(self.stop_server)
        
        # 显示窗口
        self.window.show()
    
    def _parse_server_address(self, address: str) -> Tuple[str, int]:
        """解析服务器地址
        
        Args:
            address: 服务器地址字符串（格式：host:port）
            
        Returns:
            主机名和端口号元组
        """
        try:
            host, port = address.split(':')
            return host.strip(), int(port.strip())
        except ValueError:
            raise ValueError('服务器地址格式错误，应为 host:port')
    
    def start_server(self, address: str):
        """启动服务器"""
        try:
            host, port = self._parse_server_address(address)
            
            # 创建服务器socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((host, port))
            self.server_socket.listen(5)
            
            # 更新UI状态
            self.window.set_server_state(True)
            self.window.log_message(f'服务器已启动，监听地址：{address}')
            
            # 启动接收线程
            self.stop_event.clear()
            self.accept_thread = threading.Thread(target=self._accept_connections)
            self.accept_thread.start()
            
            # 在主线程中启动定时器
            QTimer.singleShot(0, lambda: self._start_timers())
            
        except Exception as e:
            self.window.log_message(f'启动服务器失败：{str(e)}')
            self.stop_server()
    
    def _start_timers(self):
        """在主线程中启动定时器"""
        self.heartbeat_timer.start(3000)  # 3秒检查一次心跳
        self.update_timer.start(1000)  # 1秒更新一次客户端列表
    
    def stop_server(self):
        """停止服务器"""
        # 停止定时器
        self.heartbeat_timer.stop()
        self.update_timer.stop()
        
        # 停止接收线程
        if self.accept_thread and self.accept_thread.is_alive():
            self.stop_event.set()
            if self.server_socket:
                try:
                    # 创建一个连接来解除accept阻塞
                    socket.create_connection(self.server_socket.getsockname())
                except:
                    pass
            self.accept_thread.join()
        
        # 断开所有客户端连接
        for client_id in list(self.clients.keys()):
            self._remove_client(client_id)
        
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        # 更新UI状态
        self.window.set_server_state(False)
        self.window.log_message('服务器已停止')
    
    def _accept_connections(self):
        """接受客户端连接的线程函数"""
        while not self.stop_event.is_set():
            try:
                client_socket, address = self.server_socket.accept()
                if self.stop_event.is_set():
                    client_socket.close()
                    break
                
                # 创建客户端处理线程
                client = ClientInfo(client_socket, address)
                threading.Thread(target=self._handle_client, args=(client,)).start()
                
            except Exception as e:
                if not self.stop_event.is_set():
                    self.window.log_message(f'接受连接错误：{str(e)}')
    
    def _handle_client(self, client: ClientInfo):
        """处理客户端连接
        
        Args:
            client: 客户端信息对象
        """
        try:
            while not self.stop_event.is_set():
                data = client.socket.recv(1024)
                if not data:
                    break
                
                # 解析消息
                message = Protocol.unpack(data)
                client_id = message['client_id']
                
                # 处理不同类型的消息
                if message['type'] == 'connect':
                    # 检查是否存在同名在线客户端
                    if client_id in self.clients and self.clients[client_id].status == "在线":
                        # 发送拒绝连接消息
                        response = {
                            "type": "connect_response",
                            "success": False,
                            "message": "已存在同名客户端在线"
                        }
                        client.socket.send(json.dumps(response).encode('utf-8'))
                        break
                    self._handle_connect(client, client_id)
                    # 发送接受连接消息
                    response = {
                        "type": "connect_response",
                        "success": True,
                        "message": "连接成功"
                    }
                    client.socket.send(json.dumps(response).encode('utf-8'))
                elif message['type'] == 'disconnect':
                    self._handle_disconnect(client_id)
                    break
                elif message['type'] == 'heartbeat':
                    self._handle_heartbeat(client_id)
                elif message['type'] == 'data':
                    self._handle_data(client_id, message['data'])
                
        except Exception as e:
            self.window.log_message(f'处理客户端消息错误：{str(e)}')
        finally:
            if client.id:
                self._remove_client(client.id)
    
    def _handle_connect(self, client: ClientInfo, client_id: str):
        """处理客户端连接消息"""
        if client_id in self.clients:
            old_client = self.clients[client_id]
            if old_client.status == "离线":
                # 如果是离线客户端重新连接
                old_client.socket.close()
                self.window.add_status_record(client_id, "重新上线")
            else:
                # 如果是新连接替换旧连接
                self._remove_client(client_id)
                self.window.add_status_record(client_id, "重新连接")
        else:
            self.window.add_status_record(client_id, "上线")
        
        # 添加新客户端
        client.id = client_id
        client.status = "在线"
        client.missed_heartbeats = 0
        self.clients[client_id] = client
        self.window.log_message(f'客户端 {client_id} 已连接')
        
        # 通知UI添加新客户端
        self.window._handle_connect(client_id)
    
    def _handle_disconnect(self, client_id: str):
        """处理客户端断开连接消息"""
        if client_id in self.clients:
            self._remove_client(client_id, send_offline_record=True)
            self.window.log_message(f'客户端 {client_id} 已断开连接')
            # 通知UI处理断开连接
            self.window._handle_disconnect(client_id)
    
    def _handle_heartbeat(self, client_id: str):
        """处理心跳消息"""
        if client_id in self.clients:
            client = self.clients[client_id]
            client.last_heartbeat = time.time()
            client.missed_heartbeats = 0
            if client.status == "离线":
                client.status = "在线"
                self.window.add_status_record(client_id, "重新上线")
    
    def _handle_data(self, client_id: str, data: Dict):
        """处理数据消息"""
        if client_id in self.clients:
            client = self.clients[client_id]
            client.temperature = data['temperature']
            client.humidity = data['humidity']
            # 更新UI显示
            self.window.update_client_data(client_id, data['temperature'], data['humidity'])
    
    def _check_heartbeats(self):
        """检查客户端心跳"""
        current_time = time.time()
        for client_id in list(self.clients.keys()):
            client = self.clients[client_id]
            if client.status == "在线":
                # 计算距离上次心跳的时间（秒）
                time_since_last_heartbeat = current_time - client.last_heartbeat
                # 如果超过4秒（心跳间隔3秒+1秒容差）没有收到心跳，增加未响应次数
                if time_since_last_heartbeat > 4:
                    client.missed_heartbeats += 1
                    if client.missed_heartbeats > 0:
                        self.window.log_message(f'客户端 {client_id} 未响应心跳 {client.missed_heartbeats} 次')
                    if client.missed_heartbeats >= 3:  # 连续3次没有心跳就标记为离线
                        client.status = "离线"
                        self.window.add_status_record(client_id, "离线")
                        self.window.log_message(f'客户端 {client_id} 心跳超时')
    
    def _update_client_list(self):
        """更新客户端列表显示"""
        clients = []
        for client_id, client in self.clients.items():
            client_info = {
                'id': client_id,
                'status': client.status
            }
            if client.temperature is not None:
                client_info['temperature'] = client.temperature
            if client.humidity is not None:
                client_info['humidity'] = client.humidity
            clients.append(client_info)
        self.window.update_client_list(clients)
    
    def _remove_client(self, client_id: str, send_offline_record: bool = False):
        """移除客户端
        
        Args:
            client_id: 客户端ID
            send_offline_record: 是否发送离线记录
        """
        if client_id in self.clients:
            try:
                self.clients[client_id].socket.close()
            except:
                pass
            if send_offline_record:
                self.window.add_status_record(client_id, "下线")
            # 不删除客户端数据，只更新状态
            self.clients[client_id].status = "离线"
            self.window.remove_client_data(client_id)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    server = Server()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 