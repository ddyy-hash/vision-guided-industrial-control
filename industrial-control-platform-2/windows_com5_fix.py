#!/usr/bin/env python3

import serial
import serial.tools.list_ports
import time
import logging
import subprocess
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("windows_com5_fix")

def check_com5_exists():
    ports = list(serial.tools.list_ports.comports())
    com5_exists = any(port.device.upper() == 'COM5' for port in ports)

    if com5_exists:
        print("✓ COM5在系统中已检测到")
        for port in ports:
            if port.device.upper() == 'COM5':
                print(f"  - 设备: {port.device}")
                print(f"  - 描述: {port.description}")
                print(f"  - 制造商: {port.manufacturer}")
                print(f"  - 硬件ID: {port.hwid}")
        return True
    else:
        print("✗ COM5未在系统中检测到")
        return False

def test_com5_connection():
    print("\n测试COM5连接状态...")

    try:
        ser = serial.Serial('COM5', 115200, timeout=1)
        print("✓ COM5 打开成功")

        print("测试通信...")
        ser.write(b'test\n')
        time.sleep(0.1)
        response = ser.read_all()
        print(f"收到响应: {response}")

        ser.close()
        print("✓ COM5 关闭成功")
        return True

    except Exception as e:
        print(f"✗ COM5 连接失败: {repr(e)}")
        return False

def check_process_using_com5():
    print("\n检查进程占用情况...")

    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            check=True
        )

        com5_in_use = False
        for line in result.stdout.split('\n'):
            if 'COM5' in line.upper():
                com5_in_use = True
                print(f"⚠ COM5被占用: {line.strip()}")

                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    print(f"  占用进程PID: {pid}")

                    try:
                        process_info = subprocess.run(
                            ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        lines = process_info.stdout.split('\n')
                        if len(lines) > 1 and ',' in lines[1]:
                            process_name = lines[1].split(',')[0].strip('"')
                            print(f"  进程名称: {process_name}")
                    except:
                        pass

        if not com5_in_use:
            print("✓ 未发现COM5被占用")

        return com5_in_use

    except Exception as e:
        print(f"检查进程占用时出错: {e}")
        return False

def kill_com5_processes():
    print("\n尝试终止使用COM5的进程...")

    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            check=True
        )

        killed_count = 0
        for line in result.stdout.split('\n'):
            if 'COM5' in line.upper():
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], check=True)
                        print(f"✓ 已终止进程 PID: {pid}")
                        killed_count += 1
                    except Exception as e:
                        print(f"✗ 无法终止进程 PID {pid}: {e}")

        if killed_count > 0:
            print(f"✓ 已终止 {killed_count} 个占用COM5的进程")
        else:
            print("未发现需要终止的进程")

        return killed_count > 0

    except Exception as e:
        print(f"终止进程时出错: {e}")
        return False

def check_device_manager():
    print("\n检查设备管理器状态...")

    try:
        subprocess.run(['devmgmt.msc'], check=False)
        print("✓ 设备管理器已打开")
        print("请检查以下项目:")
        print("1. 查看'端口(COM和LPT)'下的COM5")
        print("2. 检查是否有黄色感叹号或问号")
        print("3. 如果有问题，尝试更新驱动程序")
        print("4. 或者禁用后重新启用设备")

    except Exception as e:
        print(f"打开设备管理器时出错: {e}")

def reset_com5_driver():
    print("\n重置COM5驱动程序...")

    try:
        disable_cmd = 'pnputil /disable-device "USB\\VID_1A86&PID_7523\\5&1B6C5C5D&0&3"'
        subprocess.run(disable_cmd, shell=True, check=False)
        print("✓ 已禁用COM5设备")

        time.sleep(2)

        enable_cmd = 'pnputil /enable-device "USB\\VID_1A86&PID_7523\\5&1B6C5C5D&0&3"'
        subprocess.run(enable_cmd, shell=True, check=False)
        print("✓ 已启用COM5设备")

        print("等待设备重新初始化...")
        time.sleep(3)

        return True

    except Exception as e:
        print(f"重置驱动程序时出错: {e}")
        return False

def provide_solutions():
    print("\n" + "="*60)
    print("COM5连接问题解决方案")
    print("="*60)

    solutions = [
        "1. 重新插拔USB转串口设备",
        "2. 重启计算机",
        "3. 在设备管理器中禁用并重新启用COM5端口",
        "4. 检查是否有其他程序(如Arduino IDE、串口调试助手)在使用COM5",
        "5. 尝试使用不同的USB端口",
        "6. 更新USB转串口驱动程序",
        "7. 如果持续失败，使用软件模拟模式"
    ]

    for solution in solutions:
        print(solution)

def check_system_requirements():
    print("\n检查系统要求...")

    python_version = sys.version_info
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

    try:
        import serial
        print(f"pyserial版本: {serial.__version__}")
    except ImportError:
        print("✗ 未安装pyserial")
        print("请运行: pip install pyserial")
        return False

    if os.name != 'nt':
        print("⚠ 非Windows系统，某些功能可能不可用")

    return True

def main():
    print("Windows COM5串口连接修复工具")
    print("="*60)

    if not check_system_requirements():
        return

    if not check_com5_exists():
        provide_solutions()
        return

    com5_in_use = check_process_using_com5()

    connection_ok = test_com5_connection()

    if not connection_ok:
        print("\n开始修复过程...")

        if com5_in_use:
            kill_com5_processes()
            time.sleep(2)

            print("\n重新测试连接...")
            connection_ok = test_com5_connection()

        if not connection_ok:
            print("\n尝试重置驱动程序...")
            reset_com5_driver()
            time.sleep(3)

            print("\n再次测试连接...")
            connection_ok = test_com5_connection()

    print("\n" + "="*60)
    print("诊断结果:")
    print("="*60)

    if connection_ok:
        print("✓ COM5连接测试通过")
        print("系统应该能够正常使用COM5端口")
    else:
        print("✗ COM5连接测试失败")
        print("\n请尝试以下解决方案:")
        provide_solutions()

        print("\n紧急解决方案:")
        print("在代码中设置 hardware_enabled=False 使用软件模拟模式")
        print("示例: belt = BeltController(port='COM5', hardware_enabled=False)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n修复工具被用户中断")
    except Exception as e:
        print(f"\n修复工具运行出错: {e}")
        import traceback
        traceback.print_exc()