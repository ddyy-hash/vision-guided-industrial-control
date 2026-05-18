import cv2
import numpy as np
import colorsys
import logging
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)

# 预定义的5级能耗等级标准颜色（RGB格式） - 基于实际能效标签调整
STANDARD_COLORS = {
    1: (0, 100, 0),     # 深绿色 - 1级（最节能）
    2: (0, 200, 0),     # 绿色 - 2级
    3: (255, 255, 0),   # 黄色 - 3级
    4: (255, 140, 0),   # 橙色 - 4级
    5: (200, 50, 50)    # 红色 - 5级（进一步调整，更接近实际能效红色）
}

# 能效等级颜色名称
ENERGY_LEVEL_NAMES = {
    1: "深绿色",
    2: "绿色",
    3: "黄色",
    4: "橙色",
    5: "红色"
}

def filter_blue_white_black_colors(image):
    """严格过滤掉蓝色、白色、黑色，返回剩余的有效颜色"""
    try:
        # 转换为HSV颜色空间
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # 定义忽略的颜色范围（HSV空间）
        # 蓝色范围 - 扩大范围以覆盖更多蓝色调
        blue_lower = np.array([90, 40, 40])    # 扩大Hue范围，降低饱和度阈值
        blue_upper = np.array([150, 255, 255]) # 覆盖更多蓝色调
        
        # 白色范围
        white_lower = np.array([0, 0, 200])    # 降低亮度阈值
        white_upper = np.array([180, 50, 255]) # 扩大饱和度范围
        
        # 黑色范围
        black_lower = np.array([0, 0, 0])
        black_upper = np.array([180, 255, 40]) # 提高亮度阈值
        
        # 灰色范围
        gray_lower = np.array([0, 0, 30])      # 降低亮度阈值
        gray_upper = np.array([180, 80, 200])  # 扩大饱和度范围
        
        # 创建忽略颜色掩膜
        blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        black_mask = cv2.inRange(hsv, black_lower, black_upper)
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        # 合并所有要忽略的掩膜
        ignore_mask = blue_mask | white_mask | black_mask | gray_mask
        valid_mask = ~ignore_mask
        
        # 应用掩膜
        filtered_image = image.copy()
        filtered_image[ignore_mask.astype(bool)] = [0, 0, 0]
        
        # 额外的RGB空间过滤（确保蓝色被完全过滤）
        rgb = image.copy()
        # RGB空间蓝色过滤：B值高，R和G值相对较低
        blue_rgb_mask = ((rgb[:, :, 2] > 100) &  # B通道高
                        (rgb[:, :, 0] < 150) &   # R通道低
                        (rgb[:, :, 1] < 150))    # G通道低
        
        # 更新有效掩膜（同步更新）
        valid_mask = valid_mask & ~blue_rgb_mask
        filtered_image[blue_rgb_mask] = [0, 0, 0]
        
        logger.info(f"颜色过滤: 原始像素 {image.size//3}, 过滤后有效像素 {np.sum(valid_mask)}")
        return filtered_image, valid_mask
        
    except Exception as e:
        logger.error(f"颜色过滤失败: {e}")
        return image, None

