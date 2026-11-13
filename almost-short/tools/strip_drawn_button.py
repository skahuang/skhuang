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
from PIL import Image, ImageFilter

D = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")
im = np.array(Image.open(os.path.join(D, "nova_button_slam_sheet.png")).convert("RGBA"))
H, W = im.shape[:2]
cw, ch = W // 3, H // 2
for j in range(2):
    for i in range(3):
        c = im[j * ch:(j + 1) * ch, i * cw:(i + 1) * cw]
        erased = np.zeros((ch, cw), bool)
        for y in range(int(ch * 0.66), ch):
            for x in range(int(cw * 0.15), int(cw * 0.85)):
                r, g, b, a = (int(v) for v in c[y, x])
                if not a:
                    continue
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                skin = (h < 0.11 or h > 0.97) and 0.10 < s < 0.65 and v > 0.42 and r >= g >= b * 0.85
                skin = skin or (v > 0.7 and 0.05 < s < 0.3 and r >= g >= b)     # fingernails
                mid = cw * 0.20 <= x < cw * 0.70        # the drawn button's columns (the sleeve is further right)
                magenta = mid and (h > 0.88 or h < 0.02) and s > 0.5 and not skin
                cuff = v < 0.30 and y < ch * 0.84            # her dark sleeve cuff dips into the band in cells 3-5
                core = y >= ch * 0.78 and cw * 0.26 <= x < cw * 0.74 and (not skin or a < 200) and not cuff
                ghost = mid and y >= ch * 0.74 and (a < 230 or s < 0.14) and not skin and not cuff   # grey / see-through leftovers
                if core or magenta or ghost:
                    c[y, x, 3] = 0
                    c[y, x, :3] = (225, 172, 150)       # skin tone, so the feathered fringe is not pink/grey
                    erased[y, x] = True
        # opening (erode + dilate, 5 px) inside the button band: drops thin leftover outline arcs, keeps fingers
        band = np.zeros((ch, cw), bool)
        band[int(ch * 0.78):, int(cw * 0.26):int(cw * 0.74)] = True
        m8 = Image.fromarray(((c[..., 3] > 8) * 255).astype(np.uint8))
        opened = np.array(m8.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))) > 0
        thin = band & (c[..., 3] > 8) & ~opened
        c[..., 3][thin] = 0
        erased |= thin
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
        # feather the new cut edge by ~1.5 px (only around the erased area, the art's own edges stay)
        # smooth the cut contour (blur + soft re-threshold removes the pixel stair steps), then feather inward only
        al = np.array(Image.fromarray(c[..., 3].copy()).filter(ImageFilter.GaussianBlur(2.0))).astype(float)
        smooth = np.clip((al - 128.0) * 1.6 + 128.0, 0, 255)
        near = np.array(Image.fromarray((erased * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))) > 0
        c[..., 3][near] = np.minimum(c[..., 3][near], smooth[near]).astype(np.uint8)
Image.fromarray(im).save(os.path.join(D, "nova_button_hand_sheet.png"))
print("wrote nova_button_hand_sheet.png")
