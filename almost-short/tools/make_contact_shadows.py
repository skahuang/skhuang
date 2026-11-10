"""Bake soft contact shadows for the pin sprites: where the FRONT zombie layer (hands, knees) sits on
Rin or the roof, darken what is underneath. Output sits between pin_*_rin and pin_*_front in Blender.

    python3 tools/make_contact_shadows.py            # writes assets/sprites/pin_*_contact_sheet.png
"""
import os
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SPR = os.path.join(HERE, "..", "assets", "sprites")


def alpha(name):
    return Image.open(os.path.join(SPR, name + "_sheet.png")).convert("RGBA").split()[3]


def bake(prefix, cell=512, blur=7, shift=(4, 6), on_rin=0.85, on_roof=0.45):
    fa = alpha(prefix + "_front")
    ra = alpha(prefix + "_rin").filter(ImageFilter.MaxFilter(5))
    f = np.asarray(fa, np.float32) / 255
    soft = np.asarray(fa.filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255
    # light from upper-left: the occlusion falls a little right and down of the hands
    soft = np.roll(np.roll(soft, shift[1], 0), shift[0], 1)
    r = np.asarray(ra, np.float32) / 255
    a = soft * (1 - f) * (on_roof + (on_rin - on_roof) * r)
    a = np.clip(a * 2.4, 0, on_rin)
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., 3] = (a * 255).astype(np.uint8)
    path = os.path.join(SPR, prefix + "_contact_sheet.png")
    Image.fromarray(out, "RGBA").save(path, optimize=True)
    return path


if __name__ == "__main__":
    for p in ("pin_layer", "pin_takedown"):
        print(bake(p))
