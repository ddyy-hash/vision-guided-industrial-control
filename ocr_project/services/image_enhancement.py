import cv2
import numpy as np
import time
from loguru import logger

def adaptive_histogram_equalization(image):
    """
    自适应直方图均衡 - 阶段二实现
    针对工业金属表面逆光问题
    """
    try:
        # 转换为LAB颜色空间，单独处理亮度通道
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 创建CLAHE对象 - 限制对比度2.0，分块8×8
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        # 对亮度通道应用CLAHE
        l_enhanced = clahe.apply(l)
        
        # 合并通道
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        
        # 转换回BGR
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        logger.debug(f"CLAHE增强完成: {image.shape} -> {enhanced.shape}")
        return enhanced
        
    except Exception as e:
        logger.warning(f"CLAHE增强失败: {e}, 返回原图")
        return image

def edge_preserving_sharpen(image, amount=1.0):
    """
    边缘保持锐化 - 简单版本
    仅对边缘层进行锐化，抑制背景噪声
    """
    try:
        # 高斯模糊获取低频分量
        blurred = cv2.GaussianBlur(image, (0, 0), 3)
        
        # 计算高频分量（边缘）
        high_freq = cv2.subtract(image, blurred)
        
        # 对高频分量进行锐化
        sharpened = cv2.addWeighted(image, 1.0, high_freq, amount, 0)
        
        # 限制像素值范围
        sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
        
        logger.debug(f"边缘锐化完成，强度: {amount}")
        return sharpened
        
    except Exception as e:
        logger.warning(f"边缘锐化失败: {e}, 返回原图")
        return image

def enhance_industrial_image(image, enable_clahe=True, enable_sharpen=True):
    """
    工业图像增强主函数 - 阶段二基础版本
    组合CLAHE和边缘锐化
    """
    try:
        logger.info("开始工业图像增强处理")
        start_time = time.time()
        
        result = image.copy()
        
        # 阶段1: CLAHE自适应直方图均衡
        if enable_clahe:
            result = adaptive_histogram_equalization(result)
            logger.debug("CLAHE处理完成")
        
        # 阶段2: 边缘保持锐化
        if enable_sharpen:
            result = edge_preserving_sharpen(result, amount=0.8)
            logger.debug("边缘锐化完成")
        
        processing_time = (time.time() - start_time) * 1000
        logger.info(f"图像增强处理完成，耗时: {processing_time:.2f}ms")
        
        return result
        
    except Exception as e:
        logger.error(f"工业图像增强失败: {e}")
        return image

# 测试函数
if __name__ == "__main__":
    import time
    import cv2
    import numpy as np
    
    # 创建测试图像
    test_image = np.ones((400, 300, 3), dtype=np.uint8) * 100
    cv2.putText(test_image, "TEST", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 3, (150, 150, 150), 8)
    
    print("测试图像创建完成")
    
    # 测试增强功能
    enhanced = enhance_industrial_image(test_image)
    
    print(f"原图形状: {test_image.shape}")
    print(f"增强后形状: {enhanced.shape}")
    print("功能测试完成")