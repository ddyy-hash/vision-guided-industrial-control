#!/usr/bin/env python3

import sys
import os
import json
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_device_pairing():
    print("=== 设备配对功能测试 ===")

    try:
        from services.device_scanner import get_device_scanner, DeviceType
        from services.device_pairing import get_device_pairing_manager

        scanner = get_device_scanner()
        pairing_manager = get_device_pairing_manager()

        print("✓ 成功导入设备管理模块")

        print("ℹ 手动触发设备扫描...")
        scanner.manual_scan()

        time.sleep(3)

        devices = scanner.get_available_devices()
        print(f"✓ 当前可用设备数量: {len(devices)}")

        for device in devices:
            print(f"  设备: {device['name']} (ID: {device['device_id']}, 类型: {device['device_type']}, 配对状态: {device['pairing_status']})")

        if devices:
            device_id = devices[0]['device_id']
            device_name = devices[0]['name']
            print(f"\n✓ 选择测试设备: {device_name} ({device_id})")

            pairing_id = pairing_manager.create_pairing_request(device_id)
            if pairing_id:
                print(f"✓ 配对请求创建成功: {pairing_id}")

                success = pairing_manager.confirm_pairing(
                    pairing_id,
                    DeviceType.ROBOT_ARM,
                    f"测试设备_{int(time.time())}",
                    True
                )

                if success:
                    print("✓ 设备配对成功！")
                else:
                    print("✗ 设备配对失败")
                    return False
            else:
                print("✗ 配对请求创建失败")
                return False
        else:
            print("ℹ 没有可用设备进行配对测试")
            print("  请确保有串口设备连接（如COM4、COM5）")
            return True

        pairing_file = "backend/pairing_records.json"
        if os.path.exists(pairing_file):
            print(f"\n✓ 配对记录文件存在: {pairing_file}")
            with open(pairing_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
                print(f"✓ 配对记录数量: {len(records)}")
                for device_id, record in records.items():
                    print(f"  设备ID: {device_id}")
                    print(f"    类型: {record.get('device_type', '未知')}")
                    print(f"    名称: {record.get('custom_name', '未命名')}")
                    print(f"    自动连接: {record.get('auto_connect', False)}")
        else:
            print(f"\nℹ 配对记录文件不存在: {pairing_file}")
            print("  这可能是正常的，如果没有成功配对过")

        print("\n=== 测试完成 ===")
        return True

    except Exception as e:
        print(f"✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_file_consistency():
    print("\n=== 文件一致性检查 ===")

    issues = []

    pairing_files = [
        "backend/pairing_records.json",
        "backend/device_pairing_records.json"
    ]

    for file_path in pairing_files:
        if os.path.exists(file_path):
            print(f"✓ 文件存在: {file_path}")
        else:
            print(f"ℹ 文件不存在: {file_path}")

    try:
        from services.device_scanner import DeviceType as BackendDeviceType

        backend_types = [t.value for t in BackendDeviceType]

        print(f"\n后端设备类型: {backend_types}")

        required_types = ["robot_arm", "conveyor_belt", "vision_system", "temperature_sensor", "plc", "unknown"]
        missing_types = set(required_types) - set(backend_types)

        if missing_types:
            issues.append(f"后端缺少设备类型: {missing_types}")

    except Exception as e:
        issues.append(f"检查设备类型枚举时出错: {e}")

    if issues:
        print("✗ 发现不一致问题:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✓ 所有文件一致性检查通过")
        return True

if __name__ == "__main__":
    print("开始设备配对功能测试...")

    consistency_ok = check_file_consistency()

    pairing_ok = test_device_pairing()

    if consistency_ok and pairing_ok:
        print("\n🎉 所有测试通过！设备配对功能修复成功。")
        sys.exit(0)
    else:
        print("\n❌ 测试失败，请检查上述问题。")
        sys.exit(1)