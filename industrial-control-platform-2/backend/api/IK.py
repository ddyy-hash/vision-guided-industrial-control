from math import cos, sqrt, sin, acos
from math import degrees, atan2, radians
import logging

logger = logging.getLogger(__name__)

class IK:
    l1 = 8.80
    l2 = 5.80
    l3 = 6.20
    l4 = 9.50

    def setLinkLength(self, L1=l1, L2=l2, L3=l3, L4=l4):
        self.l1 = L1
        self.l2 = L2
        self.l3 = L3
        self.l4 = L4

    def getLinkLength(self):
        return {"L1": self.l1, "L2": self.l2, "L3": self.l3, "L4": self.l4}

    def getRotationAngle(self, coordinate_data, Alpha):
        X, Y, Z = coordinate_data
        theta6 = degrees(atan2(Y, X))

        P_O = sqrt(X * X + Y * Y)
        CD = self.l4 * cos(radians(Alpha))
        PD = self.l4 * sin(radians(Alpha))
        AF = P_O - CD
        CF = Z - self.l1 - PD
        AC = sqrt(pow(AF, 2) + pow(CF, 2))
        if round(CF, 4) < -self.l1:
            logger.debug('高度低于0, CF(%s)<l1(%s)', CF, -self.l1)
            return False
        if self.l2 + self.l3 < round(AC, 4):
            logger.debug('不能构成连杆结构, l2(%s) + l3(%s) < AC(%s)', self.l2, self.l3, AC)
            return False
        cos_ABC = round((pow(self.l2, 2) + pow(self.l3, 2) - pow(AC, 2)) / (2 * self.l2 * self.l3), 4)
        if abs(cos_ABC) > 1:
            logger.debug('不能构成连杆结构, abs(cos_ABC(%s)) > 1', cos_ABC)
            return False
        ABC = acos(cos_ABC)
        theta4 = 180.0 - degrees(ABC)
        CAF = acos(AF / AC)
        cos_BAC = round((pow(AC, 2) + pow(self.l2, 2) - pow(self.l3, 2)) / (2 * self.l2 * AC), 4)
        if abs(cos_BAC) > 1:
            logger.debug('不能构成连杆结构, abs(cos_BAC(%s)) > 1', cos_BAC)
            return False
        if CF < 0:
            zf_flag = -1
        else:
            zf_flag = 1
        theta5 = degrees(CAF * zf_flag + acos(cos_BAC))
        theta3 = Alpha - theta5 + theta4

        return {"theta3": theta3, "theta4": theta4, "theta5": theta5, "theta6": theta6}
