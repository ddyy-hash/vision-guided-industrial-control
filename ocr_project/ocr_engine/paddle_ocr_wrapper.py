import subprocess
import json
import time
import threading
import queue
import os
import re
from loguru import logger
from pathlib import Path
from core.config import Config


class PaddleOCREngine:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.is_ready = False
        # 异步启动引擎，避免阻塞主线程
        threading.Thread(target=self._init_engine, daemon=True).start()

    def _init_engine(self):
        try:
            self.start_engine()
            self._wait_for_ready()
            logger.success("OCR引擎初始化完成")
        except Exception as e:
            logger.error(f"OCR引擎初始化失败: {e}")

    def start_engine(self):
        exe = str(Config.OCR_EXE_PATH)
        cmd = [
            exe,
            f"--models_path={Config.MODEL_DIR}",
            f"--cpu_threads={Config.CPU_THREADS}",
            f"--use_angle_cls={'true' if Config.USE_ANGLE_CLS else 'false'}"
        ]

        logger.debug(f"启动命令: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=-1,  # 行缓冲，避免bufsize=0导致的问题
            text=False,  # 保持二进制模式以便手动控制编码
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        logger.success("OCR引擎进程已启动")

    def _wait_for_ready(self):
        logger.info("等待 OCR 引擎初始化...")

        # 创建线程停止标志
        self.stop_init_threads = threading.Event()
        self.init_complete = threading.Event()  # 新增初始化完成标志

        out_q = queue.Queue()
        err_q = queue.Queue()

        # 启动初始化线程
        self.init_stdout_thread = threading.Thread(
            target=self._read_stream,
            args=(self.process.stdout, out_q, "STDOUT"),
            daemon=True
        )
        self.init_stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(self.process.stderr, err_q, "STDERR"),
            daemon=True
        )
        self.init_stdout_thread.start()
        self.init_stderr_thread.start()

        start = time.time()
        while time.time() - start < 120:
            try:
                line = out_q.get(timeout=0.5)
                if "OCR init completed." in line:
                    # 设置初始化完成标志
                    self.init_complete.set()

                    # 通知读取线程停止
                    self.stop_init_threads.set()

                    # 等待线程安全退出
                    time.sleep(0.1)

                    self.is_ready = True
                    logger.success("OCR 引擎初始化完成")
                    return

                if "error" in line.lower():
                    logger.error(f"初始化失败: {line}")
                    break
            except queue.Empty:
                continue

        # 超时处理
        self.stop_init_threads.set()
        raise RuntimeError("OCR 引擎初始化失败")

    def _read_stream(self, stream, q, tag):
        try:
            while not self.stop_init_threads.is_set():
                # 检查初始化是否已完成
                if self.init_complete.is_set():
                    logger.debug(f"[{tag}] 检测到初始化完成，停止读取")
                    break

                try:
                    # 非阻塞读取
                    if hasattr(stream, 'read1'):  # 检查是否支持非阻塞读取
                        data = stream.read1(1024)
                    else:
                        data = stream.read(1024)

                    if not data:
                        break

                    # 分割行处理
                    lines = data.decode("utf-8", errors="replace").splitlines()
                    for line in lines:
                        if line.strip():
                            q.put(line)
                            logger.debug(f"[{tag}] {line}")

                            # 检查是否包含初始化完成消息
                            if "OCR init completed." in line:
                                # 设置初始化完成标志
                                self.init_complete.set()
                except BlockingIOError:
                    time.sleep(0.1)  # 无数据时短暂等待
                except Exception as e:
                    logger.error(f"[{tag}] 读取异常: {e}")
                    break
        except Exception as e:
            logger.error(f"[{tag}] 线程异常: {e}")
        finally:
            logger.debug(f"[{tag}] 读取线程退出")

    def _stop_init_threads(self):
        """安全关闭初始化线程"""
        logger.debug("开始关闭初始化线程...")
        start_close = time.time()

        if hasattr(self, 'stop_init_threads'):
            self.stop_init_threads.set()

        # 等待线程退出
        threads_closed = 0
        for thread in [self.init_stdout_thread, self.init_stderr_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=2)
                if thread.is_alive():
                    logger.warning(f"{thread.name} 线程未正常退出")
                else:
                    threads_closed += 1

        elapsed = time.time() - start_close
        logger.debug(f"初始化线程关闭完成, 耗时: {elapsed:.3f}秒, 关闭线程数: {threads_closed}/2")

    def process_image(self, image_path, enable_preprocessing=True, enable_yolo=True, target_class_id=0, max_repair_time=2.0) -> dict:
        with self.lock:
            try:
                # 图像预处理（阶段一+二功能）
                if enable_preprocessing:
                    try:
                        import cv2
                        
                        # 读取图像
                        image = cv2.imread(image_path)
                        if image is not None:
                            if enable_yolo:
                                # 使用YOLO预处理（阶段一+二）
                                from services.yolo_preprocessing import yolo_preprocess_for_ocr
                                yolo_result = yolo_preprocess_for_ocr(
                                    image,
                                    target_class_id=target_class_id,
                                    enable_yolo=True,
                                    enable_enhancement=True,
                                    enable_repair=True,
                                    max_repair_time=max_repair_time
                                )
                                
                                # 使用第一个处理区域进行OCR
                                if yolo_result['processed_regions']:
                                    processed_image = yolo_result['processed_regions'][0]['image']
                                    logger.info(f"YOLO预处理完成，找到 {len(yolo_result['processed_regions'])} 个区域，使用第一个区域")
                                    logger.debug(f"YOLO预处理详情: {yolo_result}")
                                else:
                                    processed_image = image
                                    logger.warning("YOLO预处理未找到任何区域，使用原图")
                            else:
                                # 使用传统预处理（阶段二）
                                from services.preprocessing_pipeline import preprocess_for_ocr
                                processed_image, processing_info = preprocess_for_ocr(image)
                                logger.info(f"传统预处理完成，耗时: {processing_info['processing_time_ms']:.2f}ms")
                            
                            # 保存处理后的图像
                            processed_path = image_path.replace(".", "_processed.")
                            cv2.imwrite(processed_path, processed_image)
                            
                            # 使用处理后的图像
                            abs_path = os.path.abspath(processed_path).replace("/", "\\")
                        else:
                            abs_path = os.path.abspath(image_path).replace("/", "\\")
                            logger.warning("图像预处理失败，使用原图")
                    except Exception as e:
                        logger.warning(f"预处理模块加载失败: {e}，使用原图")
                        abs_path = os.path.abspath(image_path).replace("/", "\\")
                else:
                    abs_path = os.path.abspath(image_path).replace("/", "\\")

                if self.process.poll() is not None:
                    logger.error("引擎已退出，尝试重启...")
                    self.close()
                    self.start_engine()
                    self._wait_for_ready()

                logger.debug(f"发送图片路径: {abs_path}")

                json_cmd = json.dumps({"image_path": abs_path}, ensure_ascii=False)
                self.process.stdin.write((json_cmd + "\r\n").encode("utf-8"))
                self.process.stdin.flush()

                q = queue.Queue()
                stop_evt = threading.Event()

                def _reader():
                    try:
                        buffer = b""  # 添加字节缓冲区
                        while not stop_evt.is_set():
                            # 使用非阻塞读取
                            chunk = self.process.stdout.read(1)  # 每次读取一个字节
                            if chunk:
                                buffer += chunk
                                # 检查是否遇到换行符（JSON结束）
                                if chunk == b'\n' or chunk == b'\r':
                                    try:
                                        # 尝试解码整行
                                        txt = buffer.decode("utf-8", errors="replace").strip()
                                        if txt:  # 只处理非空行
                                            q.put(txt)
                                            logger.debug(f"[PROCESS] {txt}")
                                            buffer = b""  # 清空缓冲区

                                            # 检查是否为完整JSON
                                            if txt.startswith('{') and txt.endswith('}'):
                                                try:
                                                    json.loads(txt)  # 验证JSON
                                                    logger.debug("检测到完整JSON行")
                                                    stop_evt.set()  # 提前结束读取
                                                    break
                                                except:
                                                    pass
                                    except UnicodeDecodeError:
                                        logger.warning("解码失败，继续读取")
                            else:
                                # 没有数据时短暂休眠
                                time.sleep(0.01)
                    except Exception as e:
                        logger.error(f"[PROCESS] 读取异常: {e}")

                # 确保线程启动并记录日志
                logger.debug("正在启动读取线程...")
                reader_thread = threading.Thread(target=_reader, daemon=True)
                reader_thread.start()
                logger.debug(f"读取线程已启动，线程ID: {reader_thread.ident}")

                start = time.time()
                result_lines = []
                complete_json = ""

                # 增加超时时间，确保完整读取
                while time.time() - start < Config.OCR_TIMEOUT * 1.5:
                    try:
                        line = q.get(timeout=1.0)

                        # 检查是否为完整的JSON行
                        if line.strip().startswith('{') and line.strip().endswith('}'):
                            try:
                                # 尝试解析JSON验证完整性
                                result = json.loads(line.strip())
                                complete_json = line.strip()
                                break
                            except json.JSONDecodeError:
                                # JSON不完整，继续收集
                                result_lines.append(line)
                                continue

                        # 使用正则表达式提取JSON（备用方案）
                        match = re.search(r'(\{.*\})', line)
                        if match:
                            json_candidate = match.group(1)
                            try:
                                result = json.loads(json_candidate)
                                complete_json = json_candidate
                                break
                            except json.JSONDecodeError:
                                result_lines.append(line)
                                continue

                    except queue.Empty:
                        continue

                stop_evt.set()

                if not complete_json:
                    # 尝试拼接多行构成完整JSON
                    if result_lines:
                        combined = ''.join(result_lines)
                        match = re.search(r'(\{.*\})', combined)
                        if match:
                            complete_json = match.group(1)

                if not complete_json:
                    logger.error("处理超时，未收到完整 JSON 结果")
                    logger.debug(f"收集到的行数: {len(result_lines)}")
                    return {"code": 500, "data": [], "message": "处理超时或JSON不完整"}

                logger.debug(f"完整 JSON: {complete_json}")
                return json.loads(complete_json)

            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {e}")
                logger.error(f"JSON内容: {complete_json}")
                return {"code": 500, "data": [], "message": "JSON解析错误"}
            except Exception as e:
                logger.critical(f"未知错误: {e}")
                return {"code": 500, "data": [], "message": str(e)}

    def close(self):
        if self.process:
            try:
                self.process.stdin.write(b"exit\n")
                self.process.stdin.flush()
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None


# 全局实例
ocr_engine = PaddleOCREngine()
