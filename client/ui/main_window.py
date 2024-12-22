from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

class MainWindow(QMainWindow):
    """客户端主窗口"""
    
    # 定义信号
    connect_clicked = pyqtSignal(str, str)  # 连接按钮点击信号（服务器地址，客户端ID）
    disconnect_clicked = pyqtSignal()      # 断开连接按钮点击信号
    pause_clicked = pyqtSignal(bool)      # 暂停按钮点击信号（是否暂停）
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.is_paused = False
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('传感器数据采集客户端')
        self.setMinimumSize(500, 400)
        self.setWindowIcon(QIcon('icons/client.png'))  # 设置窗口图标
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        
        # 创建连接部分
        conn_layout = QHBoxLayout()
        self.server_input = QLineEdit('localhost:5000')
        self.server_input.setPlaceholderText('服务器地址:端口')
        conn_layout.addWidget(QLabel('服务器:'))
        conn_layout.addWidget(self.server_input)
        
        self.client_id_input = QLineEdit('client_001')
        self.client_id_input.setPlaceholderText('客户端ID')
        conn_layout.addWidget(QLabel('客户端ID:'))
        conn_layout.addWidget(self.client_id_input)
        
        self.connect_btn = QPushButton('连接')
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        conn_layout.addWidget(self.connect_btn)
        
        self.pause_btn = QPushButton('暂停')
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        conn_layout.addWidget(self.pause_btn)
        
        layout.addLayout(conn_layout)
        
        # 创建数据显示部分
        data_layout = QHBoxLayout()
        
        # 温度显示
        self.temp_label = QLabel('温度: --°C')
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.temp_label.setStyleSheet('font-size: 18px; padding: 10px;')
        data_layout.addWidget(self.temp_label)
        
        # 湿度显示
        self.humidity_label = QLabel('湿度: --%')
        self.humidity_label.setAlignment(Qt.AlignCenter)
        self.humidity_label.setStyleSheet('font-size: 18px; padding: 10px;')
        data_layout.addWidget(self.humidity_label)
        
        layout.addLayout(data_layout)
        
        # 创建日志显示部分
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
    def _on_connect_clicked(self):
        """连接按钮点击处理"""
        if self.connect_btn.text() == '连接':
            server = self.server_input.text().strip()
            client_id = self.client_id_input.text().strip()
            if server and client_id:
                self.connect_clicked.emit(server, client_id)
        else:
            self.disconnect_clicked.emit()
    
    def _on_pause_clicked(self):
        """暂停按钮点击处理"""
        self.is_paused = not self.is_paused
        self.pause_btn.setText('继续' if self.is_paused else '暂停')
        self.pause_clicked.emit(self.is_paused)
    
    def set_connected_state(self, connected: bool):
        """设置连接状态
        
        Args:
            connected: 是否已连接
        """
        self.server_input.setEnabled(not connected)
        self.client_id_input.setEnabled(not connected)
        self.connect_btn.setText('断开' if connected else '连接')
        self.pause_btn.setEnabled(connected)
        if not connected:
            self.pause_btn.setText('暂停')
            self.is_paused = False
    
    def update_sensor_data(self, temperature: float, humidity: float):
        """更新传感器数据显示
        
        Args:
            temperature: 温度值
            humidity: 湿度值
        """
        self.temp_label.setText(f'温度: {temperature:.1f}°C')
        self.humidity_label.setText(f'湿度: {humidity:.1f}%')
    
    def log_message(self, message: str):
        """添加日志消息
        
        Args:
            message: 日志消息
        """
        self.log_text.append(message) 