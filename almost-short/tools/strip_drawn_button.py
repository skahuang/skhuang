"""nova_button_slam_sheet.png -> nova_button_hand_sheet.png: keep only Nova's hand and sleeve.

topi wants the S15m button to be the modelled 3D button, so the drawn button (pink cap, dark bezel,
highlights) is erased from the lower middle of every cell (anything that is not skin there), then any
specks left that are not connected to the hand are removed. Run from the repo root:
    python3 almost-short/tools/strip_drawn_button.py
"""
import colorsys
import os
from collections import deque

import numpy as np
from PIL import Image

D = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")
im = np.array(Image.open(os.path.join(D, "nova_button_slam_sheet.png")).convert("RGBA"))
H, W = im.shape[:2]
cw, ch = W // 3, H // 2
for j in range(2):
    for i in range(3):
        c = im[j * ch:(j + 1) * ch, i * cw:(i + 1) * cw]
        for y in range(int(ch * 0.78), ch):
            for x in range(int(cw * 0.26), int(cw * 0.74)):
                r, g, b, a = (int(v) for v in c[y, x])
                if not a:
                    continue
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if not ((h < 0.11 or h > 0.97) and 0.10 < s < 0.65 and v > 0.42 and r >= g >= b * 0.85):
                    c[y, x, 3] = 0
        # keep only the largest connected piece (the hand + sleeve)
        m = c[..., 3] > 8
        lab = np.zeros(m.shape, int)
        sizes, k = {}, 0
        for y, x in zip(*np.nonzero(m)):
            if lab[y, x]:
                continue
            k += 1
            q, n = deque([(y, x)]), 0
            lab[y, x] = k
            while q:
                a, b = q.popleft()
                n += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = a + dy, b + dx
                    if 0 <= yy < ch and 0 <= xx < cw and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = k
                        q.append((yy, xx))
            sizes[k] = n
        if sizes:
            c[..., 3][lab != max(sizes, key=sizes.get)] = 0
Image.fromarray(im).save(os.path.join(D, "nova_button_hand_sheet.png"))
print("wrote nova_button_hand_sheet.png")
