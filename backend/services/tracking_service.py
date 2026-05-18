import cv2
import numpy as np
import threading
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os
import base64
from io import BytesIO
from PIL import Image
import requests

from .mqtt_service import get_mqtt_service

try:
    from ultralytics import YOLO
    from deep_sort_realtime.deepsort_tracker import DeepSort
    TRACKING_AVAILABLE = True

    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        GPU_DEVICE_COUNT = torch.cuda.device_count()
        GPU_DEVICE_NAME = torch.cuda.get_device_name(0)
        logging.info(f"检测到GPU设备: {GPU_DEVICE_NAME} (共{GPU_DEVICE_COUNT}个)")
    else:
        logging.info("未检测到GPU设备，将使用CPU推理")

except ImportError:
    TRACKING_AVAILABLE = False
    GPU_AVAILABLE = False
    logging.warning("追踪依赖未安装，将使用模拟模式")
except Exception as e:
    TRACKING_AVAILABLE = False
    GPU_AVAILABLE = False
    logging.warning(f"GPU检测失败: {e}，将使用CPU推理")

OCR_SERVICE_URL = "http://localhost:8000"

logger = logging.getLogger(__name__)

def safe_set_camera_parameter(camera, prop_id, value, param_name=""):
    try:
        if camera is None or not camera.isOpened():
            logger.warning(f"摄像头未打开，无法设置{param_name}")
            return None

        current_value = camera.get(prop_id)
        if current_value is None:
            logger.warning(f"无法获取摄像头{param_name}当前值")
            return None

        success = camera.set(prop_id, value)
        if success:
            new_value = camera.get(prop_id)
            logger.debug(f"摄像头{param_name}设置成功: {current_value} -> {new_value}")
            return new_value
        else:
            logger.warning(f"摄像头{param_name}设置失败，保持当前值: {current_value}")
            return current_value

    except Exception as e:
        error_msg = str(e)
        if "C++ exception" in error_msg or "Unknown C++ exception" in error_msg:
            logger.warning(f"设置摄像头{param_name}时检测到OpenCV C++异常，跳过此参数设置")
        else:
            logger.warning(f"设置摄像头{param_name}时出现异常: {e}")

        try:
            if camera and camera.isOpened():
                return camera.get(prop_id)
        except:
            pass
        return None

