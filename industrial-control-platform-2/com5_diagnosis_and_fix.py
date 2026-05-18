#!/usr/bin/env python3

import serial
import serial.tools.list_ports
import time
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("com5_diagnosis")

def scan_serial_ports():
    print("=" * 50)
    print("串口扫描结果:")
    print("=" * 50)

    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("未找到任何串口设备")
        return []

    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device} - {port.description}")
        print(f"   制造商: {port.manufacturer}")
        print(f"   硬件ID: {port.hwid}")
        print(f"   产品: {port.product}")
        print()

    return ports

def test_com5_connection():
    print("=" * 50)
    print("COM5连接测试:")
    print("=" * 50)

    print("测试1: 基本连接测试...")
    try:
        ser = serial.Serial('COM5', 115200, timeout=1, exclusive=False)
        print("✓ COM5 打开成功")

        print("测试写入...")
        ser.write(b'test\n')
        time.sleep(0.1)

        print("测试读取...")
        response = ser.read_all()
        print(f"收到响应: {response}")

        ser.close()
        print("✓ COM5 关闭成功")
        return True

    except Exception as e:
        print(f"✗ COM5 连接失败: {repr(e)}")
        return False

def test_com5_with_different_params():
    print("\n" + "=" * 50)
    print("不同参数测试:")
    print("=" * 50)

    test_cases = [
        {"baudrate": 115200, "timeout": 1},
        {"baudrate": 9600, "timeout": 1},
        {"baudrate": 115200, "timeout": 2},
        {"baudrate": 9600, "timeout": 2},
    ]

    for i, params in enumerate(test_cases):
        print(f"测试用例 {i+1}: {params}")
        try:
            ser = serial.Serial(
                port='COM5',
                baudrate=params['baudrate'],
                timeout=params['timeout']
            )
            print(f"✓ 参数 {params} 连接成功")
            ser.close()
        except Exception as e:
            print(f"✗ 参数 {params} 连接失败: {repr(e)}")

def check_pyserial_version():
    print("\n" + "=" * 50)
    print("pyserial版本检查:")
    print("=" * 50)

    try:
        import serial
        version = serial.__version__
        print(f"当前pyserial版本: {version}")

        major, minor, patch = map(int, version.split('.'))
        if major > 3 or (major == 3 and minor >= 4):
            print("✓ pyserial版本支持exclusive参数")
            print("⚠ 但Windows系统不支持exclusive=False参数")
        else:
            print("⚠ pyserial版本较旧，建议升级到3.4+")

    except ImportError:
        print("✗ 未安装pyserial")
    except Exception as e:
        print(f"检查版本时出错: {e}")

def system_info():
    print("\n" + "=" * 50)
    print("系统信息:")
    print("=" * 50)

    import platform
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"系统版本: {platform.version()}")
    print(f"处理器: {platform.processor()}")
    print(f"Python版本: {platform.python_version()}")

def check_process_holding_com5():
    print("\n" + "=" * 50)
    print("进程占用检查:")
    print("=" * 50)

    if os.name == 'nt':
        try:
            import psutil
            print("使用psutil检查进程...")

            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                try:
                    if proc.info['open_files']:
                        for file in proc.info['open_files']:
                            if 'COM5' in file.path.upper():
                                print(f"⚠ 进程 {proc.info['name']} (PID: {proc.info['pid']}) 正在使用COM5")
                                return True
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue

            print("✓ 未发现进程占用COM5")
            return False

        except ImportError:
            print("未安装psutil，无法检查进程占用")
            return None
    else:
        print("非Windows系统，跳过进程检查")
        return None

def fix_com5_issues():
    print("\n" + "=" * 50)
    print("COM5问题修复:")
    print("=" * 50)

    fixes_applied = []

    print("修复1: 确保使用exclusive=False参数...")
    fixes_applied.append("使用exclusive=False参数")

    print("修复2: 检查pyserial版本...")
    try:
        import serial
        version = serial.__version__
        major, minor, patch = map(int, version.split('.'))
        if major < 3 or (major == 3 and minor < 4):
            print("建议升级pyserial: pip install -U pyserial")
            fixes_applied.append("建议升级pyserial")
    except:
        pass

    print("修复3: 建议重新插拔USB转串口设备...")
    fixes_applied.append("重新插拔USB设备")

    print("修复4: 如果问题持续，建议重启系统...")
    fixes_applied.append("系统重启建议")

    return fixes_applied

def main():
    print("COM5串口连接诊断工具")
    print("=" * 60)

    system_info()

    ports = scan_serial_ports()

    com5_exists = any(port.device.upper() == 'COM5' for port in ports)

    if not com5_exists:
        print("\n⚠ COM5未在系统中检测到")
        print("可能的解决方案:")
        print("1. 检查USB转串口设备是否连接")
        print("2. 重新插拔USB设备")
        print("3. 检查设备管理器中的驱动程序")
        return

    print("\n✓ COM5在系统中已检测到")

    process_holding = check_process_holding_com5()

    connection_ok = test_com5_connection()

    if not connection_ok:
        test_com5_with_different_params()

    check_pyserial_version()

    fixes = fix_com5_issues()

    print("\n" + "=" * 60)
    print("诊断总结:")
    print("=" * 60)

    if connection_ok:
        print("✓ COM5连接测试通过")
        print("系统应该能够正常使用COM5端口")
    else:
        print("✗ COM5连接测试失败")
        print("\n已应用的修复建议:")
        for fix in fixes:
            print(f"  • {fix}")

        if process_holding:
            print("\n⚠ 发现有进程占用COM5，请关闭相关程序后重试")

        print("\n下一步操作建议:")
        print("1. 重新插拔USB转串口设备")
        print("2. 关闭所有可能使用COM5的程序")
        print("3. 重启计算机")
        print("4. 检查设备管理器中的端口设置")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n诊断工具被用户中断")
    except Exception as e:
        print(f"\n诊断工具运行出错: {e}")
        import traceback
        traceback.print_exc()