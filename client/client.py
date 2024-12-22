import sys
import socket
import time
import json
from threading import Thread, Event
from typing import Tuple
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from .ui.main_window import MainWindow
from .sensor import SensorSimulator
from common.protocol import Protocol, MessageType

class Client:
    """传感器数据采集客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.window = MainWindow()
        self.sensor = SensorSimulator()
        self.socket = None
        self.client_id = None
        self.is_paused = False
        
        # 创建心跳定时器
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._send_heartbeat)
        
        # 创建数据上报定时器
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self._send_sensor_data)
        
        # 创建接收线程停止事件
        self.stop_event = Event()
        self.receive_thread = None
        
        # 连接信号
        self.window.connect_clicked.connect(self.connect_to_server)
        self.window.disconnect_clicked.connect(self.disconnect_from_server)
        self.window.pause_clicked.connect(self.set_pause_state)
        
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
    
    def connect_to_server(self, server: str, client_id: str):
        """连接到服务器"""
        try:
            host, port = self._parse_server_address(server)
            
            # 创建socket连接
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            
            # 发送连接消息
            self.socket.send(Protocol.create_connect_message(client_id))
            
            # 等待服务器响应
            response = json.loads(self.socket.recv(1024).decode('utf-8'))
            if not response.get('success', False):
                self.window.log_message(f'连接失败：{response.get("message", "未知错误")}')
                self.socket.close()
                self.socket = None
                return
            
            self.client_id = client_id
            
            # 更新UI状态
            self.window.set_connected_state(True)
            self.window.log_message(f'已连接到服务器 {server}')
            
            # 启动定时器（在主线程中）
            self.heartbeat_timer.start(3000)  # 3秒发送一次心跳
            self.data_timer.start(1000)  # 1秒上报一次数据
            
            # 启动接收线程
            self.stop_event.clear()
            self.receive_thread = Thread(target=self._receive_messages)
            self.receive_thread.start()
            
        except Exception as e:
            self.window.log_message(f'连接失败：{str(e)}')
            self.disconnect_from_server()
    
    def disconnect_from_server(self):
        """断开与服务器的连接"""
        # 先停止定时器，避免在断开过程中继续发送数据
        self.heartbeat_timer.stop()
        self.data_timer.stop()
        
        # 发送断开连接消息
        if self.socket and self.client_id:
            try:
                self.socket.send(Protocol.create_disconnect_message(self.client_id))
                # 等待一小段时间确保消息发送完成
                time.sleep(0.1)
            except:
                pass
        
        # 停止接收线程
        if self.receive_thread and self.receive_thread.is_alive():
            self.stop_event.set()
            # 关闭socket以解除recv阻塞
            if self.socket:
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                    self.socket.close()
                except:
                    pass
            # 等待接收线程结束
            self.receive_thread.join(timeout=1.0)
        
        # 确保socket已关闭
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # 更新UI状态
        self.window.set_connected_state(False)
        self.window.log_message('已断开连接')
    
    def set_pause_state(self, paused: bool):
        """设置暂停状态
        
        Args:
            paused: 是否暂停
        """
        self.is_paused = paused
        if paused:
            self.window.log_message('已暂停数据发送')
        else:
            self.window.log_message('已恢复数据发送')
    
    def _send_heartbeat(self):
        """发送心跳包"""
        if self.socket and self.client_id and not self.is_paused:
            try:
                self.socket.send(Protocol.create_heartbeat_message(self.client_id))
                # 不记录心跳包发送日志，避免日志过多
            except Exception as e:
                self.window.log_message('发送心跳包失败')
                self.disconnect_from_server()
    
    def _send_sensor_data(self):
        """发送传感器数据"""
        if self.socket and self.client_id and not self.is_paused:
            try:
                # 获取传感器数据
                data = self.sensor.get_sensor_data()
                # 更新UI显示
                self.window.update_sensor_data(data['temperature'], data['humidity'])
                # 发送数据
                self.socket.send(Protocol.create_data_message(self.client_id, data))
                # 记录发送数据
                self.window.log_message(f'已发送数据：温度 {data["temperature"]:.1f}°C，湿度 {data["humidity"]:.1f}%')
            except:
                self.window.log_message('发送数据失败')
                self.disconnect_from_server()
    
    def _receive_messages(self):
        """接收服务器消息的线程函数"""
        while not self.stop_event.is_set():
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                
                # 解析消息
                message = Protocol.unpack(data)
                self.window.log_message(f'收到服务器消息：{message}')
                
            except Exception as e:
                if not self.stop_event.is_set():
                    self.window.log_message(f'接收消息错误：{str(e)}')
                    self.disconnect_from_server()
                break

def main():
    """主函数"""
    app = QApplication(sys.argv)
    client = Client()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 