"""
YOLO目标检测模块
用于检测图像中特定类别的目标并提取边界框
"""
import cv2
import numpy as np
import logging
from pathlib import Path
import time
from loguru import logger

logger = logging.getLogger(__name__)

class YOLODetector:
    """YOLO目标检测器"""
    
    def __init__(self, model_path=None, confidence_threshold=0.5, nms_threshold=0.4):
        """
        初始化YOLO检测器
        
        Args:
            model_path: YOLO模型文件路径
            confidence_threshold: 置信度阈值
            nms_threshold: 非极大值抑制阈值
        """
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.net = None
        self.class_names = []
        
        # 如果提供了模型路径，则加载模型
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
        else:
            logger.warning("未提供有效的YOLO模型路径，将使用模拟检测模式")
    
    def load_model(self, model_path):
        """加载YOLO模型"""
        try:
            # 加载YOLO模型
            weights_path = str(model_path)
            config_path = str(model_path).replace('.weights', '.cfg')
            
            if Path(config_path).exists():
                self.net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
                logger.info(f"YOLO模型加载成功: {model_path}")
                
                # 尝试加载类别名称
                names_path = str(model_path).replace('.weights', '.names')
                if Path(names_path).exists():
                    with open(names_path, 'r') as f:
                        self.class_names = [line.strip() for line in f.readlines()]
                    logger.info(f"加载了 {len(self.class_names)} 个类别名称")
                else:
                    # 如果没有类别文件，创建默认的
                    self.class_names = [f"class_{i}" for i in range(100)]
                    logger.info("使用默认类别名称")
            else:
                logger.warning(f"YOLO配置文件不存在: {config_path}")
                
        except Exception as e:
            logger.error(f"加载YOLO模型失败: {e}")
            self.net = None
    
    def detect_objects(self, image, target_class_id=0):
        """
        检测图像中的目标
        
        Args:
            image: 输入图像
            target_class_id: 目标类别ID（默认为0）
            
        Returns:
            list: 检测到的目标边界框列表，每个边界框为 [x, y, w, h, confidence, class_id]
        """
        if self.net is None:
            # 模拟检测模式 - 返回整个图像作为检测区域
            logger.info("使用模拟检测模式")
            height, width = image.shape[:2]
            return [[0, 0, width, height, 0.9, target_class_id]]
        
        try:
            # 获取图像尺寸
            height, width = image.shape[:2]
            
            # 创建blob
            blob = cv2.dnn.blobFromImage(image, 1/255.0, (416, 416), swapRB=True, crop=False)
            self.net.setInput(blob)
            
            # 获取输出层名称
            layer_names = self.net.getLayerNames()
            output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
            
            # 前向传播
            outputs = self.net.forward(output_layers)
            
            # 解析检测结果
            boxes = []
            confidences = []
            class_ids = []
            
            for output in outputs:
                for detection in output:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    # 只保留目标类别和置信度高的检测
                    if class_id == target_class_id and confidence > self.confidence_threshold:
                        # 获取边界框坐标
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        
                        # 计算边界框的左上角坐标
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)
                        
                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)
            
            # 应用非极大值抑制
            indices = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, self.nms_threshold)
            
            # 构建结果
            results = []
            if len(indices) > 0:
                for i in indices.flatten():
                    x, y, w, h = boxes[i]
                    confidence = confidences[i]
                    class_id = class_ids[i]
                    results.append([x, y, w, h, confidence, class_id])
            
            logger.info(f"检测到 {len(results)} 个类别ID为{target_class_id}的目标")
            return results
            
        except Exception as e:
            logger.error(f"目标检测失败: {e}")
            return []
    
    def crop_detected_regions(self, image, detections, margin_ratio=0.05):
        """
        根据检测结果裁剪图像区域
        
        Args:
            image: 原始图像
            detections: 检测结果列表
            margin_ratio: 边界框扩展比例
            
        Returns:
            list: 裁剪后的图像区域列表
        """
        cropped_regions = []
        
        for detection in detections:
            x, y, w, h, confidence, class_id = detection
            
            # 计算扩展后的边界框
            margin_x = int(w * margin_ratio)
            margin_y = int(h * margin_ratio)
            
            x1 = max(0, x - margin_x)
            y1 = max(0, y - margin_y)
            x2 = min(image.shape[1], x + w + margin_x)
            y2 = min(image.shape[0], y + h + margin_y)
            
            # 裁剪图像区域
            cropped_region = image[y1:y2, x1:x2]
            if cropped_region.size > 0:
                cropped_regions.append({
                    'image': cropped_region,
                    'bbox': [x1, y1, x2 - x1, y2 - y1],
                    'confidence': confidence,
                    'class_id': class_id
                })
                logger.debug(f"裁剪区域: [{x1}, {y1}, {x2-x1}, {y2-y1}], 置信度: {confidence:.3f}")
        
        return cropped_regions
    
    def visualize_detections(self, image, detections, target_class_id=0):
        """
        在图像上可视化检测结果
        
        Args:
            image: 原始图像
            detections: 检测结果
            target_class_id: 目标类别ID
            
        Returns:
            numpy.ndarray: 带有检测框的可视化图像
        """
        vis_image = image.copy()
        
        for detection in detections:
            x, y, w, h, confidence, class_id = detection
            
            # 只可视化目标类别
            if class_id == target_class_id:
                # 绘制边界框
                color = (0, 255, 0)  # 绿色
                cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 2)
                
                # 添加标签
                label = f"Class {class_id}: {confidence:.2f}"
                if class_id < len(self.class_names):
                    label = f"{self.class_names[class_id]}: {confidence:.2f}"
                
                # 计算标签位置
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                label_y = max(y - 10, label_size[1] + 10)
                
                # 绘制标签背景
                cv2.rectangle(vis_image, (x, label_y - label_size[1] - 10), 
                             (x + label_size[0], label_y), color, -1)
                # 绘制标签文字
                cv2.putText(vis_image, label, (x, label_y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return vis_image

# 创建全局YOLO检测器实例
yolo_detector = YOLODetector()

def detect_and_crop_targets(image, target_class_id=0, enable_visualization=False):
    """
    检测并裁剪图像中特定类别的目标区域
    
    Args:
        image: 输入图像
        target_class_id: 目标类别ID
        enable_visualization: 是否生成可视化图像
        
    Returns:
        dict: 包含裁剪区域和检测信息的字典
    """
    try:
        logger.info(f"开始YOLO检测，目标类别ID: {target_class_id}")
        start_time = time.time()
        
        # 检测目标
        detections = yolo_detector.detect_objects(image, target_class_id)
        
        # 如果没有检测到目标，返回整个图像
        if not detections:
            logger.info("未检测到目标，返回整个图像")
            result = {
                'regions': [{
                    'image': image.copy(),
                    'bbox': [0, 0, image.shape[1], image.shape[0]],
                    'confidence': 1.0,
                    'class_id': target_class_id
                }],
                'detections': [],
                'processing_time_ms': 0,
                'target_class_id': target_class_id
            }
        else:
            # 裁剪检测到的区域
            cropped_regions = yolo_detector.crop_detected_regions(image, detections)
            
            result = {
                'regions': cropped_regions,
                'detections': detections,
                'processing_time_ms': (time.time() - start_time) * 1000,
                'target_class_id': target_class_id
            }
        
        # 生成可视化图像（如果需要）
        if enable_visualization:
            result['visualization'] = yolo_detector.visualize_detections(
                image, detections, target_class_id
            )
        
        logger.info(f"YOLO检测完成，找到 {len(result['regions'])} 个区域，耗时: {result['processing_time_ms']:.2f}ms")
        return result
        
    except Exception as e:
        logger.error(f"YOLO检测和裁剪失败: {e}")
        # 返回整个图像作为回退
        return {
            'regions': [{
                'image': image.copy(),
                'bbox': [0, 0, image.shape[1], image.shape[0]],
                'confidence': 1.0,
                'class_id': target_class_id
            }],
            'detections': [],
            'processing_time_ms': 0,
            'target_class_id': target_class_id,
            'error': str(e)
        }