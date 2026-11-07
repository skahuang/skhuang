"""
差一點 / ALMOST — Blender scene blockout builder
=================================================

Builds the whole 60 s, 9:16 short as ONE continuous world:
the zombie rooftop is a real miniature diorama inside a claw-machine cabinet,
so the reveal (S14-S15) is a genuine camera pull-out through the glass, not a cut.

2D characters are flat "acrylic standee" sprite planes (image + alpha) that
always yaw toward the active camera, animated FRAME BY FRAME from sprite
sheets (<name>_sheet.png, grid left->right / top->bottom) at 8-12 fps — see
the ANIM table below and ASSET_PROMPTS.md. Drop the GPT-generated PNGs into
  <blend dir>/assets/sprites/   and   <blend dir>/assets/textures/
using the filenames listed in ASSET_PROMPTS.md, then re-run this script.
Missing files are replaced by coloured placeholder silhouettes so the
layout, timing and cameras can be reviewed before any art exists.

Run (Blender 4.2+ / 5.x):
  blender -b -P build_almost_scene.py -- --out almost.blend
  blender -b -P build_almost_scene.py -- --out almost.blend --preview previews/
Inside Blender: open the Scripting tab, load this file, Run Script.

Units: metres, REAL cabinet scale. The diorama is ~1:60, so Rin is 2.3 cm tall.
Timeline: 24 fps, frames 1-1440 (60 s). Shot cameras are bound to timeline
markers, so pressing Play / rendering the full range switches shots.
"""

import math
import os
import random
import sys

import bpy

try:
    import numpy as np
except ImportError:  # Blender always ships numpy, but stay safe
    np = None

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
FPS = 24
DURATION_S = 60
RES_X, RES_Y = 1080, 1920
SEED = 7

ROOF_Z = 1.10          # rooftop surface height (diorama bed is at 0.95)
BED_Z = 0.95
TOWER_XY = (0.10, 0.14)
SHED_XY = (-0.11, 0.13)
DOOR_XY = (-0.11, 0.105)   # door face of the stair shed (faces -Y)
RIN_H = 0.023              # Rin standee height
ZOMBIE_H = 0.026
NOVA_XY = (0.25, -0.85)
NOVA_H = 1.62
PIN_XY = (0.02, 0.0)       # where Rin lands and gets pinned
CHUTE_XY = (-0.33, -0.33)  # prize chute
RESET_S = 57.0
TIMER_START = 32           # overlay countdown hits 00:00 at 32 s, the moment her grip fails

ASSET_DIR = None  # resolved in main()
TEX_DIR = None    # resolved in main()

# --------------------------------------------------------------------------
# 2D frame-by-frame sheets. Each character pose is ONE PNG laid out as a grid
# (left->right, top->bottom) named "<sprite>_sheet.png"; see ASSET_PROMPTS.md.
# (cols, rows, frames, fps, mode)   mode: loop | once (hold last) | pingpong
# Missing sheet -> falls back to "<sprite>.png" still -> animated placeholder.
# --------------------------------------------------------------------------
ANIM = {
    "rin_backing_away":    (4, 2, 8, 12, "loop"),      # stumbling backwards
    "rin_boot_grab":       (4, 3, 12, 12, "once"),     # kick, pull, boot slips off, scramble free
    "rin_climb_back":      (4, 2, 8, 12, "loop"),      # ladder climb cycle
    "door_fingers":        (3, 2, 6, 12, "loop"),      # S01 grey fingers squirming through the door gap
    "rin_cling_scared":    (4, 1, 4, 12, "loop"),      # trembling, glancing down
    "rin_look_up":         (4, 2, 8, 12, "once"),      # S06 sees the light: squints, shields eyes, awe
    "rin_cling_hope":      (4, 2, 8, 8, "pingpong"),   # reaching up, breathing, hair in the wind
    "rin_slip_shock":      (4, 2, 8, 12, "once"),      # fingers slide off the rung
    "rin_falling":         (3, 2, 6, 12, "loop"),      # flailing fall
    "rin_impact":          (4, 2, 8, 12, "once"),      # land, bounce, push up on one elbow
    "pin_layer_rin":       (4, 3, 12, 8, "loop"),      # struggle beats: push up / cry out / twist+kick / look up
    "pin_face_closeup":    (4, 3, 12, 8, "once"),      # S13b face ECU: grit teeth -> eyes to tower -> cry -> defiance
    "pin_layer_back":      (3, 2, 6, 8, "pingpong"),   # pulling the hoodie, tentacles writhing
    "pin_layer_front":     (4, 3, 12, 8, "loop"),      # pressing down; frame-locked to pin_layer_rin (same clock, phase 0)
    "rin_reset_lookup":    (4, 2, 8, 12, "once"),      # slowly tilts head up to the lens
    "nova_back_joystick":  (4, 2, 8, 12, "loop"),      # joystick jiggle, shoulders tense
    "nova_profile_almost": (4, 3, 12, 8, "once"),      # wince, exhale, glance at the chute
    "nova_hand_coin":      (4, 2, 8, 12, "once"),      # flip token, push it into the slot
}
ZOMBIE_ANIM = {
    "walk":  (4, 2, 8, 12, "loop"),
    "reach": (3, 2, 6, 8, "pingpong"),
    "climb": (3, 2, 6, 12, "loop"),
}


def f(sec):
    """seconds -> frame number (1-based)."""
    return int(round(sec * FPS)) + 1


# Shot list — must match README.md §3. (id, start_s, end_s, lens, cam_from, cam_to, aim_from, aim_to)
SHOTS = [
    # ---- Act 1: trapped (0-15 s)
    ("S01_door_bang",     0.0,  2.5, 50, (-0.085, -0.03, 1.114),  (-0.092, -0.005, 1.116), (-0.11, 0.11, 1.124), (-0.11, 0.11, 1.122)),
    ("S02_establish",     2.5,  6.0, 35, (0.26, -0.46, 1.56),    (0.18, -0.30, 1.32),    (0.0, 0.05, 1.11),    (0.0, 0.04, 1.11)),
    ("S03_lost_boot",     6.0,  8.5, 50, (0.03, -0.085, 1.104),  (0.025, -0.075, 1.104), (0.0, 0.0, 1.104),    (0.0, 0.0, 1.104)),
    ("S04_run_climb",     8.5, 12.0, 35, (-0.09, -0.11, 1.14),   (0.02, -0.03, 1.165),   (0.08, 0.10, 1.12),   (0.10, 0.12, 1.18)),
    ("S05_pile_topdown", 12.0, 15.0, 35, (0.15, 0.02, 1.58),     (0.12, 0.06, 1.52),     (0.10, 0.14, 1.10),   (0.10, 0.14, 1.12)),
    # ---- Act 2: false rescue (15-32 s)
    ("S06_light_above",  15.0, 18.0, 28, (0.112, 0.058, 1.168),  (0.110, 0.061, 1.170),  (0.10, 0.099, 1.192), (0.10, 0.099, 1.196)),
    ("S07_claw_descends",18.0, 22.0, 35, (0.32, -0.16, 1.42),    (0.30, -0.15, 1.38),    (0.10, 0.14, 1.30),   (0.10, 0.14, 1.24)),
    ("S08_grip_lift",    22.0, 26.0, 35, (0.28, -0.20, 1.34),    (0.30, -0.22, 1.47),    (0.10, 0.14, 1.20),   (0.10, 0.14, 1.42)),
    ("S09_false_hope",   26.0, 30.0, 50, (0.016, -0.105, 0.080), (0.013, -0.098, 0.088), (0.0, -0.041, 0.087), (0.0, -0.041, 0.090)),  # local to TOWER_ROOT
    ("S10_slip",         30.0, 32.0, 35, (0.00, -0.08, 1.66),    (0.01, -0.07, 1.65),    (0.10, 0.14, 1.48),   (0.10, 0.14, 1.48)),
    # ---- Act 3: fall, pinned, pull-back (32-45 s) — the tower stays in the claw, only Rin falls
    ("S11_fall",         32.0, 35.0, 35, (0.28, -0.22, 1.42),    (0.20, -0.15, 1.20),    (0.10, 0.10, 1.40),   (0.03, 0.00, 1.11)),
    ("S12_impact",       35.0, 36.0, 50, (0.065, -0.05, 1.106),  (0.065, -0.05, 1.106),  (0.02, 0.0, 1.108),   (0.02, 0.0, 1.108)),
    ("S13a_pinned",      36.0, 39.0, 50, (0.034, -0.034, 1.109), (0.031, -0.030, 1.108), (0.02, 0.0, 1.105),   (0.02, 0.0, 1.105)),
    ("S13b_pinned_face", 39.0, 41.0, 50, (0.02, -0.052, 1.108),  (0.02, -0.046, 1.108),  (0.02, -0.013, 1.108), (0.02, -0.013, 1.108)),
    ("S14_pullback",     41.0, 45.0, 24, (0.034, -0.034, 1.109), (0.14, -0.44, 1.34),    (0.02, 0.0, 1.105),   (0.06, 0.08, 1.38)),
    # ---- Act 4: reveal + loop (45-60 s)
    ("S15_glass_reveal", 45.0, 51.0, 35, (0.14, -0.44, 1.34),    (-0.45, -2.30, 1.78),   (0.06, 0.08, 1.38),   (0.05, -0.30, 1.20)),
    ("S16_nova_almost",  51.0, 55.0, 85, (0.62, -1.30, 1.56),    (0.60, -1.25, 1.55),    (0.25, -0.85, 1.50),  (0.25, -0.85, 1.50)),
    ("S17a_coin",        55.0, 57.0, 50, (0.58, -0.86, 0.98),    (0.55, -0.80, 0.95),    (0.36, -0.52, 0.86),  (0.36, -0.52, 0.86)),
    ("S17b_reset_loop",  57.0, 60.0, 35, (0.02, -0.04, 1.30),    (-0.085, -0.03, 1.114), (0.0, -0.01, 1.10),   (-0.11, 0.11, 1.124)),
]


# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------
# Shots whose camera + aim ride with a moving object (coordinates above are then local to it)
SHOT_PARENT = {"S09_false_hope": "TOWER_ROOT"}


def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c


def link(obj, collection):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def mat(name, color=(0.5, 0.5, 0.5), rough=0.6, metal=0.0, emit=None, strength=0.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = node_of_type(m.node_tree, "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Alpha"].default_value = alpha
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    if alpha < 1.0 and hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    m.diffuse_color = (*color, alpha)
    return m


def node_of_type(tree, kind):
    """Find a node by type, not by name (names are translated in non-English UIs)."""
    for n in tree.nodes:
        if n.type == kind:
            return n
    return None


# Surface textures (assets/textures/). Missing file -> the flat colour from mat() stays.
#   key: (filename, tile size in metres or None = use the mesh UVs, bump strength)
SURFACE_TEX = {
    "roof_wet":      ("tex_roof_tiles_wet.png",       0.04, 0.15),
    "concrete":      ("tex_concrete_peel.png",        0.06, 0.20),
    "concrete_dark": ("tex_city_facade_windows.png",  0.08, 0.10),
    "street":        ("tex_street_asphalt_wet.png",   0.15, 0.15),
    "rust":          ("tex_rust_metal.png",           0.02, 0.20),
    "tank_metal":    ("tex_water_tank_paint.png",     0.07, 0.15),
    "metal_dull":    ("tex_metal_scratched.png",      0.03, 0.10),
    "door_green":    ("tex_door_green_metal.png",     None, 0.15),
    "cab_body":      ("tex_cabinet_body.png",         0.50, 0.05),
    "marquee":       ("tex_marquee_logo.png",         None, 0.00),
    "floor":         ("tex_arcade_carpet.png",        1.00, 0.05),
    "wall":          ("tex_arcade_wall.png",          2.00, 0.05),
    "glass":         ("tex_glass_smudge.png",         None, 0.00),
}


def apply_surface_texture(m, filename, tile, bump):
    path = os.path.join(TEX_DIR, filename)
    if not (TEX_DIR and os.path.isfile(path)):
        return False
    nt = m.node_tree
    bsdf = node_of_type(nt, "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if tile:   # tileable: box-project in object space, one repeat every `tile` metres
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1 / tile)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
        tex.projection = "BOX"
        tex.projection_blend = 0.2
    else:      # whole image on each face (default cube UVs)
        tex.extension = "CLIP"
        nt.links.new(tc.outputs["UV"], tex.inputs["Vector"])
    if m.name == "glass":   # greyscale smudges -> rougher, slightly more visible glass
        tex.image.colorspace_settings.name = "Non-Color"
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = 0.02
        mr.inputs["To Max"].default_value = 0.18      # subtle: the reveal must stay readable through the glass
        nt.links.new(tex.outputs["Color"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
        return True
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if bsdf.inputs["Emission Strength"].default_value > 0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    if bump > 0:
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.001
        nt.links.new(tex.outputs["Color"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return True


def box(name, size, loc, material, collection, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return link(o, collection)


def cyl(name, r, depth, loc, material, collection, verts=32, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    return link(o, collection)


def empty(name, loc, collection, kind="PLAIN_AXES", size=0.02):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = kind
    o.empty_display_size = size
    o.location = loc
    collection.objects.link(o)
    return o


def fcurves_of(id_block):
    """F-curves of an object's action — works on 4.x and on 5.x slotted actions."""
    ad = getattr(id_block, "animation_data", None)
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "layers") and len(act.layers):
        try:
            from bpy_extras import anim_utils
            cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
            return list(cb.fcurves) if cb else []
        except Exception:
            pass
    return list(getattr(act, "fcurves", []))


def set_interp(id_block, kind="CONSTANT", data_path=None):
    for fc in fcurves_of(id_block):
        if data_path and fc.data_path != data_path:
            continue
        for kp in fc.keyframe_points:
            kp.interpolation = kind


def key_loc(o, frame, loc):
    o.location = loc
    o.keyframe_insert("location", frame=frame)


def key_rot(o, frame, rot):
    o.rotation_euler = rot
    o.keyframe_insert("rotation_euler", frame=frame)


def key_visible(o, visible_ranges):
    """visible_ranges: list of (start_frame, end_frame) inclusive. Hidden elsewhere."""
    o.hide_render = True
    o.hide_viewport = False  # keep selectable in viewport; render visibility drives output
    o.keyframe_insert("hide_render", frame=1)
    for a, b in visible_ranges:
        o.hide_render = False
        o.keyframe_insert("hide_render", frame=a)
        o.hide_render = True
        o.keyframe_insert("hide_render", frame=b + 1)
    set_interp(o, "CONSTANT", "hide_render")


# --------------------------------------------------------------------------
# Sprites (2D acrylic standees)
# --------------------------------------------------------------------------
def placeholder_image(name, color, w=256, h=512, shape="figure"):
    img = bpy.data.images.get(name)
    if img:
        return img
    img = bpy.data.images.new(name, w, h, alpha=True)
    if np is not None:
        yy, xx = np.mgrid[0:h, 0:w]
        cx = w / 2
        if shape == "figure":
            head = ((xx - cx) ** 2 + (yy - h * 0.86) ** 2) < (w * 0.17) ** 2
            body = (np.abs(xx - cx) < w * 0.26) & (yy > h * 0.06) & (yy < h * 0.74)
            m = head | body
        elif shape == "hand":
            m = ((xx - cx) ** 2 / (w * 0.35) ** 2 + (yy - h / 2) ** 2 / (h * 0.3) ** 2) < 1
        else:  # full card (backdrops)
            m = np.ones((h, w), bool)
        px = np.zeros((h, w, 4), np.float32)
        grad = (0.65 + 0.35 * (yy / h))[..., None]
        px[..., :3] = np.array(color, np.float32) * grad
        px[..., 3] = m.astype(np.float32)
        img.pixels.foreach_set(px.ravel())
    else:
        img.generated_color = (*color, 1.0)
    img.pack()
    return img


def load_image(filename, color, shape="figure", w=256, h=512):
    path = os.path.join(ASSET_DIR, filename)
    if os.path.isfile(path):
        img = bpy.data.images.load(path, check_existing=True)
        try:
            img.filepath = bpy.path.relpath(path)
        except ValueError:
            pass
        return img, True
    return placeholder_image("PH_" + os.path.basename(filename), color, w, h, shape), False


def placeholder_sheet(name, color, cols, rows, frames, cw=128, ch=256):
    """Grid of figure silhouettes whose arm swings and body sways per cell, so previews show motion."""
    img = bpy.data.images.get(name)
    if img:
        return img
    W, H = cw * cols, ch * rows
    img = bpy.data.images.new(name, W, H, alpha=True)
    if np is not None:
        px = np.zeros((H, W, 4), np.float32)
        yy, xx = np.mgrid[0:ch, 0:cw]
        for i in range(frames):
            c, r = i % cols, i // cols
            ph = i / max(frames, 1) * math.tau
            cx = cw / 2 + math.sin(ph) * cw * 0.08
            head = ((xx - cx) ** 2 + (yy - ch * 0.86) ** 2) < (cw * 0.17) ** 2
            body = (np.abs(xx - cx) < cw * 0.22) & (yy > ch * 0.06) & (yy < ch * 0.74)
            ang = math.sin(ph) * 1.1
            ax, ay = cx + cw * 0.2, ch * 0.66                     # shoulder
            ux, uy = math.sin(ang), math.cos(ang)                   # arm direction
            t = (xx - ax) * ux + (yy - ay) * uy
            d = np.abs((xx - ax) * uy - (yy - ay) * ux)
            arm = (t > 0) & (t < ch * 0.3) & (d < cw * 0.06)
            m = head | body | arm
            cell = np.zeros((ch, cw, 4), np.float32)
            cell[..., :3] = np.array(color, np.float32) * (0.65 + 0.35 * (yy / ch))[..., None]
            cell[..., 3] = m
            y0 = (rows - 1 - r) * ch                                # Blender pixel rows start at the bottom
            px[y0:y0 + ch, c * cw:(c + 1) * cw] = cell
        img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


def sprite_material(name, image, emission=0.15, cols=1, rows=1, frames=1, fps=12, mode="loop"):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Closest" if image.size[0] < 300 * cols else "Linear"
    tex.extension = "CLIP"
    uv = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.name = "SHEET_MAPPING"
    mp.inputs["Scale"].default_value = (1.0 / cols, 1.0 / rows, 1.0)
    mp.inputs["Location"].default_value = (0.0, (rows - 1) / rows, 0.0)   # first cell = top-left
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    # a little self-illumination keeps painted 2D art readable under dark scene light
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = emission
    bsdf.inputs["Roughness"].default_value = 0.35   # acrylic sheen
    bsdf.inputs["Specular IOR Level"].default_value = 0.6
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    m.use_backface_culling = False
    m["sheet"] = [cols, rows, frames, fps]
    m["sheet_mode"] = mode
    return m


def load_sheet(name, color, spec, mat_name=None):
    """-> (material, frame_aspect). Prefers <name>_sheet.png, then <name>.png still, then a placeholder sheet."""
    cols, rows, frames, fps, mode = spec
    sheet = os.path.join(ASSET_DIR, name + "_sheet.png")
    still = os.path.join(ASSET_DIR, name + ".png")
    if os.path.isfile(sheet):
        img, _ = load_image(name + "_sheet.png", color)
    elif os.path.isfile(still):
        img, _ = load_image(name + ".png", color)
        cols = rows = frames = 1
    else:
        img = placeholder_sheet("PH_" + name + "_sheet", color, cols, rows, frames)
    aspect = (img.size[0] / cols) / max(img.size[1] / rows, 1)
    return sprite_material(mat_name or ("M_" + name), img, cols=cols, rows=rows, frames=frames, fps=fps, mode=mode), aspect


def animate_sheet(mat, ranges, phase=0):
    """Step the sheet's UV window through its cells on 2s/3s (12 or 8 fps) inside each visible range."""
    cols, rows, frames, fps = [int(v) for v in mat["sheet"]]
    if frames <= 1:
        return
    mode = mat["sheet_mode"]
    mp = mat.node_tree.nodes["SHEET_MAPPING"]
    step = max(1, round(FPS / fps))
    for a, b in ranges:
        k, fr = phase, a
        while fr <= b:
            if mode == "once":
                i = min(k, frames - 1)
            elif mode == "pingpong":
                period = 2 * frames - 2
                i = k % period
                i = i if i < frames else period - i
            else:
                i = k % frames
            c, r = i % cols, i // cols
            mp.inputs["Location"].default_value = (c / cols, (rows - 1 - r) / rows, 0.0)
            mp.inputs["Location"].keyframe_insert("default_value", frame=fr)
            fr += step
            k += 1
    set_interp(mat.node_tree, "CONSTANT")


def sprite_mesh(name, height, aspect):
    me = bpy.data.meshes.get(name)
    if me:
        return me
    w = height * aspect
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, height), (-w / 2, 0, height)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for i, co in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = co
    return me


def add_standee_base(o, height, collection, material):
    """Tiny clear acrylic base — the visual clue that everyone inside is a prize standee."""
    r = height * 0.28
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=height * 0.05, vertices=24, location=(0, 0, height * 0.025))
    b = bpy.context.active_object
    b.name = o.name + "_base"
    b.data.materials.append(material)
    link(b, collection)
    b.parent = o
    return b


def sprite(name, filename, height, loc, collection, face_target, color, aspect=0.5,
           parent=None, base_mat=None, shape="figure", mesh_name=None, material=None):
    if material is None and name in ANIM:
        material, aspect = load_sheet(name, color, ANIM[name])
    if material is None:
        img, _ = load_image(filename, color, shape)
        if img.size[1]:
            aspect = img.size[0] / img.size[1]
        material = sprite_material("M_" + name, img)
    me = sprite_mesh(mesh_name or ("ME_" + name), height, aspect)
    if not me.materials:
        me.materials.append(material)
    o = bpy.data.objects.new(name, me)
    collection.objects.link(o)
    o.location = loc
    if parent:
        o.parent = parent
    c = o.constraints.new("LOCKED_TRACK")
    c.target = face_target
    c.track_axis = "TRACK_NEGATIVE_Y"
    c.lock_axis = "LOCK_Z"
    if base_mat:
        add_standee_base(o, height, collection, base_mat)
    return o


# --------------------------------------------------------------------------
# Scene construction
# --------------------------------------------------------------------------
def reset_scene():
    # Wipe data instead of read_factory_settings(): that call also unloads add-ons
    # (including the Blender MCP server) when the script runs inside a live session.
    for coll_name in ("objects", "meshes", "materials", "images", "cameras", "lights",
                      "curves", "collections", "actions", "worlds", "node_groups"):
        data = getattr(bpy.data, coll_name, None)
        if data is not None:
            for block in list(data):
                data.remove(block)
    scn = bpy.context.scene
    scn.timeline_markers.clear()
    scn.name = "ALMOST"
    scn.render.resolution_x = RES_X
    scn.render.resolution_y = RES_Y
    scn.render.fps = FPS
    scn.frame_start = 1
    scn.frame_end = f(DURATION_S) - 1   # 1440
    scn.unit_settings.system = "METRIC"
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = eng
            break
        except TypeError:
            continue
    scn.render.filepath = "//render/almost_"
    scn.render.image_settings.file_format = "PNG"
    try:
        scn.view_settings.view_transform = "AgX"
        scn.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    world = bpy.data.worlds.new("W_arcade_dark")
    world.use_nodes = True
    bg = node_of_type(world.node_tree, "BACKGROUND")
    bg.inputs["Color"].default_value = (0.012, 0.008, 0.02, 1)
    bg.inputs["Strength"].default_value = 0.4
    scn.world = world
    return scn


def build_cabinet(C, M):
    cab = coll("CABINET", C["root"])
    # lower body
    box("cab_body", (1.0, 1.0, BED_Z), (0, 0, BED_Z / 2), M["cab_body"], cab)
    # four corner pillars + roof
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"cab_pillar_{sx}{sy}", (0.05, 0.05, 0.92), (sx * 0.475, sy * 0.475, BED_Z + 0.46), M["cab_trim"], cab)
    box("cab_roof", (1.0, 1.0, 0.06), (0, 0, 1.90), M["cab_body"], cab)
    box("cab_marquee", (1.0, 0.10, 0.18), (0, -0.46, 2.02), M["marquee"], cab)
    # glass: front / left / right / back(back is opaque printed backdrop)
    box("glass_front", (0.90, 0.004, 0.90), (0, -0.475, BED_Z + 0.45), M["glass"], cab)
    box("glass_left", (0.004, 0.90, 0.90), (-0.475, 0, BED_Z + 0.45), M["glass"], cab)
    box("glass_right", (0.004, 0.90, 0.90), (0.475, 0, BED_Z + 0.45), M["glass"], cab)
    # neon edge strips (pink left, cyan right) — panel 07/08 look
    box("neon_left", (0.012, 0.012, 0.92), (-0.50, -0.50, BED_Z + 0.46), M["neon_pink"], cab)
    box("neon_right", (0.012, 0.012, 0.92), (0.50, -0.50, BED_Z + 0.46), M["neon_cyan"], cab)
    # printed sky/city backdrop on the inside back wall
    img, _ = load_image("../textures/tex_backdrop_city_sky.png", (0.10, 0.14, 0.30), "card", 512, 512)
    bd = sprite_material("M_backdrop", img, emission=0.6)
    me = sprite_mesh("ME_backdrop", 0.90, 1.0)
    me.materials.append(bd)
    back = bpy.data.objects.new("backdrop_print", me)
    back.location = (0, 0.47, BED_Z)
    back.rotation_euler = (0, 0, math.pi)
    cab.objects.link(back)
    # the "moon": actually the cabinet ceiling lamp (clue in S06 / S09)
    moon = cyl("ceiling_lamp_MOON", 0.035, 0.006, (0.16, 0.30, 1.865), M["moon_lamp"], cab, verts=48)
    # control panel, joystick, button, coin slot, LED timer, prize chute
    box("ctrl_panel", (0.90, 0.22, 0.08), (0, -0.58, 0.86), M["cab_trim"], cab, rot=(math.radians(-12), 0, 0))
    cyl("joystick_shaft", 0.008, 0.08, (-0.12, -0.60, 0.94), M["chrome"], cab, verts=12)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, location=(-0.12, -0.60, 0.985))
    ball = bpy.context.active_object
    ball.name = "joystick_ball"
    ball.data.materials.append(M["red_glossy"])
    link(ball, cab)
    cyl("button_grab", 0.03, 0.02, (0.08, -0.60, 0.91), M["neon_pink"], cab)
    box("coin_slot_plate", (0.08, 0.01, 0.12), (0.36, -0.52, 0.86), M["chrome"], cab)
    box("coin_slot", (0.004, 0.012, 0.05), (0.36, -0.527, 0.87), M["black"], cab)
    box("led_timer", (0.16, 0.01, 0.05), (0.0, -0.505, 1.88), M["led_red"], cab)
    box("prize_chute_bin", (0.16, 0.16, 0.14), (-0.33, -0.33, BED_Z + 0.07), M["glass"], cab)
    box("prize_tray", (0.20, 0.10, 0.04), (-0.33, -0.53, 0.55), M["cab_trim"], cab)
    # tiny single boots in the prize tray: earlier failed rounds (dark-humour clue)
    for i in range(5):
        box(f"lost_boot_{i}", (0.006, 0.010, 0.007),
            (-0.39 + i * 0.028, -0.53 + (i % 2) * 0.012, 0.575), M["boot"], cab, rot=(0, 0, i * 0.7))
    return moon


def build_diorama(C, M):
    dio = coll("DIORAMA", C["root"])
    rnd = random.Random(SEED)
    box("bed", (0.90, 0.90, 0.01), (0, 0, BED_Z), M["street"], dio)
    # hero building (matches the rooftop concept art: shed back-left, tower back-right)
    box("hero_building", (0.36, 0.36, ROOF_Z - BED_Z), (0, 0.05, (ROOF_Z + BED_Z) / 2), M["concrete"], dio)
    box("roof_tiles", (0.35, 0.35, 0.002), (0, 0.05, ROOF_Z + 0.001), M["roof_wet"], dio)
    for name, size, loc in [
        ("parapet_N", (0.36, 0.006, 0.012), (0, 0.23, ROOF_Z + 0.006)),
        ("parapet_S", (0.36, 0.006, 0.012), (0, -0.13, ROOF_Z + 0.006)),
        ("parapet_E", (0.006, 0.36, 0.012), (0.18, 0.05, ROOF_Z + 0.006)),
        ("parapet_W", (0.006, 0.36, 0.012), (-0.18, 0.05, ROOF_Z + 0.006)),
    ]:
        box(name, size, loc, M["concrete"], dio)
    # railing posts along parapet
    for i in range(13):
        t = -0.17 + i * 0.0283
        for loc in ((t, 0.228, ROOF_Z + 0.02), (t, -0.128, ROOF_Z + 0.02)):
            cyl(f"rail_post_{i}_{loc[1]:.2f}", 0.0007, 0.016, loc, M["rust"], dio, verts=6)
    # stair shed + door (door hinge animated: bang in S01, burst open S02)
    box("stair_shed", (0.08, 0.06, 0.05), (SHED_XY[0], SHED_XY[1] + 0.005, ROOF_Z + 0.025), M["concrete"], dio)
    hinge = empty("door_hinge", (DOOR_XY[0] - 0.012, DOOR_XY[1] - 0.001, ROOF_Z), dio)
    door = box("shed_door", (0.024, 0.002, 0.038), (0.012, 0, 0.019), M["door_green"], dio)
    door.parent = hinge
    box("door_lamp", (0.010, 0.004, 0.003), (DOOR_XY[0], DOOR_XY[1] - 0.002, ROOF_Z + 0.044), M["green_glow"], dio)
    for i, (x, y) in enumerate([(-0.15, -0.09), (0.05, -0.10), (0.15, 0.0)]):
        box(f"ac_unit_{i}", (0.022, 0.016, 0.016), (x, y, ROOF_Z + 0.008), M["metal_dull"], dio)
    # surrounding city blocks (forced perspective: lower toward the back)
    for i in range(60):
        x = rnd.uniform(-0.43, 0.43)
        y = rnd.uniform(-0.43, 0.43)
        if abs(x) < 0.23 and -0.17 < y < 0.27:
            continue
        if x < -0.22 and y < -0.22:  # keep prize chute corner clear
            continue
        h = rnd.uniform(0.04, 0.17) * (0.7 if y > 0.2 else 1.0)
        w = rnd.uniform(0.04, 0.09)
        box(f"city_{i:02d}", (w, w * rnd.uniform(0.8, 1.3), h), (x, y, BED_Z + h / 2), M["concrete_dark"], dio)
        if rnd.random() < 0.3:  # fires
            box(f"fire_{i:02d}", (w * 0.4, w * 0.4, 0.004), (x, y, BED_Z + h + 0.002), M["fire"], dio)
            L = bpy.data.lights.new(f"L_fire_{i:02d}", "POINT")
            L.energy = 0.6
            L.color = (1.0, 0.45, 0.12)
            L.shadow_soft_size = 0.01
            lo = bpy.data.objects.new(L.name, L)
            lo.location = (x, y, BED_Z + h + 0.02)
            dio.objects.link(lo)
    return dio, hinge


def build_tower(C, M):
    tw = coll("WATER_TOWER", C["root"])
    root = empty("TOWER_ROOT", (TOWER_XY[0], TOWER_XY[1], ROOF_Z), tw, "ARROWS", 0.03)
    parts = []
    leg_h = 0.04
    for i, a in enumerate((45, 135, 225, 315)):
        r = 0.026
        x, y = math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r
        parts.append(cyl(f"tower_leg_{i}", 0.0018, leg_h, (x, y, leg_h / 2), M["rust"], tw, verts=8))
    parts.append(cyl("tower_tank", 0.035, 0.07, (0, 0, leg_h + 0.035), M["tank_metal"], tw))
    bpy.ops.mesh.primitive_cone_add(radius1=0.036, radius2=0.004, depth=0.014, vertices=32, location=(0, 0, leg_h + 0.077))
    roof = bpy.context.active_object
    roof.name = "tower_roof"
    roof.data.materials.append(M["tank_metal"])
    parts.append(link(roof, tw))
    # ladder on the front (-Y) side so Rin reads to the S07/S08 camera
    for side in (-1, 1):
        parts.append(box(f"ladder_rail_{side}", (0.0012, 0.0012, 0.11), (side * 0.006, -0.037, 0.055), M["rust"], tw))
    for i in range(14):
        parts.append(box(f"ladder_rung_{i:02d}", (0.012, 0.001, 0.001), (0, -0.037, 0.004 + i * 0.0075), M["rust"], tw))
    for p in parts:
        p.parent = root
    return root


def build_claw(C, M):
    cl = coll("CLAW", C["root"])
    root = empty("CLAW_ROOT", (TOWER_XY[0], TOWER_XY[1], 1.80), cl, "ARROWS", 0.04)
    hub = cyl("claw_hub", 0.022, 0.03, (0, 0, 0.03), M["tank_metal"], cl)
    hub.parent = root
    cable = cyl("claw_cable", 0.002, 0.8, (0, 0, 0.44), M["chrome"], cl, verts=8)
    cable.parent = root
    pivots = []
    for i, a in enumerate((90, 210, 330)):
        pv = empty(f"prong_pivot_{i}", (0, 0, 0.018), cl, "SINGLE_ARROW", 0.02)
        pv.parent = root
        pv.rotation_euler = (0, 0, math.radians(a))
        # pivot local +Y points outward; prong hangs down and hooks inward
        upper = box(f"prong_{i}_upper", (0.008, 0.006, 0.07), (0, 0.03, -0.02), M["rust"], cl, rot=(math.radians(-35), 0, 0))
        lower = box(f"prong_{i}_tip", (0.007, 0.005, 0.045), (0, 0.045, -0.07), M["rust"], cl, rot=(math.radians(25), 0, 0))
        upper.parent = pv
        lower.parent = pv
        pivots.append(pv)
    # gantry rails under the cabinet roof
    for x in (-0.40, 0.40):
        box(f"gantry_rail_{x:+.1f}", (0.015, 0.88, 0.015), (x, 0, 1.855), M["chrome"], cl)
    box("gantry_bridge", (0.82, 0.03, 0.02), (0, TOWER_XY[1], 1.845), M["chrome"], cl)
    return root, pivots


def animate_story(rig):
    tower, claw, pivots, hinge, face = rig["tower"], rig["claw"], rig["pivots"], rig["hinge"], rig["face"]
    tx, ty = TOWER_XY
    R = f(RESET_S)
    # ---- door: bangs in S01, bursts open at 2.5 s, shuts again on reset
    key_rot(hinge, 1, (0, 0, 0))
    for sec in (0.5, 1.2, 1.9):
        key_rot(hinge, f(sec), (0, 0, math.radians(-8)))
        key_rot(hinge, f(sec) + 3, (0, 0, 0))
    key_rot(hinge, f(2.5), (0, 0, 0))
    key_rot(hinge, f(2.75), (0, 0, math.radians(-115)))
    key_rot(hinge, R - 1, (0, 0, math.radians(-115)))
    key_rot(hinge, R, (0, 0, 0))
    set_interp(hinge, "CONSTANT")
    for fc in fcurves_of(hinge):   # keep the bangs/opening smooth, only the reset snaps
        for kp in fc.keyframe_points:
            if int(kp.co.x) < R - 1:
                kp.interpolation = "BEZIER"

    # ---- claw + tower. The tower hangs HOLD below the claw from grip until it drops into the chute.
    open_a, closed_a = math.radians(-38), math.radians(4)
    HOLD = 0.135

    def prongs(frame, ang):
        for pv in pivots:
            key_rot(pv, frame, (ang, 0, pv.rotation_euler.z))

    def both(frame, x, y, cz, tilt=0.0):
        key_loc(claw, frame, (x, y, cz))
        key_loc(tower, frame, (x, y, cz - HOLD))
        key_rot(tower, frame, (math.radians(tilt), 0, 0))

    key_loc(claw, 1, (tx, ty, 1.80))
    prongs(1, closed_a)
    key_loc(claw, f(15.0), (tx, ty, 1.80))
    key_loc(claw, f(18.0), (tx, ty, 1.72))
    prongs(f(18.0), closed_a)
    prongs(f(19.0), open_a)
    key_loc(claw, f(22.0), (tx, ty, ROOF_Z + HOLD))
    prongs(f(23.0), open_a)
    prongs(f(24.0), closed_a)
    key_loc(tower, 1, (tx, ty, ROOF_Z))
    key_rot(tower, 1, (0, 0, 0))
    both(f(24.5), tx, ty, ROOF_Z + HOLD)
    both(f(26.0), tx, ty, ROOF_Z + 0.34)
    both(f(30.0), tx, ty, ROOF_Z + 0.42)
    for i, sec in enumerate((30.5, 31.0, 31.5, 32.0)):      # the classic weak-grip jitter shakes Rin loose
        both(f(sec), tx + (0.005 if i % 2 else -0.005), ty, ROOF_Z + 0.42, 4 if i % 2 else -4)
    both(f(33.0), tx, ty, ROOF_Z + 0.42, 2)                 # tower keeps swinging, empty
    both(f(38.0), tx, ty, ROOF_Z + 0.43, -1.5)
    both(f(45.0), tx, ty, ROOF_Z + 0.44, 0)
    both(f(46.5), tx, ty, 1.70)                            # reveal: claw homes to the prize chute...
    both(f(49.0), CHUTE_XY[0], CHUTE_XY[1], 1.70)
    prongs(f(49.0), closed_a)
    prongs(f(49.6), open_a)                                # ...and drops the EMPTY tower in: wrong prize
    key_loc(tower, f(49.6), (CHUTE_XY[0], CHUTE_XY[1], 1.70 - HOLD))
    key_loc(tower, f(50.3), (CHUTE_XY[0], CHUTE_XY[1], BED_Z + 0.004))
    key_rot(tower, f(50.3), (math.radians(18), 0, math.radians(30)))
    key_loc(tower, R - 1, (CHUTE_XY[0], CHUTE_XY[1], BED_Z + 0.004))
    key_rot(tower, R - 1, (math.radians(18), 0, math.radians(30)))
    key_loc(tower, R, (tx, ty, ROOF_Z))
    key_rot(tower, R, (0, 0, 0))
    key_loc(claw, R - 1, (CHUTE_XY[0], CHUTE_XY[1], 1.70))
    prongs(R - 1, open_a)
    key_loc(claw, R, (tx, ty, 1.80))
    prongs(R, closed_a)
    for ob in [tower, claw] + list(pivots):   # hard snap only on the reset frame
        for fc in fcurves_of(ob):
            for kp in fc.keyframe_points:
                if int(kp.co.x) in (R - 1, R):
                    kp.interpolation = "CONSTANT"

    # ---- face target follows the active shot camera so standees always face the lens
    for sid, a, b, lens, c0, c1, *_ in SHOTS:
        key_loc(face, f(a), c0)
        key_loc(face, f(b) - 1, c1)
    set_interp(face, "LINEAR")


def build_characters(C, M, face, tower_root):
    ch = coll("CHARACTERS_2D", C["root"])
    base = M["acrylic"]
    RIN = (0.75, 0.15, 0.12)
    R = f(RESET_S)
    shot_rng = {s[0]: (f(s[1]), f(s[2]) - 1) for s in SHOTS}
    rin = {}
    # (object, file, shots-visible, location, parent)
    defs = [
        ("rin_backing_away",  "rin_backing_away.png",  ["S02_establish"],                 (0.0, -0.03, ROOF_Z), None),
        ("rin_boot_grab",     "rin_boot_grab.png",     ["S03_lost_boot"],                 (0.0, 0.0, ROOF_Z), None),
        ("rin_climb_back",    "rin_climb_back.png",    ["S04_run_climb"],                 (0.0, -0.041, 0.035), tower_root),
        ("rin_cling_scared",  "rin_cling_scared.png",  ["S05_pile_topdown"],              (0.0, -0.041, 0.075), tower_root),
        ("rin_look_up",       "rin_look_up.png",       ["S06_light_above"],               (0.0, -0.041, 0.075), tower_root),
        ("rin_cling_hope",    "rin_cling_hope.png",    ["S07_claw_descends", "S08_grip_lift", "S09_false_hope"], (0.0, -0.041, 0.075), tower_root),
        ("rin_slip_shock",    "rin_slip_shock.png",    ["S10_slip"],                      (0.0, -0.041, 0.07), tower_root),
        ("rin_reset_lookup",  "rin_reset_lookup.png",  ["S17b_reset_loop"],               (0.0, -0.01, ROOF_Z), None),
    ]
    for name, fn, shots, loc, parent in defs:
        o = sprite(name, fn, RIN_H, loc, ch, face, RIN, parent=parent, base_mat=None if parent else base)
        rng = [shot_rng[s] for s in shots]
        key_visible(o, rng)
        animate_sheet(o.data.materials[0], rng)
        rin[name] = o
    # falling: leaves the ladder (world pos of the hanging tower) and lands on the roof at PIN_XY
    fall = sprite("rin_falling", "rin_falling.png", RIN_H, (0, 0, 0), ch, face, RIN)
    tx, ty = TOWER_XY
    key_loc(fall, f(32.0), (tx, ty - 0.041, ROOF_Z + 0.42 - 0.135 + 0.07))
    key_loc(fall, f(32.6), (tx - 0.01, ty - 0.05, ROOF_Z + 0.34))      # slow-mo hang
    key_loc(fall, f(34.8), (PIN_XY[0], PIN_XY[1], ROOF_Z + 0.002))
    key_visible(fall, [shot_rng["S11_fall"]])
    animate_sheet(fall.data.materials[0], [shot_rng["S11_fall"]])
    rin["rin_falling"] = fall
    imp = sprite("rin_impact", "rin_impact.png", RIN_H * 0.55, (PIN_XY[0], PIN_XY[1], ROOF_Z), ch, face, RIN)
    key_visible(imp, [shot_rng["S12_impact"]])
    animate_sheet(imp.data.materials[0], [shot_rng["S12_impact"]])
    # PINNED GROUP: three parallax layers (back zombies / Rin / front zombies), visible until the reset
    # (hidden during the face ECU, where the close-up sheet carries the same struggle at face size)
    pin_rng = [(shot_rng["S13a_pinned"][0], shot_rng["S13a_pinned"][1]), (shot_rng["S14_pullback"][0], R - 1)]
    for name, fn, h, dy, col in [
        ("pin_layer_back",  "pin_layer_back.png",  0.034, +0.010, (0.40, 0.30, 0.20)),
        ("pin_layer_rin",   "pin_layer_rin.png",   0.012,  0.000, RIN),
        ("pin_layer_front", "pin_layer_front.png", 0.012, -0.0004, (0.30, 0.45, 0.40)),  # same plane as pin_layer_rin
    ]:
        o = sprite(name, fn, h, (PIN_XY[0], PIN_XY[1] + dy, ROOF_Z), ch, face, col)
        key_visible(o, pin_rng)
        animate_sheet(o.data.materials[0], pin_rng)
        rin[name] = o
    face_cu = sprite("pin_face_closeup", "pin_face_closeup.png", 0.017, (PIN_XY[0], PIN_XY[1] - 0.013, ROOF_Z), ch, face, RIN)
    key_visible(face_cu, [shot_rng["S13b_pinned_face"]])
    animate_sheet(face_cu.data.materials[0], [shot_rng["S13b_pinned_face"]])
    # S01: grey fingers squirming out of the gap on the door's free edge
    fingers = sprite("door_fingers", "door_fingers.png", 0.014,
                     (DOOR_XY[0] + 0.013, DOOR_XY[1] - 0.004, ROOF_Z + 0.010), ch, face, (0.45, 0.55, 0.45))
    key_visible(fingers, [shot_rng["S01_door_bang"]])
    animate_sheet(fingers.data.materials[0], [shot_rng["S01_door_bang"]])
    # tiny lost boot on the rooftop from S03 on (callback in the prize tray)
    bt = box("rin_lost_boot_on_roof", (0.003, 0.005, 0.0035), (0.004, -0.004, ROOF_Z + 0.002), M["boot"], ch)
    key_visible(bt, [(f(6.8), R - 1)])
    # Nova (real-world scale)
    NOVA = (0.55, 0.40, 0.78)
    nova_defs = [
        ("nova_back_joystick", "nova_back_joystick.png", ["S15_glass_reveal"], (NOVA_XY[0], NOVA_XY[1], 0.0), NOVA_H),
        ("nova_profile_almost","nova_profile_almost.png",["S16_nova_almost"],  (NOVA_XY[0], NOVA_XY[1], 0.87), 0.75),  # waist-up art
        ("nova_hand_coin",     "nova_hand_coin.png",     ["S17a_coin"],        (0.40, -0.56, 0.80), 0.16),
    ]
    for name, fn, shots, loc, h in nova_defs:
        o = sprite(name, fn, h, loc, ch, face, NOVA, shape="hand" if "hand" in name else "figure")
        rng = [shot_rng[s] for s in shots]
        key_visible(o, rng)
        animate_sheet(o.data.materials[0], rng)
    return rin


def build_crowd(C, M, face):
    cr = coll("ZOMBIE_CROWD", C["root"])
    root = empty("CROWD_ROOT", (0, 0, 0), cr, "CUBE", 0.01)
    rnd = random.Random(SEED + 1)
    variants = [
        ("Z01_mechanic", (0.80, 0.35, 0.12)),
        ("Z02_tourist",  (0.15, 0.55, 0.55)),
        ("Z03_cop_brute",(0.12, 0.15, 0.30)),
        ("Z04_raincoat", (0.80, 0.70, 0.15)),
    ]
    # each variant: 3 frame-by-frame pose sheets (walk / reach-up / climb), each in 3 phase-offset
    # copies so neighbouring standees never move in lock-step. Materials are shared across instances.
    R = f(RESET_S)
    mats = {}
    for vname, col in variants:
        for pose, spec in ZOMBIE_ANIM.items():
            for ph in range(3):
                key = f"zombie_{vname.lower()}_{pose}"
                m, asp = load_sheet(key, col, spec, mat_name=f"M_{key}_ph{ph}")
                animate_sheet(m, [(1, R - 1)], phase=ph * 3)
                mats[(vname, pose, ph)] = (m, asp)
    tx, ty = TOWER_XY
    n = 96
    for i in range(n):
        vname, _ = variants[i % 4]
        # spawn order: first 6 burst out with the door at 2.5 s, the rest stream out until ~14 s
        spawn = 2.5 + (i / n) * 11.5 if i >= 6 else 2.5
        ang = rnd.uniform(0, math.tau)
        rad = rnd.uniform(0.04, 0.14) if i > 20 else rnd.uniform(0.03, 0.06)
        gx = max(-0.165, min(0.165, tx + math.cos(ang) * rad - 0.03))
        gy = max(-0.115, min(0.215, ty + math.sin(ang) * rad - 0.05))
        pose = "climb" if rad < 0.045 else ("reach" if rad < 0.07 else "walk")   # climbers pile up the tower legs
        m, asp = mats[(vname, pose, i % 3)]
        h = ZOMBIE_H * (1.25 if vname == "Z03_cop_brute" else rnd.uniform(0.93, 1.05))
        o = sprite(f"zombie_{i:03d}", None, h, (0, 0, 0), cr, face, (1, 1, 1), aspect=asp, parent=root,
                   base_mat=M["acrylic"], material=m, mesh_name=f"ME_{vname}_{pose}_{i % 3}_{h:.4f}")
        door = (DOOR_XY[0] + rnd.uniform(-0.01, 0.01), DOOR_XY[1] - 0.01, ROOF_Z)
        key_loc(o, 1, door)
        key_loc(o, f(spawn), door)
        key_loc(o, f(spawn) + rnd.randint(36, 70), (gx, gy, ROOF_Z))
        # after Rin lands (35 s) the nearest half of the horde swarms the pin spot and rings it
        swarm = i % 2 == 0
        ring = rnd.uniform(0.022, 0.07)
        sx = PIN_XY[0] + math.cos(ang) * ring
        sy = PIN_XY[1] + abs(math.sin(ang)) * ring * 0.8 + 0.012   # always BEHIND her: the lens is on the -Y side
        t = spawn + 3.0
        while t < RESET_S - 0.5:
            # anyone standing in the lens path (in front of the pin spot) is pushed behind her too
            in_lens = gy < PIN_XY[1] + 0.012 and abs(gx - PIN_XY[0]) < 0.10
            cx, cy = (sx, sy) if ((swarm or in_lens) and t > 35.6) else (gx, gy)
            key_loc(o, f(t), (cx + rnd.uniform(-0.004, 0.004), cy + rnd.uniform(-0.004, 0.004), ROOF_Z))
            t += rnd.uniform(0.6, 1.0) if 35 < t < 41 else rnd.uniform(1.2, 2.2)
        key_visible(o, [(f(spawn), R - 1)])
    return root


def build_arcade_room(C, M):
    ar = coll("ARCADE_ROOM", C["root"])
    box("floor", (8, 8, 0.01), (0, -1.5, -0.005), M["floor"], ar)
    box("wall_back_far", (8, 0.05, 4), (0, 2.5, 2), M["wall"], ar)
    img, _ = load_image("../textures/tex_arcade_bokeh_plate.png", (0.45, 0.10, 0.45), "card", 512, 512)
    me = sprite_mesh("ME_bokeh", 3.2, 0.5625 * 2)
    me.materials.append(sprite_material("M_bokeh", img, emission=1.5))
    pl = bpy.data.objects.new("bokeh_plate_side", me)
    pl.location = (2.2, -0.4, 0)
    pl.rotation_euler = (0, 0, math.radians(-70))
    ar.objects.link(pl)
    for i, x in enumerate((-1.3, 1.4, 2.4)):
        box(f"other_cabinet_{i}", (0.9, 0.9, 1.9), (x, 0.2 + i * 0.3, 0.95), M["cab_body"], ar)
        box(f"other_cabinet_glow_{i}", (0.8, 0.01, 0.8), (x, 0.2 + i * 0.3 - 0.46, 1.4), M["neon_pink" if i % 2 else "neon_cyan"], ar)
    for name, col, loc, energy in [
        ("L_neon_pink", (1.0, 0.2, 0.7), (-0.9, -1.2, 1.8), 120),
        ("L_neon_cyan", (0.2, 0.8, 1.0), (1.0, -1.0, 1.6), 120),
    ]:
        L = bpy.data.lights.new(name, "AREA")
        L.energy, L.color, L.size = energy, col, 0.8
        o = bpy.data.objects.new(name, L)
        o.location = loc
        o.rotation_euler = (math.radians(70), 0, math.atan2(-loc[0], 1.0))
        ar.objects.link(o)


def build_lights(C):
    lt = coll("LIGHTS_DIORAMA", C["root"])
    # cold "moonlight" = the cabinet's ceiling LED panel
    L = bpy.data.lights.new("L_cabinet_ceiling_LED", "AREA")
    L.energy, L.color, L.size = 6.0, (0.55, 0.68, 1.0), 0.6
    o = bpy.data.objects.new(L.name, L)
    o.location = (0.05, 0.10, 1.84)
    lt.objects.link(o)
    # green door spill
    L = bpy.data.lights.new("L_door_green", "POINT")
    L.energy, L.color, L.shadow_soft_size = 0.04, (0.25, 1.0, 0.4), 0.004  # tiny: 2 cm from the door
    o = bpy.data.objects.new(L.name, L)
    o.location = (DOOR_XY[0], DOOR_XY[1] - 0.012, ROOF_Z + 0.046)
    lt.objects.link(o)
    # spotlight that "comes from heaven" in S06 (the claw's work light)
    L = bpy.data.lights.new("L_claw_spot", "SPOT")
    L.energy, L.color, L.spot_size = 3.0, (0.85, 0.92, 1.0), math.radians(25)
    o = bpy.data.objects.new(L.name, L)
    o.location = (TOWER_XY[0], TOWER_XY[1], 1.78)
    lt.objects.link(o)
    L.energy = 0.0
    L.keyframe_insert("energy", frame=f(15.0))
    L.energy = 3.0
    L.keyframe_insert("energy", frame=f(16.0))
    L.keyframe_insert("energy", frame=f(43.0))
    L.energy = 0.0
    L.keyframe_insert("energy", frame=f(45.0))


def build_rin_fill(C, tower_root):
    """Soft face light for Rin on the ladder so the 2.3 cm figure reads against the rusty tower."""
    lt = coll("LIGHTS_DIORAMA", C["root"])
    L = bpy.data.lights.new("L_rin_fill", "POINT")
    L.color, L.shadow_soft_size = (1.0, 0.86, 0.75), 0.01
    o = bpy.data.objects.new(L.name, L)
    o.parent = tower_root
    o.location = (-0.03, -0.07, 0.12)    # upper-left, off the lens axis so the acrylic sheen does not flare
    lt.objects.link(o)
    for fr, e in ((f(12.0) - 1, 0.0), (f(12.0), 0.12), (f(32.0), 0.12), (f(32.0) + 1, 0.0)):
        L.energy = e
        L.keyframe_insert("energy", frame=fr)
    set_interp(L, "CONSTANT")


def build_cameras(C):
    cams = coll("CAMERAS", C["root"])
    scn = bpy.context.scene
    for m in list(scn.timeline_markers):
        scn.timeline_markers.remove(m)
    first = None
    for sid, a, b, lens, c0, c1, t0, t1 in SHOTS:
        cd = bpy.data.cameras.new("CAM_" + sid)
        cd.lens = lens
        cd.clip_start = 0.0005
        cd.clip_end = 30
        cd.sensor_fit = "VERTICAL"
        cam = bpy.data.objects.new("CAM_" + sid, cd)
        cams.objects.link(cam)
        aim = empty("AIM_" + sid, t0, cams, "SPHERE", 0.005)
        tr = cam.constraints.new("TRACK_TO")
        tr.target = aim
        tr.track_axis = "TRACK_NEGATIVE_Z"
        tr.up_axis = "UP_Y"
        if sid in SHOT_PARENT:
            cam.parent = aim.parent = bpy.data.objects[SHOT_PARENT[sid]]
        key_loc(cam, f(a), c0)
        key_loc(cam, f(b) - 1, c1)
        key_loc(aim, f(a), t0)
        key_loc(aim, f(b) - 1, t1)
        # miniature look: shallow DOF focused on the aim point
        cd.dof.use_dof = True
        cd.dof.focus_object = aim
        # at 1:60 scale f/1.4 blurs everything; f/2.8-4 still reads as tilt-shift miniature
        cd.dof.aperture_fstop = 8.0 if sid in ("S01_door_bang", "S03_lost_boot", "S06_light_above", "S12_impact", "S13a_pinned", "S13b_pinned_face", "S17b_reset_loop") else 2.8
        if sid == "S15_glass_reveal":   # rack DOF wider as we exit the glass
            cd.dof.aperture_fstop = 2.0
            cd.keyframe_insert("dof.aperture_fstop", frame=f(a))
            cd.dof.aperture_fstop = 5.6
            cd.keyframe_insert("dof.aperture_fstop", frame=f(b) - 1)
        if sid in ("S12_impact", "S13a_pinned", "S13b_pinned_face"):    # handheld shake on impact
            for k in range(0, 10):
                key_loc(cam, f(a) + k * 2, (c0[0] + random.uniform(-0.002, 0.002), c0[1], c0[2] + random.uniform(-0.002, 0.002)))
        mk = scn.timeline_markers.new(sid, frame=f(a))
        mk.camera = cam
        first = first or cam
    scn.camera = first


def build_materials():
    M = {
        "cab_body":      mat("cab_body", (0.06, 0.07, 0.10), 0.35, 0.2),
        "cab_trim":      mat("cab_trim", (0.55, 0.58, 0.65), 0.25, 0.8),
        "chrome":        mat("chrome", (0.85, 0.85, 0.9), 0.12, 1.0),
        "black":         mat("black", (0.01, 0.01, 0.01), 0.5),
        "glass":         mat("glass", (0.75, 0.85, 1.0), 0.02, 0.0, alpha=0.10),
        "acrylic":       mat("acrylic_base", (0.9, 0.95, 1.0), 0.05, 0.0, alpha=0.25),
        "marquee":       mat("marquee", (0.3, 0.05, 0.3), 0.4, 0, emit=(1.0, 0.25, 0.8), strength=6),
        "neon_pink":     mat("neon_pink", (1.0, 0.2, 0.7), 0.3, 0, emit=(1.0, 0.2, 0.7), strength=12),
        "neon_cyan":     mat("neon_cyan", (0.2, 0.8, 1.0), 0.3, 0, emit=(0.2, 0.8, 1.0), strength=12),
        "led_red":       mat("led_red", (0.2, 0.0, 0.0), 0.4, 0, emit=(1.0, 0.05, 0.05), strength=8),
        "moon_lamp":     mat("moon_lamp", (0.9, 0.95, 1.0), 0.2, 0, emit=(0.85, 0.92, 1.0), strength=25),
        "red_glossy":    mat("red_glossy", (0.8, 0.02, 0.05), 0.1),
        "boot":          mat("boot", (0.12, 0.08, 0.06), 0.7),
        "street":        mat("street", (0.04, 0.045, 0.06), 0.25),
        "concrete":      mat("concrete", (0.30, 0.31, 0.30), 0.85),
        "concrete_dark": mat("concrete_dark", (0.08, 0.09, 0.12), 0.8),
        "roof_wet":      mat("roof_wet", (0.10, 0.12, 0.16), 0.08),     # glossy = resin diorama sheen
        "rust":          mat("rust", (0.35, 0.16, 0.07), 0.8, 0.4),
        "tank_metal":    mat("tank_metal", (0.45, 0.46, 0.47), 0.35, 0.9),
        "metal_dull":    mat("metal_dull", (0.25, 0.26, 0.27), 0.6, 0.6),
        "door_green":    mat("door_green", (0.10, 0.35, 0.18), 0.5, 0.3),
        "green_glow":    mat("green_glow", (0.2, 1, 0.4), 0.5, 0, emit=(0.2, 1, 0.4), strength=4),
        "fire":          mat("fire", (1, 0.4, 0.1), 0.5, 0, emit=(1, 0.42, 0.1), strength=30),
        "floor":         mat("floor", (0.05, 0.04, 0.07), 0.15, 0.1),
        "wall":          mat("wall", (0.03, 0.02, 0.05), 0.6),
    }
    found = [k for k, (fn, tile, bump) in SURFACE_TEX.items() if apply_surface_texture(M[k], fn, tile, bump)]
    print(f"surface textures: {len(found)}/{len(SURFACE_TEX)} found", found)
    return M


def render_previews(out_dir, every_shot_frac=0.5):
    """Low-res stills, one per shot, for checking layout/cameras (not final quality)."""
    scn = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    scn.render.resolution_percentage = 25
    try:
        scn.eevee.taa_render_samples = 16
    except AttributeError:
        pass
    for sid, a, b, *_ in SHOTS:
        fr = f(a + (b - a) * every_shot_frac)
        scn.frame_set(fr)
        scn.camera = bpy.data.objects["CAM_" + sid]
        scn.render.filepath = os.path.join(out_dir, f"{sid}_f{fr:04d}.png")
        bpy.ops.render.render(write_still=True)
    scn.render.resolution_percentage = 100
    scn.render.filepath = "//render/almost_"


def main():
    global ASSET_DIR, TEX_DIR
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    preview = argv[argv.index("--preview") + 1] if "--preview" in argv else None
    here = os.path.dirname(os.path.abspath(out)) if out else (
        bpy.path.abspath("//") or os.path.dirname(os.path.abspath(__file__)))
    ASSET_DIR = os.path.join(here, "assets", "sprites")
    TEX_DIR = os.path.join(here, "assets", "textures")
    random.seed(SEED)

    reset_scene()
    C = {"root": bpy.context.scene.collection}
    M = build_materials()
    build_cabinet(C, M)
    dio, hinge = build_diorama(C, M)
    tower = build_tower(C, M)
    claw, pivots = build_claw(C, M)
    face = empty("FACE_TARGET", SHOTS[0][4], coll("CAMERAS", C["root"]), "SPHERE", 0.004)
    build_characters(C, M, face, tower)
    crowd = build_crowd(C, M, face)
    build_arcade_room(C, M)
    build_lights(C)
    build_rin_fill(C, tower)
    build_cameras(C)
    animate_story({"tower": tower, "claw": claw, "pivots": pivots, "hinge": hinge, "face": face})
    bpy.context.scene.frame_set(1)

    if out:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
        print("saved", out)
    if preview:
        render_previews(preview)
        print("previews ->", preview)


if __name__ == "__main__":
    main()
