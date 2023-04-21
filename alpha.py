from PIL import Image
import re
import sys
import os


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


def encrpt(img_path, message, output_path, x=0, y=0, width=0, height=0):
    original_img = Image.open(img_path)
    img, left, top, right, bottom = getRectRegion(
        img_path, x, y, width, height)
    binary_message = "".join(format(ord(c), '08b')
                             for c in "DATA:" + message + ";")

    a = img.getchannel('A')
    a_data = list(a.getdata())

    # 按照rgba顺序依次塞入信息
    for i, bit in enumerate(binary_message):
        a_data[i] = (a_data[i] & 254) | int(bit)
    a.putdata(a_data)
    img.putalpha(a)

    original_img.paste(img, (left, top, right, bottom))
    original_img.save(output_path)


def decrpt(img_path, x=0, y=0, width=0, height=0):
    tuple = getRectRegion(
        img_path, x, y, width, height)
    img = tuple[0]
    a_data = img.getchannel('A').getdata()
    pixelLength = img.width * img.height

    # 读取二进制信息
    binary_message = ''
    for i in range(0, pixelLength):
        binary_message += str(a_data[i] & 1)

    # 将二进制信息转换为文本
    message = ""
    for i in range(0, len(binary_message), 8):
        message += chr(int(binary_message[i:i+8], 2))

    data_pattern = r'DATA:\s*(.*?);'
    match = re.search(data_pattern, message)
    if match:
        data = match.group(1)
        print(data)
    else:
        print('找不到加密信息')


def getImageCenterInfo(image_path, width, height):
    img = Image.open(image_path)
    centerX = img.width / 2
    centerY = img.height / 2
    x = centerX - width / 2
    y = centerY - height / 2
    return (x, y, width, height)


testMsg = ""
for i in range(0, 10):
    testMsg += "c"


# 示例1： 以图像中心点周围 100x100 的区域
# 1. getImageCenterInfo 函数获取 x,y,width,height 四个参数
# 2. 按照以下传参加密  注意加密信息的大小！就当前隐写公式来说，加密信息大小 x 计算公式为 x = width * height * 3 (单位bit)
# 3. 按照以下传参解密
# x, y, width, height = getImageCenterInfo('./6.png', 100, 100)
# encrpt('./6.png', testMsg, './output2.png', x, y, width, height)
# decrpt('./output2.png', x, y, width, height)

# 示例2： 不传x,y,width,height等参数默认全图
# encrpt('./test.png', testMsg, './output2.png')
# decrpt('./output2.png')


if __name__ == "__main__":
    # 用法：加水印 python alpha_png.py ./01.png duitang
    # 用法：打印水印 python alpha_png.py ./01_alphamarked.png

    image_path = sys.argv[1]
    keystr = sys.argv[2] if len(sys.argv) > 2 else ''
    is_decrypt = keystr == ''

    encrypted_path = os.path.splitext(image_path)[0] + "_alphamarked.png"

    x, y, width, height = getImageCenterInfo(image_path, 100, 100)

    # Load image
    if is_decrypt:
        decrpt(image_path, x, y, width, height)
    else:
        encrpt(image_path, keystr, encrypted_path, x, y, width, height)
