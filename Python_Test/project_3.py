"""INTEL REALSENSE DEPTH CAMERA D435i 颜色识别工程
    @Time   2023.10.24
    @Author SSC
"""

import pyrealsense2 as rs
import numpy as np
import cv2

#############################
# 基础设置段（Intel 标准例程）
#############################

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()

# Get device product line for setting a supporting resolution
pipeline_wrapper = rs.pipeline_wrapper(pipeline)
pipeline_profile = config.resolve(pipeline_wrapper)
device = pipeline_profile.get_device()
device_product_line = str(device.get_info(rs.camera_info.product_line))

found_rgb = False
for s in device.sensors:
    if s.get_info(rs.camera_info.name) == 'RGB Camera':
        found_rgb = True
        break
if not found_rgb:
    print("The demo requires Depth camera with Color sensor")
    exit(0)

config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

if device_product_line == 'L500':
    config.enable_stream(rs.stream.color, 960, 540, rs.format.bgr8, 30)
else:
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start streaming
pipeline.start(config)

# 全局定义段
# 1. 饱和度增强定义
# 调节通道强度
lutEqual = np.array([i for i in range(256)]).astype("uint8")
lutRaisen = np.array([int(102+0.6*i) for i in range(256)]).astype("uint8")
# 调节饱和度
lutSRaisen = np.dstack((lutEqual, lutRaisen, lutEqual))  # Saturation raisen
# 2. 掩膜阈值定义
lower_purple = np.array([137, 143, 0])
upper_purple = np.array([179, 203, 255])
lower_red = np.array([117, 143, 0])
upper_red = np.array([133, 255, 255])
lower_blue = np.array([0, 159, 0])
upper_blue = np.array([16, 255, 255])
# 3. 结构元素定义
kernel = np.ones((3, 3), np.uint8)

