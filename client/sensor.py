import random
import time
from typing import Dict, Tuple

class SensorSimulator:
    """传感器模拟器类"""
    
    def __init__(self, temp_range: Tuple[float, float] = (15.0, 30.0),
                 humidity_range: Tuple[float, float] = (30.0, 80.0)):
        """初始化传感器模拟器
        
        Args:
            temp_range: 温度范围（最小值，最大值）
            humidity_range: 湿度范围（最小值，最大值）
        """
        self.temp_range = temp_range
        self.humidity_range = humidity_range
        self._last_temp = (temp_range[0] + temp_range[1]) / 2
        self._last_humidity = (humidity_range[0] + humidity_range[1]) / 2
        
    def get_sensor_data(self) -> Dict[str, float]:
        # 生成新的温度值，与上一次的值相差不超过0.5度
        new_temp = self._last_temp + random.uniform(-0.5, 0.5)
        # 温度在指定范围内
        new_temp = max(self.temp_range[0], min(self.temp_range[1], new_temp))
        self._last_temp = new_temp
        
        # 生成新的湿度值，与上一次的值相差不超过2%
        new_humidity = self._last_humidity + random.uniform(-2, 2)
        # 确保湿度在指定范围内
        new_humidity = max(self.humidity_range[0], min(self.humidity_range[1], new_humidity))
        self._last_humidity = new_humidity
        
        return {
            "temperature": round(new_temp, 1),
            "humidity": round(new_humidity, 1)
        }

if __name__ == "__main__":
    # 测试代码
    simulator = SensorSimulator()
    for _ in range(5):
        print(simulator.get_sensor_data())
        time.sleep(1) 