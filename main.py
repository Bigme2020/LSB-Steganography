from PIL import Image
import math
import re
import sys
import os
import numpy as np


def verify_binary(type, binary_msg):
    message = ""
    for i in range(0, len(binary_msg), 8):
        message += chr(int(binary_msg[i:i+8], 2))
    print(f'{type}verify', message)


def encrpt(type, img_path, message, output_path, x=0, y=0, width=0, height=0):
    is_rgb = type == 'rgb'  # 不是rgb就是alpha
    original_img = Image.open(img_path)
    img, left, top, right, bottom = getRectRegion(
        img_path, x, y, width, height)
    binary_messages = list("".join(format(ord(c), '08b')
                           for c in "DATA:" + message + ";"))

    r = img.getchannel('R')
    g = img.getchannel('G')
    b = img.getchannel('B')
    a = img.getchannel('A')
    r_data = list(r.getdata())
    g_data = list(g.getdata())
    b_data = list(b.getdata())
    a_data = list(a.getdata())

    currentBit = 0  # 当前需要填充的bit index，按照rgb来算，一个像素能填3个bit
    maxBitPerRow = width * 3 if is_rgb else width  # 每一行可填充的数量
    startSymbol = 's(('  # 行开始符号
    endSymbol = '))e'  # 行结束符号
    startSymbolBinary = "".join(format(ord(c), '08b')
                                for c in startSymbol)
    endSymbolBinary = "".join(format(ord(c), '08b')
                              for c in endSymbol)

    def fillIn(indexOfBit, bit):
        if (is_rgb):
            currentIndexOfPixel = math.floor(indexOfBit / 3)
            remainder = indexOfBit % 3
            if (remainder == 0):
                r_data[currentIndexOfPixel] = (
                    r_data[currentIndexOfPixel] & 254) | int(bit)
                indexOfBit += 1
            if (remainder == 1):
                g_data[currentIndexOfPixel] = (
                    g_data[currentIndexOfPixel] & 254) | int(bit)
                indexOfBit += 1
            if (remainder == 2):
                b_data[currentIndexOfPixel] = (
                    b_data[currentIndexOfPixel] & 254) | int(bit)
                indexOfBit += 1
        else:
            a_data[indexOfBit] = (
                a_data[indexOfBit] & 254) | int(bit)
            indexOfBit += 1
        return indexOfBit

    def is_fitable_end(endBinary, currentBit, maxBit):  # 这里判断当前bit是不是maxBit下最大8的整数倍的下一个bit
        currentRowBit = currentBit % maxBit
        max_times_of_eight = math.floor(((maxBit - len(endBinary)) -
                                         (maxBit - len(endBinary)) % 8) / 8)
        # 如果要 判断当前bit是不是8的整数倍，那么这里需要currentRowBit + 1，但是求下一个bit不需要
        return (currentRowBit / 8 == max_times_of_eight)

    binary_for_verify = ""

    while (len(binary_messages)):
        currentRow = math.floor(currentBit / maxBitPerRow)
        if (currentBit % maxBitPerRow == 0):
            for i, bit in enumerate(startSymbolBinary):
                # print('行头:', currentBit)
                binary_for_verify += bit
                currentBit = fillIn(currentBit, bit)
            continue

        if (is_fitable_end(endSymbolBinary, currentBit, maxBitPerRow)):
            for i, bit in enumerate(endSymbolBinary):
                # print('行尾:', currentBit)
                binary_for_verify += bit
                currentBit = fillIn(currentBit, bit)
            currentBit = (currentRow + 1) * maxBitPerRow
            continue

        # print('正常录入数据', currentBit)
        poped = binary_messages.pop(0)
        binary_for_verify += poped
        currentBit = fillIn(currentBit, poped)

    # 按照rgb顺序依次塞入信息
    if (is_rgb):
        r.putdata(r_data)
        g.putdata(g_data)
        b.putdata(b_data)
        verify_binary('RGB Verify', binary_for_verify)
        new_img = Image.merge("RGB", (r, g, b))
        original_img.paste(new_img, (left, top, right, bottom))
        original_img.save(output_path)
    else:
        a.putdata(a_data)
        img.putalpha(a)
        verify_binary('Alpha Verify', binary_for_verify)
        original_img.paste(img, (left, top, right, bottom))
        original_img.save(output_path)


