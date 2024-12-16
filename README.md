# Tempre - 传感器数据采集与监控系统

## 项目简介

Tempre 是一个基于 Python 的实时传感器数据采集和监控系统，提供了一个完整的客户端-服务器架构解决方案，用于收集、传输和可视化传感器数据。

## 功能特性

- 实时温湿度数据采集
- 多客户端支持
- WebSocket 实时通信
- 数据可视化仪表盘
- 客户端状态监控
- 数据历史记录

## 技术栈

- 后端: Flask, Flask-SocketIO
- 前端: HTML5, JavaScript, Chart.js
- 客户端: PyQt5
- 通信协议: WebSocket
- 语言: Python

## 系统架构

### 客户端 (client.py)
- 模拟传感器数据生成
- 实时数据传输
- 断线重连机制
- 心跳检测

### 服务器 (server.py)
- 数据接收与广播
- 客户端管理
- 数据历史记录
- 状态监控

### Web 界面 (index.html)
- 实时数据图表
- 客户端状态展示
- 数据表格
- 交互式控件

## 安装与运行

### 依赖安装

```bash
pip install -r requirements.txt
```

### 启动服务器
```bash
python server.py
```
