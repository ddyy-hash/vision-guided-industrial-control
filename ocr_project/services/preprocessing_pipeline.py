"""
工业OCR图像预处理管道
集成所有增强功能，为PaddleOCR引擎提供优化输入
"""
import cv2
import numpy as np
import time
from loguru import logger
from .image_enhancement import enhance_industrial_image
from .character_repair import repair_metal_characters

def is_metal_surface(image):
    """
    判断是否为金属表面图像
    基于图像统计特征 - 优化版本
    """
    try:
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 计算图像统计特征
        mean_intensity = np.mean(gray)
        std_intensity = np.std(gray)
        
        # 金属表面特征：中等亮度 + 低对比度 + 存在边缘
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
        
        # 优化判断条件 - 更严格的阈值
        is_metal = (100 < mean_intensity < 160 and
                   std_intensity < 40 and
                   edge_density > 0.05 and
                   edge_density < 0.3)  # 添加上限避免复杂纹理
        
        logger.debug(f"金属表面检测: mean={mean_intensity:.1f}, std={std_intensity:.1f}, edge_density={edge_density:.3f} -> {is_metal}")
        return is_metal
        
    except Exception as e:
        logger.warning(f"金属表面检测失败: {e}, 默认返回False")
        return False

def preprocess_for_ocr(image, enable_enhancement=True, enable_repair=True, max_repair_time=2.0):
    """
    OCR预处理主函数 - 阶段二+三集成版本
    集成图像增强和字符修复功能，添加性能优化
    """
    try:
        logger.info("开始OCR图像预处理")
        start_time = time.time()
        
        result = image.copy()
        processing_info = {
            "original_shape": image.shape,
            "enhancement_applied": False,
            "repair_applied": False,
            "metal_surface": False,
            "processing_time_ms": 0,
            "repair_timeout": False
        }
        
        # 阶段1: 基础图像增强
        if enable_enhancement:
            result = enhance_industrial_image(result, enable_clahe=True, enable_sharpen=True)
            processing_info["enhancement_applied"] = True
            logger.debug("图像增强完成")
        
        # 阶段2: 金属字符修复（仅对金属表面图像，添加时间限制）
        if enable_repair:
            is_metal = is_metal_surface(result)
            processing_info["metal_surface"] = is_metal
            
            if is_metal:
                # 检查剩余时间是否足够进行修复
                elapsed = time.time() - start_time
                remaining_time = max_repair_time - elapsed
                
                if remaining_time > 0.5:  # 至少保留0.5秒用于修复
                    result, swt_map, break_mask = repair_metal_characters(
                        result, enable_swt=True, enable_repair=True,
                        max_processing_time=remaining_time
                    )
                    processing_info["repair_applied"] = True
                    logger.debug("金属字符修复完成")
                else:
                    logger.warning("处理时间不足，跳过金属字符修复")
                    processing_info["repair_timeout"] = True
            else:
                logger.debug("非金属表面，跳过字符修复")
        
        processing_time = (time.time() - start_time) * 1000
        processing_info["processing_time_ms"] = processing_time
        
        logger.info(f"OCR预处理完成，总耗时: {processing_time:.2f}ms")
        logger.info(f"处理详情: {processing_info}")
        
        return result, processing_info
        
    except Exception as e:
        logger.error(f"OCR预处理失败: {e}")
        return image, {
            "original_shape": image.shape,
            "enhancement_applied": False,
            "repair_applied": False,
            "metal_surface": False,
            "processing_time_ms": 0,
            "repair_timeout": False,
            "error": str(e)
        }

def create_enhancement_debug_image(original, enhanced, info):
    """
    创建增强效果对比调试图像
    """
    try:
        # 确保图像是相同尺寸
        if original.shape != enhanced.shape:
            enhanced = cv2.resize(enhanced, (original.shape[1], original.shape[0]))
        
        # 创建对比图像
        debug_image = np.zeros((original.shape[0], original.shape[1] * 2 + 20, 3), dtype=np.uint8)
        
        # 左侧：原图
        if len(original.shape) == 3:
            debug_image[:, :original.shape[1]] = original
        else:
            debug_image[:, :original.shape[1]] = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
        
        # 右侧：增强图
        if len(enhanced.shape) == 3:
            debug_image[:, original.shape[1] + 20:] = enhanced
        else:
            debug_image[:, original.shape[1] + 20:] = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
        # 添加分隔线
        cv2.line(debug_image, (original.shape[1] + 10, 0), 
                (original.shape[1] + 10, original.shape[0]), (255, 255, 255), 2)
        
        # 添加文字说明
        cv2.putText(debug_image, "Original", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(debug_image, "Enhanced", (original.shape[1] + 30, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # 添加处理信息
        info_text = f"Time: {info['processing_time_ms']:.1f}ms"
        if info['enhancement_applied']:
            info_text += " | CLAHE: Yes"
        if info['repair_applied']:
            info_text += " | Repair: Yes"
        
        cv2.putText(debug_image, info_text, (10, original.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        
        return debug_image
        
    except Exception as e:
        logger.warning(f"调试图像创建失败: {e}")
        return original

# 测试函数
if __name__ == "__main__":
    import time
    import cv2
    import numpy as np
    
    # 创建测试图像
    test_image = np.ones((400, 300, 3), dtype=np.uint8) * 120
    
    # 添加一些文字和边缘
    cv2.putText(test_image, "INDUSTRY", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (80, 80, 80), 2)
    cv2.rectangle(test_image, (20, 20), (280, 380), (100, 100, 100), 2)
    
    print("测试图像创建完成")
    
    # 测试预处理管道
    processed, info = preprocess_for_ocr(test_image)
    debug_img = create_enhancement_debug_image(test_image, processed, info)
    
    print(f"处理完成，耗时: {info['processing_time_ms']:.2f}ms")
    print(f"增强应用: {info['enhancement_applied']}")
    print(f"修复应用: {info['repair_applied']}")
    print(f"金属表面: {info['metal_surface']}")
    print("预处理管道测试完成")