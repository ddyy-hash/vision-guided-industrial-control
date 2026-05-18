#!/usr/bin/env python3
# encoding:utf-8
import time
import math
import logging
import numpy as np
from .ArmIK import ArmIK
from .Communication import set_serial_params, setPWMServosPulse, setPWMServoPulse, getPWMServoPulse, calibrate_servo, close_serial

logger = logging.getLogger(__name__)

class RobotArm:
    SERVO_RANGES = {
        1: (500, 2500, 0, 180),
        3: (500, 2500, -90, 90),
        4: (500, 2500, -90, 90),
        5: (500, 2500, 0, 180),
        6: (500, 2500, 0, 180)
    }

    def __init__(self, serial_port="COM9", baudrate=9600):
        self.connected = False
        self.serial_port = serial_port

        self.ik = ArmIK()

        self.servo_params = {}
        self.set_servo_ranges()

        self.current_position = (0, 0, 0)
        self.current_pitch = 0
        self.is_gripper_open = False

        try:
            set_serial_params(serial_port, baudrate)
            self.connected = True
            logger.info(f"机械臂初始化完成，已连接 {serial_port}")
        except Exception as e:
            logger.warning(f"机械臂串口连接失败 ({serial_port}): {e}，进入模拟模式")
            self.connected = False

    def get_status(self):
        return {
            "connected": self.connected,
            "serial_port": self.serial_port,
            "current_position": self.current_position,
            "current_pitch": self.current_pitch,
            "is_gripper_open": self.is_gripper_open
        }

    def set_servo_ranges(self, ranges=None):
        if ranges:
            self.SERVO_RANGES = ranges

        for servo_id, (min_pulse, max_pulse, min_angle, max_angle) in self.SERVO_RANGES.items():
            param = (max_pulse - min_pulse) / (max_angle - min_angle)
            self.servo_params[servo_id] = {
                "min_pulse": min_pulse,
                "max_pulse": max_pulse,
                "min_angle": min_angle,
                "max_angle": max_angle,
                "param": param
            }

    def angle_to_pulse(self, servo_id, angle):
        if servo_id not in self.servo_params:
            raise ValueError(f"无效的舵机ID: {servo_id}")

        params = self.servo_params[servo_id]
        min_pulse = params["min_pulse"]
        max_pulse = params["max_pulse"]
        min_angle = params["min_angle"]
        max_angle = params["max_angle"]

        pulse = min_pulse + (angle - min_angle) * (max_pulse - min_pulse) / (max_angle - min_angle)
        pulse = int(round(pulse))

        if pulse < min_pulse:
            logger.warning(f"舵机 {servo_id} 脉宽值 {pulse} 低于最小值 {min_pulse}，已修正")
            pulse = min_pulse
        elif pulse > max_pulse:
            logger.warning(f"舵机 {servo_id} 脉宽值 {pulse} 超过最大值 {max_pulse}，已修正")
            pulse = max_pulse

        return pulse

    def pulse_to_angle(self, servo_id, pulse):
        if servo_id not in self.servo_params:
            raise ValueError(f"无效的舵机ID: {servo_id}")

        params = self.servo_params[servo_id]
        min_pulse = params["min_pulse"]
        max_pulse = params["max_pulse"]
        min_angle = params["min_angle"]
        max_angle = params["max_angle"]

        angle = min_angle + (pulse - min_pulse) * (max_angle - min_angle) / (max_pulse - min_pulse)
        return angle

    def move_servo(self, servo_id, pulse, movetime=500):
        if servo_id not in self.SERVO_RANGES:
            raise ValueError(f"无效的舵机ID: {servo_id}")

        if self.connected:
            setPWMServoPulse(servo_id, pulse, movetime)
            logger.info(f"移动舵机 {servo_id} 到脉宽 {pulse}，时间 {movetime}ms")
        else:
            logger.info(f"模拟模式: 移动舵机 {servo_id} 到脉宽 {pulse}，时间 {movetime}ms")

        if servo_id == 1:
            angle = self.pulse_to_angle(1, pulse)
            self.is_gripper_open = angle > 90

        return True

    def move_servos(self, movetime, servos):
        servo_list = []
        for servo_id, pulse in servos:
            if servo_id not in self.SERVO_RANGES:
                logger.warning(f"跳过无效舵机ID: {servo_id}")
                continue
            servo_list.append((servo_id, pulse))

        if self.connected:
            setPWMServosPulse(movetime, servo_list)
            logger.info(f"移动 {len(servo_list)} 个舵机，时间 {movetime}ms")
        else:
            logger.info(f"模拟模式: 移动 {len(servo_list)} 个舵机，时间 {movetime}ms")

        for servo_id, pulse in servos:
            if servo_id == 1:
                angle = self.pulse_to_angle(1, pulse)
                self.is_gripper_open = angle > 90

        return True

    def move_to_position(self, x, y, z, pitch=0, movetime=1000):
        logger.info(f"尝试移动到位置: ({x}, {y}, {z}), 俯仰角: {pitch}°")

        result = self.ik.setPitchRangeMoving((x, y, z), pitch, pitch-30, pitch+30, movetime)

        if not result:
            logger.error(f"无法到达位置 ({x}, {y}, {z})")
            return False

        servos, alpha, movetime_used = result
        self.current_position = (x, y, z)
        self.current_pitch = alpha

        logger.info(f"成功移动到位置，实际俯仰角: {alpha}°，用时 {movetime_used}ms")
        return True

    def set_joint_angle(self, joint_id, angle, movetime=500):
        if joint_id not in [1, 3, 4, 5, 6]:
            logger.error(f"无效关节ID: {joint_id}")
            return False

        pulse = self.angle_to_pulse(joint_id, angle)
        success = self.move_servo(joint_id, pulse, movetime)

        if joint_id == 1:
            self.is_gripper_open = angle > 90

        return success

    def open_gripper(self, movetime=500):
        return self.set_joint_angle(1, 180, movetime)

    def close_gripper(self, movetime=500):
        return self.set_joint_angle(1, 0, movetime)

    def get_joint_angle(self, joint_id):
        if joint_id not in [1, 3, 4, 5, 6]:
            logger.error(f"无效关节ID: {joint_id}")
            return None

        pulse = getPWMServoPulse(joint_id)
        return self.pulse_to_angle(joint_id, pulse)

    def run_sequence(self, sequence, callback=None):
        total_steps = len(sequence)
        logger.info(f"开始执行动作序列，共 {total_steps} 个步骤")

        try:
            for index, action in enumerate(sequence):
                action_type = action.get('type', 'joint')
                step_desc = f"步骤 {index+1}/{total_steps}: {action.get('name', f'动作{index+1}')}"
                logger.info(step_desc)

                if callback:
                    progress = int((index + 1) / total_steps * 100)
                    callback(progress, step_desc)

                if action_type == 'move':
                    self._handle_move_action(action)
                elif action_type == 'gripper':
                    self._handle_gripper_action(action)
                elif action_type == 'joint':
                    self._handle_joint_action(action)
                else:
                    logger.warning(f"未知的动作类型: {action_type}")
                    continue

                delay = action.get('delay', 0)
                movetime = action.get('movetime', 500)

                wait_time = max(movetime / 1000.0, 0.5) + delay
                logger.debug(f"等待 {wait_time:.2f} 秒")
                time.sleep(wait_time)

            logger.info("动作序列执行成功")
            return True

        except Exception as e:
            logger.error(f"执行序列时出错: {str(e)}", exc_info=True)
            self.home_position()
            return False

    def _handle_joint_action(self, action):
        joint_id = action.get('joint_id')
        angle = action.get('angle')
        movetime = action.get('movetime', 500)

        if joint_id is None:
            params = action.get('params', {})
            joint_id = params.get('joint')
            angle = params.get('angle')

        if joint_id is not None and angle is not None:
            self.set_joint_angle(joint_id, angle, movetime)
        else:
            logger.warning(f"关节动作参数不完整: {action}")

    def _handle_move_action(self, action):
        params = action.get('params', {})
        x = params.get('x')
        y = params.get('y')
        z = params.get('z')
        pitch = params.get('pitch', 0)
        movetime = action.get('movetime', 1000)

        if x is not None and y is not None and z is not None:
            self.move_to_position(x, y, z, pitch, movetime)
        else:
            logger.warning(f"移动动作参数不完整: {action}")

    def _handle_gripper_action(self, action):
        params = action.get('params', {})
        action_type = params.get('action')  # 'open' or 'close'
        movetime = action.get('movetime', 500)

        if action_type == 'open':
            self.open_gripper(movetime)
        elif action_type == 'close':
            self.close_gripper(movetime)
        else:
            logger.warning(f"未知的夹爪动作: {action_type}")

    def home_position(self, movetime=1500):
        logger.info("返回初始位置")
        return self.move_servos(movetime, [
            (1, self.angle_to_pulse(1, 130)),
            (3, self.angle_to_pulse(3, -75)),
            (4, self.angle_to_pulse(4, 60)),
            (5, self.angle_to_pulse(5, 45)),
            (6, self.angle_to_pulse(6, 90))
        ])
    def calibrate_servo(self, servo_id, offset):
        if servo_id not in self.SERVO_RANGES:
            logger.error(f"无效的舵机ID: {servo_id}")
            return

        calibrate_servo(servo_id, offset)
        logger.info(f"舵机 {servo_id} 校准完成，偏移量: {offset}")

    def close(self):
        close_serial()
        logger.info("串口连接已关闭")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    arm = RobotArm(serial_port="COM9")

    try:
        logger.info("设置初始位置")
        arm.move_servos(1500, [
            (1, arm.angle_to_pulse(1, 130)),
            (3, arm.angle_to_pulse(3, -75)),
            (4, arm.angle_to_pulse(4, 60)),
            (5, arm.angle_to_pulse(5, 45)),
            (6, arm.angle_to_pulse(6, 90))
        ])
        time.sleep(2)

        logger.info("移动到检测位置")
        arm.move_servos(1500, [
            (1, arm.angle_to_pulse(1, 130)),
            (3, arm.angle_to_pulse(3, -70)),
            (4, arm.angle_to_pulse(4, 90)),
            (5, arm.angle_to_pulse(5, 80)),
            (6, arm.angle_to_pulse(6, 90))
        ])
        time.sleep(2)

        logger.info("过渡位置")
        arm.move_servos(1500, [
            (1, arm.angle_to_pulse(1, 130)),
            (3, arm.angle_to_pulse(3, -45)),
            (4, arm.angle_to_pulse(4, 85)),
            (5, arm.angle_to_pulse(5, 110)),
            (6, arm.angle_to_pulse(6, 90))
        ])
        time.sleep(1)

        logger.info("移动到抓取位置")
        arm.move_servos(1500, [
            (1, arm.angle_to_pulse(1, 130)),
            (3, arm.angle_to_pulse(3, -20)),
            (4, arm.angle_to_pulse(4, 80)),
            (5, arm.angle_to_pulse(5, 140)),
            (6, arm.angle_to_pulse(6, 90))
        ])
        time.sleep(1)

        logger.info("闭合夹爪抓取物体")
        arm.move_servos(500, [
            (1, arm.angle_to_pulse(1, 0)),
        ])
        time.sleep(0.5)

        logger.info("过渡1（抬升+转向）")
        arm.move_servos(1000, [
            (3, arm.angle_to_pulse(3, -10)),
            (4, arm.angle_to_pulse(4, 75)),
            (5, arm.angle_to_pulse(5, 120)),
            (6, arm.angle_to_pulse(6, 70))
        ])
        time.sleep(0.5)

        logger.info("过渡2（抬升+转向）")
        arm.move_servos(1000, [
            (3, arm.angle_to_pulse(3, -10)),
            (4, arm.angle_to_pulse(4, 70)),
            (5, arm.angle_to_pulse(5, 100)),
            (6, arm.angle_to_pulse(6, 45))
        ])
        time.sleep(0.5)

        logger.info("过渡3（抬升+转向）")
        arm.move_servos(1000, [
            (3, arm.angle_to_pulse(3, -10)),
            (4, arm.angle_to_pulse(4, 65)),
            (5, arm.angle_to_pulse(5, 120)),
            (6, arm.angle_to_pulse(6, 20))
        ])
        time.sleep(0.5)

        logger.info("移动到放置位置")
        arm.move_servos(1500, [
            (1, arm.angle_to_pulse(1, 0)),
            (3, arm.angle_to_pulse(3, -20)),
            (4, arm.angle_to_pulse(4, 60)),
            (5, arm.angle_to_pulse(5, 140)),
            (6, arm.angle_to_pulse(6, 0))
        ])
        time.sleep(0.5)

        logger.info("打开夹爪放置物体")
        arm.move_servos(500, [
            (1, arm.angle_to_pulse(1, 130)),
        ])
        time.sleep(2)

        logger.info("过渡1（抬升+转向）")
        arm.move_servos(1000, [
            (3, arm.angle_to_pulse(3, -32)),
            (4, arm.angle_to_pulse(4, 70)),
            (5, arm.angle_to_pulse(5, 120)),
            (6, arm.angle_to_pulse(6, 30))
        ])
        time.sleep(0.5)

        logger.info("过渡2（抬升+转向）")
        arm.move_servos(1000, [
            (3, arm.angle_to_pulse(3, -45)),
            (4, arm.angle_to_pulse(4, 70)),
            (5, arm.angle_to_pulse(5, 100)),
            (6, arm.angle_to_pulse(6, 45))
        ])
        time.sleep(0.5)

        logger.info("过渡3（抬升+转向）")
        arm.move_servos(1000, [
            (3, arm.angle_to_pulse(3, -57)),
            (4, arm.angle_to_pulse(4, 80)),
            (5, arm.angle_to_pulse(5, 90)),
            (6, arm.angle_to_pulse(6, 60))
        ])
        time.sleep(0.5)

        logger.info("返回检测位置")
        arm.move_servos(1500, [
            (1, arm.angle_to_pulse(1, 130)),
            (3, arm.angle_to_pulse(3, -70)),
            (4, arm.angle_to_pulse(4, 90)),
            (5, arm.angle_to_pulse(5, 80)),
            (6, arm.angle_to_pulse(6, 90))
        ])
        time.sleep(1)

        logger.info("任务完成，等待下一次操作")

    except Exception as e:
        logger.error(f"操作出错: {str(e)}", exc_info=True)
    finally:
        arm.close()

if __name__ == "__main__":
    main()