from email.policy import default
import imp
import cv2
import numpy as np
import random
from collections import Counter, defaultdict
import pytesseract


# Load image, grayscale, median blur, sharpen image
image = cv2.imread('iphone.jpeg')
# image = cv2.imread('mac.png')
# image = cv2.imread('android.png')

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
blur = cv2.medianBlur(gray, 5)
sharpen_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
sharpen = cv2.filter2D(blur, -1, sharpen_kernel)

# Threshold and morph close
thresh = cv2.threshold(sharpen, 160, 255, cv2.THRESH_BINARY_INV)[1]
# kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
# close = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

# Find contours and filter using threshold area
contours = cv2.findContours(sharpen, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
contours = contours[0] if len(contours) == 2 else contours[1]

min_area = 30000
max_area = 35000
image_number = 29

sizes = Counter()

areas = set()
for c in contours:
    area = cv2.contourArea(c)
    x, y, w, h = cv2.boundingRect(c)
    if w == h:
        areas.add(area)
    sizes[area] += 1

print(sizes.most_common())

print(sorted(areas))
max_area = sorted(areas)[-2]
colors = {
    "121214": "null",
    "121213": "null",
    "1b1b1f": "null",
    "2b2c36": "null",
    "528c4f": "green",
    "608b55": "green",
    "618c55": "green",
    "3a3a3c": "red",

    "b19f4b": "yellow",
    "b1a04c": "yellow",
    "b59f3b": "yellow",
}

words = defaultdict(list)

matrix = {i: ['b'] * 5 for i in range(6)}
guesses = {i: [''] * 5 for i in range(6)}

for c in contours:
    area = cv2.contourArea(c)
    x, y, w, h = cv2.boundingRect(c)
    if area == max_area:
        row = image_number // 5
        col = image_number % 5
        ROI = image[y:y+h, x:x+w]
        cv2.imwrite('ROI_{}.png'.format(image_number), ROI)
        cv2.rectangle(image, (x, y), (x + w, y + h),
                      (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)), 2)
        pixels = Counter([tuple(x) for x in ROI.reshape((w * h, 3))])
        b, g, r = pixels.most_common()[0][0]
        color = f"{hex(r)[2:]}{hex(g)[2:]}{hex(b)[2:]}"

        text = None
        if colors.get(color) in ('green', 'yellow', 'red'):
            text = pytesseract.image_to_string(
                thresh[y:y+h, x:x+w], config="--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ", lang='eng', )
        if text:
            guesses[row][col] = text[0]
            text = text[0]
        print(color)
        matrix[row][col] = colors.get(color)[0]

        words[row].append((x, y))
        words[row].append((x+w, y+h))

        print(image_number, x, y, w, h, area, row,
              col, color, colors.get(color), text)

        image_number -= 1

final = {}
for row, coords in words.items():
    x = min([x[0] for x in coords])
    w = max([x[0] for x in coords])

    y = min([y[1] for y in coords])
    h = max([y[1] for y in coords])
    # print(row, x, w, y, h)
    text = pytesseract.image_to_string(
        thresh[y:h, x:w], config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ", lang='eng', )
    # cv2.imshow(f"{row}", thresh[y:h, x:w])
    print(row, text.split('\n'))
    final[row] = text.split('\n')[0]

for row in range(6):
    if len(final[row]) != 5:
        print(row, ''.join(guesses[row]), ''.join(matrix[row]))
    else:
        print(row, final[row], ''.join(matrix[row]))

cv2.imshow('sharpen', sharpen)
# # cv2.imshow('close', close)
cv2.imshow('thresh', thresh)
cv2.imshow('image', image)
cv2.waitKey()
