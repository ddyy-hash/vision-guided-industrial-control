#!/usr/bin/env python3
# encoding:utf-8

import serial
import threading
import logging
import platform
import time

logger = logging.getLogger("communication")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

SERVO_CMD_HEADER = b'\xA5\x5A'
SERVO_ADJUSTMENTS = {
    1: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0
}
US_TO_DEG = 0.09

_serial_conn = None
_serial_lock = threading.Lock()
_servo_angles = [0] * 7
_servo_pulses = [0] * 7
_serial_port = "COM9"
_serial_baudrate = 9600
_simulate_mode = False

def set_serial_params(port="COM9", baudrate=9600):
    global _serial_port, _serial_baudrate

    with _serial_lock:
        params_changed = (_serial_port != port) or (_serial_baudrate != baudrate)

        if _serial_conn is not None and params_changed:
            logger.warning("串口参数更改，需要重新连接")
            _close_serial()

        _serial_port = port
        _serial_baudrate = baudrate

        if params_changed:
            logger.info(f"串口参数设置为: {port}@{baudrate}")
        else:
            logger.debug(f"串口参数未变化，保持: {port}@{baudrate}")

def _get_serial_connection():
    global _serial_conn, _simulate_mode

    with _serial_lock:
        if _serial_conn is not None:
            return _serial_conn

        if _simulate_mode:
            logger.info("模拟模式: 使用虚拟串口")
            return None

        try:
            logger.info(f"尝试连接串口 {_serial_port}...")
            _serial_conn = serial.Serial(
                port=_serial_port,
                baudrate=_serial_baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )

            if _serial_conn.is_open:
                logger.info(f"成功连接到串口 {_serial_port}")
                return _serial_conn
            else:
                logger.error(f"串口 {_serial_port} 未打开")
                return None

        except serial.SerialException as e:
            logger.error(f"串口连接失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return None

def _close_serial():
    global _serial_conn

    with _serial_lock:
        if _serial_conn is not None and _serial_conn.is_open:
            try:
                _serial_conn.close()
                logger.info("串口连接已关闭")
            except Exception as e:
                logger.error(f"关闭串口时出错: {str(e)}")
            finally:
                _serial_conn = None

def enable_simulate_mode(enable=True):
    global _simulate_mode
    _simulate_mode = enable
    logger.info(f"模拟模式 {'已启用' if enable else '已禁用'}")

    if enable:
        _close_serial()

def close_serial():
    _close_serial()

def setPWMServoPulse(servo_id, pulse=1500, movetime=500):
    if servo_id not in [1, 3, 4, 5, 6]:
        logger.error(f"无效的舵机ID: {servo_id}")
        return None

    pulse = max(500, min(2500, pulse))

    adjusted_pulse = pulse + SERVO_ADJUSTMENTS.get(servo_id, 0)
    adjusted_pulse = max(500, min(2500, adjusted_pulse))

    movetime = max(0, min(30000, movetime))

    cmd = (
        SERVO_CMD_HEADER +
        b'\x01' +
        movetime.to_bytes(2, 'little') +
        servo_id.to_bytes(1, 'little') +
        adjusted_pulse.to_bytes(2, 'little')
    )

    _servo_pulses[servo_id] = pulse
    _servo_angles[servo_id] = int((pulse - 500) * US_TO_DEG)

    logger.debug(f"舵机 {servo_id} 命令: 脉宽={pulse} -> {adjusted_pulse} (校准后), 时间={movetime}ms")

    return _send_command(cmd, pulse)

def setPWMServosPulse(movetime, servos):
    movetime = max(0, min(30000, movetime))

    if not servos or len(servos) > 6:
        logger.error(f"无效的舵机数量: {len(servos)}")
        return False

    cmd = (
        SERVO_CMD_HEADER +
        len(servos).to_bytes(1, 'little') +
        movetime.to_bytes(2, 'little')
    )

    valid_servos = []

    for servo_id, pulse in servos:
        if servo_id not in [1, 3, 4, 5, 6]:
            logger.warning(f"跳过无效舵机ID: {servo_id}")
            continue

        pulse = max(500, min(2500, pulse))

        adjusted_pulse = pulse + SERVO_ADJUSTMENTS.get(servo_id, 0)
        adjusted_pulse = max(500, min(2500, adjusted_pulse))

        cmd += (
            servo_id.to_bytes(1, 'little') +
            adjusted_pulse.to_bytes(2, 'little')
        )

        _servo_pulses[servo_id] = pulse
        _servo_angles[servo_id] = int((pulse - 500) * US_TO_DEG)

        valid_servos.append(servo_id)
        logger.debug(f"舵机 {servo_id} 设置: 脉宽={pulse} -> {adjusted_pulse} (校准后)")

    if not valid_servos:
        logger.error("没有有效的舵机指令")
        return False

    return _send_command(cmd, True) is not None

def getPWMServoPulse(servo_id):
    if 1 <= servo_id <= 6:
        return _servo_pulses[servo_id]
    logger.error(f"无效的舵机ID: {servo_id}")
    return None

def getPWMServoAngle(servo_id):
    if 1 <= servo_id <= 6:
        return _servo_angles[servo_id]
    logger.error(f"无效的舵机ID: {servo_id}")
    return None

def calibrate_servo(servo_id, offset):
    if servo_id not in SERVO_ADJUSTMENTS:
        logger.error(f"无法校准舵机 {servo_id}: 不支持")
        return

    SERVO_ADJUSTMENTS[servo_id] = offset
    logger.info(f"舵机 {servo_id} 校准偏移量设置为: {offset}")

def _send_command(cmd, success_value):
    if _simulate_mode:
        logger.info(f"模拟模式: 发送命令 {cmd.hex()}")
        return success_value

    conn = _get_serial_connection()
    if conn is None:
        logger.warning("串口未连接，命令未发送")
        return None

    try:
        logger.debug(f"发送命令: {cmd.hex()}")
        conn.write(cmd)
        return success_value
    except serial.SerialException as e:
        logger.error(f"发送失败: {str(e)}")

        _close_serial()
        try:
            conn = _get_serial_connection()
            if conn:
                conn.write(cmd)
                logger.info("重新连接后发送成功")
                return success_value
        except:
            logger.error("重新连接后发送失败")

        return None
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        return None

import atexit
atexit.register(close_serial)

if __name__ == "__main__":
    print("串口通信模块测试")

    enable_simulate_mode(True)

    print("测试单个舵机控制...")
    setPWMServoPulse(1, 1500, 500)
    setPWMServoPulse(3, 2000, 1000)

    print("测试多个舵机控制...")
    setPWMServosPulse(1500, [(4, 1500), (5, 1800), (6, 1200)])

    print("舵机1脉宽:", getPWMServoPulse(1))
    print("舵机3角度:", getPWMServoAngle(3))

    calibrate_servo(3, 50)
    setPWMServoPulse(3, 1500, 500)

    print("测试完成")