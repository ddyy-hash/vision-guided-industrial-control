#include <Servo.h>

#define H0 0xA5
#define H1 0x5A

Servo servos[7];
int servo_pins[7] = {0, 5, 0, 6, 9, 10, 11};
int current_pluse[7] = {0};  
float current_speed[7] = {0};
int target_pluse[7] = {0};   
bool initialized[7] = {false};  

// 平滑控制参数
const float MAX_ACCEL = 2.5;    
const float MAX_SPEED = 20.0;   
const float MIN_SPEED = 1;    

void setup() {
  delay(1000);  // 初始延迟确保系统稳定
  Serial.begin(9600);
  while(Serial.available()) Serial.read();  // 清空串口缓冲区
}

void update_servo();
void send_servo_pluse();

void loop() {
  update_servo();
  send_servo_pluse();
}

#define WAIT_COMMAND 0
#define WAIT_H1 1
#define WAIT_COMMAND_PAYLOAD 2
#define COMMAND_EOT 3

void update_servo() {
  static int state = 0;
  static int command_len_rec = 0;
  static byte command[18] = {0};
  
  switch (state) {
    case WAIT_COMMAND: {
      if (!Serial.available()) break;
      byte input = Serial.read();
      if (input == H0)
        state = WAIT_H1;
    } break;
    
    case WAIT_H1: {
      if (!Serial.available()) break;
      byte input = Serial.read();
      if (input == H1)
        state = WAIT_COMMAND_PAYLOAD;
      else
        state = WAIT_COMMAND;
    } break;
    
    case WAIT_COMMAND_PAYLOAD: {
      if (command_len_rec == 0 && Serial.available()) {
        command[0] = Serial.read();  // 读取舵机数量
        command_len_rec = 1;
      }
      
      int expected_len = 3 + command[0] * 3;
      while (Serial.available() && command_len_rec < expected_len) {
        command[command_len_rec] = Serial.read();
        command_len_rec++;
      }
      
      if (command_len_rec >= expected_len) 
        state = COMMAND_EOT;
    } break;
    
    case COMMAND_EOT: {
      int servo_number = command[0];
      int move_time = command[1] | (command[2] << 8); // 小端格式时间
      
      for (int i = 3; i < 3 + command[0] * 3; i += 3) {
        byte servo_id = command[i];
        if (servo_id >= 7) continue;  // 确保舵机ID有效
        
        int pulse = command[i+1] | ((command[i+2] & 0x0F) << 8);
        
        // 首次收到该舵机命令时的处理
        if (!initialized[servo_id]) {
          // 检查引脚有效性
          if (servo_pins[servo_id] != 0) {
            servos[servo_id].attach(servo_pins[servo_id]); // 首次连接舵机
            servos[servo_id].writeMicroseconds(pulse);      // 立即设置位置
            current_pluse[servo_id] = pulse;
            target_pluse[servo_id] = pulse;
          }
          initialized[servo_id] = true;  // 标记为已初始化
        } 
        // 后续命令设置目标位置
        else {
          target_pluse[servo_id] = pulse;
          current_speed[servo_id] = MIN_SPEED;  // 重置速度
        }
      }
      
      command_len_rec = 0;
      state = WAIT_COMMAND;
    } break;
  }
}

void send_servo_pluse() {
  static unsigned long last_time = millis();
  unsigned long now = millis();
  if (now - last_time < 20) return;  // 20ms更新周期
  
  for (int i = 1; i <= 6; i++) {
    // 跳过未初始化的舵机
    if (!initialized[i] || servo_pins[i] == 0) continue;
    if (!servos[i].attached()) continue;
    
    int target = target_pluse[i];
    int current = current_pluse[i];
    int distance = target - current;
    
    // 检查是否需要移动
    if (distance == 0) {
      current_speed[i] = 0;
      continue;
    }
    
    // 计算方向
    int direction = (distance > 0) ? 1 : -1;
    float abs_distance = abs(distance);
    
    // 平滑加速控制
    if (abs_distance > 0) {
      // 计算目标速度（基于剩余距离）
      float target_speed = MIN_SPEED + (MAX_SPEED - MIN_SPEED) * 
                          min(1.0, abs_distance / 200.0);
      
      // 应用加速度限制
      if (current_speed[i] < target_speed) {
        current_speed[i] = min(target_speed, current_speed[i] + MAX_ACCEL);
      } else {
        current_speed[i] = max(target_speed, current_speed[i] - MAX_ACCEL);
      }
      
      // 计算实际移动步长
      int step = direction * min(abs_distance, (int)current_speed[i]);
      current_pluse[i] += step;
    }
    
    // 写入舵机位置
    servos[i].writeMicroseconds(current_pluse[i]);
  }
  
  last_time = now;
}