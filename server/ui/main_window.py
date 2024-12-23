from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QTextEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QListWidget, QSplitter, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
import pyqtgraph as pg
import numpy as np
from typing import Dict, List
from datetime import datetime
import time
from PyQt5.QtGui import QIcon
import os

class MainWindow(QMainWindow):
    """服务器主窗口"""
    
    # 定义信号
    start_server_clicked = pyqtSignal(str)  # 启动服务器按钮点击信号（服务器地址）
    stop_server_clicked = pyqtSignal()     # 停止服务器按钮点击信号
    
    def __init__(self):
        super().__init__()
        
        # 设置应用图标
        icon_path = 'icons/server.png'
        if not os.path.exists('icons'):
            os.makedirs('icons')
        if not os.path.exists(icon_path):
            print(f"{icon_path} is ready to use.")
        
        self.setWindowIcon(QIcon(icon_path))
        
        # 存储每个客户端的数据历史
        self.client_data_history = {}
        
        # 最大显示点数（不是存储限制）
        self.max_display_points = 100
        
        # 固定Y轴范围
        self.temp_range = (15, 35)  # 温度范围
        self.humidity_range = (20, 90)  # 湿度范围
        
        # 设置图表样式
        pg.setConfigOptions(antialias=True)  # 启用抗锯齿
        
        # 初始化分页变量
        self.current_page = 0
        
        # 添加视图控制标志
        self.auto_range = True  # 初始时启用自动范围
        
        # 初始化UI
        self.init_ui()
        
        # 使用单个定时器更新所有数据
        self.update_timer = QTimer(self)
        self.update_timer.moveToThread(self.thread())
        self.update_timer.timeout.connect(self._update_all)
        self.update_timer.start(100)
        
        # 缓存需要更新的数据
        self.pending_updates = set()

    def _update_all(self):
        """统一更新所有数据"""
        try:
            # 更新图表
            if self.pending_updates and self.view_combo.currentText() == '图表视图':
                self._update_plots()
            
            # 更新表格（如果在表格视图且有新数据）
            if self.view_combo.currentText() == '数据表格' and self.pending_updates:
                self._update_data_table()
        except Exception as e:
            print(f"Error in update_all: {e}")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            # 停止定时器
            self.update_timer.stop()
            # 如果服务器正在运行，发送停止信号
            if self.start_btn.text() == '停止服务器':
                self.stop_server_clicked.emit()
            event.accept()
        except Exception as e:
            print(f"Error in closeEvent: {e}")

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('传感器数据采集服务器')
        self.setMinimumSize(1000, 600)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        
        # 创建服务器控制部分
        control_layout = QHBoxLayout()
        self.server_input = QLineEdit('localhost:5000')
        self.server_input.setPlaceholderText('服务器地址:端口')
        control_layout.addWidget(QLabel('服务器:'))
        control_layout.addWidget(self.server_input)
        
        self.start_btn = QPushButton('启动服务器')
        self.start_btn.clicked.connect(self._on_start_clicked)
        control_layout.addWidget(self.start_btn)
        
        layout.addLayout(control_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 创建左侧面板（客户端状态记录）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 创建客户端列表表格
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(4)
        self.client_table.setHorizontalHeaderLabels(['客户端ID', '状态', '温度', '湿度'])
        header = self.client_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        # 添加表格点击事件
        self.client_table.itemClicked.connect(self._on_table_clicked)
        left_layout.addWidget(self.client_table)
        
        # 创建上下线记录列表
        left_layout.addWidget(QLabel('客户端上下线记录'))
        self.status_list = QListWidget()
        left_layout.addWidget(self.status_list)
        
        splitter.addWidget(left_panel)
        
        # 创建右侧面板（图表和数据表）
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建客户端选择和视图切换部分
        control_layout = QHBoxLayout()
        
        # 客户端选择
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel('显示客户端:'))
        self.client_combo = QComboBox()
        self.client_combo.addItem('全部')
        self.client_combo.currentTextChanged.connect(self._on_client_selected)
        select_layout.addWidget(self.client_combo)
        control_layout.addLayout(select_layout)
        
        # 视图切换按钮
        self.view_combo = QComboBox()
        self.view_combo.addItems(['图表视图', '数据表格'])
        self.view_combo.currentTextChanged.connect(self._on_view_changed)
        control_layout.addWidget(self.view_combo)
        
        right_layout.addLayout(control_layout)
        
        # 创建堆叠布局用于切换视图
        self.stack_layout = QVBoxLayout()
        
        # 图表视图
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        
        # 温度图表
        self.temp_plot = pg.PlotWidget()
        self.temp_plot.setTitle('温度历史')
        self.temp_plot.setLabel('left', '温度 (°C)')
        self.temp_plot.setLabel('bottom', '时间点')
        self.temp_plot.showGrid(x=True, y=True)
        self.temp_plot.setBackground('k')
        self.temp_plot.getAxis('left').setTextPen('w')
        self.temp_plot.getAxis('bottom').setTextPen('w')
        self.temp_plot.setMouseEnabled(x=True, y=True)
        # 添加视图范围变化事件处理
        self.temp_plot.sigRangeChanged.connect(self._on_view_range_changed)
        plot_layout.addWidget(self.temp_plot)
        
        # 湿度图表
        self.humidity_plot = pg.PlotWidget()
        self.humidity_plot.setTitle('湿度历史')
        self.humidity_plot.setLabel('left', '湿度 (%)')
        self.humidity_plot.setLabel('bottom', '时间点')
        self.humidity_plot.showGrid(x=True, y=True)
        self.humidity_plot.setBackground('k')
        self.humidity_plot.getAxis('left').setTextPen('w')
        self.humidity_plot.getAxis('bottom').setTextPen('w')
        self.humidity_plot.setMouseEnabled(x=True, y=True)
        # 添加视图范围变化事件处理
        self.humidity_plot.sigRangeChanged.connect(self._on_view_range_changed)
        plot_layout.addWidget(self.humidity_plot)
        
        # 数据表格视图
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(['时间', '客户端ID', '温度', '湿度'])
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # 分页控制
        self.page_control = QWidget()
        page_layout = QHBoxLayout(self.page_control)
        self.prev_btn = QPushButton('上一页')
        self.next_btn = QPushButton('下一页')
        self.page_label = QLabel('第 1 页')
        self.prev_btn.clicked.connect(self._on_prev_page)
        self.next_btn.clicked.connect(self._on_next_page)
        page_layout.addWidget(self.prev_btn)
        page_layout.addWidget(self.page_label)
        page_layout.addWidget(self.next_btn)
        
        # 将表格和分页控制添加到一个容器中
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.addWidget(self.data_table)
        table_layout.addWidget(self.page_control)
        
        # 初始显示图表视图
        self.stack_layout.addWidget(plot_widget)
        self.stack_layout.addWidget(table_widget)
        plot_widget.show()
        table_widget.hide()
        
        right_layout.addLayout(self.stack_layout)
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
        
        # 创建日志显示部分
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)  # 设置最小高度
        self.log_text.setStyleSheet("font-size: 12pt;")  # 增大字体
        layout.addWidget(self.log_text)
    
    def _on_start_clicked(self):
        """启动/停止服务器按钮点击处理"""
        if self.start_btn.text() == '启动服务器':
            server = self.server_input.text().strip()
            if server:
                self.start_server_clicked.emit(server)
        else:
            self.stop_server_clicked.emit()
    
    def set_server_state(self, running: bool):
        """设置服务器状态"""
        try:
            self.server_input.setEnabled(not running)
            self.start_btn.setText('停止服务器' if running else '启动服务器')
            # 停止服务器时保持所有数据和显示状态不变
            if not running:
                # 保持所有曲线可见
                for client_id, history in self.client_data_history.items():
                    if self.client_combo.currentText() == '全部' or self.client_combo.currentText() == client_id:
                        history['temp_curve'].show()
                        history['humidity_curve'].show()
        except Exception as e:
            print(f"Error setting server state: {e}")
    
    def update_client_list(self, clients: List[Dict]):
        """更新客户端列表
        
        Args:
            clients: 客户端列表，每个客户端是一个字典，包含id、status、temperature、humidity字段
        """
        self.client_table.setRowCount(len(clients))
        for i, client in enumerate(clients):
            self.client_table.setItem(i, 0, QTableWidgetItem(client['id']))
            self.client_table.setItem(i, 1, QTableWidgetItem(client['status']))
            if 'temperature' in client:
                self.client_table.setItem(i, 2, QTableWidgetItem(f"{client['temperature']:.1f}°C"))
            if 'humidity' in client:
                self.client_table.setItem(i, 3, QTableWidgetItem(f"{client['humidity']:.1f}%"))
    
    def add_status_record(self, client_id: str, status: str):
        """添加客户端状态记录
        
        Args:
            client_id: 客户端ID
            status: 状态（上线/下线）
        """
        time_str = datetime.now().strftime('%H:%M:%S')
        self.status_list.insertItem(0, f'[{time_str}] 客户端 {client_id} {status}')
        # 限制记录数量
        if self.status_list.count() > 100:
            self.status_list.takeItem(self.status_list.count() - 1)
    
    def update_client_data(self, client_id: str, temperature: float, humidity: float):
        """更新客户端数据"""
        try:
            if client_id not in self.client_data_history:
                self.client_data_history[client_id] = {
                    'temp': [],
                    'humidity': [],
                    'timestamps': [],
                    'temp_curve': self.temp_plot.plot(
                        pen=pg.mkPen(color='w', width=2)
                    ),
                    'humidity_curve': self.humidity_plot.plot(
                        pen=pg.mkPen(color='w', width=2)
                    ),
                    'display_start': 0  # 显示起始索引
                }
            
            history = self.client_data_history[client_id]
            
            # 添加新数据和时间戳
            history['temp'].append(temperature)
            history['humidity'].append(humidity)
            history['timestamps'].append(time.time())
            
            # 更新显示范围（保留所有数据，只调整显示窗口）
            total_points = len(history['temp'])
            if total_points > self.max_display_points:
                history['display_start'] = total_points - self.max_display_points
            
            # 标记需要更新
            self.pending_updates.add(client_id)
        except Exception as e:
            print(f"Error updating client data: {e}")
    
    def remove_client_data(self, client_id: str):
        """移除客户端数据"""
        # 客户端下线时不删除数据，只隐藏曲线
        if client_id in self.client_data_history:
            history = self.client_data_history[client_id]
            if self.client_combo.currentText() != '全部' and self.client_combo.currentText() != client_id:
                history['temp_curve'].hide()
                history['humidity_curve'].hide()
            # 保持数据不变，以便后续查看
    
    def log_message(self, message: str):
        """添加日志消息
        
        Args:
            message: 日志消息
        """
        self.log_text.append(message) 
    
    def _on_client_selected(self, client_id: str):
        """客户端选择变化处理"""
        try:
            # 切换客户端时重新启用自动范围
            self.auto_range = True
            
            # 显示/隐藏相应的曲线
            for cid, history in self.client_data_history.items():
                if client_id == '全部' or client_id == cid:
                    history['temp_curve'].show()
                    history['humidity_curve'].show()
                else:
                    history['temp_curve'].hide()
                    history['humidity_curve'].hide()
        except Exception as e:
            print(f"Error in client selection: {e}")
    
    def _handle_connect(self, client_id: str):
        """处理客户端连接
        
        Args:
            client_id: 客户端ID
        """
        # 如果是新客户端，添加到下拉列表
        if self.client_combo.findText(client_id) == -1:
            self.client_combo.addItem(client_id)
    
    def _handle_disconnect(self, client_id: str):
        """处理客户端断开连接
        
        Args:
            client_id: 客户端ID
        """
        # 不从下拉列表中移除，保留历史数据
        pass
    
    def _on_table_clicked(self, item):
        """处理表格点击事件"""
        if item.column() == 0:  # 只处理客户端ID列的点击
            client_id = item.text()
            self.client_combo.setCurrentText(client_id)
    
    def _on_view_changed(self, view_type: str):
        """处理视图切换"""
        try:
            widgets = []
            for i in range(self.stack_layout.count()):
                widget = self.stack_layout.itemAt(i).widget()
                if widget:
                    widgets.append(widget)
            
            if view_type == '图表视图':
                widgets[0].show()
                widgets[1].hide()
            else:
                widgets[0].hide()
                widgets[1].show()
                self._update_data_table()  # 立即更新一次
        except Exception as e:
            print(f"Error in view change: {e}")
    
    def _update_data_table(self):
        """更新数据表格"""
        try:
            selected_client = self.client_combo.currentText()
            
            # 收集所有数据
            all_data = []
            for client_id, history in self.client_data_history.items():
                if selected_client == '全部' or selected_client == client_id:
                    for i in range(len(history['temp'])):
                        all_data.append({
                            'time': time.strftime('%H:%M:%S', time.localtime(history['timestamps'][i])),
                            'client_id': client_id,
                            'temp': history['temp'][i],
                            'humidity': history['humidity'][i]
                        })
            
            # 按时间戳降序排序
            all_data.sort(key=lambda x: x['time'], reverse=True)
            
            # 计算分页
            self.rows_per_page = max(1, (self.data_table.height() - 50) // 30)
            self.total_rows = len(all_data)
            self.total_pages = max(1, (self.total_rows + self.rows_per_page - 1) // self.rows_per_page)
            
            # 确保当前页码有效
            if not hasattr(self, 'current_page'):
                self.current_page = 0
            if self.current_page >= self.total_pages:
                self.current_page = max(0, self.total_pages - 1)
            
            self._show_current_page(all_data)
        except Exception as e:
            print(f"Error updating data table: {e}")
    
    def _show_current_page(self, all_data: List[Dict]):
        """显示当前页的数据"""
        try:
            start = self.current_page * self.rows_per_page
            end = min(start + self.rows_per_page, self.total_rows)
            page_data = all_data[start:end]
            
            # 设置表格行数
            self.data_table.setRowCount(len(page_data))
            
            # 设置表格数据
            for i, data in enumerate(page_data):
                # 设置单元格文本对齐方式为居中
                for j, text in enumerate([
                    data['time'],
                    data['client_id'],
                    f"{data['temp']:.1f}°C",
                    f"{data['humidity']:.1f}%"
                ]):
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)  # 居中对齐
                    self.data_table.setItem(i, j, item)
            
            # 更新页码显示
            if self.total_rows == 0:
                self.page_label.setText('无数据')
            else:
                self.page_label.setText(f'第 {self.current_page + 1} 页 / 共 {self.total_pages} 页 (共 {self.total_rows} 条记录)')
            
            # 更新按钮状态
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < self.total_pages - 1)
            
            # 调整表格外观
            self.data_table.resizeColumnsToContents()  # 自动调整列宽
            self.data_table.setAlternatingRowColors(True)  # 交替行颜色
            self.data_table.setStyleSheet("""
                QTableWidget {
                    gridline-color: #d0d0d0;
                    background-color: white;
                    alternate-background-color: #f7f7f7;
                }
                QTableWidget::item {
                    padding: 5px;
                }
            """)
        except Exception as e:
            print(f"Error showing current page: {e}")
    
    def _on_prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_data_table()
    
    def _on_next_page(self):
        """下一页"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_data_table()

    def _update_plots(self):
        """更新所有需要更新的图表"""
        try:
            if not self.pending_updates:
                return
            
            # 更新曲线数据
            for client_id in self.pending_updates:
                if client_id in self.client_data_history:
                    history = self.client_data_history[client_id]
                    if history['temp_curve'].isVisible():
                        total_points = len(history['temp'])
                        if total_points > 0:
                            # 创建X轴数据
                            x = np.arange(total_points)
                            
                            # 更新曲线数据
                            history['temp_curve'].setData(
                                x, 
                                history['temp']
                            )
                            history['humidity_curve'].setData(
                                x, 
                                history['humidity']
                            )
                            
                            # 只在自动范围模式下调整视图
                            if self.auto_range and total_points > self.max_display_points:
                                display_start = total_points - self.max_display_points
                                self.temp_plot.setXRange(display_start, total_points)
                                self.humidity_plot.setXRange(display_start, total_points)
            
            self.pending_updates.clear()
        except Exception as e:
            print(f"Error updating plots: {e}")

    def _on_view_range_changed(self):
        """处理视图范围变化"""
        # 用户手动调整视图范围时，禁用自动范围
        self.auto_range = False