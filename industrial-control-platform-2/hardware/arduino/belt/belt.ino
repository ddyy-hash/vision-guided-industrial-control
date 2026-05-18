#include <AccelStepper.h>
#include <stdlib.h>
#include <stdlib.h>  // 包含strtof()的函数声明
#include <stdio.h>   // 可选，确保标准库函数可用

// 电机接口定义
#define PUL_PIN 2
#define DIR_PIN 3

// 系统参数配置
const int STEPS_PER_REV = 400;   // 对应拨码开关设置
const float BELT_PER_REV = 0.25; // ★关键参数★ 传送带每转一圈移动距离(米)
                                 // 根据实际机械结构测量确定

AccelStepper stepper(AccelStepper::DRIVER, PUL_PIN, DIR_PIN);

// 运行状态跟踪
float currentSpeed = 0;           // 当前速度(m/s)
unsigned long lastPrintTime = 0;  // 上次打印时间

void setup() {
  Serial.begin(115200);

  // 步进电机参数
  stepper.setMaxSpeed(10000);     // 最大速度(步/秒)
  stepper.setAcceleration(2000);  // 加速度(步/秒²)

  Serial.println("传送带控制系统");
  Serial.print("每转移动距离: ");
  Serial.print(BELT_PER_REV, 3);
  Serial.println(" m");
  Serial.println("输入目标速度(m/s):");
}

void loop() {
  // 非阻塞式串口处理
  static uint32_t lastUpdateTime = 0;
  const uint16_t SERIAL_UPDATE_INTERVAL = 20; // 20ms串口更新间隔
  
  // 优先执行电机控制（确保实时性）
  stepper.runSpeed();

  // 定时处理串口输入（避免阻塞）
  if (millis() - lastUpdateTime >= SERIAL_UPDATE_INTERVAL) {
    if (Serial.available()) {
      String input = Serial.readStringUntil('\n');
      input.trim(); // 去除首尾空白字符

      if (input.startsWith("#")) {
        // 状态查询
        currentSpeed = (stepper.speed() * BELT_PER_REV) / STEPS_PER_REV;
        
        Serial.print("当前速度: ");
        Serial.print(abs(currentSpeed), 2);
        Serial.print(" m/s | 方向: ");
        Serial.println(currentSpeed >= 0 ? "正向" : "反向");
      } 
      else if (input.length() > 0) {  // 非空输入
        // 改进的速度输入处理（支持所有数字输入）
        char* endptr;
        float targetSpeed = atof(input.c_str());
        
        if (endptr != input.c_str()) { // 成功转换数字
          // 带限幅的速度转换
          float stepsPerSec = constrain(
            (targetSpeed / BELT_PER_REV) * STEPS_PER_REV,
            -stepper.maxSpeed(), 
            stepper.maxSpeed()
          );
          
          stepper.setSpeed(stepsPerSec);
          
          Serial.print("设定速度: ");
          Serial.print(targetSpeed, 2);
          Serial.println(" m/s");
        }
      }
    }
    lastUpdateTime = millis();
  }

  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    // 新增：解析 "速度 方向" 格式（如 "0.5 forward"）
    int spaceIndex = input.indexOf(' ');
    if (spaceIndex > 0) {
      float targetSpeed = input.substring(0, spaceIndex).toFloat();
      String directionStr = input.substring(spaceIndex + 1);

      // 计算步进电机速度（带方向）
      float stepsPerSec = (targetSpeed / BELT_PER_REV) * STEPS_PER_REV;
      if (directionStr == "backward") stepsPerSec *= -1;

      stepper.setSpeed(stepsPerSec);
      Serial.print("设定速度: ");
      Serial.print(targetSpeed, 2);
      Serial.print(" m/s | 方向: ");
      Serial.println(directionStr);
    }
  }
}