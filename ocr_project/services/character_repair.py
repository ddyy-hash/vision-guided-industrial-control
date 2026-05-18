import cv2
import numpy as np
import time
from loguru import logger

def stroke_width_transform(image, max_processing_time=1.0):
    """
    笔画宽度变换 (SWT) - 优化版本
    检测字符笔画宽度，识别断裂区域，添加时间限制
    """
    try:
        start_time = time.time()
        
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 简化边缘检测 - 使用更快的参数
        edges = cv2.Canny(gray, 80, 200)
        
        # 简化梯度计算 - 使用更小的核
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=1)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=1)
        grad_direction = np.arctan2(grad_y, grad_x)
        
        # 初始化SWT图
        swt_map = np.full_like(gray, np.inf, dtype=np.float32)
        
        # 简化的射线传播算法 - 减少采样点
        height, width = gray.shape
        step_size = 2  # 增加步长减少计算量
        
        for y in range(1, height-1, step_size):
            # 检查处理时间
            if time.time() - start_time > max_processing_time:
                logger.warning("SWT计算超时，使用简化结果")
                break
                
            for x in range(1, width-1, step_size):
                if edges[y, x] > 0:  # 边缘点
                    # 沿梯度方向发射射线
                    dx = np.cos(grad_direction[y, x])
                    dy = np.sin(grad_direction[y, x])
                    
                    # 简化的射线传播
                    step = 0
                    max_steps = min(width, height) // 4  # 减少最大步数
                    
                    while step < max_steps:
                        step += 1
                        new_x = int(x + step * dx)
                        new_y = int(y + step * dy)
                        
                        if (0 <= new_x < width and 0 <= new_y < height):
                            if edges[new_y, new_x] > 0:  # 找到对边
                                stroke_width = np.sqrt((new_x - x)**2 + (new_y - y)**2)
                                if stroke_width < swt_map[y, x]:
                                    swt_map[y, x] = stroke_width
                                break
                        else:
                            break
        
        # 将无穷大替换为0，便于后续处理
        swt_map[np.isinf(swt_map)] = 0
        
        # 使用中值滤波平滑结果
        swt_map = cv2.medianBlur(swt_map.astype(np.float32), 3)
        
        processing_time = (time.time() - start_time) * 1000
        logger.debug(f"SWT计算完成，耗时: {processing_time:.2f}ms，形状: {swt_map.shape}")
        return swt_map
        
    except Exception as e:
        logger.warning(f"SWT计算失败: {e}")
        return np.zeros_like(image if len(image.shape) == 2 else image[:,:,0])

def detect_character_breaks(swt_map, min_width=1, max_width=2, normal_width=(5, 7), max_processing_time=0.5):
    """
    检测字符断裂区域 - 优化版本
    识别宽度突降到1-2像素的区域，添加时间限制
    """
    try:
        start_time = time.time()
        
        # 创建断裂掩码
        break_mask = np.zeros_like(swt_map, dtype=np.uint8)
        
        # 简化检测算法 - 减少采样点
        height, width = swt_map.shape
        step_size = 2  # 增加步长减少计算量
        
        for y in range(1, height-1, step_size):
            # 检查处理时间
            if time.time() - start_time > max_processing_time:
                logger.warning("断裂检测超时，使用简化结果")
                break
                
            for x in range(1, width-1, step_size):
                current_width = swt_map[y, x]
                
                # 检测宽度突降 (从正常宽度突降到断裂宽度)
                if min_width <= current_width <= max_width:
                    # 简化的周围检查 - 使用更小的邻域
                    y_start = max(0, y-1)
                    y_end = min(height, y+2)
                    x_start = max(0, x-1)
                    x_end = min(width, x+2)
                    
                    neighborhood = swt_map[y_start:y_end, x_start:x_end]
                    normal_count = np.sum((neighborhood >= normal_width[0]) &
                                        (neighborhood <= normal_width[1]))
                    
                    if normal_count > 0:  # 周围有正常笔画
                        break_mask[y, x] = 255
        
        # 使用形态学操作增强断裂区域
        kernel = np.ones((2, 2), np.uint8)
        break_mask = cv2.dilate(break_mask, kernel, iterations=1)
        
        processing_time = (time.time() - start_time) * 1000
        logger.debug(f"断裂检测完成，耗时: {processing_time:.2f}ms，发现断裂点数: {np.sum(break_mask > 0)}")
        return break_mask
        
    except Exception as e:
        logger.warning(f"断裂检测失败: {e}")
        return np.zeros_like(swt_map, dtype=np.uint8)

