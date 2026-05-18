#!/usr/bin/env python3
# encoding:utf-8
import time
import numpy as np
from .Communication import *
from .IK import *


ik = IK()


class ArmIK:
    servo3Range = (500, 2500.0, 0, 180.0)
    servo4Range = (500, 2500.0, 0, 180.0)
    servo5Range = (500, 2500.0, 0, 180.0)
    servo6Range = (500, 2500.0, 0, 180.0)

    def __init__(self):
        self.setServoRange()

    def setServoRange(self, servo3_Range=servo3Range, servo4_Range=servo4Range, servo5_Range=servo5Range,
                      servo6_Range=servo6Range):
        self.servo3Range = servo3_Range
        self.servo4Range = servo4_Range
        self.servo5Range = servo5_Range
        self.servo6Range = servo6_Range
        self.servo3Param = (self.servo3Range[1] - self.servo3Range[0]) / (self.servo3Range[3] - self.servo3Range[2])
        self.servo4Param = (self.servo4Range[1] - self.servo4Range[0]) / (self.servo4Range[3] - self.servo4Range[2])
        self.servo5Param = (self.servo5Range[1] - self.servo5Range[0]) / (self.servo5Range[3] - self.servo5Range[2])
        self.servo6Param = (self.servo6Range[1] - self.servo6Range[0]) / (self.servo6Range[3] - self.servo6Range[2])

    def transformAngelAdaptArm(self, theta3, theta4, theta5, theta6):
        servo3 = int(round(theta3 * self.servo3Param + (self.servo3Range[1] + self.servo3Range[0]) / 2))
        if servo3 > self.servo3Range[1] or servo3 < self.servo3Range[0]:
            logger.info('servo3(%s)超出范围(%s, %s)', servo3, self.servo3Range[0], self.servo3Range[1])
            return False

        servo4 = int(round(theta4 * self.servo4Param + (self.servo4Range[1] + self.servo4Range[0]) / 2))
        if servo4 > self.servo4Range[1] or servo4 < self.servo4Range[0]:
            logger.info('servo4(%s)超出范围(%s, %s)', servo4, self.servo4Range[0], self.servo4Range[1])
            return False

        servo5 = int(round((self.servo5Range[1] + self.servo5Range[0]) / 2 + (90.0 - theta5) * self.servo5Param))
        if servo5 > ((self.servo5Range[1] + self.servo5Range[0]) / 2 + 90 * self.servo5Param) or servo5 < (
                (self.servo5Range[1] + self.servo5Range[0]) / 2 - 90 * self.servo5Param):
            logger.info('servo5(%s)超出范围(%s, %s)', servo5, self.servo5Range[0], self.servo5Range[1])
            return False

        if theta6 < -(self.servo6Range[3] - self.servo6Range[2]) / 2:
            servo6 = int(
                round(((self.servo6Range[3] - self.servo6Range[2]) / 2 + (90 + (180 + theta6))) * self.servo6Param))
        else:
            servo6 = int(round(((self.servo6Range[3] - self.servo6Range[2]) / 2 - (90 - theta6)) * self.servo6Param)) + \
                     self.servo6Range[0]
        if servo6 > self.servo6Range[1] or servo6 < self.servo6Range[0]:
            logger.info('servo6(%s)超出范围(%s, %s)', servo6, self.servo6Range[0], self.servo6Range[1])
            return False
        return {"servo3": servo3, "servo4": servo4, "servo5": servo5, "servo6": servo6}

    def servosMove(self, servos: tuple[int], movetime=None):
        time.sleep(0.02)
        if movetime is None:
            max_d = 0
            for i in range(0, 4):
                d = abs(getPWMServoPulse(i + 3) - servos[i])
                if d > max_d:
                    max_d = d
            movetime = int(max_d * 10)
        setPWMServosPulse(movetime, [(3, servos[0]), (4, servos[1]), (5, servos[2]), (6, servos[3])])

        return movetime

    def setPitchRange(self, coordinate_data, alpha1, alpha2, da=1):
        x, y, z = coordinate_data
        if alpha1 >= alpha2:
            da = -da
        for alpha in np.arange(alpha1, alpha2, da):
            result = ik.getRotationAngle((x, y, z), alpha)
            if result:
                theta3, theta4, theta5, theta6 = result['theta3'], result['theta4'], result['theta5'], result['theta6']
                servos = self.transformAngelAdaptArm(theta3, theta4, theta5, theta6)
                if servos != False:
                    return servos, alpha

        return False

    def setPitchRanges(self, coordinate_data, alpha, alpha1, alpha2, d=0.01):

        x, y, z = coordinate_data
        a_range = abs(int(abs(alpha1 - alpha2) / d)) + 1
        for i in range(a_range):
            if i % 2:
                alpha_ = alpha + (i + 1) / 2 * d
            else:
                alpha_ = alpha - i / 2 * d
                if alpha_ < alpha1:
                    alpha_ = alpha2 - i / 2 * d
            result = ik.getRotationAngle((x, y, z), alpha_)
            if result:
                theta3, theta4, theta5, theta6 = result['theta3'], result['theta4'], result['theta5'], result['theta6']
                servos = self.transformAngelAdaptArm(theta3, theta4, theta5, theta6)
                return servos, alpha_

        return False

    def setPitchRangeMoving(self, coordinate_data, alpha, alpha1, alpha2, movetime=None):
        x, y, z = coordinate_data
        result1 = self.setPitchRange((x, y, z), alpha, alpha1)
        result2 = self.setPitchRange((x, y, z), alpha, alpha2)
        if result1 != False:
            data = result1
            if result2 != False:
                if abs(result2[1] - alpha) < abs(result1[1] - alpha):
                    data = result2
        else:
            if result2 != False:
                data = result2
            else:
                return False
        servos, alpha = data[0], data[1]
        movetime = self.servosMove((servos["servo3"], servos["servo4"], servos["servo5"], servos["servo6"]), movetime)
        return servos, alpha, movetime

    def unified_control(command, params):
        if command == "move_to_position":
            return AK.setPitchRangeMoving(
            (params['x'], params['y'], params['z']),
            params.get('alpha', 0),
            params.get('alpha1', -90),
            params.get('alpha2', 90),
            params.get('movetime', 1000)
        )
        elif command == "set_joint_angle":
            servo_id = params['joint']
            angle = params['angle']
            pulse = int(1500 + angle * 11.11)
            return setPWMServoPulse(servo_id, pulse, params.get('movetime', 500))
        elif command == "run_sequence":
            sequence = params['sequence']
        for action in sequence:
            if action['type'] == 'move':
                AK.setPitchRangeMoving(
                    (action['x'], action['y'], action['z']),
                    action.get('alpha', 0),
                    action.get('alpha1', -90),
                    action.get('alpha2', 90),
                    action.get('movetime', 1000)
                )
                time.sleep(action.get('delay', 1))
            elif action['type'] == 'gripper':
                if action['action'] == 'open':
                    setPWMServoPulse(1, 2000, action.get('movetime', 500))
                else:
                    setPWMServoPulse(1, 1450, action.get('movetime', 500))
                time.sleep(action.get('delay', 0.5))
                return True
            else:
                raise ValueError("未知命令类型")

if __name__ == "__main__":
    AK = ArmIK()
    print(AK.setPitchRange((0, 8, 10), -90, 90))