#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading
import logging
import math
import json
import numpy as np
from collections import deque, defaultdict
from datetime import datetime

class PipelineController:

    def __init__(self, socketio=None, debug_mode=True):
        self.logger = logging.getLogger(__name__)
        self.socketio = socketio
        self.debug_mode = debug_mode

        self.debug_simulation = {
            'tracking_active': False,
            'conveyor_running': False,
            'arm_busy': False,
            'ocr_processing': False
        }

        from services.device_connection_manager import get_device_connection_manager
        from services.tracking_service import get_tracking_service

        self.device_manager = get_device_connection_manager()
        self.tracking_service = get_tracking_service()

        self.pipeline_state = {
            "status": "idle",  # idle, running, paused, error
            "current_object": None,
            "progress": 0.0,
            "processed_count": 0,
            "error_count": 0,
            "start_time": None,
            "current_step": "等待启动"
        }

        self.tracking_state = {
            "tracked_objects": {},
            "last_update": None,
            "active_tracks": 0,
            "alignment_status": {}
        }

        self.ocr_history = deque(maxlen=50)

        self.processing_history = deque(maxlen=100)

        self.ocr_frame_cache = deque(maxlen=5)

        self.config = {
            "belt_speed": 0.1,
            "alignment_threshold": 15,
            "alignment_timeout": 10.0,
            "ocr_frame_interval": 2,
            "ocr_total_frames": 5,
            "confidence_threshold": 0.7,
            "pickup_height": 8.0,
            "deposit_position": (0, 15, 12),
            "brick_class_name": "brick",
            "arm_class_name": "arm"
        }

        self.is_processing_object = False
        self.current_brick_id = None
        self.current_arm_id = None
        self.ocr_frame_count = 0
        self.last_ocr_frame_time = 0

        self.lock = threading.Lock()

        self.tracking_thread = threading.Thread(target=self._tracking_processor, daemon=True)
        self.tracking_thread_running = True
        self.tracking_thread.start()

        self.logger.info("流水线控制器重构版初始化完成")

    def set_socketio(self, socketio):
        self.socketio = socketio

    def _tracking_processor(self):
        self.logger.info("追踪数据处理线程已启动")
        processing_count = 0

        while self.tracking_thread_running:
            try:
                if self.pipeline_state["status"] != "running" or self.is_processing_object:
                    time.sleep(0.1)
                    continue

                tracked_objects = self.tracking_service.get_current_objects()
                processing_count += 1

                if processing_count % 100 == 0:
                    self.logger.info(f"追踪处理循环运行中，处理次数: {processing_count}, 当前追踪物体: {len(tracked_objects)}")

                if not tracked_objects:
                    if processing_count % 50 == 0:
                        self.logger.debug("当前无追踪物体，等待检测...")
                    time.sleep(0.1)
                    continue

                with self.lock:
                    self.tracking_state["tracked_objects"] = {obj["track_id"]: obj for obj in tracked_objects}
                    self.tracking_state["last_update"] = datetime.now().isoformat()
                    self.tracking_state["active_tracks"] = len(tracked_objects)

                brick_obj = None
                arm_obj = None

                self.logger.debug(f"处理 {len(tracked_objects)} 个追踪物体: {[obj.get('class_name', 'unknown') for obj in tracked_objects]}")

                for obj in tracked_objects:
                    class_name = obj.get("class_name", "unknown")
                    if class_name == self.config["brick_class_name"]:
                        brick_obj = obj
                        self.logger.debug(f"检测到砖块: ID={obj.get('track_id')}, 位置=({obj.get('conveyor_x', 0):.3f}, {obj.get('conveyor_y', 0):.3f})")
                    elif class_name == self.config["arm_class_name"]:
                        arm_obj = obj
                        self.logger.debug(f"检测到机械臂: ID={obj.get('track_id')}, 位置=({obj.get('conveyor_x', 0):.3f}, {obj.get('conveyor_y', 0):.3f})")

                if brick_obj and arm_obj:
                    self.logger.info(f"同时检测到砖块和机械臂，进行对齐检查")
                    alignment_result = self._check_brick_arm_alignment(brick_obj, arm_obj)

                    if alignment_result["aligned"] and not self.is_processing_object:
                        self.logger.info(f"检测到砖块和机械臂对齐，开始处理流程")
                        self._start_object_processing(brick_obj, arm_obj, alignment_result)
                    else:
                        self.logger.debug(f"砖块和机械臂未对齐: 水平距离={alignment_result['x_distance']:.3f}m, 对齐状态={alignment_result['aligned']}")
                else:
                    if processing_count % 20 == 0:
                        missing = []
                        if not brick_obj: missing.append("砖块")
                        if not arm_obj: missing.append("机械臂")
                        self.logger.debug(f"缺少必要的物体: {', '.join(missing)}")

                time.sleep(0.05)

            except Exception as e:
                self.logger.error(f"追踪数据处理线程错误: {str(e)}")
                time.sleep(0.5)

    def _check_brick_arm_alignment(self, brick_obj, arm_obj):
        brick_x, brick_y = brick_obj.get("conveyor_x", 0), brick_obj.get("conveyor_y", 0)
        arm_x, arm_y = arm_obj.get("conveyor_x", 0), arm_obj.get("conveyor_y", 0)

        x_distance = abs(brick_x - arm_x)

        y_distance = abs(brick_y - arm_y)

        horizontal_threshold = 0.05

        same_vertical_line = x_distance <= horizontal_threshold

        reasonable_y_distance = y_distance <= 0.2

        aligned = same_vertical_line and reasonable_y_distance

        self.logger.debug(f"对齐检查: 砖块位置({brick_x:.3f}, {brick_y:.3f}), 机械臂位置({arm_x:.3f}, {arm_y:.3f}), "
                         f"水平距离: {x_distance:.3f}m, 垂直距离: {y_distance:.3f}m, "
                         f"对齐状态: {aligned}")

        return {
            "aligned": aligned,
            "brick_position": (brick_x, brick_y),
            "arm_position": (arm_x, arm_y),
            "x_distance": x_distance,
            "y_distance": y_distance,
            "horizontal_threshold": horizontal_threshold,
            "same_vertical_line": same_vertical_line
        }

    def _start_object_processing(self, brick_obj, arm_obj, alignment_result):
        try:
            self.is_processing_object = True
            self.current_brick_id = brick_obj["track_id"]
            self.current_arm_id = arm_obj["track_id"]

            self.pipeline_state["current_object"] = self.current_brick_id
            self.pipeline_state["current_step"] = "检测到物体对齐"

            self.logger.info(f"开始处理物体 {self.current_brick_id}，机械臂 {self.current_arm_id}")

            self._execute_pipeline_sequence(brick_obj, arm_obj)

        except Exception as e:
            self.logger.error(f"开始处理物体失败: {str(e)}")
            self._reset_processing_state()

    def _execute_pipeline_sequence(self, brick_obj, arm_obj):
        try:
            self.pipeline_state["current_step"] = "停止传送带"
            self._stop_conveyor()
            time.sleep(0.5)

            self.pipeline_state["current_step"] = "执行机械臂夹取"
            self._execute_robot_arm_pickup_sequence(brick_obj)

            self.pipeline_state["current_step"] = "重启传送带"
            self._start_conveyor()

            self.pipeline_state["current_step"] = "执行多帧OCR识别"
            ocr_result = self._perform_multi_frame_ocr()

            self.pipeline_state["current_step"] = "处理识别结果"
            self._process_ocr_result(ocr_result, brick_obj)

            self.pipeline_state["processed_count"] += 1
            self.pipeline_state["progress"] = (
                self.pipeline_state["processed_count"] /
                max(self.pipeline_state["processed_count"] + 1, 1)
            )

            self._record_processing_history(brick_obj, ocr_result)

            self.logger.info(f"物体 {self.current_brick_id} 处理完成")

        except Exception as e:
            self.logger.error(f"流水线处理序列失败: {str(e)}")
            self.pipeline_state["error_count"] += 1
            self.pipeline_state["current_step"] = f"处理错误: {str(e)}"
        finally:
            self._reset_processing_state()

    def _stop_conveyor(self):
        belt_controller = self.device_manager.get_belt_controller()
        if belt_controller:
            try:
                belt_controller.set_speed_mps(0, "forward")
                self.logger.info("传送带已停止")
            except Exception as e:
                self.logger.error(f"停止传送带失败: {e}")
                if self.debug_mode:
                    self.logger.info("调试模式：模拟传送带停止")
        else:
            self.logger.warning("传送带控制器未连接，模拟停止")
            if self.debug_mode:
                self.logger.info("调试模式：传送带停止模拟完成")

    def _start_conveyor(self):
        belt_controller = self.device_manager.get_belt_controller()
        if belt_controller:
            try:
                belt_controller.set_speed_mps(self.config["belt_speed"], "forward")
                self.logger.info(f"传送带已启动，速度: {self.config['belt_speed']} m/s")
            except Exception as e:
                self.logger.error(f"启动传送带失败: {e}")
                if self.debug_mode:
                    self.logger.info("调试模式：模拟传送带启动")
        else:
            self.logger.warning("传送带控制器未连接，模拟启动")
            if self.debug_mode:
                self.logger.info(f"调试模式：传送带启动模拟完成，速度: {self.config['belt_speed']} m/s")

    def _execute_robot_arm_pickup_sequence(self, brick_obj):
        arm_controller = self.device_manager.get_robot_arm()
        if not arm_controller:
            self.logger.warning("机械臂未连接，跳过夹取操作")
            if self.debug_mode:
                self.logger.info("调试模式：模拟机械臂夹取序列")
                for step in self._get_debug_pickup_sequence():
                    self.logger.info(f"调试模式 - 模拟机械臂动作: {step}")
                    time.sleep(0.2)
            return

        try:
            custom_sequence = self.config.get("custom_arm_sequence")

            if custom_sequence and len(custom_sequence) > 0:
                self.logger.info(f"使用自定义机械臂序列，共 {len(custom_sequence)} 个步骤")
                sequence_to_use = custom_sequence
            else:
                self.logger.info("使用默认预设机械臂序列")
                sequence_to_use = self._get_default_pickup_sequence()

            for step in sequence_to_use:
                step_name = step.get('name', '未知步骤')
                step_duration = step.get('duration', 1000)
                step_actions = step.get('actions', [])

                self.pipeline_state["current_step"] = f"机械臂动作: {step_name}"
                self.logger.info(f"执行机械臂步骤: {step_name}")

                actions = []
                for action in step_actions:
                    joint_id = action.get("jointId") or action.get("joint")
                    angle = action.get("angle")

                    if joint_id is not None and angle is not None:
                        actions.append({
                            "type": "joint",
                            "joint": joint_id,
                            "angle": angle,
                            "speed": 50,
                            "movetime": step_duration
                        })

                if actions:
                    try:
                        if hasattr(arm_controller, 'run_sequence'):
                            success = arm_controller.run_sequence(actions)
                            if not success:
                                self.logger.warning(f"机械臂步骤执行失败: {step_name}")
                        else:
                            for action in actions:
                                arm_controller.set_joint_angle(
                                    action["joint"],
                                    action["angle"],
                                    action["movetime"]
                                )
                                time.sleep(action["movetime"] / 1000.0)
                    except Exception as arm_error:
                        self.logger.error(f"机械臂执行失败: {step_name} - {arm_error}")
                        if self.debug_mode:
                            self.logger.info(f"调试模式：跳过失败的机械臂步骤 {step_name}")

                time.sleep(step_duration / 1000.0 + 0.1)

            self.logger.info("机械臂夹取序列执行完成")
            if self.debug_mode:
                self.logger.info("调试模式：机械臂夹取序列完成")

        except Exception as e:
            self.logger.error(f"机械臂夹取序列执行失败: {str(e)}")
            if self.debug_mode:
                self.logger.error(f"调试模式：机械臂错误 - {e}")
            raise

    def _perform_multi_frame_ocr(self):
        self.logger.info("开始多帧OCR识别")
        self.ocr_frame_cache.clear()
        self.ocr_frame_count = 0
        self.last_ocr_frame_time = time.time()

        frame_interval = self.config["ocr_frame_interval"]
        total_frames = self.config["ocr_total_frames"]

        while self.ocr_frame_count < total_frames:
            current_time = time.time()

            if current_time - self.last_ocr_frame_time >= (frame_interval * 0.1):
                try:
                    frame_base64 = self.tracking_service.get_smooth_frame_base64()
                    if frame_base64:
                        ocr_result = self._call_ocr_service(frame_base64)
                        if ocr_result:
                            self.ocr_frame_cache.append(ocr_result)
                            self.ocr_frame_count += 1
                            self.last_ocr_frame_time = current_time
                            self.logger.info(f"采集到OCR帧 {self.ocr_frame_count}/{total_frames}")

                    time.sleep(0.1)

                except Exception as e:
                    self.logger.error(f"采集OCR帧失败: {str(e)}")
                    time.sleep(0.1)
            else:
                time.sleep(0.05)

        final_result = self._vote_ocr_results(list(self.ocr_frame_cache))
        self.logger.info(f"多帧OCR识别完成，最终结果: {final_result}")
        return final_result

    def _call_ocr_service(self, frame_base64):
        try:
            import random
            energy_levels = ['1级', '2级', '3级', '4级', '5级']

            return {
                "energy_level": random.choice(energy_levels),
                "confidence": random.uniform(0.7, 0.95),
                "timestamp": datetime.now().isoformat(),
                "frame_data": frame_base64[:100] + "..."
            }
        except Exception as e:
            self.logger.error(f"调用OCR服务失败: {str(e)}")
            return None

    def _vote_ocr_results(self, frame_results):
        if not frame_results:
            return {"energy_level": "未知", "confidence": 0.0, "vote_count": 0}

        level_groups = defaultdict(list)

        for result in frame_results:
            level = result.get("energy_level", "未知")
            confidence = result.get("confidence", 0)
            level_groups[level].append(confidence)

        best_level = None
        max_count = 0
        avg_confidence = 0

        for level, confidences in level_groups.items():
            count = len(confidences)
            current_avg = np.mean(confidences) if confidences else 0

            if count > max_count or (count == max_count and current_avg > avg_confidence):
                best_level = level
                max_count = count
                avg_confidence = current_avg

        return {
            "energy_level": best_level or "未知",
            "confidence": avg_confidence,
            "vote_count": max_count,
            "total_frames": len(frame_results),
            "all_results": frame_results
        }

    def _process_ocr_result(self, ocr_result, brick_obj):
        self.ocr_history.append({
            "energy_level": ocr_result["energy_level"],
            "confidence": ocr_result["confidence"],
            "timestamp": datetime.now().isoformat(),
            "object_data": brick_obj,
            "vote_count": ocr_result["vote_count"],
            "total_frames": ocr_result["total_frames"]
        })

        self.logger.info(f"OCR识别结果: 能效等级 {ocr_result['energy_level']} (置信度: {ocr_result['confidence']:.2f})")

    def _record_processing_history(self, brick_obj, ocr_result):
        history_entry = {
            "object_id": brick_obj["track_id"],
            "timestamp": datetime.now().isoformat(),
            "position": {"x": brick_obj.get("conveyor_x", 0), "y": brick_obj.get("conveyor_y", 0)},
            "ocr_result": ocr_result,
            "success": True
        }

        self.processing_history.append(history_entry)

    def _reset_processing_state(self):
        self.is_processing_object = False
        self.current_brick_id = None
        self.current_arm_id = None
        self.ocr_frame_count = 0
        self.ocr_frame_cache.clear()
        if self.pipeline_state["status"] == "running":
            self.pipeline_state["current_object"] = None
            self.pipeline_state["current_step"] = "等待下一个物体"

    def start_pipeline(self):
        with self.lock:
            if self.pipeline_state["status"] == "running":
                return {"success": False, "message": "流水线已在运行"}

            try:
                self.logger.info("开始启动流水线系统...")

                self.pipeline_state["current_step"] = "启动物体追踪服务"
                self.logger.info("正在启动物体追踪服务...")
                try:
                    tracking_result = self.tracking_service.start_tracking(0)
                    self.logger.info(f"物体追踪服务启动结果: {tracking_result}")

                    if not tracking_result:
                        self.logger.warning("物体追踪服务启动失败，将使用模拟模式")

                    if self.debug_mode:
                        self.debug_simulation['tracking_active'] = True
                        self.logger.info("调试模式：物体追踪已激活")

                except Exception as tracking_error:
                    self.logger.error(f"启动物体追踪服务时出错: {tracking_error}")
                    if self.debug_mode:
                        self.debug_simulation['tracking_active'] = True
                        self.logger.info("调试模式：追踪服务异常，启用模拟追踪")

                self.pipeline_state["current_step"] = "启动传送带"
                self._start_conveyor()

                if self.debug_mode:
                    self.debug_simulation['conveyor_running'] = True
                    self.logger.info("调试模式：传送带已启动")

                self.pipeline_state["status"] = "running"
                self.pipeline_state["processed_count"] = 0
                self.pipeline_state["error_count"] = 0
                self.pipeline_state["start_time"] = datetime.now().isoformat()
                self.pipeline_state["current_step"] = "系统运行中"
                self.pipeline_state["current_object"] = None

                self._reset_processing_state()

                self.logger.info("流水线系统启动完成")
                self._emit_status_update()
                return {"success": True, "message": "流水线系统启动成功"}

            except Exception as e:
                self.logger.error(f"启动流水线失败: {str(e)}")
                self.pipeline_state["status"] = "error"
                self.pipeline_state["current_step"] = f"启动失败: {str(e)}"
                return {"success": False, "message": f"启动失败: {str(e)}"}

    def stop_pipeline(self):
        with self.lock:
            if self.pipeline_state["status"] != "running":
                return {"success": False, "message": "流水线未在运行"}

            try:
                self.pipeline_state["status"] = "idle"
                self.pipeline_state["current_step"] = "已停止"

                belt_controller = self.device_manager.get_belt_controller()
                if belt_controller:
                    belt_controller.set_speed_mps(0, "forward")
                else:
                    self.logger.warning("传送带控制器未连接，使用模拟模式")

                self.logger.info("流水线停止")
                self._emit_status_update()
                return {"success": True, "message": "流水线停止成功"}

            except Exception as e:
                self.logger.error(f"停止流水线失败: {str(e)}")
                self.pipeline_state["status"] = "error"
                self.pipeline_state["current_step"] = f"停止失败: {str(e)}"
                return {"success": False, "message": f"停止失败: {str(e)}"}

    def pause_pipeline(self):
        with self.lock:
            if self.pipeline_state["status"] != "running":
                return {"success": False, "message": "流水线未在运行"}

            try:
                self.pipeline_state["status"] = "paused"
                self.pipeline_state["current_step"] = "已暂停"

                belt_controller = self.device_manager.get_belt_controller()
                if belt_controller:
                    belt_controller.set_speed_mps(0, "forward")
                else:
                    self.logger.warning("传送带控制器未连接，使用模拟模式")

                self.logger.info("流水线暂停")
                self._emit_status_update()
                return {"success": True, "message": "流水线暂停成功"}

            except Exception as e:
                self.logger.error(f"暂停流水线失败: {str(e)}")
                self.pipeline_state["status"] = "error"
                self.pipeline_state["current_step"] = f"暂停失败: {str(e)}"
                return {"success": False, "message": f"暂停失败: {str(e)}"}

    def resume_pipeline(self):
        with self.lock:
            if self.pipeline_state["status"] != "paused":
                return {"success": False, "message": "流水线未暂停"}

            try:
                self.pipeline_state["status"] = "running"
                self.pipeline_state["current_step"] = "恢复运行"

                belt_controller = self.device_manager.get_belt_controller()
                if belt_controller:
                    belt_controller.set_speed_mps(self.config["belt_speed"], "forward")
                else:
                    self.logger.warning("传送带控制器未连接，使用模拟模式")

                self.logger.info("流水线恢复")
                self._emit_status_update()
                return {"success": True, "message": "流水线恢复成功"}

            except Exception as e:
                self.logger.error(f"恢复流水线失败: {str(e)}")
                self.pipeline_state["status"] = "error"
                self.pipeline_state["current_step"] = f"恢复失败: {str(e)}"
                return {"success": False, "message": f"恢复失败: {str(e)}"}

    def update_tracking_data(self, tracking_data):
        """Update externally supplied tracking data for compatibility tests and diagnostics."""
        with self.lock:
            objects = tracking_data
            if isinstance(tracking_data, list):
                objects = {obj.get("track_id", index): obj for index, obj in enumerate(tracking_data)}

            self.tracking_state["tracked_objects"] = objects
            self.tracking_state["last_update"] = datetime.now().isoformat()
            self.tracking_state["active_tracks"] = len(objects)
            self._emit_status_update()

    def _get_default_pickup_sequence(self):
        """Return the default robot-arm pick-and-place sequence."""
        return [
            {"name": "Initial position", "duration": 1000, "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -75},
                {"jointId": 4, "angle": 60},
                {"jointId": 5, "angle": 45},
                {"jointId": 6, "angle": 90}
            ]},
            {"name": "Detection position", "duration": 1000, "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -70},
                {"jointId": 4, "angle": 90},
                {"jointId": 5, "angle": 80},
                {"jointId": 6, "angle": 90}
            ]},
            {"name": "Transition to pickup", "duration": 500, "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -45},
                {"jointId": 4, "angle": 85},
                {"jointId": 5, "angle": 110},
                {"jointId": 6, "angle": 90}
            ]},
            {"name": "Pickup position", "duration": 1000, "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -20},
                {"jointId": 4, "angle": 80},
                {"jointId": 5, "angle": 140},
                {"jointId": 6, "angle": 90}
            ]},
            {"name": "Grip object", "duration": 500, "actions": [
                {"jointId": 1, "angle": 0}
            ]},
            {"name": "Lift turn 1", "duration": 500, "actions": [
                {"jointId": 1, "angle": 0},
                {"jointId": 3, "angle": -10},
                {"jointId": 4, "angle": 75},
                {"jointId": 5, "angle": 120},
                {"jointId": 6, "angle": 70}
            ]},
            {"name": "Lift turn 2", "duration": 500, "actions": [
                {"jointId": 1, "angle": 0},
                {"jointId": 3, "angle": -10},
                {"jointId": 4, "angle": 70},
                {"jointId": 5, "angle": 100},
                {"jointId": 6, "angle": 45}
            ]},
            {"name": "Lift turn 3", "duration": 500, "actions": [
                {"jointId": 1, "angle": 0},
                {"jointId": 3, "angle": -10},
                {"jointId": 4, "angle": 65},
                {"jointId": 5, "angle": 120},
                {"jointId": 6, "angle": 20}
            ]},
            {"name": "Place position", "duration": 1000, "actions": [
                {"jointId": 1, "angle": 0},
                {"jointId": 3, "angle": -20},
                {"jointId": 4, "angle": 60},
                {"jointId": 5, "angle": 140},
                {"jointId": 6, "angle": 0}
            ]},
            {"name": "Release object", "duration": 1500, "actions": [
                {"jointId": 1, "angle": 130}
            ]},
            {"name": "Return turn 1", "duration": 500, "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -32},
                {"jointId": 4, "angle": 70},
                {"jointId": 5, "angle": 120},
                {"jointId": 6, "angle": 30}
            ]},
            {"name": "Return turn 2", "duration": 500, "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -45},
                {"jointId": 4, "angle": 70},
                {"jointId": 5, "angle": 100},
                {"jointId": 6, "angle": 45}
            ]},
            {"name": "Return turn 3", "duration": 500, "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -57},
                {"jointId": 4, "angle": 80},
                {"jointId": 5, "angle": 90},
                {"jointId": 6, "angle": 60}
            ]},
            {"name": "Return to detection", "duration": 1000, "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -70},
                {"jointId": 4, "angle": 90},
                {"jointId": 5, "angle": 80},
                {"jointId": 6, "angle": 90}
            ]}
        ]

    def _get_debug_pickup_sequence(self):
        """Return readable debug steps for simulated pickup runs."""
        return [
            "Move to initial position",
            "Detect object position",
            "Move to pickup position",
            "Grip object",
            "Lift object",
            "Move to placement position",
            "Release object",
            "Return to initial position"
        ]
    def _emit_status_update(self):
        if self.socketio:
            status_data = {
                "pipeline_state": self.pipeline_state,
                "tracking_state": self.tracking_state,
                "config": self.config,
                "timestamp": datetime.now().isoformat()
            }
            self.socketio.emit('pipeline_status_update', status_data)

    def get_status(self):
        pipeline_state = self.pipeline_state.copy()
        if pipeline_state["start_time"]:
            if hasattr(pipeline_state["start_time"], 'isoformat'):
                pipeline_state["start_time"] = pipeline_state["start_time"].isoformat()

        tracking_state = self.tracking_state.copy()
        if tracking_state["last_update"]:
            if hasattr(tracking_state["last_update"], 'isoformat'):
                tracking_state["last_update"] = tracking_state["last_update"].isoformat()

        uptime = 0
        if pipeline_state["start_time"]:
            try:
                if isinstance(pipeline_state["start_time"], str):
                    start_time = datetime.fromisoformat(pipeline_state["start_time"].replace('Z', '+00:00'))
                else:
                    start_time = pipeline_state["start_time"]
                uptime = (datetime.now() - start_time).total_seconds()
            except Exception as e:
                self.logger.warning(f"计算运行时间失败: {e}")
                uptime = 0

        return {
            "pipeline_state": pipeline_state,
            "tracking_state": tracking_state,
            "config": self.config,
            "ocr_history_count": len(self.ocr_history),
            "processing_history_count": len(self.processing_history),
            "uptime": uptime
        }

    def update_config(self, new_config):
        with self.lock:
            self.config.update(new_config)
            self.logger.info(f"配置更新: {new_config}")
            return {"success": True, "message": "配置更新成功"}

    def get_processing_history(self, limit=10):
        return list(self.processing_history)[-limit:]

    def reset_statistics(self):
        with self.lock:
            self.pipeline_state["processed_count"] = 0
            self.pipeline_state["error_count"] = 0
            self.processing_history.clear()
            self.ocr_history.clear()
            return {"success": True, "message": "统计信息已重置"}

_pipeline_controller = None

def get_pipeline_controller(socketio=None, debug_mode=True):
    global _pipeline_controller
    if _pipeline_controller is None:
        _pipeline_controller = PipelineController(socketio, debug_mode)
    elif socketio and _pipeline_controller.socketio is None:
        _pipeline_controller.set_socketio(socketio)
    return _pipeline_controller

def initialize_pipeline_controller(belt_controller, robot_arm, tracking_service, energy_detection_service):
    return get_pipeline_controller()