def repair_character_breaks(image, break_mask, dilation_size=1):
    """
    修复字符断裂
    对检测到的断裂区域进行1像素膨胀
    """
    try:
        # 创建修复核
        kernel = np.ones((dilation_size*2+1, dilation_size*2+1), np.uint8)
        
        # 对断裂区域进行膨胀
        repaired_mask = cv2.dilate(break_mask, kernel, iterations=1)
        
        # 获取修复区域的坐标
        repair_coords = np.where(repaired_mask > 0)
        
        if len(repair_coords[0]) == 0:
            return image
        
        # 创建结果图像
        result = image.copy()
        
        # 简单的灰度均值膨胀修复
        if len(image.shape) == 3:  # 彩色图像
            # 计算局部灰度均值
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            for i in range(len(repair_coords[0])):
                y, x = repair_coords[0][i], repair_coords[1][i]
                
                # 获取局部区域
                y_start = max(0, y-1)
                y_end = min(image.shape[0], y+2)
                x_start = max(0, x-1)
                x_end = min(image.shape[1], x+2)
                
                # 计算局部均值
                local_region = image[y_start:y_end, x_start:x_end]
                mean_color = np.mean(local_region, axis=(0, 1))
                
                # 应用修复
                result[y, x] = mean_color.astype(np.uint8)
        
        else:  # 灰度图像
            for i in range(len(repair_coords[0])):
                y, x = repair_coords[0][i], repair_coords[1][i]
                
                # 获取局部区域
                y_start = max(0, y-1)
                y_end = min(image.shape[0], y+2)
                x_start = max(0, x-1)
                x_end = min(image.shape[1], x+2)
                
                # 计算局部均值
                local_region = image[y_start:y_end, x_start:x_end]
                mean_value = np.mean(local_region)
                
                # 应用修复
                result[y, x] = int(mean_value)
        
        logger.debug(f"断裂修复完成，修复点数: {len(repair_coords[0])}")
        return result
        
    except Exception as e:
        logger.warning(f"断裂修复失败: {e}")
        return image

def repair_metal_characters(image, enable_swt=True, enable_repair=True, max_processing_time=2.0):
    """
    金属字符断裂修复主函数 - 优化版本
    组合SWT检测和断裂修复，添加时间限制和简化算法
    """
    try:
        logger.info("开始金属字符断裂修复处理")
        start_time = time.time()
        
        result = image.copy()
        swt_map = np.zeros_like(result if len(result.shape) == 2 else result[:,:,0])
        break_mask = np.zeros_like(result if len(result.shape) == 2 else result[:,:,0])
        
        # 阶段1: 笔画宽度变换检测（带时间限制）
        if enable_swt:
            remaining_time = max_processing_time - (time.time() - start_time)
            if remaining_time > 0.5:  # 至少保留0.5秒用于SWT
                swt_map = stroke_width_transform(result, max_processing_time=remaining_time)
                logger.debug("SWT检测完成")
            else:
                logger.warning("时间不足，跳过SWT检测")
                enable_swt = False
        
        # 阶段2: 断裂检测与修复（带时间限制）
        if enable_repair and enable_swt:
            remaining_time = max_processing_time - (time.time() - start_time)
            if remaining_time > 0.3:  # 至少保留0.3秒用于断裂修复
                break_mask = detect_character_breaks(swt_map, max_processing_time=remaining_time)
                result = repair_character_breaks(result, break_mask)
                logger.debug("断裂修复完成")
            else:
                logger.warning("时间不足，跳过断裂修复")
        
        processing_time = (time.time() - start_time) * 1000
        logger.info(f"字符修复处理完成，耗时: {processing_time:.2f}ms")
        
        return result, swt_map, break_mask
        
    except Exception as e:
        logger.error(f"金属字符修复失败: {e}")
        return image, np.zeros_like(image if len(image.shape) == 2 else image[:,:,0]), np.zeros_like(image if len(image.shape) == 2 else image[:,:,0])

# 测试函数
if __name__ == "__main__":
    import time
    import cv2
    import numpy as np
    
    # 创建模拟断裂字符的测试图像
    test_image = np.ones((200, 300), dtype=np.uint8) * 255
    
    # 绘制有断裂的字符
    cv2.line(test_image, (50, 100), (120, 100), 0, 6)  # 正常笔画
    cv2.line(test_image, (125, 100), (130, 100), 255, 2)  # 断裂
    cv2.line(test_image, (135, 100), (200, 100), 0, 6)  # 正常笔画
    
    print("测试图像创建完成")
    
    # 测试修复功能
    repaired, swt_map, break_mask = repair_metal_characters(test_image)
    
    print(f"原图形状: {test_image.shape}")
    print(f"修复后形状: {repaired.shape}")
    print(f"SWT图形状: {swt_map.shape}")
    print(f"断裂掩码形状: {break_mask.shape}")
    print("功能测试完成")