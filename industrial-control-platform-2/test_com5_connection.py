import serial
import time
import serial.tools.list_ports

def test_com5_connection():
    print('扫描可用端口:', [p.device for p in serial.tools.list_ports.comports()])

    try:
        ser = serial.Serial('COM5', 115200, timeout=1)
        print('COM5 打开成功，写入测试...')
        ser.write(b'hello\n')
        time.sleep(0.1)
        print('收到:', ser.read_all())
        ser.close()
        print('COM5 关闭成功')
        return True
    except Exception as e:
        print('失败:', repr(e))
        return False

if __name__ == "__main__":
    test_com5_connection()