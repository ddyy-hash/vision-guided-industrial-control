import serial
import time
import logging

logger = logging.getLogger(__name__)

class BeltController:
    def __init__(self, port='COM5', baud_rate=115200, hardware_enabled=True):
        self.hardware_enabled = hardware_enabled
        self.ser = None
        self.connected = False

        if self.hardware_enabled:
            try:
                self.ser = serial.Serial(port, baud_rate, timeout=1)
                time.sleep(2)
                self.connected = True
                logger.info(f"已连接 Arduino ({port})")
            except Exception as e:
                logger.error(f"无法连接 Arduino ({port}): {e}")
                self.hardware_enabled = False
                self.connected = False
                self.ser = None
        else:
            logger.info("硬件控制已禁用，使用软件模式")
            self.connected = False

    def get_status(self):
        return {
            "hardware_enabled": self.hardware_enabled,
            "connected": self.connected,
            "port": "COM7" if self.hardware_enabled else "N/A"
        }

    def set_speed_mps(self, speed_mps, direction="forward"):
        max_speed_mps = 0.8
        if not 0 <= speed_mps <= max_speed_mps:
            raise ValueError(f"速度必须在 0 - {max_speed_mps} m/s 之间")

        if not self.hardware_enabled:
            logger.info(f"软件模式: 设置传送带速度为 {speed_mps:.3f} m/s, 方向: {direction}")
            return {"success": True, "response": f"软件模式: 速度 {speed_mps:.3f} m/s, 方向 {direction}"}

        try:
            cmd = f"{speed_mps:.3f} {direction}"
            logger.info(f"发送指令到 Arduino: {cmd}")
            self.ser.write((cmd + '\n').encode())

            time.sleep(0.1)
            response = self.ser.readline().decode().strip()
            logger.info(f"Arduino 响应: {response}")
            return {"success": True, "response": response}
        except Exception as e:
            logger.error(f"发送指令失败: {e}")
            return {"success": False, "response": f"发送指令失败: {e}"}

    def set_speed_percent(self, speed_percent, direction="forward"):
        if not 0 <= speed_percent <= 100:
            raise ValueError("速度必须在 0 - 100% 之间")

        speed_mps = (speed_percent / 100.0) * 0.8

        return self.set_speed_mps(speed_mps, direction)

    def close(self):
        if self.ser and self.hardware_enabled:
            try:
                self.ser.close()
                self.connected = False
                logger.info(f"已关闭串口连接")
            except Exception as e:
                logger.error(f"关闭串口连接时出错: {e}")
            finally:
                self.ser = None

    def reconnect(self, port=None, baud_rate=115200):
        if port is None:
            port = self.ser.port if self.ser else 'COM5'

        self.close()

        time.sleep(1)

        try:
            self.ser = serial.Serial(port, baud_rate, timeout=1, exclusive=False)
            time.sleep(2)
            self.connected = True
            self.hardware_enabled = True
            logger.info(f"重新连接 Arduino 成功 ({port})")
            return True
        except Exception as e:
            logger.error(f"重新连接 Arduino 失败 ({port}): {e}")
            self.hardware_enabled = False
            self.connected = False
            self.ser = None
            return False

if __name__ == "__main__":
    belt = BeltController()
    try:
        belt.set_speed_percent(50)
    finally:
        belt.close()