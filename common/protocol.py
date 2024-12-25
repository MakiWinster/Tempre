import json
import time
from enum import Enum, auto

class MessageType(Enum):
    """消息类型枚举"""
    CONNECT = auto()      # 客户端连接
    DISCONNECT = auto()   # 客户端断开
    HEARTBEAT = auto()    # 心跳包
    DATA = auto()         # 数据上报

class Protocol:
    """通信协议类"""
    
    @staticmethod
    def pack(msg_type: MessageType, client_id: str, data: dict = None) -> bytes:
        """打包消息
    
        Args:
            msg_type: 消息类型
            client_id: 客户端ID
            data: 数据内容（可选）
            
        Returns:
            打包后的字节串
        """
        message = {
            "type": msg_type.name.lower(),
            "client_id": client_id,
            "timestamp": int(time.time())
        }
        
        if data:
            message["data"] = data
            
        return json.dumps(message).encode('utf-8')
    
    @staticmethod
    def unpack(data: bytes) -> dict:
        """解包消息
        
        Args:
            data: 接收到的字节串
            
        Returns:
            解析后的消息字典
        """
        return json.loads(data.decode('utf-8'))
    
    @staticmethod
    def create_connect_message(client_id: str) -> bytes:
        """创建连接消息"""
        return Protocol.pack(MessageType.CONNECT, client_id)
    
    @staticmethod
    def create_disconnect_message(client_id: str) -> bytes:
        """创建断开连接消息"""
        return Protocol.pack(MessageType.DISCONNECT, client_id)
    
    @staticmethod
    def create_heartbeat_message(client_id: str) -> bytes:
        """创建心跳消息"""
        return Protocol.pack(MessageType.HEARTBEAT, client_id)
    
    @staticmethod
    def create_data_message(client_id: str, sensor_data: dict) -> bytes:
        """创建数据上报消息"""
        return Protocol.pack(MessageType.DATA, client_id, sensor_data) 