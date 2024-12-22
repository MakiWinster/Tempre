# 传感器数据采集系统

基于PyQt5的传感器数据采集系统，实现了客户端数据采集和服务器端数据展示功能。

## 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **开发语言** | Python | 3.8+ | 主要开发语言 |
| **GUI框架** | PyQt5 | 5.15.9 | 图形界面开发 |
| **数据可视化** | PyQtGraph | 0.13.3 | 实时数据图表展示 |
| **网络通信** | Socket | - | TCP/IP通信 |
| | JSON | - | 数据序列化 |
| **并发处理** | threading | - | 线程管理 |
| | Queue | - | 线程间通信 |
| **系统组件** | logging | - | 日志管理 |
| | time | - | 时间处理 |
| | random | - | 数据模拟 |

## 功能特点

1. 数据采集客户端
   - 模拟温度、湿度传感器数据生成
   - 数据实时上报到服务器
   - 支持心跳检测
   - 上线/下线处理

2. 数据采集服务器
   - 支持多客户端连接
   - 实时数据展示
   - 客户端状态监控
   - 数据可视化展示

## 系统架构

1. 通信协议
   - 基于TCP/IP的Socket通信
   - JSON格式的消息协议
   - 支持心跳、数据上报、客户端上下线等消息类型

2. 客户端组件
   - 传感器模拟器：生成模拟的温度、湿度数据
   - 通信模块：负责与服务器的数据交换
   - 用户界面：显示当前数据和连接状态

3. 服务器组件
   - 多客户端管理：支持多个客户端同时连接
   - 数据处理：接收和处理客户端数据
   - 可视化界面：实时显示所有客户端数据和状态

## 安装步骤

1. 确保已安装Python 3.8或更高版本
2. 安装依赖包：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 启动服务器：
```bash
python start_server.py
```
- 在服务器界面输入监听地址（如：localhost:5000）
- 点击"启动服务器"按钮

2. 启动客户端：
```bash
python start_client.py
```
- 在客户端界面输入服务器地址和客户端ID
- 点击"连接"按钮

## 项目结构

```
.
├── README.md                 # 项目说明文件
├── requirements.txt          # 项目依赖
├── start_server.py          # 服务器启动脚本
├── start_client.py          # 客户端启动脚本
├── client/                  # 客户端代码
│   ├── __init__.py
│   ├── client.py           # 客户端主程序
│   ├── sensor.py           # 传感器数据模拟
│   └── ui/                 # 客户端UI
│       ├── __init__.py
│       └── main_window.py
├── server/                  # 服务器端代码
│   ├── __init__.py
│   ├── server.py           # 服务器主程序
│   └── ui/                 # 服务器UI
│       ├── __init__.py
│       └── main_window.py
└── common/                 # 公共模块
    ├── __init__.py
    └── protocol.py        # 通信协议定义
```

## 通信协议说明

1. 连接消息
```json
{
    "type": "connect",
    "client_id": "client_001",
    "timestamp": 1640001234
}
```

2. 断开连接消息
```json
{
    "type": "disconnect",
    "client_id": "client_001",
    "timestamp": 1640001234
}
```

3. 心跳消息
```json
{
    "type": "heartbeat",
    "client_id": "client_001",
    "timestamp": 1640001234
}
```

4. 数据上报消���
```json
{
    "type": "data",
    "client_id": "client_001",
    "timestamp": 1640001234,
    "data": {
        "temperature": 25.6,
        "humidity": 65.3
    }
}
```

## 注意事项

1. 确保服务器和客户端的Python环境中已安装所有依赖包
2. 服务器需要先于客户端启动
3. 客户端ID在同一时间内必须唯一
4. 如果客户端在9秒内未发送心跳，服务器将自动断开连接
5. 数据上报频率为1秒一次，心跳包发送频率为5秒一次

## 开发环境

- Python 3.8+
- PyQt5 5.15.9
- PyQtGraph 0.13.3
- Windows/Linux/macOS 