#############################
# 运行段
#############################
try:
    while True:
        ##############################
        # 接收颜色图像数据
        ##############################
        # Wait for a coherent pair of frames: depth and color
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue

        # Convert images to numpy arrays
        color_image = np.asanyarray(color_frame.get_data())
        # cv2.imshow('color_image',color_image)
        # print(color_image.shape)

        """
            图像处理段
        """
        """
            1. 饱和度增强
        """
        hsv = cv2.cvtColor(color_image, cv2.COLOR_RGB2HSV)  # 色彩空间转换, RGB->HSV

        # cv2.imshow('hsv', hsv)
        blendSRaisen = cv2.LUT(hsv, lutSRaisen)             # 饱和度增大
        # img_enhance_saturation = cv2.cvtColor(blendSRaisen, cv2.COLOR_HSV2RGB)
        # cv2.imshow('img_enhance_saturation',img_enhance_saturation)
        """
            2. 掩膜创建
        """
        purple_mask = cv2.inRange(blendSRaisen, lower_purple, upper_purple)
        purple_img = cv2.bitwise_and(
            color_image, color_image, mask=purple_mask)
        # cv2.imshow('result',purple_img)
        red_mask = cv2.inRange(blendSRaisen, lower_red, upper_red)
        red_img = cv2.bitwise_and(color_image, color_image, mask=red_mask)
        # cv2.imshow('result',red_img)
        blue_mask = cv2.inRange(blendSRaisen, lower_blue, upper_blue)
        blue_img = cv2.bitwise_and(color_image, color_image, mask=blue_mask)
        """
            3. 滤波
        """
        # purple_img = cv2.GaussianBlur(purple_img, (3, 3), 0)
        # red_img = cv2.GaussianBlur(red_img, (3, 3), 0)
        purple_img = cv2.medianBlur(purple_img, 5)
        red_img = cv2.medianBlur(red_img, 5)
        blue_img = cv2.medianBlur(blue_img, 5)
        """
            4. 二值化
        """
        purple_gray = cv2.cvtColor(purple_img, cv2.COLOR_RGB2GRAY)
        red_gray = cv2.cvtColor(red_img, cv2.COLOR_BGR2GRAY)
        blue_gray = cv2.cvtColor(blue_img, cv2.COLOR_BGR2GRAY)
        # purple_gray = cv2.GaussianBlur(purple_gray, (3, 3), 0)
        # red_gray = cv2.GaussianBlur(red_gray, (3, 3), 0)
        # cv2.imshow('result',purple_gray)
        # purple_thre = cv2.adaptiveThreshold(purple_gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,5,-10)
        # red_thre = cv2.adaptiveThreshold(red_gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,5,-10)
        res, purple_thre = cv2.threshold(
            purple_gray, 0, 255, cv2.THRESH_BINARY)
        res, red_thre = cv2.threshold(
            red_gray, 0, 255, cv2.THRESH_BINARY)
        res, blue_thre = cv2.threshold(
            blue_gray, 0, 255, cv2.THRESH_BINARY)
        # cv2.imshow('result', purple_thre)
        # cv2.imshow('result', red_thre)

        purple_thre = cv2.morphologyEx(purple_thre, cv2.MORPH_OPEN, kernel)
        red_thre = cv2.morphologyEx(red_thre, cv2.MORPH_OPEN, kernel)
        blue_thre = cv2.morphologyEx(blue_thre, cv2.MORPH_OPEN, kernel)
        purple_thre = cv2.morphologyEx(purple_thre, cv2.MORPH_CLOSE, kernel)
        red_thre = cv2.morphologyEx(red_thre, cv2.MORPH_CLOSE, kernel)
        blue_thre = cv2.morphologyEx(blue_thre, cv2.MORPH_CLOSE, kernel)
        cv2.imshow('result_thre', red_thre)
        """
            5. 球的检测
        """
        # 先进行霍夫圆变换
        red_circles = cv2.HoughCircles(red_thre, cv2.HOUGH_GRADIENT_ALT,
                                       1.5, 20, param1=30, param2=0.50, minRadius=10, maxRadius=200)
        # 如果找到了球，则直接判定
        if red_circles is not None:
            filter_circle = []
            red_circles = np.uint16(np.around(red_circles))
            for cir_ in red_circles:
                cir = cir_[0]
                # 凹凸判断，通过创建掩膜进行逻辑与进行凹凸性判断
                x = cir[0]
                y = cir[1]
                r = cir[2]
                red_circle_mask = np.zeros_like(red_thre)
                cv2.circle(red_circle_mask, (x, y), r, 255, thickness=-1)
                pixel_count = np.sum(np.logical_and(
                    red_circle_mask, red_thre) > 0)
                if pixel_count > 0.9 * np.pi * r * r:
                    filter_circle.append((x, y, r))
            if len(filter_circle) > 0:
                print(filter_circle)
                for cir_ in filter_circle:
                    cv2.circle(
                        color_image, (cir_[0], cir_[1]), cir_[2], (0, 255, 255), 2)
                    cv2.circle(color_image, (cir_[0], cir_[1]), 2, (255, 255, 0), 2)
            else:
                # 提取轮廓
                contours_red, hierarchy_red = cv2.findContours(
                    red_thre, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(
                    color_image, contours_red, -1, (0, 255, 255), 1)
                if not contours_red:
                    pass
                else:
                    # 寻找最大面积的轮廓
                    areas_red = []
                    for c in range(len(contours_red)):
                        areas_red.append(cv2.contourArea(contours_red[c]))

                    max_id_red = areas_red.index(max(areas_red))
                    print(max_id_red)
                    # 椭圆拟合
                    if contours_red[max_id_red].size < 50:
                        pass
                    else:
                        (x_red, y_red), radius_red = cv2.minEnclosingCircle(
                            contours_red[max_id_red])
                        center_red = (int(x_red), int(y_red))
                        radius_red = int(radius_red)
                        cv2.circle(color_image, center_red,
                                   radius_red, (0, 0, 255), 3)

        purple_circles = cv2.HoughCircles(purple_thre, cv2.HOUGH_GRADIENT_ALT,
                                       1.5, 20, param1=30, param2=0.50, minRadius=10, maxRadius=200)
        # 如果找到了球，则直接判定
        if purple_circles is not None:
            filter_circle = []
            purple_circles = np.uint16(np.around(purple_circles))
            for cir_ in purple_circles:
                cir = cir_[0]
                # 凹凸判断，通过创建掩膜进行逻辑与进行凹凸性判断
                x = cir[0]
                y = cir[1]
                r = cir[2]
                purple_circle_mask = np.zeros_like(purple_thre)
                cv2.circle(purple_circle_mask, (x, y), r, 255, thickness=-1)
                pixel_count = np.sum(np.logical_and(
                    purple_circle_mask, purple_thre) > 0)
                if pixel_count > 0.9 * np.pi * r * r:
                    filter_circle.append((x, y, r))
            if len(filter_circle) > 0:
                print(filter_circle)
                for cir_ in filter_circle:
                    cv2.circle(
                        color_image, (cir_[0], cir_[1]), cir_[2], (0, 255, 255), 2)
                    cv2.circle(color_image, (cir_[0], cir_[1]), 2, (255, 255, 0), 2)
            else:
                # 提取轮廓
                contours_purple, hierarchy_purple = cv2.findContours(
                    purple_thre, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(
                    color_image, contours_purple, -1, (0, 255, 255), 1)
                if not contours_purple:
                    pass
                else:
                    # 寻找最大面积的轮廓
                    areas_purple = []
                    for c in range(len(contours_purple)):
                        areas_purple.append(cv2.contourArea(contours_purple[c]))

                    max_id_purple = areas_purple.index(max(areas_purple))
                    print(max_id_purple)
                    # 椭圆拟合
                    if contours_purple[max_id_purple].size < 50:
                        pass
                    else:
                        (x_purple, y_purple), radius_purple = cv2.minEnclosingCircle(
                            contours_purple[max_id_purple])
                        center_purple = (int(x_purple), int(y_purple))
                        radius_purple = int(radius_purple)
                        cv2.circle(color_image, center_purple,
                                   radius_purple, (0, 0, 255), 3)
                        
        # 先进行霍夫圆变换
        blue_circles = cv2.HoughCircles(blue_thre, cv2.HOUGH_GRADIENT_ALT,
                                       1.5, 20, param1=30, param2=0.50, minRadius=10, maxRadius=200)
        # 如果找到了球，则直接判定
        if blue_circles is not None:
            filter_circle = []
            blue_circles = np.uint16(np.around(blue_circles))
            for cir_ in blue_circles:
                cir = cir_[0]
                # 凹凸判断，通过创建掩膜进行逻辑与进行凹凸性判断
                x = cir[0]
                y = cir[1]
                r = cir[2]
                blue_circle_mask = np.zeros_like(blue_thre)
                cv2.circle(blue_circle_mask, (x, y), r, 255, thickness=-1)
                pixel_count = np.sum(np.logical_and(
                    blue_circle_mask, blue_thre) > 0)
                if pixel_count > 0.9 * np.pi * r * r:
                    filter_circle.append((x, y, r))
            if len(filter_circle) > 0:
                print(filter_circle)
                for cir_ in filter_circle:
                    cv2.circle(
                        color_image, (cir_[0], cir_[1]), cir_[2], (0, 255, 255), 2)
                    cv2.circle(color_image, (cir_[0], cir_[1]), 2, (255, 255, 0), 2)
            else:
                # 提取轮廓
                contours_blue, hierarchy_blue = cv2.findContours(
                    blue_thre, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(
                    color_image, contours_blue, -1, (0, 255, 255), 1)
                if not contours_blue:
                    pass
                else:
                    # 寻找最大面积的轮廓
                    areas_blue = []
                    for c in range(len(contours_blue)):
                        areas_blue.append(cv2.contourArea(contours_blue[c]))

                    max_id_blue = areas_blue.index(max(areas_blue))
                    print(max_id_blue)
                    # 椭圆拟合
                    if contours_blue[max_id_blue].size < 50:
                        pass
                    else:
                        (x_blue, y_blue), radius_blue = cv2.minEnclosingCircle(
                            contours_blue[max_id_blue])
                        center_blue = (int(x_blue), int(y_blue))
                        radius_blue = int(radius_blue)
                        cv2.circle(color_image, center_blue,
                                   radius_blue, (0, 0, 255), 3)
                        
        cv2.imshow('result', color_image)
        print("--------------")

        key = cv2.waitKey(1)
        if key == 27:
            break


finally:

    # Stop streaming
    pipeline.stop()