def detect_energy_level_by_color_mapping(valid_colors, arrow_color):
    """根据检测到的颜色动态映射能效等级序列 - 使用详细调试脚本的正确算法"""
    try:
        if not valid_colors:
            return 1  # 默认1级
            
        # 如果箭头颜色为空，返回默认等级
        if arrow_color is None:
            return 1
            
        logger.info(f"检测到的颜色数量: {len(valid_colors)}")
        for i, color in enumerate(valid_colors):
            logger.info(f"  颜色 {i+1}: RGB{tuple(color)}")
        
        logger.info(f"箭头颜色: RGB{tuple(arrow_color)}")
        
        # 步骤1: 将检测到的颜色映射到标准能效颜色（使用简单欧几里得距离，如调试脚本）
        logger.info(f"步骤1: 颜色映射到标准能效等级")
        mapped_levels = []
        for i, color in enumerate(valid_colors):
            min_distance = float('inf')
            best_level = 1
            
            # 计算与每个标准颜色的距离（使用简单欧几里得距离，如调试脚本）
            for level, standard_color in STANDARD_COLORS.items():
                distance = np.linalg.norm(np.array(color) - np.array(standard_color))
                if distance < min_distance:
                    min_distance = distance
                    best_level = level
            
            mapped_levels.append(best_level)
            logger.info(f"  颜色 {i+1} -> 标准{best_level}级 {ENERGY_LEVEL_NAMES[best_level]} (距离: {min_distance:.2f})")
        
        # 步骤2: 去重并排序，得到实际存在的标准能效等级
        actual_standard_levels = sorted(set(mapped_levels))
        logger.info(f"实际存在的标准等级: {actual_standard_levels}")
        
        # 步骤3: 创建标准等级到实际等级的重新映射
        level_mapping = {}
        for actual_index, standard_level in enumerate(actual_standard_levels):
            level_mapping[standard_level] = actual_index + 1
        
        logger.info(f"等级重新映射表: {level_mapping}")
        
        # 步骤4: 计算箭头颜色与每个标准颜色的距离
        logger.info(f"步骤4: 箭头颜色匹配")
        min_distance = float('inf')
        best_match_standard_level = 1
        
        for level, standard_color in STANDARD_COLORS.items():
            # 只考虑实际存在的标准能效等级
            if level not in actual_standard_levels:
                continue
                
            distance = np.linalg.norm(np.array(arrow_color) - np.array(standard_color))
            logger.info(f"  标准{level}级 {ENERGY_LEVEL_NAMES[level]}: 距离 {distance:.2f}")
            if distance < min_distance:
                min_distance = distance
                best_match_standard_level = level
        
        # 步骤5: 将匹配的标准等级映射为实际等级
        actual_energy_level = level_mapping.get(best_match_standard_level, 1)
        
        logger.info(f"步骤5: 最终结果")
        logger.info(f"  箭头颜色匹配到: 标准{best_match_standard_level}级 {ENERGY_LEVEL_NAMES[best_match_standard_level]}")
        logger.info(f"  重新映射为: 实际{actual_energy_level}级能效")
        
        # 记录到日志
        logger.info(f"颜色映射完成: 检测到的标准等级{actual_standard_levels}, 映射表{level_mapping}")
        logger.info(f"箭头颜色匹配: 标准等级{best_match_standard_level} -> 实际等级{actual_energy_level}, 距离{min_distance:.2f}")
        
        return actual_energy_level
        
    except Exception as e:
        logger.error(f"能效等级映射失败: {e}")
        return 1

