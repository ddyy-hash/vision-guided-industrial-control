import cv2
import numpy as np
import threading
import time
import base64
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, List
import json

logger = logging.getLogger(__name__)

OCR_SERVICE_URL = "http://localhost:8000"

class RealTimeEnergyDetectionService:

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.is_running = False
        self.detection_thread = None
        self.camera = None

        self.detection_interval = self.config.get('detection_interval', 2.0)
        self.frame_quality = self.config.get('frame_quality', 70)
        self.target_fps = self.config.get('target_fps', 15)

        self.current_frame = None
        self.last_detection_time = 0
        self.detection_results = []
        self.frame_count = 0

        self.callbacks = {
            'on_frame_captured': [],
            'on_energy_detected': [],
            'on_detection_error': []
        }

        logger.info("实时能效检测服务初始化完成")

    def start_detection(self, camera_source: int = 0):
        try:
            self.camera = cv2.VideoCapture(camera_source)
            if not self.camera.isOpened():
                logger.warning("无法打开摄像头，启动模拟模式")
                self._start_simulation()
                return True

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, self.target_fps)

            self.is_running = True
            self.detection_thread = threading.Thread(
                target=self._detection_loop,
                name="EnergyDetectionThread"
            )
            self.detection_thread.daemon = True
            self.detection_thread.start()

            logger.info(f"实时能效检测启动成功，摄像头源: {camera_source}")
            return True

        except Exception as e:
            logger.error(f"启动能效检测失败: {e}")
            logger.info("启动模拟模式作为备用")
            self._start_simulation()
            return True

    def stop_detection(self):
        try:
            self.is_running = False

            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=3)

            if self.camera:
                self.camera.release()
                self.camera = None

            self.current_frame = None
            self.detection_results.clear()

            logger.info("实时能效检测已停止")

        except Exception as e:
            logger.error(f"停止能效检测时出错: {e}")

    def _detection_loop(self):
        fps_start_time = time.time()
        fps_frame_count = 0

        logger.info("能效检测循环开始运行")

        while self.is_running:
            try:
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    logger.warning("读取摄像头帧失败")
                    time.sleep(0.1)
                    continue

                self.current_frame = frame.copy()
                self.frame_count += 1
                fps_frame_count += 1

                current_time = time.time()
                if current_time - fps_start_time >= 1.0:
                    fps = fps_frame_count / (current_time - fps_start_time)
                    fps_frame_count = 0
                    fps_start_time = current_time
                    logger.debug(f"能效检测帧率: {fps:.1f} FPS")

                time_since_last_detection = current_time - self.last_detection_time
                if time_since_last_detection >= self.detection_interval:
                    self._perform_energy_detection(frame)
                    self.last_detection_time = current_time

                self._trigger_callback('on_frame_captured', {
                    'frame_id': self.frame_count,
                    'timestamp': datetime.now().isoformat(),
                    'has_frame': True
                })

                time.sleep(1.0 / self.target_fps)

            except Exception as e:
                logger.error(f"检测循环出错: {e}")
                time.sleep(0.1)

        logger.info("能效检测循环正常结束")

    def _perform_energy_detection(self, frame: np.ndarray):
        try:
            frame_base64 = self._encode_frame_to_base64(frame)
            if not frame_base64:
                logger.warning("无法编码视频帧")
                return

            image_data = base64.b64decode(frame_base64.split(',')[1])

            files = {'file': ('realtime_frame.jpg', image_data, 'image/jpeg')}

            response = requests.post(
                f"{OCR_SERVICE_URL}/api/energy/detect",
                files=files,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()

                detection_result = self._process_detection_result(result, frame_base64)
                self.detection_results.append(detection_result)

                if len(self.detection_results) > 10:
                    self.detection_results.pop(0)

                self._trigger_callback('on_energy_detected', detection_result)

                logger.info(f"能效检测成功: {detection_result.get('energy_level', '未知')}")

            else:
                error_msg = f"OCR服务返回错误: {response.status_code}"
                logger.error(error_msg)
                self._trigger_callback('on_detection_error', {
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                })

        except requests.exceptions.RequestException as e:
            error_msg = f"OCR服务连接失败: {e}"
            logger.error(error_msg)
            self._trigger_callback('on_detection_error', {
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            error_msg = f"能效检测处理失败: {e}"
            logger.error(error_msg)
            self._trigger_callback('on_detection_error', {
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })

    def _process_detection_result(self, ocr_result: Dict, frame_base64: str) -> Dict:
        try:
            energy_level = "未知"
            confidence = 0.0
            ocr_text = ""

            if ocr_result.get('code') == 100:
                data = ocr_result.get('data', {})
                energy_level = data.get('energy_level', '未知')

                if 'ocr_text' in data:
                    ocr_text = data['ocr_text']
                    import re
                    level_match = re.search(r'[一二三四五12345]级', ocr_text)
                    if level_match:
                        energy_level = level_match.group()

                confidence = 0.9

            result = {
                'success': True,
                'energy_level': energy_level,
                'confidence': confidence,
                'ocr_text': ocr_text,
                'frame_base64': frame_base64,
                'timestamp': datetime.now().isoformat(),
                'raw_result': ocr_result
            }

            return result

        except Exception as e:
            logger.error(f"处理检测结果失败: {e}")
            return {
                'success': False,
                'energy_level': '未知',
                'confidence': 0.0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _encode_frame_to_base64(self, frame: np.ndarray) -> Optional[str]:
        try:
            height, width = frame.shape[:2]
            target_width = 640
            target_height = 480

            if width != target_width or height != target_height:
                frame_resized = cv2.resize(frame, (target_width, target_height))
            else:
                frame_resized = frame

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.frame_quality]
            _, buffer = cv2.imencode('.jpg', frame_resized, encode_param)

            image_base64 = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{image_base64}"

        except Exception as e:
            logger.error(f"帧编码失败: {e}")
            return None

    def get_current_frame(self) -> Optional[str]:
        if self.current_frame is None:
            return None

        return self._encode_frame_to_base64(self.current_frame)

    def get_detection_results(self, limit: int = 5) -> List[Dict]:
        return self.detection_results[-limit:] if self.detection_results else []

    def get_latest_result(self) -> Optional[Dict]:
        return self.detection_results[-1] if self.detection_results else None

    def get_service_status(self) -> Dict:
        return {
            'is_running': self.is_running,
            'frame_count': self.frame_count,
            'detection_count': len(self.detection_results),
            'last_detection_time': self.last_detection_time,
            'detection_interval': self.detection_interval
        }

    def add_callback(self, event: str, callback: callable):
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, data: any):
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"回调函数错误: {e}")

    def _start_simulation(self):
        self.is_running = True
        self.detection_thread = threading.Thread(target=self._simulation_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        logger.info("模拟能效检测模式已启动")

    def _simulation_loop(self):
        while self.is_running:
            try:
                self.frame_count += 1

                current_time = time.time()
                time_since_last_detection = current_time - self.last_detection_time

                if time_since_last_detection >= self.detection_interval:
                    simulated_result = {
                        'success': True,
                        'energy_level': np.random.choice(['1', '2', '3', '未知']),
                        'confidence': np.random.uniform(0.7, 0.95),
                        'ocr_text': f"模拟能效标签文本 - 等级{np.random.choice(['1', '2', '3'])}",
                        'timestamp': datetime.now().isoformat(),
                        'simulated': True
                    }

                    self.detection_results.append(simulated_result)
                    self.last_detection_time = current_time

                    self._trigger_callback('on_energy_detected', simulated_result)

                self._trigger_callback('on_frame_captured', {
                    'frame_id': self.frame_count,
                    'timestamp': datetime.now().isoformat(),
                    'has_frame': False,
                    'simulated': True
                })

                time.sleep(1.0 / self.target_fps)

            except Exception as e:
                logger.error(f"模拟循环出错: {e}")
                time.sleep(0.1)

_energy_detection_service = None

def get_energy_detection_service(config: Optional[Dict] = None) -> RealTimeEnergyDetectionService:
    global _energy_detection_service
    if _energy_detection_service is None:
        _energy_detection_service = RealTimeEnergyDetectionService(config)
    return _energy_detection_service

def initialize_energy_detection_service(config: Optional[Dict] = None):
    global _energy_detection_service
    _energy_detection_service = RealTimeEnergyDetectionService(config)
    return _energy_detection_service