class ConveyorObjectTracker:

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.tracking_enabled = TRACKING_AVAILABLE and self.config.get('enabled', True)

        self.detector = None
        self.tracker = None
        self.camera = None

        self.mqtt_enabled = self.config.get('mqtt_enabled', True)
        self.mqtt_service = None
        self.mqtt_connected = False
        self.last_mqtt_publish_time = 0

        self.class_names = ['brick', 'arm']
        self.arm_detection_config = {
            'min_confidence': 0.5,
            'max_size_ratio': 0.8,
            'min_size_ratio': 0.1
        }

        self.is_running = False
        self.tracking_thread = None
        self.frame_count = 0
        self.tracked_objects = {}
        self.ocr_processing = {}
        self.current_frame = None
        self.frame_encoding_quality = self.config.get('frame_quality', 30)

        self.camera_health = {
            'last_successful_frame_time': time.time(),
            'total_frame_read_errors': 0,
            'total_camera_restarts': 0,
            'consecutive_failures': 0,
            'health_score': 100.0,
            'last_health_check': time.time(),
            'camera_backend': 'unknown',
            'camera_resolution': 'unknown'
        }

        self.frame_buffer = []
        self.max_buffer_size = 5
        self.last_frame_sent = 0
        self.frame_send_interval = 1
        self.last_frame_time = time.time()
        self.target_fps = 30

        self.conveyor_speed = self.config.get('conveyor_speed', 0.1)
        self.conveyor_width = self.config.get('conveyor_width', 0.6)
        self.conveyor_height = self.config.get('conveyor_height', 0.2)

        self.ocr_trigger_x = self.config.get('ocr_trigger_x', 0.3)
        self.ocr_trigger_width = self.config.get('ocr_trigger_width', 0.1)
        self.ocr_processing_timeout = self.config.get('ocr_timeout', 5.0)

        self.camera_matrix = None
        self.dist_coeffs = None
        self.perspective_matrix = None

        self.image_to_conveyor_scale = self.config.get('image_scale', 0.001)

        self.fps = 0
        self.processing_time = 0
        self.detection_count = 0
        self.ocr_requests = 0
        self.ocr_success = 0

        self.callbacks = {
            'on_object_detected': [],
            'on_object_lost': [],
            'on_frame_processed': [],
            'on_ocr_triggered': [],
            'on_ocr_result': [],
            'on_conveyor_status': []
        }

        if self.mqtt_enabled:
            self._initialize_mqtt_service()

        if self.tracking_enabled:
            self._initialize_tracker()

    def _initialize_tracker(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))

            model_path = self.config.get('yolo_model', os.path.join(current_dir, '..', 'model', 'best.pt'))
            model_path = os.path.abspath(model_path)

            logger.info(f"尝试加载模型文件: {model_path}")

            if os.path.exists(model_path):
                logger.info(f"找到模型文件: {model_path}, 文件大小: {os.path.getsize(model_path)} 字节")

                if GPU_AVAILABLE:
                    device = 'cuda:0'
                    logger.info(f"使用GPU设备进行推理: {device}")
                else:
                    device = 'cpu'
                    logger.info("使用CPU设备进行推理")

                try:
                    logger.info("开始加载YOLO模型...")
                    self.detector = YOLO(model_path)
                    logger.info("YOLO模型加载成功")

                    if hasattr(self.detector, 'to'):
                        self.detector = self.detector.to(device)
                        logger.info(f"模型已成功加载到设备: {device}")
                    else:
                        logger.warning("模型不支持设备切换，使用默认设备")

                    logger.info("测试模型推理...")
                    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    test_results = self.detector(test_frame, verbose=False)
                    logger.info("模型推理测试成功")

                except Exception as e:
                    logger.error(f"YOLO模型加载失败: {e}", exc_info=True)
                    self.tracking_enabled = False
                    logger.info("追踪功能不可用，将使用模拟模式")
                    return

            else:
                logger.warning(f"模型文件不存在: {model_path}")
                logger.info("检查模型目录内容:")
                model_dir = os.path.dirname(model_path)
                if os.path.exists(model_dir):
                    for file in os.listdir(model_dir):
                        logger.info(f"  模型目录文件: {file}")
                self.tracking_enabled = False
                logger.info("追踪功能不可用，将使用模拟模式")
                return

            try:
                logger.info("初始化DeepSORT追踪器...")

                deepsort_config = {
                    'max_age': self.config.get('max_age', 20),
                    'n_init': self.config.get('n_init', 2),
                    'nn_budget': self.config.get('nn_budget', 50),
                    'max_cosine_distance': 0.3,
                    'max_iou_distance': 0.8,
                }

                if GPU_AVAILABLE:
                    try:
                        self.tracker = DeepSort(**deepsort_config)
                        logger.info("DeepSORT追踪器初始化成功（GPU模式）")
                    except Exception as gpu_error:
                        logger.warning(f"GPU模式初始化失败，回退到CPU: {gpu_error}")
                        self.tracker = DeepSort(**deepsort_config)
                        logger.info("DeepSORT追踪器初始化成功（CPU模式）")
                else:
                    self.tracker = DeepSort(**deepsort_config)
                    logger.info("DeepSORT追踪器初始化成功（CPU模式）")

            except Exception as e:
                logger.error(f"DeepSORT追踪器初始化失败: {e}", exc_info=True)
                self.tracking_enabled = False
                logger.info("追踪功能不可用，将使用模拟模式")
                return

            logger.info("追踪器初始化成功 - YOLO + DeepSORT 已就绪")

        except Exception as e:
            logger.error(f"追踪器初始化失败: {e}", exc_info=True)
            self.tracking_enabled = False
            logger.info("追踪功能不可用，将使用模拟模式")

    def _initialize_mqtt_service(self):
        try:
            if not self.mqtt_enabled:
                return

            self.mqtt_service = get_mqtt_service()
            if self.mqtt_service:
                if self.mqtt_service.connect():
                    self.mqtt_connected = True
                    logger.info("MQTT服务初始化成功")
                else:
                    logger.warning("MQTT服务连接失败，将继续使用WebSocket通信")
                    self.mqtt_connected = False
            else:
                logger.warning("无法获取MQTT服务实例，将继续使用WebSocket通信")
                self.mqtt_connected = False

        except Exception as e:
            logger.error(f"MQTT服务初始化失败: {e}，将继续使用WebSocket通信")
            self.mqtt_connected = False

    def load_camera_calibration(self, calib_file: str):
        try:
            if os.path.exists(calib_file):
                calib_data = np.load(calib_file)
                self.camera_matrix = calib_data['camera_matrix']
                self.dist_coeffs = calib_data['dist_coeffs']
                if 'transform_matrix' in calib_data:
                    self.perspective_matrix = calib_data['transform_matrix']
                logger.info(f"相机标定参数加载成功: {calib_file}")
                return True
            else:
                logger.warning(f"标定文件不存在: {calib_file}")
                return False
        except Exception as e:
            logger.error(f"加载相机标定参数失败: {e}")
            return False

    def _initialize_camera_windows(self, camera_source: int = 0) -> bool:
        try:
            logger.info("使用Windows专用摄像头初始化方案")

            windows_backends = [
                (cv2.CAP_MSMF, "MediaFoundation"),
                (cv2.CAP_DSHOW, "DirectShow"),
                (cv2.CAP_ANY, "Any"),
            ]

            if self.camera:
                try:
                    self.camera.release()
                    self.camera = None
                    time.sleep(1.0)
                except Exception as e:
                    logger.warning(f"释放现有摄像头资源时出错: {e}")
                    self.camera = None

            for backend, backend_name in windows_backends:
                try:
                    logger.info(f"尝试Windows摄像头初始化: 源={camera_source}, 后端={backend_name}")

                    if backend == -1:
                        self.camera = cv2.VideoCapture(camera_source)
                    else:
                        self.camera = cv2.VideoCapture(camera_source, backend)

                    if not self.camera or not self.camera.isOpened():
                        logger.warning(f"摄像头打开失败: 源={camera_source}, 后端={backend_name}")
                        if self.camera:
                            try:
                                self.camera.release()
                            except:
                                pass
                            self.camera = None
                        continue

                    try:
                        time.sleep(0.5)

                        ret, test_frame = self.camera.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            logger.info(f"Windows摄像头初始化成功: 源={camera_source}, 后端={backend_name}")

                            self.camera_health['camera_backend'] = backend_name

                            self._safe_set_camera_parameters()

                            return True
                        else:
                            logger.warning(f"摄像头打开但无法读取有效帧: 源={camera_source}, 后端={backend_name}")
                            self._safe_camera_release()
                            continue

                    except Exception as frame_error:
                        error_msg = str(frame_error)
                        if "C++ exception" in error_msg or "Unknown C++ exception" in error_msg:
                            logger.warning(f"检测到OpenCV C++异常，跳过此后端: {backend_name}")
                        else:
                            logger.warning(f"摄像头帧读取验证失败: {frame_error}")

                        self._safe_camera_release()
                        continue

                except Exception as e:
                    error_msg = str(e)
                    if "C++ exception" in error_msg or "Unknown C++ exception" in error_msg:
                        logger.warning(f"检测到OpenCV C++异常，跳过此后端: {backend_name}")
                    else:
                        logger.warning(f"Windows摄像头后端 {backend_name} 初始化失败: {e}")

                    self._safe_camera_release()
                    continue

            logger.error("Windows摄像头初始化失败 - 所有后端尝试均失败")
            return False

        except Exception as e:
            logger.error(f"Windows摄像头初始化过程中出现严重错误: {e}")
            return False

    def start_tracking(self, camera_source: int = 0):
        if self.is_running:
            logger.warning("追踪已在运行，跳过重复启动")
            return True

        if not self.tracking_enabled:
            logger.warning("追踪功能不可用，启动模拟模式")
            self._start_simulation()
            return True

        try:
            if isinstance(camera_source, dict):
                logger.warning(f"摄像头源参数类型错误: {type(camera_source)}，使用默认值0")
                camera_source = 0
            elif not isinstance(camera_source, (int, float)):
                logger.warning(f"摄像头源参数类型异常: {type(camera_source)}，转换为整数")
                try:
                    camera_source = int(camera_source)
                except (ValueError, TypeError):
                    camera_source = 0

            camera_source = int(camera_source)

            if not self._initialize_camera_windows(camera_source):
                logger.warning("Windows摄像头初始化失败，启动模拟模式")
                self._start_simulation()
                return True

            self.is_running = True
            self.tracking_thread = threading.Thread(target=self._tracking_loop, name="TrackingThread")
            self.tracking_thread.daemon = True
            self.tracking_thread.start()

            logger.info(f"追踪服务启动成功，摄像头源: {camera_source}")
            return True

        except Exception as e:
            logger.error(f"启动追踪失败: {e}", exc_info=True)
            logger.info("启动模拟模式作为备用")
            self._start_simulation()
            return True

            try:
                logger.debug("使用安全函数设置摄像头参数...")

                width = safe_set_camera_parameter(self.camera, cv2.CAP_PROP_FRAME_WIDTH, 640, "宽度")
                height = safe_set_camera_parameter(self.camera, cv2.CAP_PROP_FRAME_HEIGHT, 480, "高度")
                fps = safe_set_camera_parameter(self.camera, cv2.CAP_PROP_FPS, 15, "FPS")

                if width is not None and height is not None:
                    logger.info(f"摄像头参数设置完成: 宽度={width}, 高度={height}, FPS={fps if fps is not None else '未知'}")
                else:
                    logger.warning("摄像头参数设置部分失败，但继续使用默认参数运行")

            except Exception as e:
                logger.warning(f"设置摄像头参数时出现异常: {e}，但继续使用默认参数运行")

            if self.tracking_thread and self.tracking_thread.is_alive():
                logger.warning("检测到之前的追踪线程仍在运行，等待其结束...")
                self.tracking_thread.join(timeout=2)
                if self.tracking_thread.is_alive():
                    logger.error("无法停止之前的追踪线程，可能导致冲突")
                    return False

            self.is_running = True
            self.tracking_thread = threading.Thread(target=self._tracking_loop, name="TrackingThread")
            self.tracking_thread.daemon = True
            self.tracking_thread.start()

            logger.info(f"追踪服务启动成功，摄像头源: {camera_source}")
            return True

        except Exception as e:
            logger.error(f"启动追踪失败: {e}", exc_info=True)
            logger.info("启动模拟模式作为备用")
            self._start_simulation()
            return True

    def stop_tracking(self):
        try:
            logger.info("开始停止追踪服务...")

            self.is_running = False

            if self.tracking_thread and self.tracking_thread.is_alive():
                logger.info("等待追踪线程结束...")
                self.tracking_thread.join(timeout=5)
                if self.tracking_thread.is_alive():
                    logger.warning("追踪线程未在超时时间内结束，将继续清理资源")

            if self.camera:
                try:
                    logger.debug("开始释放摄像头资源...")
                    self.camera.release()
                    logger.debug("摄像头资源已释放")
                except Exception as camera_error:
                    error_msg = str(camera_error)
                    if "C++ exception" in error_msg or "Unknown C++ exception" in error_msg:
                        logger.warning("检测到OpenCV C++异常，跳过摄像头释放")
                    else:
                        logger.warning(f"释放摄像头资源时出现异常: {camera_error}")
                finally:
                    self.camera = None
                    logger.debug("摄像头引用已置空")

            if self.mqtt_service and self.mqtt_connected:
                try:
                    logger.debug("开始断开MQTT连接...")
                    self.mqtt_service.disconnect()
                    logger.debug("MQTT连接已断开")
                except Exception as mqtt_error:
                    logger.warning(f"断开MQTT连接时出现异常: {mqtt_error}")
                finally:
                    self.mqtt_connected = False

            try:
                logger.debug("开始清理帧缓冲和追踪数据...")
                self.frame_buffer.clear()
                self.current_frame = None
                self.tracked_objects.clear()
                self.ocr_processing.clear()
                logger.debug("帧缓冲和追踪数据已清理")
            except Exception as buffer_error:
                logger.warning(f"清理帧缓冲和追踪数据时出现异常: {buffer_error}")

            try:
                self.frame_count = 0
                self.fps = 0
                self.processing_time = 0
                self.detection_count = 0
                logger.debug("性能统计已重置")
            except Exception as stats_error:
                logger.warning(f"重置性能统计时出现异常: {stats_error}")

            self.tracking_thread = None

            logger.info("追踪服务已安全停止")

        except Exception as e:
            logger.error(f"停止追踪服务时出现严重错误: {e}")
            try:
                if self.camera:
                    try:
                        self.camera.release()
                    except:
                        pass
                    self.camera = None
            except:
                pass

            try:
                self.tracking_thread = None
            except:
                pass

            logger.error("追踪服务已强制停止，可能存在资源泄漏")

    def _tracking_loop(self):
        fps_start_time = time.time()
        fps_frame_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 10
        no_successful_frames_count = 0
        max_no_successful_frames = 20
        last_camera_restart_time = 0
        min_restart_interval = 10.0

        logger.info("追踪循环开始运行 - 增强稳定性模式")

        while self.is_running:
            try:
                if not self.camera or not self.camera.isOpened():
                    current_time = time.time()
                    if current_time - last_camera_restart_time < min_restart_interval:
                        logger.warning(f"摄像头重启过于频繁，等待 {min_restart_interval - (current_time - last_camera_restart_time):.1f} 秒")
                        time.sleep(min_restart_interval - (current_time - last_camera_restart_time))

                    logger.error("摄像头已关闭，尝试重新打开...")
                    if self._restart_camera():
                        logger.info("摄像头重新打开成功")
                        consecutive_errors = 0
                        no_successful_frames_count = 0
                        last_camera_restart_time = time.time()
                        time.sleep(2)
                        continue
                    else:
                        logger.error("无法重新打开摄像头，切换到模拟模式")
                        self._switch_to_simulation()
                        return

                frame = None
                ret = False

                for retry_count in range(3):
                    try:
                        ret, frame = self.camera.read()
                        if ret and frame is not None and frame.size > 0:
                            consecutive_errors = 0
                            no_successful_frames_count = 0

                            self.camera_health['last_successful_frame_time'] = time.time()
                            self.camera_health['consecutive_failures'] = 0

                            break
                        else:
                            logger.warning(f"第{retry_count+1}次读取摄像头帧失败")
                            if retry_count < 2:
                                time.sleep(0.2)
                            continue
                    except Exception as read_error:
                        error_msg = str(read_error)
                        if "C++ exception" in error_msg or "Unknown C++ exception" in error_msg:
                            logger.warning(f"检测到OpenCV C++异常，立即释放摄像头资源")
                            self._safe_camera_release()
                            break
                        else:
                            logger.warning(f"第{retry_count+1}次读取摄像头帧异常: {read_error}")
                        if retry_count < 2:
                            time.sleep(0.2)
                        continue

                if not ret or frame is None or frame.size == 0:
                    consecutive_errors += 1
                    no_successful_frames_count += 1

                    self.camera_health['total_frame_read_errors'] += 1
                    self.camera_health['consecutive_failures'] = consecutive_errors

                    logger.warning(f"连续读取摄像头帧失败 (连续错误: {consecutive_errors}, 无成功帧: {no_successful_frames_count})")

                    if no_successful_frames_count >= max_no_successful_frames:
                        logger.error(f"连续 {no_successful_frames_count} 帧无成功读取，强制重启摄像头")
                        if self._restart_camera():
                            no_successful_frames_count = 0
                            consecutive_errors = 0
                            last_camera_restart_time = time.time()
                            continue
                        else:
                            logger.error("摄像头重启失败，切换到模拟模式")
                            self._switch_to_simulation()
                            return

                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("连续读取摄像头帧失败过多，切换到模拟模式")
                        self._switch_to_simulation()
                        return

                    time.sleep(0.5)
                    continue

                try:
                    start_time = time.time()

                    result = self._process_frame(frame)

                    self._update_frame_buffer(frame, result)

                    self.processing_time = (time.time() - start_time) * 1000
                    fps_frame_count += 1

                    if time.time() - fps_start_time >= 1.0:
                        self.fps = fps_frame_count / (time.time() - fps_start_time)
                        fps_frame_count = 0
                        fps_start_time = time.time()
                        logger.debug(f"追踪性能: FPS={self.fps:.1f}, 处理时间={self.processing_time:.1f}ms")

                    self._trigger_callback('on_frame_processed', result)

                    if self.mqtt_enabled and self.mqtt_connected:
                        self._publish_via_mqtt(frame, result)

                except Exception as process_error:
                    logger.error(f"帧处理过程中出现错误: {process_error}")
                    continue

            except Exception as e:
                error_msg = str(e)
                if "Unknown C++ exception" in error_msg or "C++ exception" in error_msg:
                    logger.warning(f"摄像头帧读取时检测到OpenCV C++异常，尝试恢复...")
                    self._safe_camera_release()

                    time.sleep(3.0)

                    current_time = time.time()
                    if current_time - last_camera_restart_time >= min_restart_interval:
                        if self._restart_camera():
                            logger.info("摄像头从OpenCV C++异常中恢复成功")
                            consecutive_errors = 0
                            no_successful_frames_count = 0
                            last_camera_restart_time = time.time()
                            continue
                        else:
                            logger.error("摄像头从OpenCV C++异常中恢复失败")
                            consecutive_errors += 1
                    else:
                        logger.warning("摄像头重启间隔过短，跳过此次重启")
                        consecutive_errors += 1
                else:
                    consecutive_errors += 1
                    logger.error(f"摄像头帧读取异常: {e} (连续错误: {consecutive_errors})")

                if consecutive_errors >= max_consecutive_errors:
                    logger.error("连续帧读取错误过多，切换到模拟模式")
                    self._switch_to_simulation()
                    return

                time.sleep(1.0)
                continue

        logger.info("追踪循环正常结束")

    def _process_frame(self, frame: np.ndarray) -> Dict:
        self.frame_count += 1

        detections = self._detect_objects(frame)

        tracked_objects = self._track_objects(frame, detections)

        conveyor_objects = self._transform_to_conveyor_coords(tracked_objects)

        self._update_tracking_history(conveyor_objects)

        result = {
            'frame_id': self.frame_count,
            'timestamp': datetime.now().isoformat(),
            'detections': len(conveyor_objects),
            'tracked_objects': conveyor_objects,
            'fps': self.fps,
            'processing_time': self.processing_time,
            'has_frame': self.current_frame is not None,
            'detection_mode': 'continuous'
        }

        self._update_frame_buffer(frame, result)

        logger.debug(f"追踪更新 - 检测: {len(detections)}, 追踪: {len(conveyor_objects)}")

        return result

    def _detect_objects(self, frame: np.ndarray) -> List:
        try:
            if self.detector is None:
                logger.error("YOLO检测器未初始化")
                return []

            device = 'cuda:0' if GPU_AVAILABLE else 'cpu'

            logger.debug(f"开始YOLO检测 - 帧ID: {self.frame_count}, 设备: {device}")

            brick_conf_threshold = self.config.get('brick_conf_threshold', 0.6)
            arm_conf_threshold = self.config.get('arm_conf_threshold', 0.5)

            results = self.detector(frame,
                                  conf=min(brick_conf_threshold, arm_conf_threshold),
                                  device=device,
                                  verbose=False,
                                  half=GPU_AVAILABLE)

            detections = []
            for r in results:
                boxes = r.boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())

                        if class_id == 0:  # brick
                            if confidence < brick_conf_threshold:
                                continue
                        elif class_id == 1:  # arm
                            if confidence < arm_conf_threshold:
                                continue
                        else:
                            if confidence < 0.6:
                                continue

                        w = x2 - x1
                        h = y2 - y1
                        x = x1 + w / 2
                        y = y1 + h / 2

                        detections.append([[x1, y1, w, h], confidence, class_id])

                        logger.debug(f"检测到物体 - 类别: {self.class_names[class_id]}, 置信度: {confidence:.2f}, 位置: ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})")

            brick_count = sum(1 for det in detections if det[2] == 0)
            arm_count = sum(1 for det in detections if det[2] == 1)

            self.detection_count += len(detections)
            logger.info(f"YOLO检测完成 - 砖块: {brick_count}, 机械臂: {arm_count}, 总计: {len(detections)} 个物体")
            return detections

        except Exception as e:
            logger.error(f"物体检测失败: {e}", exc_info=True)
            return []

    def _track_objects(self, frame: np.ndarray, detections: List) -> List[Dict]:
        try:
            deepsort_detections = []
            for detection in detections:
                bbox, confidence, class_id = detection

                x1, y1, w, h = bbox
                x1 = float(x1)
                y1 = float(y1)
                w = float(w)
                h = float(h)
                confidence = float(confidence)
                class_id = int(class_id)

                deepsort_detections.append(([x1, y1, w, h], confidence, class_id))

            logger.debug(f"DeepSORT输入: {len(deepsort_detections)} 个检测")

            tracks = self.tracker.update_tracks(deepsort_detections, frame=frame)

            tracked_objects = []
            for track in tracks:
                if not track.is_confirmed():
                    continue

                track_id = track.track_id
                bbox = track.to_ltrb()  # [x1, y1, x2, y2]

                bbox = [float(x) for x in bbox]
                center_x = (bbox[0] + bbox[2]) / 2
                center_y = (bbox[1] + bbox[3]) / 2

                class_id = 0
                class_name = 'brick'

                if hasattr(track, 'det_class') and track.det_class is not None:
                    class_id = int(track.det_class)
                    if class_id < len(self.class_names):
                        class_name = self.class_names[class_id]
                    else:
                        class_name = 'unknown'
                else:
                    best_match_distance = float('inf')
                    best_match_class_id = 0

                    for detection in detections:
                        det_bbox, det_confidence, det_class_id = detection
                        det_x1, det_y1, det_w, det_h = det_bbox
                        det_center_x = det_x1 + det_w / 2
                        det_center_y = det_y1 + det_h / 2

                        distance = abs(det_center_x - center_x) + abs(det_center_y - center_y)

                        if distance < best_match_distance and distance < 50:
                            best_match_distance = distance
                            best_match_class_id = det_class_id

                    if best_match_distance < float('inf'):
                        class_id = best_match_class_id
                        if class_id < len(self.class_names):
                            class_name = self.class_names[class_id]

                if hasattr(track, 'det_conf') and track.det_conf is not None:
                    confidence = float(track.det_conf)
                else:
                    confidence = 0.8

                tracked_objects.append({
                    'track_id': int(track_id),
                    'bbox': bbox,
                    'center': [float(center_x), float(center_y)],
                    'class_id': class_id,
                    'class_name': class_name,
                    'confidence': confidence
                })

            brick_tracks = sum(1 for obj in tracked_objects if obj['class_name'] == 'brick')
            arm_tracks = sum(1 for obj in tracked_objects if obj['class_name'] == 'arm')

            logger.debug(f"DeepSORT追踪结果: 砖块 {brick_tracks}, 机械臂 {arm_tracks}, 总计 {len(tracked_objects)} 个物体")
            return tracked_objects

        except Exception as e:
            logger.error(f"物体追踪失败: {e}", exc_info=True)
            return []

    def _transform_to_conveyor_coords(self, tracked_objects: List[Dict]) -> List[Dict]:
        conveyor_objects = []

        for obj in tracked_objects:
            img_x, img_y = obj['center']
            bbox = obj['bbox']

            if self.perspective_matrix is not None:
                point = np.array([[img_x, img_y]], dtype=np.float32)
                transformed = cv2.perspectiveTransform(point.reshape(-1, 1, 2),
                                                     self.perspective_matrix)
                conveyor_x, conveyor_y = transformed[0][0]
            else:
                conveyor_x = img_x * self.conveyor_width / 640
                conveyor_y = img_y * self.conveyor_height / 480

            velocity = self._calculate_velocity(obj['track_id'], conveyor_x, conveyor_y)

            conveyor_objects.append({
                'track_id': obj['track_id'],
                'conveyor_x': float(conveyor_x),
                'conveyor_y': float(conveyor_y),
                'bbox': obj['bbox'],
                'class_id': obj['class_id'],
                'class_name': obj['class_name'],
                'confidence': obj['confidence'],
                'velocity': float(velocity),
                'timestamp': time.time()
            })

        return conveyor_objects

    def _calculate_velocity(self, track_id: int, current_x: float, current_y: float) -> float:
        if track_id not in self.tracked_objects:
            return 0.0

        prev_data = self.tracked_objects[track_id]
        dt = time.time() - prev_data['timestamp']

        if dt > 0:
            dx = current_x - prev_data['conveyor_x']
            velocity = dx / dt
            return velocity

        return 0.0

    def _update_tracking_history(self, conveyor_objects: List[Dict]):
        for obj in conveyor_objects:
            track_id = obj['track_id']
            prev_obj = self.tracked_objects.get(track_id)

            if prev_obj is None:
                obj['first_detected_frame'] = self.frame_count
                obj['first_detected_time'] = time.time()
                logger.info(f"新物体追踪开始 - ID: {track_id}, 类别: {obj['class_name']}")

                self._trigger_callback('on_object_detected', obj)
            else:
                obj['first_detected_frame'] = prev_obj.get('first_detected_frame', self.frame_count)
                obj['first_detected_time'] = prev_obj.get('first_detected_time', time.time())

            self.tracked_objects[track_id] = obj

            self._check_ocr_trigger(obj, prev_obj)

        current_ids = {obj['track_id'] for obj in conveyor_objects}
        lost_ids = set(self.tracked_objects.keys()) - current_ids

        for track_id in lost_ids:
            lost_obj = self.tracked_objects.pop(track_id)
            self._trigger_callback('on_object_lost', lost_obj)

    def get_current_objects(self) -> List[Dict]:
        return list(self.tracked_objects.values())

    def get_camera_health_status(self) -> Dict:
        current_time = time.time()

        time_since_last_success = current_time - self.camera_health['last_successful_frame_time']

        health_score = 100.0

        if self.camera_health['consecutive_failures'] > 0:
            health_score -= min(self.camera_health['consecutive_failures'] * 5, 50)

        if time_since_last_success > 10:
            health_score -= min((time_since_last_success - 10) * 2, 30)

        if self.camera_health['total_camera_restarts'] > 0:
            health_score -= min(self.camera_health['total_camera_restarts'] * 3, 20)

        health_score = max(0, health_score)

        self.camera_health['health_score'] = health_score
        self.camera_health['last_health_check'] = current_time

        return {
            'health_score': round(health_score, 1),
            'status': self._get_health_status(health_score),
            'last_successful_frame_time': self.camera_health['last_successful_frame_time'],
            'time_since_last_success': round(time_since_last_success, 1),
            'total_frame_read_errors': self.camera_health['total_frame_read_errors'],
            'total_camera_restarts': self.camera_health['total_camera_restarts'],
            'consecutive_failures': self.camera_health['consecutive_failures'],
            'camera_backend': self.camera_health['camera_backend'],
            'camera_resolution': self.camera_health['camera_resolution'],
            'is_camera_available': self.camera is not None and self.camera.isOpened(),
            'current_fps': self.fps
        }

    def _get_health_status(self, health_score: float) -> str:
        if health_score >= 80:
            return "健康"
        elif health_score >= 60:
            return "一般"
        elif health_score >= 40:
            return "警告"
        elif health_score >= 20:
            return "较差"
        else:
            return "严重"

    def get_tracking_stats(self) -> Dict:
        gpu_info = {
            'gpu_available': GPU_AVAILABLE,
            'gpu_device_name': GPU_DEVICE_NAME if GPU_AVAILABLE else None,
            'gpu_device_count': GPU_DEVICE_COUNT if GPU_AVAILABLE else 0
        }

        if self.frame_count > 0:
            full_detection_ratio = (self.frame_count // 3) / self.frame_count
            prediction_ratio = ((self.frame_count - self.frame_count // 3)) / self.frame_count
            detection_mode = {
                'full_detection_ratio': round(full_detection_ratio, 2),
                'prediction_ratio': round(prediction_ratio, 2),
                'current_mode': 'full' if self.frame_count % 3 == 0 else 'prediction',
                'full_detections': self.frame_count // 3,
                'predictions': self.frame_count - self.frame_count // 3
            }
        else:
            detection_mode = {
                'full_detection_ratio': 0,
                'prediction_ratio': 0,
                'current_mode': 'unknown',
                'full_detections': 0,
                'predictions': 0
            }

        return {
            'fps': self.fps,
            'processing_time': self.processing_time,
            'frame_count': self.frame_count,
            'detection_count': self.detection_count,
            'active_tracks': len(self.tracked_objects),
            'is_running': self.is_running,
            'tracking_enabled': self.tracking_enabled,
            'detection_mode': detection_mode,
            'gpu_info': gpu_info
        }

    def _check_ocr_trigger(self, current_obj: Dict, prev_obj: Optional[Dict]):
        if prev_obj is None:
            return

        current_x = current_obj['conveyor_x']
        prev_x = prev_obj['conveyor_x']

        trigger_start = self.ocr_trigger_x - self.ocr_trigger_width / 2
        trigger_end = self.ocr_trigger_x + self.ocr_trigger_width / 2

        if (prev_x < trigger_start and
            trigger_start <= current_x <= trigger_end and
            current_obj['track_id'] not in self.ocr_processing):

            self._trigger_ocr_processing(current_obj)

    def _trigger_ocr_processing(self, obj: Dict):
        track_id = obj['track_id']

        self.ocr_processing[track_id] = {
            'trigger_time': time.time(),
            'status': 'pending',
            'object_data': obj
        }

        ocr_thread = threading.Thread(
            target=self._process_ocr_request,
            args=(track_id, obj)
        )
        ocr_thread.daemon = True
        ocr_thread.start()

        self.ocr_requests += 1

        self._trigger_callback('on_ocr_triggered', {
            'track_id': track_id,
            'object_data': obj,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"OCR触发: 物体 {track_id} 进入识别区域")

    def _process_ocr_request(self, track_id: int, obj: Dict):
        try:
            image_data = self._extract_object_image(obj)

            if image_data is None:
                logger.warning(f"无法提取物体 {track_id} 的图像")
                self.ocr_processing[track_id]['status'] = 'failed'
                return

            ocr_result = self._call_ocr_service(image_data)

            self._handle_ocr_result(track_id, ocr_result)

        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            self.ocr_processing[track_id]['status'] = 'failed'

    def _extract_object_image(self, obj: Dict) -> Optional[bytes]:
        return None

    def _call_ocr_service(self, image_data: bytes) -> Dict:
        try:
            files = {'file': ('object.jpg', image_data, 'image/jpeg')}

            response = requests.post(
                f"{OCR_SERVICE_URL}/api/energy/detect",
                files=files,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"OCR服务返回错误: {response.status_code}")
                return {'code': response.status_code, 'message': f'OCR服务错误: {response.status_code}', 'data': None}

        except requests.exceptions.RequestException as e:
            logger.error(f"OCR服务请求失败: {e}")
            return {'code': 503, 'message': f'OCR服务连接失败: {str(e)}', 'data': None}

    def _handle_ocr_result(self, track_id: int, ocr_result: Dict):
        try:
            processing_info = self.ocr_processing.get(track_id)
            if not processing_info:
                return

            if ocr_result.get('code') == 100:
                processing_info['status'] = 'success'
                processing_info['ocr_data'] = ocr_result
                self.ocr_success += 1

                energy_label = self._extract_energy_label(ocr_result)
                processing_info['energy_label'] = energy_label

                logger.info(f"OCR识别成功: 物体 {track_id} - {energy_label}")

            else:
                processing_info['status'] = 'failed'
                processing_info['error'] = ocr_result.get('message', '未知错误')
                logger.warning(f"OCR识别失败: 物体 {track_id} - {processing_info['error']}")

            self._trigger_callback('on_ocr_result', {
                'track_id': track_id,
                'object_data': processing_info['object_data'],
                'ocr_result': ocr_result,
                'energy_label': processing_info.get('energy_label'),
                'status': processing_info['status'],
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"处理OCR结果失败: {e}")

    def _extract_energy_label(self, ocr_result: Dict) -> Dict:
        energy_label = {
            'level': '未知',
            'confidence': 0.0,
            'text': '',
            'coordinates': []
        }

        try:
            energy_level = ocr_result.get('data', {}).get('energy_level')
            if energy_level:
                import re
                level_match = re.search(r'\d+', str(energy_level))
                if level_match:
                    energy_label['level'] = level_match.group() + '级'
                else:
                    energy_label['level'] = str(energy_level)

                energy_label['text'] = f"能效等级: {energy_level}"
                energy_label['confidence'] = 0.9
            else:
                data = ocr_result.get('data', {})
                if 'ocr_text' in data:
                    text = data['ocr_text'].strip().upper()
                    if any(keyword in text for keyword in ['能效', 'ENERGY', 'EFFICIENCY']):
                        energy_label['text'] = text
                        if '一级' in text or '1' in text:
                            energy_label['level'] = '一级'
                        elif '二级' in text or '2' in text:
                            energy_label['level'] = '二级'
                        elif '三级' in text or '3' in text:
                            energy_label['level'] = '三级'

        except Exception as e:
            logger.error(f"提取能效标签失败: {e}")

        return energy_label

    def get_current_frame_base64(self) -> Optional[str]:
        try:
            if self.current_frame is None:
                return None

            height, width = self.current_frame.shape[:2]
            max_size = 640
            if width > max_size or height > max_size:
                scale = max_size / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame_resized = cv2.resize(self.current_frame, (new_width, new_height))
            else:
                frame_resized = self.current_frame

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.frame_encoding_quality]
            _, buffer = cv2.imencode('.jpg', frame_resized, encode_param)

            image_base64 = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{image_base64}"

        except Exception as e:
            logger.error(f"视频帧编码失败: {e}")
            return None

    def get_smooth_frame_base64(self) -> Optional[str]:
        try:
            if self.current_frame is None:
                logger.debug("当前帧为空，使用默认帧")
                default_frame = self._create_default_frame()
                if default_frame is not None:
                    return self._encode_frame_to_base64(default_frame)
                return None

            if self.current_frame.size == 0:
                logger.warning("当前帧数据无效，使用默认帧")
                default_frame = self._create_default_frame()
                if default_frame is not None:
                    return self._encode_frame_to_base64(default_frame)
                return None

            frame_to_process = self.current_frame.copy()

            if self.tracked_objects:
                for obj in self.tracked_objects.values():
                    if 'bbox' in obj and obj['bbox']:
                        bbox = obj['bbox']
                        x1, y1, x2, y2 = map(int, bbox)
                    else:
                        img_x = int(obj['conveyor_x'] * 640 / 0.6)
                        img_y = int(obj['conveyor_y'] * 480 / 0.4)
                        box_size = 30
                        x1 = max(0, img_x - box_size)
                        y1 = max(0, img_y - box_size)
                        x2 = min(640, img_x + box_size)
                        y2 = min(480, img_y + box_size)

                    if obj['class_name'] == 'brick':
                        color = (0, 255, 0)
                    elif obj['class_name'] == 'arm':
                        color = (255, 0, 0)
                    else:
                        color = (255, 255, 0)

                    cv2.rectangle(frame_to_process, (x1, y1), (x2, y2), color, 2)

                    label = f"ID:{obj['track_id']} {obj['class_name']}"
                    cv2.putText(frame_to_process, label, (x1, y1-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    confidence_text = f"{obj['confidence']:.2f}"
                    cv2.putText(frame_to_process, confidence_text, (x1, y2+20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    cv2.circle(frame_to_process, (center_x, center_y), 4, color, -1)
            else:
                status_text = f"追踪状态: {'运行中' if self.is_running else '已停止'}"
                mode_text = f"模式: {'AI追踪' if self.tracking_enabled else '模拟'}"
                fps_text = f"FPS: {self.fps:.1f}"

                cv2.putText(frame_to_process, status_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame_to_process, mode_text, (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame_to_process, fps_text, (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            return self._encode_frame_to_base64(frame_to_process)

        except Exception as e:
            logger.error(f"平滑视频帧编码失败: {e}")
            try:
                default_frame = self._create_default_frame()
                if default_frame is not None:
                    return self._encode_frame_to_base64(default_frame)
            except Exception as default_error:
                logger.error(f"默认帧生成也失败: {default_error}")
            return None

    def _create_default_frame(self) -> Optional[np.ndarray]:
        try:
            default_frame = np.zeros((480, 640, 3), dtype=np.uint8)

            status_text = "视频流初始化中..."
            mode_text = f"追踪模式: {'AI' if self.tracking_enabled else '模拟'}"
            fps_text = f"FPS: {self.fps:.1f}"

            cv2.putText(default_frame, status_text, (50, 150),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(default_frame, mode_text, (50, 200),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(default_frame, fps_text, (50, 250),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            return default_frame

        except Exception as e:
            logger.error(f"创建默认帧失败: {e}")
            return None

    def _encode_frame_to_base64(self, frame: np.ndarray) -> Optional[str]:
        try:
            height, width = frame.shape[:2]

            target_width = 640
            target_height = 480
            if width != target_width or height != target_height:
                frame_resized = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
            else:
                frame_resized = frame

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            success, buffer = cv2.imencode('.jpg', frame_resized, encode_param)

            if success:
                image_base64 = base64.b64encode(buffer).decode('utf-8')
                return f"data:image/jpeg;base64,{image_base64}"
            else:
                logger.error("帧编码失败 - cv2.imencode返回失败")
                return None

        except Exception as e:
            logger.error(f"帧编码失败: {e}")
            return None

    def get_frame_with_detections(self) -> Optional[str]:
        try:
            if self.current_frame is None:
                return None

            frame_with_detections = self.current_frame.copy()

            for obj in self.tracked_objects.values():
                img_x = int(obj['conveyor_x'] * 640 / 0.6)
                img_y = int(obj['conveyor_y'] * 480 / 0.4)

                box_size = 30
                x1 = max(0, img_x - box_size)
                y1 = max(0, img_y - box_size)
                x2 = min(640, img_x + box_size)
                y2 = min(480, img_y + box_size)

                color = (0, 255, 0) if obj['class_name'] == 'brick' else (255, 0, 0)

                cv2.rectangle(frame_with_detections, (x1, y1), (x2, y2), color, 2)

                label = f"ID:{obj['track_id']} {obj['class_name']}"
                confidence_text = f"{obj['confidence']:.2f}"

                cv2.putText(frame_with_detections, label, (x1, y1-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                cv2.putText(frame_with_detections, confidence_text, (x1, y2+15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                cv2.circle(frame_with_detections, (img_x, img_y), 3, color, -1)

            height, width = frame_with_detections.shape[:2]
            max_size = 640
            if width > max_size or height > max_size:
                scale = max_size / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame_resized = cv2.resize(frame_with_detections, (new_width, new_height))
            else:
                frame_resized = frame_with_detections

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.frame_encoding_quality]
            _, buffer = cv2.imencode('.jpg', frame_resized, encode_param)

            image_base64 = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{image_base64}"

        except Exception as e:
            logger.error(f"检测帧编码失败: {e}")
            return None

    def get_ocr_status(self, track_id: int) -> Optional[Dict]:
        return self.ocr_processing.get(track_id)

    def get_all_ocr_status(self) -> Dict:
        return self.ocr_processing.copy()

    def add_callback(self, event: str, callback: callable):
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, data: any):
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    if hasattr(callback, '__call__'):
                        callback(data)
                except Exception as e:
                    logger.error(f"回调函数错误: {e}")

    def _start_simulation(self):
        self.is_running = True
        self.tracking_thread = threading.Thread(target=self._simulation_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        logger.info("模拟追踪模式已启动")

    def _simulation_loop(self):
        object_id = 1
        while self.is_running:
            try:
                if len(self.tracked_objects) < 3 and np.random.random() > 0.7:
                    class_id = np.random.randint(0, 2)
                    class_name = self.class_names[class_id]

                    new_obj = {
                        'track_id': object_id,
                        'conveyor_x': np.random.uniform(0, self.conveyor_width),
                        'conveyor_y': np.random.uniform(0, self.conveyor_height),
                        'bbox': [100, 100, 200, 200],
                        'class_id': class_id,
                        'class_name': class_name,
                        'confidence': 0.85,
                        'velocity': self.conveyor_speed,
                        'timestamp': time.time()
                    }
                    self.tracked_objects[object_id] = new_obj
                    object_id += 1
                    self._trigger_callback('on_object_detected', new_obj)

                for track_id, obj in list(self.tracked_objects.items()):
                    obj['conveyor_x'] += obj['velocity'] * 0.1
                    obj['timestamp'] = time.time()

                    if obj['conveyor_x'] > self.conveyor_width:
                        self.tracked_objects.pop(track_id)
                        self._trigger_callback('on_object_lost', obj)

                self.fps = 25.0 + np.random.uniform(-2, 2)
                self.processing_time = 35.0 + np.random.uniform(-5, 5)
                self.frame_count += 1

                result = {
                    'frame_id': self.frame_count,
                    'timestamp': datetime.now().isoformat(),
                    'detections': len(self.tracked_objects),
                    'tracked_objects': list(self.tracked_objects.values()),
                    'fps': self.fps,
                    'processing_time': self.processing_time
                }
                self._trigger_callback('on_frame_processed', result)

                time.sleep(0.04)  # 25 FPS

            except Exception as e:
                logger.error(f"模拟循环错误: {e}")
                time.sleep(0.1)

    def _merge_detections(self, new_detections: List, tracked_objects: List[Dict]) -> List:
        try:
            tracked_detections = []
            for obj in tracked_objects:
                img_x = obj['conveyor_x'] * 640 / 0.6
                img_y = obj['conveyor_y'] * 480 / 0.4

                bbox_size = 60
                detection = [
                    [img_x - bbox_size/2, img_y - bbox_size/2, bbox_size, bbox_size],  # [x, y, w, h]
                    obj['confidence'],
                    obj['class_id']
                ]
                tracked_detections.append(detection)

            all_detections = new_detections + tracked_detections

            filtered_detections = []
            for detection in all_detections:
                is_duplicate = False
                for existing in filtered_detections:
                    center_dist = abs(detection[0][0] - existing[0][0]) + abs(detection[0][1] - existing[0][1])
                    if center_dist < 50:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    filtered_detections.append(detection)

            return filtered_detections

        except Exception as e:
            logger.error(f"合并检测结果失败: {e}")
            return new_detections

    def _get_tracked_predictions(self, frame: np.ndarray) -> List:
        try:
            tracked_objects = self.get_current_objects()

            predictions = []
            for obj in tracked_objects:
                if hasattr(obj, 'bbox') and obj.bbox:
                    bbox = obj.bbox
                else:
                    img_x = obj['conveyor_x'] * 640 / 0.6
                    img_y = obj['conveyor_y'] * 480 / 0.4
                    bbox_size = 60
                    bbox = [img_x - bbox_size/2, img_y - bbox_size/2, bbox_size, bbox_size]

                detection = [
                    bbox,  # [x, y, w, h]
                    obj['confidence'],
                    obj['class_id']
                ]
                predictions.append(detection)

            return predictions

        except Exception as e:
            logger.error(f"获取追踪预测失败: {e}")
            return []

    def _safe_camera_release(self):
        try:
            if self.camera:
                logger.debug("开始安全释放摄像头资源...")

                try:
                    self.camera.release()
                    logger.debug("摄像头正常释放成功")
                except Exception as release_error:
                    error_msg = str(release_error)
                    if "C++ exception" in error_msg or "Unknown C++ exception" in error_msg:
                        logger.warning("检测到OpenCV C++异常，使用强制释放")
                        try:
                            import gc
                            gc.collect()
                            logger.debug("强制垃圾回收执行")
                        except:
                            pass
                    else:
                        logger.warning(f"摄像头释放异常: {release_error}")

                self.camera = None
                logger.debug("摄像头引用已置空")

                time.sleep(0.5)

        except Exception as e:
            logger.error(f"安全释放摄像头资源失败: {e}")
            self.camera = None

    def _restart_camera(self):
        try:
            self._safe_camera_release()

            time.sleep(2.0)

            camera_backends = [
                (0, cv2.CAP_DSHOW, "DirectShow"),
                (0, cv2.CAP_MSMF, "MediaFoundation"),  # Windows Media Foundation
                (0, cv2.CAP_ANY, "Any"),
            ]

            self.camera = None

            for source, backend, backend_name in camera_backends:
                try:
                    logger.info(f"尝试重新打开摄像头: 源={source}, 后端={backend_name}")

                    if backend == -1:
                        self.camera = cv2.VideoCapture(source)
                    else:
                        self.camera = cv2.VideoCapture(source, backend)

                    if self.camera and self.camera.isOpened():
                        try:
                            ret, test_frame = self.camera.read()
                            if ret and test_frame is not None and test_frame.size > 0:
                                logger.info(f"摄像头重新启动成功: 源={source}, 后端={backend_name}")

                                self._safe_set_camera_parameters()

                                return True
                            else:
                                logger.warning(f"摄像头打开但无法读取帧: 源={source}, 后端={backend_name}")
                                self._safe_camera_release()
                        except Exception as frame_error:
                            error_msg = str(frame_error)
                            if "C++ exception" in error_msg or "Unknown C++ exception" in error_msg:
                                logger.warning(f"检测到OpenCV C++异常，跳过此后端: {backend_name}")
                            else:
                                logger.warning(f"摄像头帧读取异常: {frame_error}")

                            self._safe_camera_release()
                    else:
                        logger.warning(f"摄像头打开失败: 源={source}, 后端={backend_name}")
                        self._safe_camera_release()

                except Exception as e:
                    error_msg = str(e)
                    if "C++ exception" in error_msg or "Unknown C++ exception" in error_msg:
                        logger.warning(f"检测到OpenCV C++异常，跳过此后端: {backend_name}")
                    else:
                        logger.warning(f"摄像头后端 {backend_name} 失败: {e}")

                    self._safe_camera_release()
                    continue

            logger.error("所有摄像头后端尝试均失败，无法重新启动摄像头")
            return False

        except Exception as e:
            logger.error(f"摄像头重启过程中出现严重错误: {e}")
            return False

    def _safe_set_camera_parameters(self):
        try:
            logger.debug("使用安全函数设置摄像头参数...")

            width = safe_set_camera_parameter(self.camera, cv2.CAP_PROP_FRAME_WIDTH, 640, "宽度")
            height = safe_set_camera_parameter(self.camera, cv2.CAP_PROP_FRAME_HEIGHT, 480, "高度")
            fps = safe_set_camera_parameter(self.camera, cv2.CAP_PROP_FPS, 15, "FPS")

            if width is not None and height is not None:
                logger.info(f"摄像头参数设置完成: 宽度={width}, 高度={height}, FPS={fps if fps is not None else '未知'}")
            else:
                logger.warning("摄像头参数设置部分失败，但继续使用默认参数运行")

        except Exception as e:
            logger.warning(f"设置摄像头参数时出现异常: {e}，但继续使用默认参数运行")

    def _switch_to_simulation(self):
        try:
            logger.info("切换到模拟追踪模式")

            self.is_running = False
            if self.tracking_thread:
                self.tracking_thread.join(timeout=2)

            if self.camera:
                self.camera.release()
                self.camera = None

            self._start_simulation()

        except Exception as e:
            logger.error(f"切换到模拟模式失败: {e}")

    def _update_frame_buffer(self, frame: np.ndarray, result: Dict):
        try:
            if frame is None or frame.size == 0:
                logger.warning("接收到无效帧，跳过缓冲更新")
                return

            logger.info(f"开始更新帧缓冲 - 帧ID: {self.frame_count}, 帧形状: {frame.shape}")

            frame_info = {
                'frame_id': self.frame_count,
                'timestamp': time.time(),
                'frame': frame.copy(),
                'result': result
            }

            self.frame_buffer.append(frame_info)
            logger.info(f"帧已添加到缓冲 - 当前缓冲大小: {len(self.frame_buffer)}")

            if len(self.frame_buffer) > self.max_buffer_size:
                removed_frame = self.frame_buffer.pop(0)
                logger.info(f"移除旧帧 - 帧ID: {removed_frame['frame_id']}")

            self.current_frame = frame.copy()
            logger.info(f"当前帧已更新 - 帧ID: {self.frame_count}, 帧形状: {self.current_frame.shape}")

            self._select_frame_for_display()

        except Exception as e:
            logger.error(f"更新帧缓冲失败: {e}", exc_info=True)
            if frame is not None and frame.size > 0:
                self.current_frame = frame.copy()
                logger.info(f"降级处理：直接使用当前帧 - 帧ID: {self.frame_count}")

    def _select_frame_for_display(self):
        try:
            if not self.frame_buffer:
                logger.warning("帧缓冲为空，无法选择显示帧")
                return

            current_time = time.time()
            time_since_last_frame = current_time - self.last_frame_time

            target_frame_interval = 1.0 / self.target_fps

            if time_since_last_frame >= target_frame_interval:
                latest_frame = self.frame_buffer[-1]
                self.current_frame = latest_frame['frame']
                self.last_frame_sent = latest_frame['frame_id']
                self.last_frame_time = current_time

                logger.debug(f"选择帧 {latest_frame['frame_id']} 用于显示 - 时间间隔: {time_since_last_frame:.3f}s")
            else:
                logger.debug(f"跳过帧，等待时间间隔 - 已过: {time_since_last_frame:.3f}s, 目标: {target_frame_interval:.3f}s")

        except Exception as e:
            logger.error(f"选择显示帧失败: {e}")
            if self.frame_buffer:
                self.current_frame = self.frame_buffer[-1]['frame']
                self.last_frame_time = time.time()
                logger.debug(f"降级处理：使用缓冲帧 {self.frame_buffer[-1]['frame_id']}")

    def _cleanup_old_frames(self):
        try:
            if len(self.frame_buffer) > 3:
                self.frame_buffer = self.frame_buffer[-3:]
        except Exception as e:
            logger.error(f"清理帧缓冲失败: {e}")

    def _should_trigger_yolo_detection(self, frame: np.ndarray) -> bool:
        try:
            if self.frame_count % 60 == 0:
                logger.debug(f"时间触发YOLO检测 - 帧ID: {self.frame_count}")
                return True

            if len(self.tracked_objects) == 0:
                logger.debug(f"追踪数量触发YOLO检测 - 当前追踪: {len(self.tracked_objects)}")
                return True

            if self.tracked_objects:
                avg_confidence = np.mean([obj['confidence'] for obj in self.tracked_objects.values()])
                if avg_confidence < 0.2:
                    logger.debug(f"追踪质量触发YOLO检测 - 平均置信度: {avg_confidence:.2f}")
                    return True

            if self._check_entrance_region():
                logger.debug(f"入口区域触发YOLO检测")
                return True

            quality_score = self._evaluate_tracking_quality()
            if quality_score < 0.3:
                logger.debug(f"质量评分触发YOLO检测 - 评分: {quality_score:.2f}")
                return True

            return False

        except Exception as e:
            logger.error(f"YOLO触发判断失败: {e}")
            return False

    def _filter_novel_detections(self, new_detections: List) -> List:
        try:
            novel_detections = []

            for detection in new_detections:
                bbox, confidence, class_id = detection
                x, y, w, h = bbox

                is_novel = True
                min_distance = float('inf')

                for tracked_obj in self.tracked_objects.values():
                    tracked_x = tracked_obj['conveyor_x'] * 640 / 0.6
                    tracked_y = tracked_obj['conveyor_y'] * 480 / 0.4

                    distance = np.sqrt((x - tracked_x)**2 + (y - tracked_y)**2)
                    min_distance = min(min_distance, distance)

                    if distance < 80:
                        is_novel = False
                        break

                if is_novel:
                    novel_detections.append(detection)
                    logger.debug(f"发现新物体 - 距离最近追踪: {min_distance:.1f}px")
                else:
                    logger.debug(f"过滤重复检测 - 距离: {min_distance:.1f}px")

            return novel_detections

        except Exception as e:
            logger.error(f"新物体过滤失败: {e}")
            return new_detections

    def _merge_novel_detections(self, novel_detections: List, tracked_objects: List[Dict]) -> List:
        try:
            all_detections = []

            for obj in tracked_objects:
                img_x = obj['conveyor_x'] * 640 / 0.6
                img_y = obj['conveyor_y'] * 480 / 0.4
                bbox_size = 60
                bbox = [img_x - bbox_size/2, img_y - bbox_size/2, bbox_size, bbox_size]

                detection = [bbox, obj['confidence'], obj['class_id']]
                all_detections.append(detection)

            for detection in novel_detections:
                all_detections.append(detection)

            logger.debug(f"合并检测 - 现有追踪: {len(tracked_objects)}, 新物体: {len(novel_detections)}")
            return all_detections

        except Exception as e:
            logger.error(f"合并新检测失败: {e}")
            return novel_detections + self._get_tracked_predictions_from_objects(tracked_objects)

    def _get_tracked_predictions_from_objects(self, tracked_objects: List[Dict]) -> List:
        predictions = []
        for obj in tracked_objects:
            img_x = obj['conveyor_x'] * 640 / 0.6
            img_y = obj['conveyor_y'] * 480 / 0.4
            bbox_size = 60
            bbox = [img_x - bbox_size/2, img_y - bbox_size/2, bbox_size, bbox_size]

            detection = [bbox, obj['confidence'], obj['class_id']]
            predictions.append(detection)
        return predictions

    def _check_entrance_region(self) -> bool:
        try:

            entrance_x_threshold = 0.1
            recent_disappearances = 0

            for obj in self.tracked_objects.values():
                if obj['conveyor_x'] < entrance_x_threshold and obj['velocity'] > 0.05:
                    recent_disappearances += 1

            if recent_disappearances >= 1:
                logger.debug(f"入口区域活动检测 - 最近消失: {recent_disappearances}")
                return True

            return False

        except Exception as e:
            logger.error(f"入口区域检查失败: {e}")
            return False

    def _evaluate_tracking_quality(self) -> float:
        try:
            if not self.tracked_objects:
                return 0.0

            quality_scores = []

            object_count = len(self.tracked_objects)
            count_score = min(object_count / 5.0, 1.0)

            confidences = [obj['confidence'] for obj in self.tracked_objects.values()]
            confidence_score = np.mean(confidences) if confidences else 0.0

            track_ages = [self.frame_count - obj.get('first_detected_frame', self.frame_count)
                         for obj in self.tracked_objects.values()]
            age_score = min(np.mean(track_ages) / 50.0, 1.0)

            velocities = [abs(obj['velocity']) for obj in self.tracked_objects.values()]
            velocity_score = 1.0 if np.mean(velocities) < 0.5 else 0.5

            quality_score = (count_score * 0.3 +
                           confidence_score * 0.4 +
                           age_score * 0.2 +
                           velocity_score * 0.1)

            logger.debug(f"追踪质量评估 - 数量: {count_score:.2f}, 置信度: {confidence_score:.2f}, "
                        f"时长: {age_score:.2f}, 速度: {velocity_score:.2f}, 综合: {quality_score:.2f}")

            return quality_score

        except Exception as e:
            logger.error(f"追踪质量评估失败: {e}")
            return 0.5

    def _publish_via_mqtt(self, frame: np.ndarray, result: Dict):
        try:
            if not self.mqtt_service or not self.mqtt_connected:
                return

            if self.frame_count % 2 == 0:
                self.mqtt_service.publish_video_frame(frame, self.frame_count)

            if result.get('tracked_objects'):
                self.mqtt_service.publish_object_data(result['tracked_objects'], self.frame_count)

            stats = self.get_tracking_stats()
            self.mqtt_service.publish_tracking_stats(stats)

            if hasattr(self, 'last_mqtt_publish_time'):
                mqtt_interval = time.time() - self.last_mqtt_publish_time
                if mqtt_interval < 0.5:
                    logger.debug(f"MQTT数据发布 - 帧ID: {self.frame_count}, 间隔: {mqtt_interval:.3f}s")
            self.last_mqtt_publish_time = time.time()

        except Exception as e:
            logger.error(f"MQTT数据发布失败: {e}")
            self.mqtt_enabled = False

_tracking_service = None

def get_tracking_service(config: Optional[Dict] = None) -> ConveyorObjectTracker:
    global _tracking_service
    if _tracking_service is None:
        _tracking_service = ConveyorObjectTracker(config)
    return _tracking_service

def initialize_tracking_service(config: Optional[Dict] = None):
    global _tracking_service
    _tracking_service = ConveyorObjectTracker(config)
    return _tracking_service