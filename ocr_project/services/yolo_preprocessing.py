"""
YOLO预处理服务
集成YOLO目标检测和OCR预处理管道
"""
import cv2
import numpy as np
import logging
import time
from loguru import logger
from .yolo_detector import detect_and_crop_targets
from .preprocessing_pipeline import preprocess_for_ocr

logger = logging.getLogger(__name__)

def yolo_preprocess_for_ocr(image, target_class_id=0, enable_yolo=True, enable_enhancement=True, enable_repair=True, max_repair_time=2.0):
    """
    YOLO预处理主函数 - 阶段一集成版本
    先进行YOLO目标检测，然后对每个检测区域应用OCR预处理
    
    Args:
        image: 输入图像
        target_class_id: YOLO目标类别ID（默认为0）
        enable_yolo: 是否启用YOLO检测
        enable_enhancement: 是否启用图像增强
        enable_repair: 是否启用字符修复
        
    Returns:
        dict: 包含预处理结果和检测信息的字典
    """
    try:
        logger.info("开始YOLO预处理流程")
        start_time = time.time()
        
        # 阶段1: YOLO目标检测和区域裁剪
        if enable_yolo:
            yolo_result = detect_and_crop_targets(image, target_class_id, enable_visualization=True)
            logger.info(f"YOLO检测完成，找到 {len(yolo_result['regions'])} 个区域")
        else:
            # 如果不启用YOLO，将整个图像作为一个区域
            yolo_result = {
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
            logger.info("YOLO检测已禁用，使用整个图像")
        
        # 阶段2: 对每个检测区域应用OCR预处理
        processed_regions = []
        region_processing_info = []
        
        for i, region in enumerate(yolo_result['regions']):
            region_start_time = time.time()
            
            # 应用OCR预处理（使用优化后的参数）
            processed_image, processing_info = preprocess_for_ocr(
                region['image'],
                enable_enhancement=enable_enhancement,
                enable_repair=enable_repair,
                max_repair_time=max_repair_time
            )
            
            region_processing_time = (time.time() - region_start_time) * 1000
            
            # 合并区域信息和预处理信息
            combined_info = {
                'region_index': i,
                'bbox': region['bbox'],
                'confidence': region.get('confidence', 1.0),
                'class_id': region.get('class_id', target_class_id),
                'processing_time_ms': region_processing_time,
                'enhancement_applied': processing_info.get('enhancement_applied', False),
                'repair_applied': processing_info.get('repair_applied', False),
                'metal_surface': processing_info.get('metal_surface', False)
            }
            
            processed_regions.append({
                'image': processed_image,
                'info': combined_info
            })
            region_processing_info.append(combined_info)
            
            logger.debug(f"区域 {i+1} 预处理完成，耗时: {region_processing_time:.2f}ms")
        
        total_processing_time = (time.time() - start_time) * 1000
        
        # 构建最终结果
        result = {
            'processed_regions': processed_regions,
            'yolo_detections': yolo_result.get('detections', []),
            'yolo_visualization': yolo_result.get('visualization'),
            'region_processing_info': region_processing_info,
            'total_processing_time_ms': total_processing_time,
            'target_class_id': target_class_id,
            'regions_count': len(processed_regions),
            'yolo_enabled': enable_yolo
        }
        
        logger.info(f"YOLO预处理完成，总耗时: {total_processing_time:.2f}ms")
        logger.info(f"处理了 {len(processed_regions)} 个区域，YOLO检测: {'启用' if enable_yolo else '禁用'}")
        
        return result
        
    except Exception as e:
        logger.error(f"YOLO预处理失败: {e}")
        # 返回错误信息，但包含一个基本的处理结果
        return {
            'processed_regions': [{
                'image': image.copy(),
                'info': {
                    'region_index': 0,
                    'bbox': [0, 0, image.shape[1], image.shape[0]],
                    'confidence': 1.0,
                    'class_id': target_class_id,
                    'processing_time_ms': 0,
                    'enhancement_applied': False,
                    'repair_applied': False,
                    'metal_surface': False,
                    'error': str(e)
                }
            }],
            'yolo_detections': [],
            'region_processing_info': [],
            'total_processing_time_ms': 0,
            'target_class_id': target_class_id,
            'regions_count': 1,
            'yolo_enabled': enable_yolo,
            'error': str(e)
        }

def create_yolo_preprocessing_debug_image(original_image, yolo_result):
    """
    创建YOLO预处理调试图像
    显示原始图像、YOLO检测结果和每个处理区域的对比
    """
    try:
        original_rgb = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB) if len(original_image.shape) == 3 else original_image
        
        # 如果有YOLO可视化图像，使用它
        if yolo_result.get('yolo_visualization') is not None:
            yolo_vis = yolo_result['yolo_visualization']
        else:
            yolo_vis = original_rgb.copy()
        
        # 计算调试图像尺寸
        regions_count = len(yolo_result['processed_regions'])
        if regions_count == 0:
            # 如果没有区域，只显示YOLO检测结果
            debug_image = yolo_vis
        else:
            # 计算网格布局
            cols = min(3, regions_count)  # 最多3列
            rows = (regions_count + cols - 1) // cols
            
            # 每个区域的尺寸
            region_height = 200
            region_width = 300
            
            # 主图像尺寸
            main_height = max(original_rgb.shape[0], yolo_vis.shape[0])
            main_width = original_rgb.shape[1] + yolo_vis.shape[1] + 20
            
            # 区域网格尺寸
            grid_height = rows * region_height + 50
            grid_width = cols * region_width + 20
            
            # 总调试图像尺寸
            total_height = main_height + grid_height + 50
            total_width = max(main_width, grid_width)
            
            # 创建调试图像
            debug_image = np.ones((total_height, total_width, 3), dtype=np.uint8) * 50
        
            # 添加原始图像
            orig_h, orig_w = original_rgb.shape[:2]
            debug_image[10:10+orig_h, 10:10+orig_w] = original_rgb
            cv2.putText(debug_image, "Original", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 添加YOLO检测结果
            yolo_x = orig_w + 30
            yolo_h, yolo_w = yolo_vis.shape[:2]
            debug_image[10:10+yolo_h, yolo_x:yolo_x+yolo_w] = yolo_vis
            cv2.putText(debug_image, "YOLO Detection", (yolo_x, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 添加分隔线
            separator_y = main_height + 20
            cv2.line(debug_image, (0, separator_y), (total_width, separator_y), (255, 255, 255), 2)
            
            # 添加处理区域标题
            cv2.putText(debug_image, "Processed Regions:", (10, separator_y + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            
            # 添加处理区域
            for i, region_data in enumerate(yolo_result['processed_regions']):
                row = i // cols
                col = i % cols
                
                x = col * region_width + 10
                y = separator_y + 50 + row * region_height
                
                # 调整区域图像尺寸
                region_img = region_data['image']
                if len(region_img.shape) == 2:
                    region_img = cv2.cvtColor(region_img, cv2.COLOR_GRAY2BGR)
                else:
                    region_img = cv2.cvtColor(region_img, cv2.COLOR_RGB2BGR) if len(region_img.shape) == 3 else region_img
                
                # 调整尺寸以适应显示区域
                if region_img.shape[0] > region_height or region_img.shape[1] > region_width:
                    scale = min(region_height / region_img.shape[0], region_width / region_img.shape[1])
                    new_h = int(region_img.shape[0] * scale)
                    new_w = int(region_img.shape[1] * scale)
                    region_img = cv2.resize(region_img, (new_w, new_h))
                
                # 将区域图像放置在调试图像中
                img_h, img_w = region_img.shape[:2]
                y_start = y + (region_height - img_h) // 2
                x_start = x + (region_width - img_w) // 2
                
                debug_image[y_start:y_start+img_h, x_start:x_start+img_w] = region_img
                
                # 添加区域信息
                info = region_data['info']
                info_text = f"Region {i+1}: Conf {info['confidence']:.2f}"
                cv2.putText(debug_image, info_text, (x, y_start + img_h + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 添加总体信息
            info_y = total_height - 20
            total_time = yolo_result['total_processing_time_ms']
            regions_count = yolo_result['regions_count']
            yolo_status = "Enabled" if yolo_result['yolo_enabled'] else "Disabled"
            
            info_text = f"YOLO: {yolo_status} | Regions: {regions_count} | Time: {total_time:.1f}ms"
            cv2.putText(debug_image, info_text, (10, info_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        
        return debug_image
        
    except Exception as e:
        logger.warning(f"创建YOLO调试图像失败: {e}")
        return original_image

# 测试函数
if __name__ == "__main__":
    import cv2
    import numpy as np
    
    # 创建测试图像
    test_image = np.ones((400, 600, 3), dtype=np.uint8) * 120
    cv2.rectangle(test_image, (50, 50), (200, 150), (80, 80, 80), -1)
    cv2.rectangle(test_image, (300, 100), (500, 300), (100, 100, 100), -1)
    cv2.putText(test_image, "TEST OBJECT 1", (60, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(test_image, "TEST OBJECT 2", (320, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    print("测试YOLO预处理流程...")
    
    # 测试YOLO预处理
    result = yolo_preprocess_for_ocr(test_image, target_class_id=0, enable_yolo=True)
    
    print(f"处理完成，耗时: {result['total_processing_time_ms']:.2f}ms")
    print(f"检测到 {result['regions_count']} 个区域")
    print(f"YOLO检测: {'启用' if result['yolo_enabled'] else '禁用'}")
    
    # 创建调试图像
    debug_img = create_yolo_preprocessing_debug_image(test_image, result)
    
    print("YOLO预处理测试完成")