def extract_valid_colors_from_label(label_region):
    """从标签区域提取所有非蓝、白、黑的有效颜色，并映射到标准能效颜色"""
    try:
        # 过滤掉蓝、白、黑
        filtered_image, valid_mask = filter_blue_white_black_colors(label_region)
        
        # 如果没有有效掩膜或没有有效像素，返回空列表
        if valid_mask is None or not np.any(valid_mask):
            return []
            
        # 提取所有有效像素 - 使用过滤后的图像，避免黑色像素被错误识别
        valid_pixels = filtered_image[valid_mask.astype(bool)]
        
        # 进一步过滤掉黑色像素（[0,0,0]）
        non_black_mask = np.any(valid_pixels > 0, axis=1)
        valid_pixels = valid_pixels[non_black_mask]
        
        if len(valid_pixels) == 0:
            return []
            
        # 使用K-means聚类找到主要颜色
        # 限制聚类中心最多为5个（对应5种标准能效颜色）
        k = min(5, len(valid_pixels))
        if k < 1:
            return []
            
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(valid_pixels.astype(np.float32), k, np.zeros((len(valid_pixels), 1), dtype=np.int32), criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # 获取每个聚类的像素数量
        unique, counts = np.unique(labels, return_counts=True)
        
        # 按像素数量排序
        sorted_indices = np.argsort(counts)[::-1]  # 降序排列
        detected_colors = []
        
        # 收集所有检测到的颜色
        for idx in sorted_indices:
            color = centers[idx].astype(int)
            color = np.clip(color, 0, 255)
            
            # 计算HSV值
            r, g, b = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
            cmax = max(r, g, b)
            cmin = min(r, g, b)
            delta = cmax - cmin
            
            if delta == 0:
                h = 0
            elif cmax == r:
                h = 60 * (((g - b) / delta) % 6)
            elif cmax == g:
                h = 60 * (((b - r) / delta) + 2)
            else:  # cmax == b
                h = 60 * (((r - g) / delta) + 4)
            
            s = 0 if cmax == 0 else (delta / cmax) * 100
            v = cmax * 100
            
            # 过滤背景色
            if s < 20 or v > 92:
                logger.info(f"过滤背景色: RGB{tuple(color)} -> HSV({h:.1f}, {s:.1f}, {v:.1f})")
                continue
            
            detected_colors.append(color)
            logger.info(f"检测到颜色: RGB{tuple(color)} -> HSV({h:.1f}, {s:.1f}, {v:.1f})")
        
        logger.info(f"检测到 {len(detected_colors)} 个有效颜色")
        return detected_colors
        
    except Exception as e:
        logger.error(f"提取有效颜色失败: {e}")
        return []

def detect_arrow_color_from_right(label_region):
    """从右侧开始向左扫描，检测箭头颜色"""
    try:
        height, width, _ = label_region.shape
        
        # 从右侧开始向左扫描
        scan_step = max(1, width // 30)
        for scan_x in range(width - 1, -1, -scan_step):
            scan_end = min(scan_x + scan_step, width)
            column_region = label_region[:, scan_x:scan_end, :]
            
            # 过滤掉蓝、白、黑
            filtered_column, valid_mask = filter_blue_white_black_colors(column_region)
            
            # 检查有效掩膜是否不为None且有有效像素
            if valid_mask is not None and np.any(valid_mask):
                # 提取有效像素
                valid_pixels = column_region[valid_mask.astype(bool)]
                
                if len(valid_pixels) > 0:
                    # 使用中值作为箭头颜色
                    arrow_color = np.median(valid_pixels, axis=0).astype(int)
                    arrow_color = np.clip(arrow_color, 0, 255)
                    
                    logger.info(f"从右侧检测到箭头颜色: {arrow_color}")
                    return arrow_color
                    
        logger.info("未检测到箭头颜色")
        return None
        
    except Exception as e:
        logger.error(f"检测箭头颜色失败: {e}")
        return None


def extract_dominant_color(region, k=3):
    """使用K-means聚类提取区域的主要颜色，完全忽略白色和蓝色像素"""
    try:
        # 将区域转换为二维像素数组
        pixels = region.reshape(-1, 3).astype(np.float32)
        
        # 过滤白色和蓝色像素
        # 白色：RGB值都大于230
        # 蓝色：B值高，R和G值低（B > 150, R < 100, G < 100）
        non_white_mask = np.any(pixels < [230, 230, 230], axis=1)
        non_blue_mask = ~((pixels[:, 2] > 150) & (pixels[:, 0] < 100) & (pixels[:, 1] < 100))
        valid_mask = non_white_mask & non_blue_mask
        
        valid_pixels = pixels[valid_mask]
        
        # 如果没有有效像素，则使用整个区域但过滤白色
        if len(valid_pixels) == 0:
            valid_pixels = pixels[non_white_mask]
            if len(valid_pixels) == 0:
                valid_pixels = pixels
        
        # 如果有效像素太少，则使用整个区域但过滤白色
        if len(valid_pixels) < k:
            valid_pixels = pixels[non_white_mask]
            if len(valid_pixels) == 0:
                valid_pixels = pixels
        
        # 定义终止条件
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        
        # 应用K-means聚类
        _, labels, centers = cv2.kmeans(valid_pixels, k, np.zeros((len(valid_pixels), 1), dtype=np.int32), criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # 计算每个簇的像素数量
        unique, counts = np.unique(labels, return_counts=True)
        
        # 按像素数量排序，找到最大的簇（主要颜色）
        dominant_index = unique[np.argmax(counts)]
        dominant_color = centers[dominant_index].astype(int)
        
        # 如果主要颜色是白色或蓝色，则选择次主要颜色
        if np.all(dominant_color > [230, 230, 230]) or ((dominant_color[2] > 150) and (dominant_color[0] < 100) and (dominant_color[1] < 100)):
            for i in range(k):
                if i != dominant_index and not (np.all(centers[i] > [230, 230, 230]) or ((centers[i][2] > 150) and (centers[i][0] < 100) and (centers[i][1] < 100))):
                    dominant_color = centers[i].astype(int)
                    break
        
        return dominant_color
    except Exception as e:
        logger.warning(f"聚类提取颜色失败: {e}，使用中值作为备选")
        # 备选方案：使用区域的中值颜色（过滤白色和蓝色）
        non_white_mask = np.any(region < [230, 230, 230], axis=-1)
        non_blue_mask = ~((region[:, :, 2] > 150) & (region[:, :, 0] < 100) & (region[:, :, 1] < 100))
        valid_mask = non_white_mask & non_blue_mask
        
        if np.any(valid_mask):
            return np.median(region[valid_mask], axis=0).astype(int)
        else:
            return np.median(region, axis=(0, 1)).astype(int)


def detect_level_count(color_bar):
    """检测能耗标签等级数（基于颜色条投影分析，支持1-6级）"""
    try:
        # 转换为灰度图
        gray = cv2.cvtColor(color_bar, cv2.COLOR_RGB2GRAY)
        
        # 纵向投影（每行的平均灰度值）
        row_means = np.mean(gray, axis=1)
        
        # 使用高斯滤波平滑投影曲线
        smoothed = cv2.GaussianBlur(row_means, (5, 5), 0)
        
        # 计算一阶导数（颜色变化）
        derivatives = np.abs(np.diff(smoothed))
        
        # 寻找显著的颜色变化点（峰值）
        peaks, _ = find_peaks(derivatives, height=np.percentile(derivatives, 80), distance=10)
        
        # 等级数 = 峰值数 + 1
        level_count = len(peaks) + 1
        
        # 限制在合理的范围内（1-6级）
        level_count = max(1, min(level_count, 6))
        
        logger.info(f"投影分析检测到 {level_count} 个等级，峰值位置: {peaks}")
        return level_count
        
    except Exception as e:
        logger.warning(f"投影分析失败: {e}，使用默认3级")
        return 3


def correct_label_perspective(image, contour):
    """透视变换矫正标签几何变形"""
    try:
        # 获取轮廓的近似多边形
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # 如果是四边形，进行透视变换
        if len(approx) == 4:
            # 获取四个顶点
            pts = approx.reshape(4, 2)
            
            # 计算目标矩形尺寸
            width = max(np.linalg.norm(pts[0] - pts[1]),
                       np.linalg.norm(pts[2] - pts[3]))
            height = max(np.linalg.norm(pts[0] - pts[3]),
                        np.linalg.norm(pts[1] - pts[2]))
            
            # 确保最小尺寸
            width = max(int(width), 100)
            height = max(int(height), 100)
            
            # 目标点（标准矩形）
            dst_pts = np.array([[0, 0], [width, 0], [width, height], [0, height]],
                              dtype=np.float32)
            
            # 计算透视变换矩阵
            M = cv2.getPerspectiveTransform(pts.astype(np.float32), dst_pts)
            
            # 应用透视变换
            corrected = cv2.warpPerspective(image, M, (width, height))
            
            logger.info(f"透视变换矫正成功: 原尺寸{image.shape[:2]} -> 矫正后{corrected.shape[:2]}")
            return corrected, True, M
        
        return image, False, None
        
    except Exception as e:
        logger.warning(f"透视变换矫正失败: {e}")
        return image, False, None


def detect_energy_label(image: np.ndarray) -> dict:
    """改进的能效检测算法 - 支持5级能效标准和动态映射"""
    try:
        # 输入验证
        if image is None or image.size == 0:
            raise ValueError("输入图像为空或无效")
        
        # 转换为RGB颜色空间
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width, _ = img_rgb.shape
        
        # 确保图像尺寸有效
        if height < 10 or width < 10:
            raise ValueError("图像尺寸太小，无法处理")

        # 1. 标签区域检测（使用原算法的标签检测逻辑）
        enhanced_rgb = img_rgb.copy()
        
        # 转换为HSV空间检测颜色区域
        hsv = cv2.cvtColor(enhanced_rgb, cv2.COLOR_RGB2HSV)

        # 寻找颜色条区域（非白色区域）
        lower_color = np.array([0, 30, 30])  # 降低饱和度阈值，适应光照变化
        upper_color = np.array([180, 255, 255])
        color_mask = cv2.inRange(hsv, lower_color, upper_color)

        # 形态学操作增强区域
        kernel = np.ones((5, 5), np.uint8)
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)

        # 查找轮廓
        contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        label_contour = None
        max_area = 0

        # 初始化边界变量
        x, y, w, h = 0, 0, width, height

        # 寻找最大的矩形轮廓（标签区域）
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1000:  # 过滤小区域
                continue

            # 计算轮廓的边界矩形
            contour_x, contour_y, contour_w, contour_h = cv2.boundingRect(contour)
            aspect_ratio = contour_w / float(contour_h)

            # 根据宽高比和面积筛选标签区域
            if 0.4 < aspect_ratio < 2.0 and area > max_area:  # 放宽宽高比范围
                max_area = area
                label_contour = contour
                x, y, w, h = contour_x, contour_y, contour_w, contour_h

        # 透视变换矫正标志
        perspective_corrected = False
        transformation_matrix = None
        
        if label_contour is None:
            # 如果未检测到标签，使用整个图像
            logger.warning("未检测到标签轮廓，使用全图分析")
            label_region = enhanced_rgb
            label_height, label_width = height, width
        else:
            # 获取标签边界
            label_region = enhanced_rgb[y:y + h, x:x + w]
            
            # 禁用透视变换矫正（保留标签区域检测）
            # corrected_region, perspective_corrected, transformation_matrix = correct_label_perspective(
            #     label_region, label_contour
            # )
            
            # 始终使用原始标签区域，不进行透视变换
            perspective_corrected = False
            transformation_matrix = None
            logger.info("标签区域检测完成，禁用透视变换矫正")
            
            label_height, label_width, _ = label_region.shape

        # 2. 使用新算法检测有效颜色（过滤蓝、白、黑）
        valid_colors = extract_valid_colors_from_label(label_region)
        
        # 3. 从右侧检测箭头颜色
        arrow_color = detect_arrow_color_from_right(label_region)
        
        # 4. 动态映射能效等级
        detected_level = detect_energy_level_by_color_mapping(valid_colors, arrow_color)
        
        # 5. 创建调试图像
        debug_img = image.copy()

        # 绘制标签边界（如果检测到）
        if label_contour is not None:
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # 绘制标签检测状态（不显示透视变换）
            cv2.putText(debug_img, "Label Detected", (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # 绘制检测到的有效颜色
        for i, color in enumerate(valid_colors):
            y_pos = 30 + i * 30
            color_display = np.zeros((20, 20, 3), dtype=np.uint8)
            color_display[:, :] = color
            debug_img[y_pos:y_pos+20, 10:30] = cv2.cvtColor(color_display, cv2.COLOR_RGB2BGR)
            cv2.putText(debug_img, f"颜色 {i+1}: {color}", (40, y_pos + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 绘制箭头颜色
        if arrow_color is not None:
            arrow_display = np.zeros((20, 20, 3), dtype=np.uint8)
            arrow_display[:, :] = arrow_color
            debug_img[10:30, width-30:width-10] = cv2.cvtColor(arrow_display, cv2.COLOR_RGB2BGR)
            cv2.putText(debug_img, f"箭头: {arrow_color}", (width-150, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 绘制结果
        cv2.putText(debug_img, f"Energy Level: {detected_level}级",
                    (10, height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # 绘制检测到的颜色数量
        cv2.putText(debug_img, f"检测到 {len(valid_colors)} 个有效颜色",
                    (10, height - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # 绘制算法说明
        cv2.putText(debug_img, "新算法: 5级能效动态映射", (width - 250, height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 转换颜色值为前端需要的格式（正确的RGB格式）
        level_colors_rgb = []
        for color in valid_colors:
            level_colors_rgb.append([
                int(color[0]),  # R
                int(color[1]),  # G
                int(color[2])   # B
            ])

        arrow_color_rgb = [
            int(arrow_color[0]) if arrow_color is not None and len(arrow_color) > 0 else 0,  # R
            int(arrow_color[1]) if arrow_color is not None and len(arrow_color) > 1 else 0,  # G
            int(arrow_color[2]) if arrow_color is not None and len(arrow_color) > 2 else 0   # B
        ]

        return {
            "energy_level": f"{detected_level}级",
            "debug_image": debug_img,
            "level_colors": level_colors_rgb,
            "current_color": arrow_color_rgb,
            "perspective_corrected": perspective_corrected,
            "transformation_matrix": transformation_matrix.tolist() if transformation_matrix is not None else None,
            "detected_color_count": len(valid_colors),
            "algorithm_version": "v2"
        }

    except Exception as e:
        logger.error(f"能耗识别错误: {str(e)}")
        raise ValueError(f"能耗识别失败: {str(e)}")