def decrpt(type, img_path, x=0, y=0, width=0, height=0):
    is_positioned = x or y or width or height
    is_rgb = type == 'rgb'
    tuple = getRectRegion(
        img_path, x, y, width, height)
    img = tuple[0]
    r_data = img.getchannel('R').getdata()
    g_data = img.getchannel('G').getdata()
    b_data = img.getchannel('B').getdata()
    a_data = img.getchannel('A').getdata()

    # 读取二进制信息
    binary_message = ''

    # 这段代码运行效率超级慢 :(
    # pixelLength = img.width * img.height
    # for i in range(0, pixelLength):
    #     binary_message += str(r_data[i] & 1)
    #     binary_message += str(g_data[i] & 1)
    #     binary_message += str(b_data[i] & 1)

    # 利用 numpy 后效率指数倍上升 :)
    if (is_rgb):
        # 将像素数据转换成 3 维数组，每个像素有 3 个通道
        rgb_array = np.dstack((r_data, g_data, b_data))
        # 获取每个通道的最后一位二进制
        binary_array = np.bitwise_and(rgb_array, 1)
        # 将二进制数组转换成一维数组，方便后续拼接
        binary_array_flat = binary_array.ravel()
        # 拼接二进制字符串
        binary_message = ''.join(binary_array_flat.astype(str))
    else:
        pixelLength = img.width * img.height
        for i in range(0, pixelLength):
            binary_message += str(a_data[i] & 1)

    # 将二进制信息转换为文本
    message = ""

    message = find_msg_by_row(binary_message, 0)
    data_pattern = r'DATA:\s*(.*?);'
    match = re.search(data_pattern, message)
    if match:
        data = match.group(1)
        print(
            f'{"定位" if is_positioned else "全局"}搜索{"rgb" if is_rgb else "alpha"}加密信息', data)
    else:
        print(
            f'{"定位" if is_positioned else "全局"}搜索{"rgb" if is_rgb else "alpha"}加密信息未找到')


def binary_to_str(binary):
    return chr(int(binary, 2))


def find_msg_by_row(binary_message, current_bit=0):
    if (current_bit + 48 > len(binary_message)):
        return ''
    row_msg = ''
    index_of_bit = current_bit
    current_row_finded = False
    while (index_of_bit + 48 <= len(binary_message)):
        if (current_row_finded):
            if (binary_to_str(binary_message[index_of_bit:index_of_bit+8]) == ')' and binary_to_str(binary_message[index_of_bit+8:index_of_bit+16]) == ')' and binary_to_str(binary_message[index_of_bit+16:index_of_bit+24]) == 'e'):
                index_of_bit += 24
                # print('找到行尾，结束while')
                break
            else:
                row_msg += binary_to_str(
                    binary_message[index_of_bit:index_of_bit+8])
                index_of_bit += 8
                # print('已找到行头，直接记录')
                continue

        if (not current_row_finded and binary_to_str(binary_message[index_of_bit:index_of_bit+8]) == 's' and binary_to_str(binary_message[index_of_bit+8:index_of_bit+16]) == '(' and binary_to_str(binary_message[index_of_bit+16:index_of_bit+24]) == '('):
            current_row_finded = True
            index_of_bit += 24
            # print('刚找到行头')
        else:
            # print('没找到行头，以下一个bit为起点继续寻找行头')
            index_of_bit += 1
    row_msg += find_msg_by_row(binary_message, index_of_bit)
    return row_msg


def getImageCenterInfo(image_path, width, height):
    img = Image.open(image_path)
    centerX = img.width / 2
    centerY = img.height / 2
    x = centerX - width / 2
    y = centerY - height / 2
    return (x, y, width, height)


def getRectRegion(img_path, x, y, width, height):  # 选择要放入信息的区域（方形）
    img = Image.open(img_path)
    img_width = img.width
    img_height = img.height
    left = int(x)
    top = int(y)
    right = int(img_width if (
        (x + width > img_width) | width == 0) else x + width)
    bottom = int(img_height if ((y + height > img_height) |
                                height == 0) else y + height)
    return (img.crop((left, top, right, bottom)), left, top, right, bottom)


if __name__ == "__main__":
    # 用法：加水印 python alpha_png.py ./01.png duitang
    # 用法：打印水印 python alpha_png.py ./01_alphamarked.png

    image_path = sys.argv[1]
    keystr = sys.argv[2] if len(sys.argv) > 2 else ''
    is_decrypt = keystr == ''

    tmp_path = os.path.splitext(image_path)[0] + "_rgb_tmp.png"
    encrypted_path = os.path.splitext(image_path)[0] + "_rgb_alpha_marked.png"

    # 示例1： 以图像中心点周围 100x100 的区域
    # 1. getImageCenterInfo 函数获取 x,y,width,height 四个参数
    # 2. 按照以下传参加密  注意加密信息的大小！就当前隐写公式来说，加密信息大小 x 计算公式为 x = width * height * 3 (单位bit)
    # 3. 按照以下传参解密
    x, y, width, height = getImageCenterInfo(image_path, 100, 100)

    # Load image
    if is_decrypt:
        # 直接找到中间区域rgb 100x100 像素解密信息
        decrpt('rgb', image_path, x, y, width, height)
        # 直接找到中间区域rgb 100x100 像素解密信息
        decrpt('alpha', image_path, x, y, width, height)

        print('===')

        # 遍历所有rgb像素寻找
        decrpt('rgb', image_path)
        # 遍历所有alpha像素寻找
        decrpt('alpha', image_path)

    else:
        encrpt('rgb', image_path, keystr, tmp_path, x, y, width, height)
        encrpt('alpha', tmp_path, keystr, encrypted_path, x, y, width, height)
