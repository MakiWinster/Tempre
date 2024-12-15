import sys
import socketio
import time
import random
import warnings
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QGridLayout, QTextEdit)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPalette, QColor

# 过滤掉 PyQt5 的废弃警告
warnings.filterwarnings("ignore", category=DeprecationWarning)

class SensorThread(QThread):
    data_generated = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, server_url='http://localhost:5000'):
        super().__init__()
        self.server_url = server_url
        self.running = False
        self.connected = False
        self.client_id = None
        self.sending_data = True
        self.heartbeat_timer = None
        
        # 创建 Socket.IO 客户端
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=True,
            engineio_logger=True
        )

        # 设置事件处理器
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('connect_error', self.on_connect_error)
        self.sio.on('client_id_assigned', self.on_client_id_assigned)

    def send_heartbeat(self):
        try:
            if self.connected and self.client_id:
                self.sio.emit('heartbeat', {'client_id': self.client_id})
                self.log_message.emit("发送心跳信号")
        except Exception as e:
            self.log_message.emit(f"心跳发送失败: {e}")

    def start_heartbeat(self):
        if not self.heartbeat_timer:
            self.heartbeat_timer = QTimer()
            self.heartbeat_timer.timeout.connect(self.send_heartbeat)
            self.heartbeat_timer.start(3000)

    def stop_heartbeat(self):
        if self.heartbeat_timer:
            self.heartbeat_timer.stop()
            self.heartbeat_timer = None

    def toggle_data_sending(self):
        self.sending_data = not self.sending_data
        status = "开启" if self.sending_data else "停止"
        self.log_message.emit(f"数据发送已{status}")

    def run(self):
        self.running = True
        if self.connect_to_server():  # 尝试连接
            while self.running:  # 连接成功后的主循环
                if self.connected and self.sending_data:
                    try:
                        sensor_data = self.generate_sensor_data()
                        self.sio.emit('sensor_data', sensor_data)
                        self.data_generated.emit(sensor_data)
                        self.log_message.emit(f"发送数据 - 温度: {sensor_data['temperature']}°C, 湿度: {sensor_data['humidity']}%")
                    except Exception as e:
                        self.log_message.emit(f"发送数据失败: {e}")
                        self.connected = False
                        self.connection_changed.emit(False)
                time.sleep(2)
        else:
            self.log_message.emit("连接服务器失败")
            self.running = False

    def on_connect(self):
        self.log_message.emit("Socket.IO已连接，请求客户端ID...")
        self.sio.emit('client_connect', {})

    def on_disconnect(self):
        self.connected = False
        self.connection_changed.emit(False)
        self.stop_heartbeat()
        self.log_message.emit("已断开连接")

    def on_client_id_assigned(self, data):
        self.client_id = data['client_id']
        self.connected = True
        self.connection_changed.emit(True)
        self.start_heartbeat()
        self.log_message.emit(f"已分配客户端ID: {self.client_id}")

    def connect_to_server(self):
        try:
            self.log_message.emit("正在连接服务器...")
            self.sio.connect(
                self.server_url,
                wait_timeout=10,
                transports=['websocket', 'polling'],
                socketio_path='socket.io'
            )
            return True
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def generate_sensor_data(self):
        return {
            "temperature": round(random.uniform(20, 30), 2),
            "humidity": round(random.uniform(40, 70), 2),
            "client_id": self.client_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def stop(self):
        self.running = False
        if self.connected:
            try:
                self.sio.emit('client_disconnect', {'client_id': self.client_id})
                self.stop_heartbeat()
                self.sio.disconnect()
            except:
                pass
        self.connected = False
        self.connection_changed.emit(False)

    def on_connect_error(self, error):
        self.log_message.emit(f"连接错误: {error}")
        self.error_occurred.emit(str(error))
        self.connected = False
        self.connection_changed.emit(False)
        self.stop_heartbeat()

class SensorDisplay(QWidget):
    def __init__(self, title, unit):
        super().__init__()
        self.value = 0
        layout = QVBoxLayout()
        
        # 标题标签
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        
        # 值标签
        self.value_label = QLabel(f"0 {unit}")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        self.value_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                color: #ecf0f1;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self.setLayout(layout)

    def update_value(self, value):
        self.value = value
        self.value_label.setText(f"{value}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("传感器数据采集客户端")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2574a9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QLabel {
                font-size: 14px;
            }
        """)

        # 创建主窗口部件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 状态显示
        self.status_label = QLabel("未连接")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-weight: bold;
                padding: 5px;
                border-radius: 5px;
                background-color: #fadbd8;
            }
        """)

        # 传感器显示区域
        sensors_layout = QHBoxLayout()
        self.temp_display = SensorDisplay("温度", "°C")
        self.humid_display = SensorDisplay("湿度", "%")
        sensors_layout.addWidget(self.temp_display)
        sensors_layout.addWidget(self.humid_display)

        # 控制按钮
        self.connect_button = QPushButton("连接服务器")
        self.connect_button.clicked.connect(self.toggle_connection)

        # 添加数据发送控制按钮
        self.send_data_button = QPushButton("停止发送数据")
        self.send_data_button.clicked.connect(self.toggle_data_sending)
        self.send_data_button.setEnabled(False)

        # 添加日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border-radius: 5px;
                padding: 10px;
                font-family: monospace;
            }
        """)

        # 添加所有组件到主布局
        layout.addWidget(self.status_label)
        layout.addLayout(sensors_layout)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.send_data_button)
        layout.addWidget(self.log_text)

        # 设置窗口大小和位置
        self.setMinimumSize(400, 300)

        # 创建传感器线程
        self.sensor_thread = SensorThread()
        self.sensor_thread.data_generated.connect(self.update_sensor_data)
        self.sensor_thread.connection_changed.connect(self.update_connection_status)
        self.sensor_thread.error_occurred.connect(self.show_error)
        self.sensor_thread.log_message.connect(self.append_log)

        self.connected = False

    def toggle_connection(self):
        if not self.connected:
            self.connect_button.setEnabled(False)
            self.sensor_thread.start()
        else:
            self.sensor_thread.stop()
            self.connect_button.setText("连接服务器")
            self.status_label.setText("未连接")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 5px;
                    background-color: #fadbd8;
                }
            """)
            self.connected = False

    def update_sensor_data(self, data):
        self.temp_display.update_value(f"{data['temperature']}°C")
        self.humid_display.update_value(f"{data['humidity']}%")

    def update_connection_status(self, connected):
        self.connected = connected
        self.connect_button.setEnabled(True)
        self.send_data_button.setEnabled(connected)
        if connected:
            self.connect_button.setText("断开连接")
            self.status_label.setText("已连接")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #27ae60;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 5px;
                    background-color: #d5f5e3;
                }
            """)
        else:
            self.connect_button.setText("连接服务器")
            self.status_label.setText("未连接")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 5px;
                    background-color: #fadbd8;
                }
            """)

    def show_error(self, error_msg):
        self.status_label.setText(f"错误: {error_msg}")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-weight: bold;
                padding: 5px;
                border-radius: 5px;
                background-color: #fadbd8;
            }
        """)

    def closeEvent(self, event):
        self.sensor_thread.stop()
        event.accept()

    def toggle_data_sending(self):
        self.sensor_thread.toggle_data_sending()
        is_sending = self.sensor_thread.sending_data
        self.send_data_button.setText("停止发送数据" if is_sending else "开始发送数据")

    def append_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 