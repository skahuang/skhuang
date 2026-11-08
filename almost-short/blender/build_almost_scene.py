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
CHUTE_XY = (0.30, -0.30)   # prize chute (front-right, above the outside pickup door)
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
    "rin_cling_hope":      (4, 2, 8, 4, "once"),       # each shot: fear -> hope -> smile in 2 s, then holds the smile
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
    ("S06_light_above",  15.0, 18.0, 16, (0.108, 0.070, 1.170),  (0.107, 0.071, 1.171),  (0.10, 0.103, 1.215), (0.10, 0.103, 1.220)),
    ("S07_claw_descends",18.0, 22.0, 35, (0.32, -0.16, 1.42),    (0.30, -0.15, 1.38),    (0.10, 0.14, 1.30),   (0.10, 0.14, 1.24)),
    ("S08_grip_lift",    22.0, 26.0, 35, (0.28, -0.20, 1.34),    (0.30, -0.22, 1.47),    (0.10, 0.14, 1.20),   (0.10, 0.14, 1.42)),
    ("S09_false_hope",   26.0, 30.0, 50, (0.016, -0.105, 0.080), (0.013, -0.098, 0.088), (0.0, -0.041, 0.087), (0.0, -0.041, 0.090)),  # local to TOWER_ROOT
    ("S10_slip",         30.0, 32.0, 35, (0.00, -0.08, 1.66),    (0.01, -0.07, 1.65),    (0.10, 0.14, 1.48),   (0.10, 0.14, 1.48)),
    # ---- Act 3: fall, pinned, pull-back (32-45 s) — the tower stays in the claw, only Rin falls
    ("S11_fall",         32.0, 35.0, 35, (0.28, -0.22, 1.42),    (0.20, -0.15, 1.20),    (0.10, 0.10, 1.40),   (0.03, 0.00, 1.11)),
    ("S12_impact",       35.0, 36.0, 50, (0.065, -0.05, 1.106),  (0.065, -0.05, 1.106),  (0.02, 0.0, 1.108),   (0.02, 0.0, 1.108)),
    ("S13a_pinned",      36.0, 39.0, 50, (0.034, -0.034, 1.105), (0.031, -0.030, 1.105), (0.02, 0.0, 1.108),   (0.02, 0.0, 1.108)),
    ("S13b_pinned_face", 39.0, 41.0, 50, (0.02, -0.052, 1.108),  (0.02, -0.046, 1.108),  (0.02, -0.013, 1.108), (0.02, -0.013, 1.108)),
    ("S14_pullback",     41.0, 45.0, 24, (0.034, -0.034, 1.105), (0.14, -0.44, 1.37),    (0.02, 0.0, 1.108),   (0.08, 0.10, 1.47)),
    # ---- Act 4: reveal + loop (45-60 s)
    ("S15_glass_reveal", 45.0, 51.0, 35, (0.14, -0.44, 1.37),    (-0.45, -2.30, 1.78),   (0.08, 0.10, 1.47),   (0.05, -0.30, 1.20)),
    ("S16_nova_almost",  51.0, 55.0, 85, (1.00, -1.74, 1.23),    (0.95, -1.67, 1.22),    (0.24, -0.86, 1.115), (0.24, -0.86, 1.12)),   # tight 3/4 close-up on her face (eyes ~1.15 m)
    ("S17a_coin",        55.0, 57.0, 50, (0.44, -0.86, 0.98),    (0.41, -0.80, 0.95),    (0.22, -0.52, 0.84),  (0.22, -0.52, 0.84)),
    ("S17b_reset_loop",  57.0, 60.0, 35, (0.02, -0.04, 1.30),    (-0.085, -0.03, 1.114), (0.0, -0.01, 1.10),   (-0.11, 0.11, 1.124)),
]


# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------
# Shots whose camera + aim ride with a moving object (coordinates above are then local to it)
SHOT_PARENT = {"S09_false_hope": "TOWER_ROOT"}
# Shots that aim past the subject but must keep her sharp
SHOT_FOCUS = {"S06_light_above": "rin_look_up"}


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
    "roof_wet":       ("tex_roof_tiles_wet.png",                               0.04, 0.15),
    "concrete":       ("tex_concrete_peel.png",                                0.06, 0.20),
    "facade":         (["tex_facade_stained.png", "tex_concrete_peel.png"],    0.08, 0.20),
    "parapet":        (["tex_parapet_moss.png", "tex_concrete_peel.png"],      0.04, 0.20),
    "concrete_dark":  (["tex_ruins_facade.png", "tex_city_facade_windows.png"], 0.08, 0.10),
    "street":         ("tex_street_asphalt_wet.png",                           0.15, 0.15),
    "rust":           ("tex_rust_metal.png",                                   0.02, 0.20),
    "tank_metal":     (["tex_tank_galvanized.png", "tex_water_tank_paint.png"], 0.07, 0.15),
    "metal_dull":     ("tex_metal_scratched.png",                              0.03, 0.10),
    "chrome":         ("tex_chrome_scratched.png",                             0.05, 0.03),
    "cable":          ("tex_cable_corrugated.png",                             0.012, 0.30),
    "door_green":     ("tex_door_green_metal.png",                             None, 0.15),
    "window_broken":  ("tex_window_broken.png",                                None, 0.10),
    "window_boarded": ("tex_window_boarded.png",                               None, 0.20),
    "shutter":        ("tex_shutter_rolling.png",                              None, 0.20),
    "cab_body":       (["tex_cab_body_bluesteel.png", "tex_cabinet_body.png"], 0.50, 0.05),
    "cab_trim":       (["tex_steel_brushed.png", "tex_chrome_scratched.png"],  0.20, 0.03),
    "vent_grille":    ("tex_vent_grille.png",                                  None, 0.30),
    "louver":         ("tex_louver_vent.png",                                  None, 0.30),
    "coin_mech":      ("tex_coin_mech.png",                                    None, 0.20),
    "pillar":         (["tex_concrete_pillar.png", "tex_concrete_peel.png"],   0.80, 0.10),
    "hazard":         ("tex_hazard_stripes.png",                               0.25, 0.05),
    "poster":         ("tex_poster_arcade.png",                                None, 0.00),
    "arcade_screen":  ("tex_arcade_screen.png",                                None, 0.00),
    "plush_card":     ("tex_plush_pile.png",                                   None, 0.00),
    "machine_pink":   ("tex_claw_machine_pink.png",                            None, 0.05),
    "marquee":        ("tex_marquee_logo.png",                                 None, 0.00),
    "floor":          (["tex_arcade_floor_tiles.png", "tex_arcade_carpet.png"], 1.20, 0.08),
    "wall":           ("tex_arcade_wall.png",                                  2.00, 0.05),
    "glass":          ("tex_glass_smudge.png",                                 None, 0.00),
    # V5 (TEXTURES_V5.md): lamp/sign pass; all optional, plain materials until the art arrives
    "billboard":      ("tex_billboard_ad.png",                                 None, 0.05),
    "sign_panel":     ("tex_signboard_vertical.png",                           None, 0.00),
    "window_lit":     ("tex_window_lit_interior.png",                          None, 0.00),
    "window_warm":    ("tex_window_lit_interior_warm.png",                     None, 0.00),
    "grating":        ("tex_metal_grating.png",                                0.012, 0.20),
    "awning":         ("tex_awning_torn.png",                                  0.06, 0.10),
    # V6 (TEXTURES_V6.md): arcade props outside the machine
    "racing_screen":  (["tex_racing_screen.png", "tex_arcade_screen.png"],     None, 0.00),
    "gacha_card":     ("tex_gashapon_card.png",                                None, 0.00),
    "prize_box":      ("tex_prize_boxes.png",                                  None, 0.00),
    "wall_tv":        (["tex_wall_tv_promo.png", "tex_arcade_screen.png"],     None, 0.00),
}


SURFACE_TINT = {"facade": 0.3, "parapet": 0.45, "concrete": 0.6, "pillar": 0.7, "cab_body": 1.8}   # brightness multipliers


def first_texture(names):
    """First existing file in assets/textures/ from a name or list of names (newest art first)."""
    for fn in ([names] if isinstance(names, str) else names):
        path = os.path.join(TEX_DIR or "", fn)
        if TEX_DIR and os.path.isfile(path):
            return path
    return None


# Procedural weathering (phase 1, no extra art): which layers each tiled surface gets.
#   grime = dark dirt in corners/contacts (AO)   streaks = rain stains running down walls
#   moss  = green growth on damp upward faces    vary  = per-object brightness/hue drift
#   chip  = flaking paint / spalled edges     rust = orange run-off under bolts and seams (vertical faces)
WEATHER = {
    "roof_wet":      {"grime": 0.55, "moss": 0.25, "vary": 0.10},
    "concrete":      {"grime": 0.60, "streaks": 0.45, "moss": 0.30, "chip": 0.30, "vary": 0.15},
    "facade":        {"grime": 0.50, "streaks": 0.55, "vary": 0.25},
    "parapet":       {"grime": 0.55, "streaks": 0.50, "moss": 0.55, "chip": 0.45, "vary": 0.15},
    "concrete_dark": {"grime": 0.45, "streaks": 0.50, "vary": 0.30},
    "rust":          {"grime": 0.40, "streaks": 0.35, "rust": 0.50, "vary": 0.15},
    "tank_metal":    {"grime": 0.45, "streaks": 0.60, "moss": 0.20, "rust": 0.70, "vary": 0.05},
    "metal_dull":    {"grime": 0.40, "chip": 0.30, "rust": 0.40, "vary": 0.10},
    "door_green":    {"grime": 0.40, "streaks": 0.30, "chip": 0.45, "rust": 0.50},
    "cab_body":      {"grime": 0.25},          # the hero machine is kept clean: dirt in the seams only
    "pillar":        {"grime": 0.40, "streaks": 0.20, "chip": 0.25, "vary": 0.10},
    "floor":         {"grime": 0.50, "vary": 0.05},
    "wall":          {"grime": 0.35, "streaks": 0.15, "vary": 0.05},
}

# V4 art (optional): greyscale masks replace the procedural noise, colour overlays replace the flat tints.
#   Missing file -> the procedural version above is used, so nothing breaks.
MASK_TEX = {
    "grime":   "tex_mask_grime.png",
    "streaks": "tex_mask_streaks.png",
    "chip":    "tex_mask_chipping.png",
    "height":  "tex_height_concrete.png",
    "prints":  "tex_mask_fingerprints.png",
    "moss":    "tex_moss_patches.png",      # colour + alpha
    "rust":    "tex_rust_streaks.png",      # colour + alpha
}
HEIGHT_MATS = {"concrete", "facade", "parapet", "pillar", "concrete_dark"}   # real relief, not just colour
PRINT_MATS = {"glass": 0.25, "coin_mech": 0.35, "cab_trim": 0.20}            # fingerprint roughness on touched surfaces
CHIP_COLOR = {"door_green": (0.30, 0.28, 0.25, 1.0), "cab_body": (0.38, 0.40, 0.44, 1.0),
              "metal_dull": (0.42, 0.42, 0.43, 1.0)}                        # what shows under the paint
MASK_FOUND = set()


def _mask_image(nt, key, tile, non_color=True):
    """Image node for a V4 mask/overlay: box-projected in object space with a per-object random offset
    (tile = metres per repeat), or on the mesh UVs when tile is None. None if the file is missing."""
    path = first_texture(MASK_TEX[key])
    if not path:
        return None
    MASK_FOUND.add(key)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    if non_color:
        tex.image.colorspace_settings.name = "Non-Color"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if tile:
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1 / tile)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        oi = nt.nodes.new("ShaderNodeObjectInfo")
        off = nt.nodes.new("ShaderNodeVectorMath")
        off.operation = "SCALE"
        off.inputs[0].default_value = (4.13, 2.71, 6.37)
        nt.links.new(oi.outputs["Random"], off.inputs["Scale"])
        nt.links.new(off.outputs["Vector"], mp.inputs["Location"])
        nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
        tex.projection = "BOX"
        tex.projection_blend = 0.25
    else:
        nt.links.new(tc.outputs["UV"], tex.inputs["Vector"])
    return tex


def _mul(nt, a, b):
    mm = nt.nodes.new("ShaderNodeMath")
    mm.operation, mm.use_clamp = "MULTIPLY", True
    nt.links.new(a, mm.inputs[0])
    nt.links.new(b, mm.inputs[1])
    return mm.outputs[0]


def _max(nt, a, b):
    mm = nt.nodes.new("ShaderNodeMath")
    mm.operation, mm.use_clamp = "MAXIMUM", True
    nt.links.new(a, mm.inputs[0])
    nt.links.new(b, mm.inputs[1])
    return mm.outputs[0]


def _mix(nt, blend, fac, a, b):
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type, mx.blend_type = "RGBA", blend
    if isinstance(fac, float):
        mx.inputs[0].default_value = fac
    else:
        nt.links.new(fac, mx.inputs[0])
    for sock, v in ((mx.inputs[6], a), (mx.inputs[7], b)):
        if isinstance(v, tuple):
            sock.default_value = v
        else:
            nt.links.new(v, sock)
    return mx.outputs[2]


def _ramp(nt, src, lo, hi, out_lo=0.0, out_hi=1.0):
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = lo, hi
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = out_lo, out_hi
    nt.links.new(src, mr.inputs["Value"])
    return mr.outputs["Result"]


def _noise(nt, scale_vec, detail=4.0, rough=0.6):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale_vec
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Detail"].default_value, nz.inputs["Roughness"].default_value = detail, rough
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    return nz.outputs["Fac"]


def add_weathering(nt, bsdf, col, tile, w, name=""):
    """Layer grime / rain streaks / moss / chipping / rust / per-object drift over a base colour.
    Driven by geometry (AO, normals) and, when present, the V4 masks, so the same base image ages
    differently on every surface instead of repeating. tile None = the material uses mesh UVs."""
    uv = tile is None
    tile = tile or 0.05
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    up = sep.outputs["Z"]
    side = _ramp(nt, up, 0.35, 0.05, 0.0, 1.0)     # 1 on vertical faces, 0 on floors/tops
    # macro variation: large soft blotches so the tile never reads as a grid
    macro = _ramp(nt, _noise(nt, (0.15 / tile,) * 3, 2.0, 0.5), 0.3, 0.7, 0.62, 1.18)
    col = _mix(nt, "MULTIPLY", 1.0, col, macro)
    if w.get("vary"):
        oi = nt.nodes.new("ShaderNodeObjectInfo")
        hsv = nt.nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Hue"].default_value = 0.5
        nt.links.new(_ramp(nt, oi.outputs["Random"], 0, 1, 1 - w["vary"], 1 + w["vary"] * 0.5), hsv.inputs["Value"])
        nt.links.new(_ramp(nt, oi.outputs["Random"], 0, 1, 0.5 - w["vary"] * 0.08, 0.5 + w["vary"] * 0.08), hsv.inputs["Hue"])
        nt.links.new(col, hsv.inputs["Color"])
        col = hsv.outputs["Color"]
    if w.get("grime"):   # cavities, corners and where props touch the ground
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = 0.02
        ao.samples = 8
        cav = _ramp(nt, ao.outputs["AO"], 0.35, 0.95, 1.0, 0.0)
        gm = _mask_image(nt, "grime", None if uv else tile * 1.5)
        if gm:   # painted dirt clusters break up the AO and add some dirt on open surfaces too
            brk = _ramp(nt, gm.outputs["Color"], 0.0, 0.5, 0.35, 1.0)
            src = _max(nt, _mul(nt, cav, brk), _ramp(nt, gm.outputs["Color"], 0.15, 0.8, 0.0, 0.55))
        else:
            src = _mul(nt, cav, _ramp(nt, _noise(nt, (1 / 0.02,) * 3, 6.0, 0.7), 0.35, 0.65, 0.5, 1.0))
        fac = _ramp(nt, src, 0, 1, 0, w["grime"])
        col = _mix(nt, "MULTIPLY", fac, col, (0.10, 0.08, 0.06, 1.0))
    if w.get("streaks"):   # vertical faces only: run-off stains
        sm = _mask_image(nt, "streaks", None if uv else tile * 2.0)
        if sm:   # box projection maps image-V to world Z on side faces, so the drips run downward
            st = _ramp(nt, sm.outputs["Color"], 0.04, 0.45, 0.0, 1.0)
        else:    # noise stretched along Z
            sx = 1 / max(tile * 0.06, 0.0015)
            st = _ramp(nt, _noise(nt, (sx, sx, sx * 0.04), 3.0, 0.55), 0.45, 0.70, 0.0, 1.0)
        fac = _ramp(nt, _mul(nt, side, st), 0, 1, 0, w["streaks"])
        col = _mix(nt, "MULTIPLY", fac, col, (0.22, 0.20, 0.17, 1.0))
    if w.get("chip"):   # flaking paint: bare, lighter material shows through in sharp chips
        cm = _mask_image(nt, "chip", None if uv else tile * 1.2)
        if cm:   # only the strongest chips; concrete just gets a bit paler, paint shows the metal under it
            fac = _ramp(nt, cm.outputs["Color"], 0.55, 0.85, 0.0, w["chip"])
            if name in CHIP_COLOR:
                col = _mix(nt, "MIX", fac, col, CHIP_COLOR[name])
            else:
                col = _mix(nt, "MULTIPLY", fac, col, (1.45, 1.42, 1.38, 1.0))
    if w.get("rust"):   # orange run-off under bolts and seams, vertical faces only
        rm = _mask_image(nt, "rust", None if uv else tile * 2.0, non_color=False)
        if rm:
            fac = _ramp(nt, _mul(nt, side, rm.outputs["Alpha"]), 0, 1, 0, w["rust"])
            rc = nt.nodes.new("ShaderNodeHueSaturation")      # night palette: no bright orange
            rc.inputs["Value"].default_value = 0.6
            nt.links.new(rm.outputs["Color"], rc.inputs["Color"])
            col = _mix(nt, "MIX", fac, col, rc.outputs["Color"])
    if w.get("moss"):   # damp upward faces, patchy
        top = _ramp(nt, up, 0.55, 0.9, 0.0, 1.0)
        mo = _mask_image(nt, "moss", None if uv else tile * 1.5, non_color=False)
        if mo:   # real moss clumps (colour + alpha) instead of a flat green
            fac = _ramp(nt, _mul(nt, top, mo.outputs["Alpha"]), 0, 1, 0, min(1.0, w["moss"] * 1.6))
            mc = nt.nodes.new("ShaderNodeHueSaturation")
            mc.inputs["Value"].default_value = 0.55
            nt.links.new(mo.outputs["Color"], mc.inputs["Color"])
            col = _mix(nt, "MIX", fac, col, mc.outputs["Color"])
        else:
            pat = _ramp(nt, _noise(nt, (1 / 0.035,) * 3, 5.0, 0.65), 0.48, 0.62, 0.0, 1.0)
            fac = _ramp(nt, _mul(nt, top, pat), 0, 1, 0, w["moss"])
            col = _mix(nt, "MIX", fac, col, (0.05, 0.12, 0.03, 1.0))
    return col


def add_fingerprints(m, tile, strength):
    """Greasy prints and wipe arcs on touched surfaces: rougher where fingers have been."""
    nt = m.node_tree
    bsdf = node_of_type(nt, "BSDF_PRINCIPLED")
    pm = _mask_image(nt, "prints", tile)
    if not pm:
        return
    pr = _ramp(nt, pm.outputs["Color"], 0.0, 0.25, 0.0, strength)
    rough = bsdf.inputs["Roughness"]
    add = nt.nodes.new("ShaderNodeMath")
    add.operation, add.use_clamp = "ADD", True
    if rough.links:
        nt.links.new(rough.links[0].from_socket, add.inputs[0])
    else:
        add.inputs[0].default_value = rough.default_value
    nt.links.new(pr, add.inputs[1])
    nt.links.new(add.outputs[0], rough)


def apply_surface_texture(m, filename, tile, bump):
    path = first_texture(filename)
    if not path:
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
        if m.name in WEATHER:   # anti-tiling: every object samples the texture at its own offset + spin
            oi = nt.nodes.new("ShaderNodeObjectInfo")
            off = nt.nodes.new("ShaderNodeVectorMath")
            off.operation = "SCALE"
            off.inputs[0].default_value = (7.31, 3.17, 5.73)
            nt.links.new(oi.outputs["Random"], off.inputs["Scale"])
            nt.links.new(off.outputs["Vector"], mp.inputs["Location"])
            rot = nt.nodes.new("ShaderNodeCombineXYZ")
            spin = nt.nodes.new("ShaderNodeMath")
            spin.operation = "MULTIPLY"
            spin.inputs[1].default_value = math.tau
            nt.links.new(oi.outputs["Random"], spin.inputs[0])
            nt.links.new(spin.outputs[0], rot.inputs["Z"])
            nt.links.new(rot.outputs["Vector"], mp.inputs["Rotation"])
        nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
        tex.projection = "BOX"
        tex.projection_blend = 0.2
    else:      # whole image on each face (box() lays UVs over each face's two largest axes)
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
    col_out = tex.outputs["Color"]
    if m.name in SURFACE_TINT:   # darken pale GPT art to the night palette of the references
        hsv = nt.nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Value"].default_value = SURFACE_TINT[m.name]
        nt.links.new(col_out, hsv.inputs["Color"])
        col_out = hsv.outputs["Color"]
    if m.name in WEATHER:
        col_out = add_weathering(nt, bsdf, col_out, tile, WEATHER[m.name], m.name)
    nt.links.new(col_out, bsdf.inputs["Base Color"])
    if bsdf.inputs["Emission Strength"].default_value > 0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    if bump > 0:
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.001
        hm = _mask_image(nt, "height", tile) if (tile and m.name in HEIGHT_MATS) else None
        if hm:   # pores, pits and hairline cracks from the height map, layered over the colour-derived bump
            ad = nt.nodes.new("ShaderNodeMath")
            ad.operation = "MULTIPLY_ADD"
            nt.links.new(tex.outputs["Color"], ad.inputs[0])
            ad.inputs[1].default_value = 0.4
            nt.links.new(hm.outputs["Color"], ad.inputs[2])
            nt.links.new(ad.outputs[0], bp.inputs["Height"])
            bp.inputs["Strength"].default_value = bump * 1.5
        else:
            nt.links.new(tex.outputs["Color"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return True


def add_puddles(m):
    """Optional greyscale puddle mask (black = standing water): mirror-smooth puddles, rougher dry tiles."""
    path = first_texture("tex_roof_puddle_mask.png")
    if not path:
        return
    nt = m.node_tree
    bsdf = node_of_type(nt, "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.image.colorspace_settings.name = "Non-Color"
    tex.projection = "BOX"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / 0.25, 1 / 0.25, 1 / 0.25)   # one puddle layout per 25 cm: hides the repeat
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    # only the darkest cores of the mask become standing water, broken up by noise so they read as
    # small irregular puddles in the low spots instead of big repeating blobs
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 60.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMath")
    mix.operation = "ADD"
    nt.links.new(tex.outputs["Color"], mix.inputs[0])
    nt.links.new(nz.outputs["Fac"], mix.inputs[1])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.45
    mr.inputs["From Max"].default_value = 0.70
    mr.inputs["To Min"].default_value = 0.03
    mr.inputs["To Max"].default_value = 0.45
    nt.links.new(mix.outputs["Value"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])


def box(name, size, loc, material, collection, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    box_uv(o.data, size)
    o.data.materials.append(material)
    return link(o, collection)


def box_uv(me, size):
    """UV = position on the box's two largest axes, so a window/door/sign image fills its front face."""
    ax = sorted(range(3), key=lambda k: -size[k])[:2]
    ax.sort(key=lambda k: 2 if k == 2 else k)          # horizontal axis first, Z (if used) second
    uv = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co[ax[0]] / size[ax[0]] + 0.5, co[ax[1]] / size[ax[1]] + 0.5)


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
    # key the viewport too, so the Blender viewport preview matches the render shot by shot
    for prop in ("hide_render", "hide_viewport"):
        setattr(o, prop, True)
        o.keyframe_insert(prop, frame=1)
        for a, b in visible_ranges:
            setattr(o, prop, False)
            o.keyframe_insert(prop, frame=a)
            setattr(o, prop, True)
            o.keyframe_insert(prop, frame=b + 1)
        set_interp(o, "CONSTANT", prop)
    o.hide_viewport = False


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
    # GPT cut-outs carry soft, partly transparent interiors; firm them up so standees read as solid acrylic prints
    am = nt.nodes.new("ShaderNodeMapRange")
    am.inputs["From Max"].default_value = 0.6
    am.clamp = True
    nt.links.new(tex.outputs["Alpha"], am.inputs["Value"])
    nt.links.new(am.outputs["Result"], bsdf.inputs["Alpha"])
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
    try:
        scn.eevee.use_raytracing = True      # mirror-like reflections on the polished arcade floor
    except AttributeError:
        pass
    # the cabinet fog is a small box: tight froxels stop it smearing over the whole frame in wide shots
    for attr, val in (("volumetric_start", 0.01), ("volumetric_end", 6.0), ("volumetric_tile_size", "4"),
                      ("volumetric_samples", 96)):
        try:
            setattr(scn.eevee, attr, val)
        except (AttributeError, TypeError):
            pass
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
    """The ALMOST claw machine, after the five-view sheet: dark blue steel body, brushed frame with
    cyan neon on every vertical edge, magenta belt at the glass line, glass top, warm LED bars."""
    cab = coll("CABINET", C["root"])
    H = 1.95
    # lower body + bolted panel seams
    box("cab_body", (1.0, 1.0, BED_Z - 0.03), (0, 0, (BED_Z - 0.03) / 2 + 0.03), M["cab_body"], cab)
    box("cab_plinth", (0.98, 0.98, 0.03), (0, 0, 0.015), M["black"], cab)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(f"cab_foot_{sx}{sy}", 0.025, 0.012, (sx * 0.44, sy * 0.44, 0.006), M["cab_trim"], cab, verts=16)
    box("cab_panel_seam_front", (0.90, 0.003, 0.004), (0, -0.5015, 0.68), M["cab_trim"], cab)
    for sx in (-1, 1):
        for z in (0.08, 0.62, 0.74, 0.88):
            cyl(f"cab_bolt_{sx}_{z:.2f}", 0.006, 0.004, (sx * 0.44, -0.502, z), M["cab_trim"], cab, verts=10, rot=(math.pi / 2, 0, 0))
    # back: opaque panel full height (back view), louvers + service hatch
    box("cab_back_panel", (0.96, 0.012, H - BED_Z - 0.06), (0, 0.494, BED_Z + (H - BED_Z) / 2), M["cab_body"], cab)
    box("cab_back_hatch", (0.70, 0.004, 0.45), (0, 0.5025, 0.42), M["cab_body"], cab)
    for x in (-0.24, 0.24):
        box(f"cab_back_louver_{x:+.2f}", (0.14, 0.003, 0.11), (x, 0.505, 0.22), M["louver"], cab)
    for sx in (-1, 1):   # side louvers, rear-low
        box(f"cab_side_louver_{sx}", (0.003, 0.15, 0.10), (sx * 0.5015, 0.28, 0.20), M["louver"], cab)
    # frame: corner posts, top ring, glass top
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"cab_pillar_{sx}{sy}", (0.045, 0.045, H), (sx * 0.4775, sy * 0.4775, H / 2), M["cab_trim"], cab)
            # cyan neon on the outward diagonal face of every post (front two face the viewer)
            box(f"neon_post_{sx}{sy}", (0.012, 0.012, H - 0.06), (sx * 0.497, sy * 0.497, H / 2), M["neon_cyan"], cab)
    for name, size, loc in [("cab_top_front", (1.0, 0.045, 0.045), (0, -0.4775, H - 0.0225)),
                            ("cab_top_back", (1.0, 0.045, 0.045), (0, 0.4775, H - 0.0225)),
                            ("cab_top_left", (0.045, 1.0, 0.045), (-0.4775, 0, H - 0.0225)),
                            ("cab_top_right", (0.045, 1.0, 0.045), (0.4775, 0, H - 0.0225))]:
        box(name, size, loc, M["cab_trim"], cab)
    box("neon_top_front", (0.92, 0.012, 0.012), (0, -0.497, H - 0.06), M["neon_cyan"], cab)
    box("glass_top", (0.91, 0.91, 0.004), (0, 0, H - 0.004), M["glass"], cab)
    # magenta belt at the glass line, all four sides
    for name, size, loc in [("belt_front", (1.004, 0.012, 0.055), (0, -0.502, BED_Z - 0.005)),
                            ("belt_back", (1.004, 0.012, 0.055), (0, 0.502, BED_Z - 0.005)),
                            ("belt_left", (0.012, 1.004, 0.055), (-0.502, 0, BED_Z - 0.005)),
                            ("belt_right", (0.012, 1.004, 0.055), (0.502, 0, BED_Z - 0.005))]:
        box(name, size, loc, M["belt"], cab)
    # glass: front / left / right (back is the printed backdrop)
    box("glass_front", (0.91, 0.004, H - BED_Z - 0.05), (0, -0.476, (BED_Z + H - 0.05) / 2 + 0.01), M["glass"], cab)
    box("glass_left", (0.004, 0.91, H - BED_Z - 0.05), (-0.476, 0, (BED_Z + H - 0.05) / 2 + 0.01), M["glass"], cab)
    box("glass_right", (0.004, 0.91, H - BED_Z - 0.05), (0.476, 0, (BED_Z + H - 0.05) / 2 + 0.01), M["glass"], cab)
    # warm LED bars under the top (front view)
    for x in (-0.22, 0.22):
        box(f"led_bar_{x:+.2f}", (0.20, 0.018, 0.008), (x, -0.40, H - 0.07), M["led_warm"], cab)
    L = bpy.data.lights.new("L_cab_led_bars", "AREA")
    L.energy, L.color, L.size = 12.0, (1.0, 0.85, 0.65), 0.6
    lo = bpy.data.objects.new(L.name, L)
    lo.location = (0, -0.38, H - 0.08)
    cab.objects.link(lo)
    # printed ruins backdrop on the inside back wall
    bd_file = "tex_backdrop_ruins_fog.png" if first_texture("tex_backdrop_ruins_fog.png") else "tex_backdrop_city_sky.png"
    img, _ = load_image("../textures/" + bd_file, (0.10, 0.14, 0.30), "card", 512, 512)
    bd = sprite_material("M_backdrop", img, emission=1.0)
    bb = node_of_type(bd.node_tree, "BSDF_PRINCIPLED")   # matte print: no sheen picking up the arcade neon
    bb.inputs["Specular IOR Level"].default_value = 0.0
    bb.inputs["Roughness"].default_value = 1.0
    for l in list(bd.node_tree.links):           # backlit print: emission only, so room neon can't tint it
        if l.to_socket == bb.inputs["Base Color"]:
            bd.node_tree.links.remove(l)
    bb.inputs["Base Color"].default_value = (0, 0, 0, 1)
    bb.inputs["Emission Strength"].default_value = 1.1
    me = sprite_mesh("ME_backdrop", 0.90, 1.0)
    me.materials.append(bd)
    back = bpy.data.objects.new("backdrop_print", me)
    back.location = (0, 0.47, BED_Z)
    back.rotation_euler = (0, 0, math.pi)
    cab.objects.link(back)
    # the "moon": actually the cabinet ceiling lamp (clue in S06 / S09)
    moon = cyl("ceiling_lamp_MOON", 0.035, 0.006, (0.16, 0.30, 1.865), M["moon_lamp"], cab, verts=48)
    # control box (front-left, under the belt): ball-top joystick + glowing magenta button
    box("ctrl_box", (0.34, 0.16, 0.13), (-0.17, -0.575, 0.835), M["cab_trim"], cab)
    box("ctrl_box_top", (0.32, 0.14, 0.004), (-0.17, -0.575, 0.902), M["black"], cab)
    box("joystick_plate", (0.07, 0.07, 0.004), (-0.25, -0.58, 0.905), M["black"], cab)
    cyl("joystick_shaft", 0.007, 0.07, (-0.25, -0.58, 0.94), M["chrome"], cab, verts=12)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, location=(-0.25, -0.58, 0.98))
    ball = bpy.context.active_object
    ball.name = "joystick_ball"
    ball.data.materials.append(M["red_glossy"])
    link(ball, cab)
    cyl("button_bezel", 0.036, 0.012, (-0.08, -0.58, 0.908), M["cab_trim"], cab, verts=32)
    cyl("button_grab", 0.028, 0.016, (-0.08, -0.58, 0.914), M["neon_pink"], cab, verts=32)
    # coin mechanism (right of the control box)
    box("coin_slot_plate", (0.10, 0.012, 0.16), (0.22, -0.506, 0.84), M["coin_mech"], cab)
    box("coin_slot", (0.004, 0.012, 0.05), (0.22, -0.513, 0.87), M["black"], cab)
    box("coin_return", (0.04, 0.012, 0.025), (0.22, -0.513, 0.79), M["black"], cab)
    box("led_timer", (0.16, 0.01, 0.05), (0.0, -0.505, H - 0.12), M["led_red"], cab)
    # lower front: speaker grille (left) and the prize pickup door (right)
    box("vent_grille_front", (0.17, 0.006, 0.17), (-0.30, -0.503, 0.24), M["vent_grille"], cab)
    box("vent_grille_frame", (0.19, 0.004, 0.19), (-0.30, -0.5005, 0.24), M["cab_trim"], cab)
    box("prize_door_frame", (0.21, 0.006, 0.17), (CHUTE_XY[0], -0.503, 0.24), M["cab_trim"], cab)
    box("prize_door_hole", (0.17, 0.010, 0.13), (CHUTE_XY[0], -0.505, 0.24), M["black"], cab)
    box("prize_chute_bin", (0.16, 0.16, 0.14), (CHUTE_XY[0], CHUTE_XY[1], BED_Z + 0.07), M["glass"], cab)
    box("prize_tray", (0.16, 0.10, 0.02), (CHUTE_XY[0], -0.46, 0.175), M["cab_trim"], cab)
    # tiny single boots in the prize tray: earlier failed rounds (dark-humour clue)
    for i in range(5):
        box(f"lost_boot_{i}", (0.006, 0.010, 0.007),
            (CHUTE_XY[0] - 0.06 + i * 0.028, -0.47 + (i % 2) * 0.012, 0.19), M["boot"], cab, rot=(0, 0, i * 0.7))
    return moon


def build_facade(dio, M, rnd, cx, cy, w, d, z0, floors, floor_h, prefix, shutter_side="S"):
    """Windows, sills, floor bands and wall AC units on all four faces of a block building."""
    faces = [("S", (0, -1)), ("N", (0, 1)), ("E", (1, 0)), ("W", (-1, 0))]
    for side, (nx, ny) in faces:
        span = w if nx == 0 else d
        rot = (0, 0, 0) if nx == 0 else (0, 0, math.pi / 2)
        n_win = max(2, int(span / 0.075))
        for fl in range(floors):
            zc = z0 + fl * floor_h + floor_h * 0.55
            for k in range(n_win):
                t = -span / 2 + span * (k + 0.5) / n_win
                px = cx + (t if nx == 0 else nx * (w / 2 + 0.0006))
                py = cy + (t if ny == 0 else ny * (d / 2 + 0.0006))
                if fl == 0 and side == shutter_side and abs(t) < 0.06:
                    continue    # ground-floor shutter goes here
                r = rnd.random()
                kind = "window_lit" if r < 0.04 else ("window_boarded" if r < 0.32 else "window_broken")
                box(f"{prefix}_win_{side}{fl}{k}", (0.030, 0.0012, 0.026), (px, py, zc), M[kind], dio, rot=rot)
                ox, oy = nx * 0.0012, ny * 0.0012
                box(f"{prefix}_sill_{side}{fl}{k}", (0.036, 0.004, 0.0025), (px + ox, py + oy, zc - 0.0145), M["parapet"], dio, rot=rot)
                box(f"{prefix}_lintel_{side}{fl}{k}", (0.034, 0.003, 0.003), (px + ox * 0.5, py + oy * 0.5, zc + 0.0145), M["parapet"], dio, rot=rot)
                if fl > 0 and rnd.random() < 0.18:   # wall-hung AC unit under the window
                    box(f"{prefix}_wac_{side}{fl}{k}", (0.016, 0.008, 0.011),
                        (px + nx * 0.004, py + ny * 0.004, zc - 0.024), M["metal_dull"], dio, rot=rot)
    for fl in range(1, floors):   # floor bands
        z = z0 + fl * floor_h
        box(f"{prefix}_band_{fl}", (w + 0.004, d + 0.004, 0.003), (cx, cy, z), M["parapet"], dio)


def build_roof_details(dio, M, rnd):
    """Rooftop set dressing (1:60): junk, the survivor's camp, roof services and weeds.
    Keeps clear: door -> tower walk (y 0.06-0.11), Rin's spots (0,-0.03)/(0,0)/PIN_XY, the tower base."""
    Z = ROOF_Z + 0.002
    def rot_z():
        return (0, 0, rnd.uniform(0, math.tau))
    # ---------- 1. junk ----------
    # wooden pallet (slats + bearers), one leaning on the east parapet
    for k, (px, py, tilt) in enumerate([(0.140, -0.075, 0.0), (0.163, -0.030, 1.2)]):
        root = prop_root(f"pallet_{k}", (px, py, Z + (0.009 if tilt else 0)), 0.3 if not tilt else 1.57, dio)
        root.rotation_euler = (0, tilt, root.rotation_euler.z)
        parts = [box(f"pallet_{k}_slat_{i}", (0.020, 0.0028, 0.0006), (0, -0.009 + i * 0.0045, 0.0021), M["wood"], dio) for i in range(5)]
        parts += [box(f"pallet_{k}_bearer_{i}", (0.0022, 0.020, 0.0015), (-0.008 + i * 0.008, 0, 0.0008), M["wood"], dio) for i in range(3)]
        parented(parts, root)
    # tipped-over plastic chair
    ch = prop_root("chair_tipped", (0.085, -0.075, Z + 0.004), 0.7, dio)
    ch.rotation_euler = (math.radians(80), 0, 0.7)
    parented([box("chair_seat", (0.008, 0.008, 0.0008), (0, 0, 0), M["plastic_white"], dio),
              box("chair_back", (0.008, 0.0008, 0.008), (0, 0.004, 0.004), M["plastic_white"], dio)] +
             [cyl(f"chair_leg_{i}", 0.0004, 0.007, (sx * 0.0035, sy * 0.0035, -0.0035), M["plastic_white"], dio, verts=6)
              for i, (sx, sy) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)])], ch)
    # stacked tyres + one lying alone
    for k, (tx_, ty_, tz) in enumerate([(0.150, -0.105, 0.0), (0.150, -0.105, 0.0035), (0.128, -0.112, 0.0)]):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.0055, minor_radius=0.0018, major_segments=24, minor_segments=8,
                                         location=(tx_, ty_, Z + 0.0018 + tz))
        t = bpy.context.active_object
        t.name = f"tyre_{k}"
        t.data.materials.append(M["rubber"])
        link(t, dio)
    # rusty oil drums (one on its side)
    cyl("drum_0", 0.0048, 0.014, (0.160, 0.035, Z + 0.007), M["rust"], dio, verts=20)
    cyl("drum_1", 0.0048, 0.014, (0.150, 0.050, Z + 0.0048), M["rust"], dio, verts=20, rot=(math.pi / 2, 0, 0.6))
    # cardboard boxes and black trash bags along the south parapet
    for k, (bx, by) in enumerate([(-0.05, -0.112), (-0.038, -0.108), (-0.044, -0.110), (0.03, -0.113)]):
        sz = rnd.uniform(0.006, 0.010)
        box(f"cardboard_{k}", (sz, sz * 0.8, sz * 0.7), (bx, by, Z + sz * 0.35 + (0.006 if k == 2 else 0)), M["cardboard"], dio, rot=rot_z())
    for k, (bx, by) in enumerate([(-0.02, -0.112), (-0.010, -0.115), (0.045, -0.110), (-0.065, -0.114)]):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0045, segments=12, ring_count=8, location=(bx, by, Z + 0.003))
        b = bpy.context.active_object
        b.name = f"trash_bag_{k}"
        b.scale = (1.0, 0.85, 0.75)
        b.data.materials.append(M["trash_bag"])
        link(b, dio)
    # newspapers and broken bricks scattered (kept off the action spots)
    def free(x, y):
        return not (-0.03 < x < 0.06 and -0.05 < y < 0.03) and not (-0.15 < x < 0.13 and 0.06 < y < 0.12)
    n = 0
    while n < 26:
        x, y = rnd.uniform(-0.165, 0.165), rnd.uniform(-0.115, 0.21)
        if not free(x, y):
            continue
        if n < 14:
            box(f"newspaper_{n}", (0.006, 0.0045, 0.0002), (x, y, Z + 0.0002), M["paper"], dio, rot=(rnd.uniform(-0.1, 0.1), 0, rnd.uniform(0, 3)))
        else:
            box(f"brick_{n}", (0.0036, 0.0018, 0.0012), (x, y, Z + 0.0006), M["brick"], dio, rot=rot_z())
        n += 1
    # ---------- 2. the survivor's camp (east side: the west side is the S01 door close-up's sightline) ----------
    cx, cy = 0.115, -0.055
    tent = prop_root("tarp_tent", (cx, cy, Z), 0.1, dio)
    parented([box("tarp_left", (0.028, 0.0006, 0.020), (0, -0.0065, 0.0075), M["tarp"], dio, rot=(math.radians(-38), 0, 0)),
              box("tarp_right", (0.028, 0.0006, 0.020), (0, 0.0065, 0.0075), M["tarp"], dio, rot=(math.radians(38), 0, 0)),
              cyl("tarp_ridge", 0.0004, 0.030, (0, 0, 0.0158), M["rust"], dio, verts=6, rot=(0, math.pi / 2, 0)),
              cyl("tarp_pole_a", 0.0004, 0.016, (-0.0145, 0, 0.008), M["rust"], dio, verts=6),
              cyl("tarp_pole_b", 0.0004, 0.016, (0.0145, 0, 0.008), M["rust"], dio, verts=6)], tent)
    bag = box("sleeping_bag", (0.020, 0.008, 0.0025), (cx + 0.002, cy, Z + 0.0013), M["sleeping_bag"], dio, rot=(0, 0, 0.1))
    cyl("sleeping_bag_roll", 0.0022, 0.008, (cx + 0.013, cy, Z + 0.0022), M["sleeping_bag"], dio, verts=12, rot=(math.pi / 2, 0, 0.1))
    # burnt-out fire barrel with a few embers + faint warm glow
    fb = (0.085, -0.032)
    cyl("fire_barrel", 0.0050, 0.012, (fb[0], fb[1], Z + 0.006), M["rust"], dio, verts=20)
    cyl("fire_barrel_embers", 0.0044, 0.0008, (fb[0], fb[1], Z + 0.0115), M["ember"], dio, verts=16)
    L = bpy.data.lights.new("L_fire_barrel", "POINT")
    L.energy, L.color, L.shadow_soft_size = 0.02, (1.0, 0.45, 0.12), 0.003
    lo = bpy.data.objects.new(L.name, L)
    lo.location = (fb[0], fb[1], Z + 0.016)
    dio.objects.link(lo)
    cyl("water_bucket", 0.0030, 0.0055, (0.072, -0.046, Z + 0.00275), M["metal_dull"], dio, verts=16)
    box("crate_seat", (0.007, 0.007, 0.006), (0.100, -0.022, Z + 0.003), M["wood"], dio, rot=(0, 0, 0.4))
    # festoon of warm bulbs strung over the camp between two scavenged poles
    for k, (px, py) in enumerate([(0.078, -0.088), (0.152, -0.026)]):
        cyl(f"festoon_pole_{k}", 0.0005, 0.028, (px, py, Z + 0.014), M["rust"], dio, verts=6)
    string_lights("camp_festoon", (0.078, -0.088, Z + 0.027), (0.152, -0.026, Z + 0.027), 0.007, 8, M, dio)
    # clothesline on the west side (inside the S02 frame) with a few hanging clothes
    for k, y in enumerate((-0.040, 0.050)):
        cyl(f"line_pole_{k}", 0.0005, 0.026, (-0.135, y, Z + 0.013), M["rust"], dio, verts=6)
    cyl("clothesline", 0.00015, 0.090, (-0.135, 0.005, Z + 0.025), M["black"], dio, verts=4, rot=(math.pi / 2, 0, 0))
    for k, (y, m_) in enumerate([(-0.028, "cloth_a"), (-0.010, "cloth_b"), (0.014, "cloth_a"), (0.036, "tarp")]):
        box(f"cloth_{k}", (0.0006, rnd.uniform(0.008, 0.012), rnd.uniform(0.008, 0.013)), (-0.135, y, Z + 0.019), M[m_], dio,
            rot=(rnd.uniform(-0.15, 0.15), 0, 0))
    # ---------- 3. roof services ----------
    for k, (y0, y1, x) in enumerate([(0.212, 0.212, None)]):
        pass
    # pipe runs along the north and east parapets, with elbows and wall brackets
    cyl("pipe_north", 0.0016, 0.300, (0.0, 0.214, Z + 0.004), M["rust"], dio, verts=12, rot=(0, math.pi / 2, 0))
    cyl("pipe_east", 0.0016, 0.20, (0.166, 0.110, Z + 0.004), M["rust"], dio, verts=12, rot=(math.pi / 2, 0, 0))
    for k in range(7):
        box(f"pipe_bracket_n{k}", (0.0012, 0.004, 0.006), (-0.13 + k * 0.043, 0.215, Z + 0.003), M["metal_dull"], dio)
    cyl("pipe_riser", 0.0016, 0.03, (-0.15, 0.214, Z + 0.015), M["rust"], dio, verts=12)
    # satellite dish on the shed roof and an antenna mast in the NE corner
    dish = prop_root("satellite_dish", (SHED_XY[0] + 0.025, SHED_XY[1] + 0.02, ROOF_Z + 0.054), -0.5, dio)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.009, segments=24, ring_count=12, location=(0, 0, 0))
    d = bpy.context.active_object
    d.name = "dish_bowl"
    d.scale = (1, 0.35, 1)
    d.data.materials.append(M["plastic_white"])
    link(d, dio)
    d.location = (0, 0, 0.012)
    d.rotation_euler = (math.radians(-30), 0, 0)
    parented([d, cyl("dish_post", 0.0006, 0.010, (0, 0.002, 0.005), M["metal_dull"], dio, verts=6),
              cyl("dish_arm", 0.0003, 0.010, (0, -0.005, 0.012), M["metal_dull"], dio, verts=6, rot=(math.radians(60), 0, 0))], dish)
    cyl("antenna_mast", 0.0006, 0.07, (0.160, 0.205, Z + 0.035), M["metal_dull"], dio, verts=6)
    for k in range(4):
        cyl(f"antenna_bar_{k}", 0.0003, 0.016 - k * 0.003, (0.160, 0.205, Z + 0.045 + k * 0.007), M["metal_dull"], dio,
            verts=4, rot=(0, math.pi / 2, 0.4))
    for k, (ox, oy) in enumerate([(0.012, -0.004), (-0.004, -0.012)]):   # guy wires
        cyl(f"antenna_guy_{k}", 0.00012, 0.06, (0.160 + ox / 2, 0.205 + oy / 2, Z + 0.028), M["black"], dio, verts=3,
            rot=(math.atan2(-oy, 0.055), math.atan2(ox, 0.055), 0))
    # electrical box on the shed's east wall with a blinking red LED
    ex = SHED_XY[0] + 0.0405
    box("electric_box", (0.003, 0.012, 0.016), (ex, SHED_XY[1] + 0.01, ROOF_Z + 0.022), M["metal_dull"], dio)
    led = box("electric_box_led", (0.001, 0.0018, 0.0018), (ex + 0.0018, SHED_XY[1] + 0.006, ROOF_Z + 0.027), M["red_led"], dio)
    cyl("electric_conduit", 0.0007, 0.012, (ex + 0.0005, SHED_XY[1] + 0.012, ROOF_Z + 0.008), M["metal_dull"], dio, verts=6)
    em = node_of_type(M["red_led"].node_tree, "BSDF_PRINCIPLED").inputs["Emission Strength"]
    for k in range(0, 60 * FPS, FPS):           # 1 s blink
        em.default_value = 10.0
        em.keyframe_insert("default_value", frame=k + 1)
        em.default_value = 0.0
        em.keyframe_insert("default_value", frame=k + 1 + FPS // 3)
    set_interp(M["red_led"].node_tree, "CONSTANT")
    # roof exhaust fan (mushroom vent)
    cyl("exhaust_fan_base", 0.0055, 0.006, (-0.03, 0.195, Z + 0.003), M["metal_dull"], dio, verts=20)
    bpy.ops.mesh.primitive_cone_add(radius1=0.0085, radius2=0.002, depth=0.005, vertices=20, location=(-0.03, 0.195, Z + 0.0085))
    hood = bpy.context.active_object
    hood.name = "exhaust_fan_hood"
    hood.data.materials.append(M["metal_dull"])
    link(hood, dio)
    # ---------- 4. weeds, vines, leaves ----------
    def tuft(name, x, y, hgt):
        for k in range(rnd.randint(3, 6)):
            bpy.ops.mesh.primitive_cone_add(radius1=0.0005, radius2=0.0, depth=hgt * rnd.uniform(0.6, 1.0), vertices=4,
                                            location=(x + rnd.uniform(-0.0015, 0.0015), y + rnd.uniform(-0.0015, 0.0015), Z + hgt * 0.4),
                                            rotation=(rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 0))
            g = bpy.context.active_object
            g.name = f"{name}_{k}"
            g.data.materials.append(M["grass"])
            link(g, dio)
    k = 0
    for side in ("N", "S", "E", "W"):            # along the parapet bases
        for _ in range(7):
            t = rnd.uniform(-0.165, 0.165)
            x, y = {"N": (t, 0.217), "S": (t, -0.118), "E": (0.168, t * 0.95 + 0.05), "W": (-0.168, t * 0.95 + 0.05)}[side]
            tuft(f"weed_{k:02d}", x, y, rnd.uniform(0.004, 0.008))
            k += 1
    for _ in range(10):                          # in floor cracks
        x, y = rnd.uniform(-0.16, 0.16), rnd.uniform(-0.11, 0.20)
        if free(x, y):
            tuft(f"weed_{k:02d}", x, y, rnd.uniform(0.003, 0.005))
            k += 1
    for k, (x, y, side) in enumerate([(-0.172, 0.15, "W"), (-0.172, -0.06, "W"), (0.172, 0.17, "E"),
                                      (-0.10, 0.222, "N"), (0.05, 0.222, "N"), (0.12, -0.127, "S")]):
        for j in range(5):                      # zig-zag ivy strands down/up the parapet
            dz = j * 0.0035
            off = (0.0012 if j % 2 else -0.0012)
            pos = (x, y + off, Z + 0.002 + dz) if side in "WE" else (x + off, y, Z + 0.002 + dz)
            box(f"ivy_{k}_{j}", (0.0012, 0.0045, 0.0045) if side in "WE" else (0.0045, 0.0012, 0.0045), pos, M["grass"], dio,
                rot=(0, 0, rnd.uniform(0, 3)))
    for k in range(40):
        x, y = rnd.uniform(-0.165, 0.165), rnd.uniform(-0.115, 0.21)
        box(f"leaf_{k:02d}", (0.0018, 0.0011, 0.0001), (x, y, Z + 0.0001), M["leaf"], dio, rot=(0, 0, rnd.uniform(0, 3)))


# --------------------------------------------------------------------------
# Light fixtures with real shapes + city detail (1:60 miniature)
# --------------------------------------------------------------------------
def sphere(name, r, loc, material, collection, segs=12, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=max(6, segs // 2), location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return link(o, collection)


def cone(name, r1, r2, depth, loc, material, collection, verts=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    return link(o, collection)


def tube(name, pts, radius, material, collection, cyclic=False, res=6):
    """Bevelled poly/bezier curve through world-space points: neon tubes, cables, railings."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth, cu.bevel_resolution = radius, 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1.0)
    sp.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, cu)
    o.data.materials.append(material)
    collection.objects.link(o)
    return o


def sag(a, b, drop, n=10):
    """Points of a hanging cable from a to b sagging by `drop` in the middle."""
    return [tuple(a[i] + (b[i] - a[i]) * t for i in range(2)) + (a[2] + (b[2] - a[2]) * t - drop * 4 * t * (1 - t),)
            for t in (k / n for k in range(n + 1))]


def point_light(name, loc, energy, color, collection, radius=0.003):
    L = bpy.data.lights.new(name, "POINT")
    L.energy, L.color, L.shadow_soft_size = energy, color, radius
    lo = bpy.data.objects.new(name, L)
    lo.location = loc
    collection.objects.link(lo)
    return lo


def wall_lamp(name, loc, normal, M, coll, glow="green_glow", light=(0.08, (0.35, 1.0, 0.45))):
    """Caged bulkhead lamp: back plate, glowing half-dome glass, two cage bars, conduit up the wall."""
    nx, ny = normal
    rz = math.atan2(nx, -ny)      # local -Y faces out along the normal
    root = prop_root(name, loc, rz, coll)
    parts = [box(f"{name}_plate", (0.0075, 0.0008, 0.0055), (0, 0, 0), M["metal_dull"], coll),
             sphere(f"{name}_dome", 0.0026, (0, -0.0004, 0), M[glow], coll, segs=14, scale=(1.15, 0.75, 0.85)),
             box(f"{name}_bar_a", (0.0004, 0.0024, 0.0050), (-0.0012, -0.0012, 0), M["black"], coll),
             box(f"{name}_bar_b", (0.0004, 0.0024, 0.0050), (0.0012, -0.0012, 0), M["black"], coll),
             box(f"{name}_bar_c", (0.0062, 0.0024, 0.0004), (0, -0.0012, 0), M["black"], coll),
             cyl(f"{name}_conduit", 0.00035, 0.014, (0.0028, 0.0003, 0.0095), M["metal_dull"], coll, verts=6)]
    parented(parts, root)
    if light:
        point_light(f"L_{name}", (loc[0] + nx * 0.008, loc[1] + ny * 0.008, loc[2] - 0.002), light[0], light[1], coll)
    return root


def street_lamp(name, x, y, M, coll, state="on", lean=0.0, facing=0.0):
    """Cobra-head street light: base, tapered pole, curved arm, flat housing, glowing lens underneath.
    state: on / off (broken) / flicker."""
    root = prop_root(name, (x, y, BED_Z), facing, coll)
    root.rotation_euler = (lean, 0, facing)
    H = 0.068
    lens_mat = M["street_lamp"] if state == "on" else (M["lamp_off"] if state == "off" else M["street_lamp_flicker"])
    parts = [cyl(f"{name}_base", 0.0016, 0.003, (0, 0, 0.0015), M["metal_dull"], coll, verts=10),
             cone(f"{name}_pole", 0.0010, 0.0006, H, (0, 0, H / 2), M["metal_dull"], coll, verts=8)]
    arm = [(0, 0, H - 0.004), (0.002, 0, H + 0.0015), (0.006, 0, H + 0.003), (0.011, 0, H + 0.0028)]
    parts.append(tube(f"{name}_arm", arm, 0.00045, M["metal_dull"], coll))
    parts.append(sphere(f"{name}_head", 0.0032, (0.0135, 0, H + 0.0024), M["metal_dull"], coll, segs=12, scale=(1.5, 0.75, 0.42)))
    parts.append(sphere(f"{name}_lens", 0.0026, (0.0138, 0, H + 0.0016), lens_mat, coll, segs=12, scale=(1.4, 0.7, 0.25)))
    parted = parented(parts, root)
    if state != "off":
        import mathutils
        mw = mathutils.Matrix.LocRotScale(root.location, root.rotation_euler.to_quaternion(), None)
        p = mw @ mathutils.Vector((0.0138, 0, H - 0.002))
        lo = point_light(f"L_{name}", tuple(p), 0.12, (0.35, 1.0, 0.45), coll, 0.004)
        if state == "flicker":
            L = lo.data
            r = random.Random(sum(map(ord, name)))
            fr = 1
            while fr < f(60):
                for e, d in ((0.12, r.randint(30, 90)), (0.01, r.randint(2, 5)), (0.12, r.randint(2, 4)), (0.0, r.randint(3, 8))):
                    L.energy = e
                    L.keyframe_insert("energy", frame=fr)
                    fr += d
            for fc in fcurves_of(L):
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"
    return root


def traffic_light(name, x, y, rz, M, coll):
    """Dead traffic signal on an L-arm: housing with three hooded lenses, only the amber one blinking."""
    root = prop_root(name, (x, y, BED_Z), rz, coll)
    parts = [cyl(f"{name}_pole", 0.0009, 0.060, (0, 0, 0.030), M["metal_dull"], coll, verts=8),
             cyl(f"{name}_arm", 0.0006, 0.030, (0.015, 0, 0.058), M["metal_dull"], coll, verts=8, rot=(0, math.pi / 2, 0)),
             box(f"{name}_housing", (0.0042, 0.0034, 0.0115), (0.026, 0, 0.051), M["black"], coll)]
    for k, (mname, z) in enumerate((("lamp_off", 0.0548), ("amber_blink", 0.0510), ("lamp_off", 0.0472))):
        parts.append(cyl(f"{name}_lens_{k}", 0.0012, 0.0005, (0.026, -0.0019, z), M[mname], coll, verts=12, rot=(math.pi / 2, 0, 0)))
        parts.append(cyl(f"{name}_hood_{k}", 0.0014, 0.0016, (0.026, -0.0026, z + 0.0003), M["black"], coll, verts=12, rot=(math.pi / 2, 0, 0)))
    parented(parts, root)
    return root


def flames(name, loc, size, M, coll, rnd):
    """Small fire: ember bed + a cluster of glowing flame cones + a warm point light."""
    x, y, z = loc
    cyl(f"{name}_embers", size * 0.5, size * 0.08, (x, y, z + size * 0.04), M["ember"], coll, verts=12)
    for k in range(5):
        h = size * rnd.uniform(0.6, 1.3)
        cone(f"{name}_flame_{k}", size * rnd.uniform(0.12, 0.22), 0.0, h,
             (x + rnd.uniform(-0.3, 0.3) * size, y + rnd.uniform(-0.3, 0.3) * size, z + h / 2 + size * 0.05),
             M["fire"], coll, verts=6, rot=(rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), 0))
    point_light(f"L_{name}", (x, y, z + size * 1.5), 0.4, (1.0, 0.45, 0.12), coll, 0.01)


def string_lights(name, a, b, drop, n, M, coll):
    """Festoon of warm bulbs on a sagging wire."""
    pts = sag(a, b, drop, 16)
    tube(f"{name}_wire", pts, 0.00012, M["cable"], coll)
    for k in range(n):
        t = (k + 0.5) / n
        p = sag(a, b, drop, 1000)[int(t * 1000)]
        cyl(f"{name}_cap_{k}", 0.00035, 0.0008, (p[0], p[1], p[2] - 0.0005), M["black"], coll, verts=6)
        sphere(f"{name}_bulb_{k}", 0.00065, (p[0], p[1], p[2] - 0.0013), M["bulb_warm"], coll, segs=8, scale=(1, 1, 1.25))
    mid = sag(a, b, drop, 2)[1]
    point_light(f"L_{name}", (mid[0], mid[1], mid[2] - 0.004), 0.05, (1.0, 0.75, 0.45), coll, 0.02)


def neon_sign(name, loc, normal, w, h, shape, color_mat, M, coll):
    """Wall-mounted neon: dark backing board on stand-offs + glowing tube shapes."""
    nx, ny = normal
    rz = math.atan2(nx, -ny)
    root = prop_root(name, loc, rz, coll)
    parts = [box(f"{name}_board", (w, 0.0008, h), (0, -0.0010, 0), M["black"], coll)]
    for sx in (-1, 1):
        for sz in (-1, 1):
            parts.append(cyl(f"{name}_standoff_{sx}{sz}", 0.0003, 0.0012, (sx * w * 0.42, -0.0004, sz * h * 0.42), M["metal_dull"], coll, verts=6, rot=(math.pi / 2, 0, 0)))
    y = -0.0018
    if shape == "arrow":
        pts = [(-w * 0.4, y, -h * 0.1), (w * 0.1, y, -h * 0.1), (w * 0.1, y, -h * 0.3), (w * 0.4, y, 0), (w * 0.1, y, h * 0.3), (w * 0.1, y, h * 0.1), (-w * 0.4, y, h * 0.1)]
        cyc = True
    elif shape == "ring":
        pts = [(math.cos(a) * w * 0.38, y, math.sin(a) * h * 0.38) for a in (k / 20 * math.tau for k in range(20))]
        cyc = True
    else:   # zig-zag "open" squiggle
        pts = [(-w * 0.42 + k * w * 0.12, y, (h * 0.25 if k % 2 else -h * 0.25)) for k in range(8)]
        cyc = False
    t = tube(f"{name}_tube", pts, 0.00045, color_mat, coll, cyclic=cyc)
    parts.append(t)
    parented(parts, root)
    return root


def vertical_signboard(name, loc, rz, w, h, M, coll):
    """Shop sign sticking out from a building corner: metal frame, glowing double-sided panel, neon edge."""
    root = prop_root(name, loc, rz, coll)
    parts = [box(f"{name}_frame", (w + 0.0016, 0.0030, h + 0.0016), (0, 0, 0), M["metal_dull"], coll),
             box(f"{name}_panel", (w, 0.0034, h), (0, 0, 0), M["sign_panel"], coll),
             box(f"{name}_bracket_t", (0.008, 0.0008, 0.0008), (-w / 2 - 0.004, 0, h * 0.4), M["metal_dull"], coll),
             box(f"{name}_bracket_b", (0.008, 0.0008, 0.0008), (-w / 2 - 0.004, 0, -h * 0.4), M["metal_dull"], coll)]
    for s in (-1, 1):
        edge = [(-w / 2, s * 0.0021, -h / 2), (w / 2, s * 0.0021, -h / 2), (w / 2, s * 0.0021, h / 2), (-w / 2, s * 0.0021, h / 2)]
        parts.append(tube(f"{name}_neon_{s}", edge, 0.0004, M["neon_cyan"], coll, cyclic=True))
    for k in range(4):   # dark divider bars: reads as stacked characters without real text
        parts.append(box(f"{name}_div_{k}", (w * 0.7, 0.0036, 0.0006), (0, 0, -h / 2 + h * (k + 1) / 5), M["black"], coll))
    parented(parts, root)
    return root


def billboard(name, loc, rz, w, h, M, coll):
    """Rooftop billboard: steel legs + catwalk, blank weathered panel, two gooseneck lamps lighting it."""
    root = prop_root(name, loc, rz, coll)
    parts = []
    for sx in (-1, 1):
        parts.append(box(f"{name}_leg_{sx}", (0.0012, 0.0012, 0.020), (sx * w * 0.38, 0.002, 0.010), M["rust"], coll))
        parts.append(box(f"{name}_brace_{sx}", (0.0008, 0.0008, 0.020), (sx * w * 0.38, 0.006, 0.010), M["rust"], coll, rot=(0.5, 0, 0)))
    parts.append(box(f"{name}_panel", (w, 0.0012, h), (0, 0, 0.020 + h / 2), M["billboard"], coll))
    parts.append(box(f"{name}_catwalk", (w, 0.004, 0.0006), (0, -0.0028, 0.0195), M["metal_dull"], coll))
    for k, sx in enumerate((-0.25, 0.25)):
        neck = [(sx * w, -0.0028, 0.0195), (sx * w, -0.006, 0.0215), (sx * w, -0.008, 0.024)]
        parts.append(tube(f"{name}_neck_{k}", neck, 0.0003, M["metal_dull"], coll))
        parts.append(cone(f"{name}_shade_{k}", 0.0016, 0.0005, 0.0018, (sx * w, -0.0082, 0.0248), M["metal_dull"], coll, verts=12, rot=(-2.3, 0, 0)))
        parts.append(cyl(f"{name}_bulb_{k}", 0.0012, 0.0003, (sx * w, -0.0076, 0.0242), M["bulb_warm"], coll, verts=12, rot=(-2.3, 0, 0)))
    parented(parts, root)
    import mathutils
    mw = mathutils.Matrix.LocRotScale(root.location, root.rotation_euler.to_quaternion(), None)
    for k, sx in enumerate((-0.25, 0.25)):
        point_light(f"L_{name}_{k}", tuple(mw @ mathutils.Vector((sx * w, -0.010, 0.026))), 0.05, (1.0, 0.8, 0.55), coll, 0.004)
    return root


def water_tank_small(name, loc, M, coll):
    x, y, z = loc
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"{name}_leg_{sx}{sy}", (0.0006, 0.0006, 0.007), (x + sx * 0.0035, y + sy * 0.0035, z + 0.0035), M["rust"], coll)
    cyl(f"{name}_drum", 0.0055, 0.009, (x, y, z + 0.0115), M["tank_metal"], coll, verts=16)
    cone(f"{name}_lid", 0.0058, 0.0008, 0.003, (x, y, z + 0.0175), M["tank_metal"], coll, verts=16)


def fire_escape(prefix, cx, face_x, y0, y1, z0, floors, floor_h, M, coll):
    """Zig-zag steel fire escape on an east/west face: landings, railings, stairs between floors."""
    s = 1 if face_x > cx else -1
    x = face_x + s * 0.004
    for fl in range(1, floors):
        z = z0 + fl * floor_h
        box(f"{prefix}_landing_{fl}", (0.008, y1 - y0, 0.0006), (x, (y0 + y1) / 2, z), M["grating"], coll)
        tube(f"{prefix}_rail_{fl}", [(face_x, y0, z + 0.006), (x + s * 0.004, y0, z + 0.006), (x + s * 0.004, y1, z + 0.006), (face_x, y1, z + 0.006)], 0.00025, M["rust"], coll)
        for k in range(6):
            yy = y0 + (y1 - y0) * k / 5
            box(f"{prefix}_post_{fl}_{k}", (0.0004, 0.0004, 0.006), (x + s * 0.004, yy, z + 0.003), M["rust"], coll)
        # stair flight down to the floor below (alternating direction)
        ya, yb = (y0 + 0.004, y1 - 0.004) if fl % 2 else (y1 - 0.004, y0 + 0.004)
        zb = z - floor_h if fl > 1 else z - floor_h * 0.6
        ang = math.atan2(z - zb, abs(yb - ya))
        L = math.hypot(z - zb, yb - ya)
        box(f"{prefix}_stair_{fl}", (0.0045, L, 0.0006), (x, (ya + yb) / 2, (z + zb) / 2), M["grating"], coll,
            rot=(ang if yb > ya else -ang, 0, 0))
        tube(f"{prefix}_stair_rail_{fl}", [(x + s * 0.0024, ya, z + 0.005), (x + s * 0.0024, yb, zb + 0.005)], 0.0002, M["rust"], coll)


def in_block(buildings, x, y, pad=0.003):
    return any(abs(x - bx) < bw / 2 + pad and abs(y - by) < bd / 2 + pad for bx, by, bw, bd, _ in buildings)


def street_spot(buildings, x, y):
    """Nudge a street-furniture spot toward the hero block until it is out of every ruined building."""
    for _ in range(20):
        if not in_block(buildings, x, y, 0.006):
            return x, y
        nx, ny = x * 0.94, 0.05 + (y - 0.05) * 0.94
        if abs(nx) < 0.188 and -0.138 < ny < 0.238:   # would walk into the hero building
            break
        x, y = nx, ny
    return x, y


def build_city_details(dio, M, buildings):
    """Second detail pass for the miniature city: ledges, lit windows, roof clutter, signs, cables, cars."""
    rnd = random.Random(SEED + 21)
    lit = 0
    for i, (x, y, w, d, h) in enumerate(buildings):
        # floor ledges every ~3 m (5 cm at 1:60), broken off at random
        for fl in range(1, int(h / 0.05) + 1):
            z = BED_Z + fl * 0.05 - 0.002
            if z < BED_Z + h - 0.006 and rnd.random() < 0.85:
                box(f"city_{i:02d}_ledge_{fl}", (w + 0.003, d + 0.003, 0.0018), (x, y, z), M["concrete_dark"], dio)
        # a few windows still lit on the faces that look at the hero block
        fx = -1 if x > 0 else 1
        fy = -1 if y > 0 else 1
        for k in range(rnd.randint(0, 3)):
            zc = BED_Z + rnd.uniform(0.02, max(0.025, h - 0.02))
            if rnd.random() < 0.5:
                pos, rot, sz = (x + fx * (w / 2 + 0.0004), y + rnd.uniform(-d, d) * 0.35, zc), (0, 0, math.pi / 2), (0.009, 0.0006, 0.007)
            else:
                pos, rot, sz = (x + rnd.uniform(-w, w) * 0.35, y + fy * (d / 2 + 0.0004), zc), (0, 0, 0), (0.009, 0.0006, 0.007)
            box(f"city_{i:02d}_litwin_{k}", sz, pos, M["window_lit" if rnd.random() < 0.7 else "window_warm"], dio, rot=rot)
            lit += 1
        # roof clutter
        r = rnd.random()
        top = BED_Z + h
        if r < 0.25:
            water_tank_small(f"city_{i:02d}_tank", (x + rnd.uniform(-w, w) * 0.2, y + rnd.uniform(-d, d) * 0.2, top), M, dio)
        elif r < 0.45:
            ah = rnd.uniform(0.012, 0.03)
            cyl(f"city_{i:02d}_antenna", 0.0004, ah, (x, y, top + ah / 2), M["metal_dull"], dio, verts=6)
            for k in range(3):
                box(f"city_{i:02d}_antenna_bar_{k}", (0.006 - k * 0.0015, 0.0004, 0.0004), (x, y, top + ah * (0.5 + k * 0.18)), M["metal_dull"], dio)
            sphere(f"city_{i:02d}_antenna_led", 0.0007, (x, y, top + ah + 0.0006), M["red_led"], dio, segs=8)
        elif r < 0.6:
            box(f"city_{i:02d}_roof_ac", (0.010, 0.008, 0.006), (x + rnd.uniform(-w, w) * 0.25, y, top + 0.003), M["metal_dull"], dio)
    # neon on the street-facing walls of the nearest blocks
    near = sorted(buildings, key=lambda b: math.hypot(b[0], b[1] - 0.05))[:6]
    shapes = [("arrow", "neon_pink"), ("ring", "neon_cyan"), ("zig", "neon_pink"), ("ring", "neon_purple"), ("arrow", "neon_cyan"), ("zig", "neon_cyan")]
    for k, ((x, y, w, d, h), (shape, cm)) in enumerate(zip(near, shapes)):
        dx, dy = -x, 0.05 - y          # face the side of the building that looks at the hero block
        if abs(dx) / (w / 2) > abs(dy) / (d / 2):
            nrm = (1 if dx > 0 else -1, 0)
            pos = (x + nrm[0] * (w / 2 + 0.0002), y, BED_Z + min(h - 0.01, 0.035 + k * 0.006))
        else:
            nrm = (0, 1 if dy > 0 else -1)
            pos = (x, y + nrm[1] * (d / 2 + 0.0002), BED_Z + min(h - 0.01, 0.035 + k * 0.006))
        if in_block([b for b in buildings if b[:2] != (x, y)], pos[0] + nrm[0] * 0.004, pos[1] + nrm[1] * 0.004, 0.0):
            continue                   # that face is buried against a neighbour
        neon_sign(f"neon_sign_{k}", pos, nrm, 0.016, 0.010, shape, M[cm], M, dio)
    # rooftop billboard on the tallest block behind the hero building
    back = [b for b in buildings if b[1] > 0.25] or buildings
    bx, by, bw, bd, bh = max(back, key=lambda b: b[4])
    billboard("billboard_back", (bx, by, BED_Z + bh), 0.0, min(bw * 0.9, 0.05), 0.022, M, dio)
    # sagging power / phone cables between the hero roof and neighbours
    for k, (x, y, w, d, h) in enumerate(near[:4]):
        a = (0.17 if x > 0 else -0.17, max(-0.12, min(0.22, y)), ROOF_Z + 0.012)
        b = (x - math.copysign(w / 2, x), y, BED_Z + h - 0.004)
        for j in range(2):
            tube(f"cable_{k}_{j}", sag((a[0], a[1] + j * 0.004, a[2]), (b[0], b[1] + j * 0.004, b[2]), 0.012 + j * 0.004), 0.00018, M["cable"], dio)
    return lit


def build_diorama(C, M):
    dio = coll("DIORAMA", C["root"])
    rnd = random.Random(SEED)
    box("bed", (0.90, 0.90, 0.01), (0, 0, BED_Z), M["street"], dio)
    # ---- hero building: 3 storeys (3 m each at 1:60), shed back-left, tower back-right
    HB, HC = 0.36, (0, 0.05)
    box("hero_building", (HB, HB, ROOF_Z - BED_Z), (HC[0], HC[1], (ROOF_Z + BED_Z) / 2), M["facade"], dio)
    build_facade(dio, M, rnd, HC[0], HC[1], HB, HB, BED_Z + 0.005, 3, 0.05, "hb")
    # ground-floor roller shutter + green emergency lamps (reference: green light spilling on the wet street)
    sy = HC[1] - HB / 2 - 0.0008
    box("hb_shutter", (0.09, 0.0015, 0.036), (0, sy, BED_Z + 0.023), M["shutter"], dio)
    box("hb_shutter_box", (0.096, 0.006, 0.006), (0, sy - 0.002, BED_Z + 0.044), M["metal_dull"], dio)
    for x in (-0.06, 0.06):
        wall_lamp(f"hb_lamp_{x:+.2f}", (x, sy - 0.0004, BED_Z + 0.047), (0, -1), M, dio)
    # torn awning over the shutter, drainpipes on the corners, a fire escape up the east face
    box("hb_awning", (0.104, 0.014, 0.0008), (0, sy - 0.007, BED_Z + 0.052), M["awning"], dio, rot=(-0.35, 0, 0))
    box("hb_awning_flap", (0.03, 0.0008, 0.010), (0.035, sy - 0.0135, BED_Z + 0.046), M["awning"], dio, rot=(0.25, 0.15, 0))
    for k, (dx, dy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        px, py = HC[0] + dx * (HB / 2 + 0.0012), HC[1] + dy * (HB / 2 + 0.0012)
        cyl(f"hb_drainpipe_{k}", 0.0011, ROOF_Z - BED_Z, (px, py, (ROOF_Z + BED_Z) / 2), M["rust"], dio, verts=8)
        for j in range(5):
            box(f"hb_drain_clamp_{k}_{j}", (0.0032, 0.0032, 0.0008), (px, py, BED_Z + 0.02 + j * 0.03), M["metal_dull"], dio)
    fire_escape("hb_fe", HC[0], HC[0] + HB / 2, HC[1] - 0.07, HC[1] + 0.03, BED_Z + 0.005, 3, 0.05, M, dio)
    vertical_signboard("hb_signboard", (HC[0] - HB / 2 - 0.007, HC[1] - HB / 2 + 0.012, BED_Z + 0.085), math.pi, 0.010, 0.040, M, dio)
    box("roof_tiles", (0.35, 0.35, 0.002), (0, 0.05, ROOF_Z + 0.001), M["roof_wet"], dio)
    # thick parapet (1.1 m) with a pipe railing on top
    PH, PT = 0.018, 0.008
    for name, size, loc in [
        ("parapet_N", (HB + 0.004, PT, PH), (0, 0.05 + HB / 2 - PT / 2 + 0.002, ROOF_Z + PH / 2)),
        ("parapet_S", (HB + 0.004, PT, PH), (0, 0.05 - HB / 2 + PT / 2 - 0.002, ROOF_Z + PH / 2)),
        ("parapet_E", (PT, HB + 0.004, PH), (HB / 2 - PT / 2 + 0.002, 0.05, ROOF_Z + PH / 2)),
        ("parapet_W", (PT, HB + 0.004, PH), (-HB / 2 + PT / 2 - 0.002, 0.05, ROOF_Z + PH / 2)),
    ]:
        box(name, size, loc, M["parapet"], dio)
        box(name + "_cap", (size[0] + 0.002, size[1] + 0.002, 0.002), (loc[0], loc[1], ROOF_Z + PH + 0.001), M["parapet"], dio)
    for i in range(13):
        t = -0.17 + i * 0.0283
        for loc in ((t, 0.227, ROOF_Z + PH + 0.007), (t, -0.127, ROOF_Z + PH + 0.007)):
            cyl(f"rail_post_{i}_{loc[1]:.2f}", 0.0006, 0.012, loc, M["rust"], dio, verts=6)
    for y in (0.227, -0.127):
        for z in (ROOF_Z + PH + 0.012, ROOF_Z + PH + 0.006):
            cyl(f"rail_bar_{y:.2f}_{z:.3f}", 0.0005, 0.345, (0, y, z), M["rust"], dio, verts=6, rot=(0, math.pi / 2, 0))
    # roof clutter: drains, vent pipes, puddle-catching debris
    for i, (x, y) in enumerate([(-0.16, -0.11), (0.16, -0.11), (0.16, 0.21)]):
        cyl(f"roof_drain_{i}", 0.003, 0.002, (x, y, ROOF_Z + 0.003), M["metal_dull"], dio, verts=10)
    for i, (x, y) in enumerate([(0.03, 0.20), (-0.02, 0.19)]):
        cyl(f"vent_pipe_{i}", 0.0025, 0.014, (x, y, ROOF_Z + 0.007), M["rust"], dio, verts=10)
    # stair shed + door (door hinge animated: bang in S01, burst open S02)
    box("stair_shed", (0.08, 0.06, 0.05), (SHED_XY[0], SHED_XY[1] + 0.005, ROOF_Z + 0.025), M["parapet"], dio)
    box("stair_shed_roof", (0.088, 0.068, 0.004), (SHED_XY[0], SHED_XY[1] + 0.005, ROOF_Z + 0.052), M["parapet"], dio)
    for x in (-0.0135, 0.0135):
        box(f"door_frame_{x:+.3f}", (0.003, 0.003, 0.041), (DOOR_XY[0] + x, DOOR_XY[1] - 0.0005, ROOF_Z + 0.0205), M["metal_dull"], dio)
    box("door_frame_top", (0.030, 0.003, 0.003), (DOOR_XY[0], DOOR_XY[1] - 0.0005, ROOF_Z + 0.0405), M["metal_dull"], dio)
    hinge = empty("door_hinge", (DOOR_XY[0] - 0.012, DOOR_XY[1] - 0.001, ROOF_Z), dio)
    door = box("shed_door", (0.024, 0.002, 0.038), (0.012, 0, 0.019), M["door_green"], dio)
    door.parent = hinge
    wall_lamp("door_lamp", (DOOR_XY[0], DOOR_XY[1] - 0.0004, ROOF_Z + 0.0455), (0, -1), M, dio, light=None)   # lit by L_door_green
    for i, (x, y) in enumerate([(0.05, 0.17), (0.05, -0.10), (0.15, 0.0)]):
        box(f"ac_unit_{i}", (0.022, 0.016, 0.016), (x, y, ROOF_Z + 0.008), M["metal_dull"], dio)
        box(f"ac_fan_{i}", (0.012, 0.012, 0.001), (x, y, ROOF_Z + 0.0165), M["black"], dio)
    build_roof_details(dio, M, rnd)
    # ---- ruined city (forced perspective: lower toward the back); fog-blue, a few green lights, rare fires
    buildings = []
    for i in range(60):
        x = rnd.uniform(-0.43, 0.43)
        y = rnd.uniform(-0.43, 0.43)
        if abs(x) < 0.23 and -0.17 < y < 0.27:
            continue
        if x > 0.20 and y < -0.20:   # keep prize chute corner clear
            continue
        h = rnd.uniform(0.04, 0.17) * (0.7 if y > 0.2 else 1.0)
        w = rnd.uniform(0.04, 0.09)
        dd = w * rnd.uniform(0.8, 1.3)
        box(f"city_{i:02d}", (w, dd, h), (x, y, BED_Z + h / 2), M["concrete_dark"], dio)
        buildings.append((x, y, w, dd, h))
        # collapsed top: a few tilted slabs and stubs of columns
        if rnd.random() < 0.55:
            for k in range(rnd.randint(1, 3)):
                sw = w * rnd.uniform(0.3, 0.6)
                box(f"city_{i:02d}_rubble_{k}", (sw, sw * 0.8, 0.004),
                    (x + rnd.uniform(-w, w) * 0.3, y + rnd.uniform(-dd, dd) * 0.3, BED_Z + h + 0.004),
                    M["concrete_dark"], dio, rot=(rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(0, 3)))
            for k in range(rnd.randint(1, 3)):
                ch = rnd.uniform(0.008, 0.025)
                box(f"city_{i:02d}_col_{k}", (0.003, 0.003, ch),
                    (x + rnd.uniform(-w, w) * 0.4, y + rnd.uniform(-dd, dd) * 0.4, BED_Z + h + ch / 2), M["concrete_dark"], dio)
        if rnd.random() < 0.08:  # rare distant fire
            flames(f"fire_{i:02d}", (x, y, BED_Z + h), w * 0.25, M, dio, rnd)
    # green street lamps along the streets around the hero block
    for i, (x, y) in enumerate([(-0.24, -0.16), (0.24, -0.16), (-0.24, 0.12), (0.24, 0.12), (0.0, -0.2),
                                (-0.12, -0.2), (0.12, -0.2), (0.3, -0.32), (-0.05, 0.3)]):
        state = {2: "off", 5: "flicker", 8: "off"}.get(i, "on")
        x, y = street_spot(buildings, x, y)
        facing = math.atan2(0.05 - y, -x)          # arm reaches toward the hero block / street centre
        street_lamp(f"street_lamp_{i}", x, y, M, dio, state, lean=0.18 if i == 8 else 0.0, facing=facing)
    traffic_light("traffic_light_0", *street_spot(buildings, -0.20, -0.215), 0.0, M, dio)
    print("city detail: lit windows", build_city_details(dio, M, buildings))
    # a wrecked car on the street in front (reference 6/7/11)
    box("car_wreck_body", (0.024, 0.011, 0.006), (0.07, -0.2, BED_Z + 0.008), M["metal_dull"], dio, rot=(0, 0, 0.25))
    box("car_wreck_cab", (0.013, 0.010, 0.005), (0.068, -0.2, BED_Z + 0.0135), M["window_broken"], dio, rot=(0, 0, 0.25))
    # low fog inside the cabinet (reference: blue haze swallowing the ruins)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, BED_Z + 0.20))
    fog = bpy.context.active_object
    fog.name = "fog_volume"
    fog.scale = (0.89, 0.89, 0.40)
    fm = bpy.data.materials.new("fog")
    fm.use_nodes = True
    nt = fm.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.30, 0.42, 0.65, 1)
    vol.inputs["Density"].default_value = 0.35
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    fog.data.materials.append(fm)
    fog.display_type = "WIRE"
    link(fog, dio)
    return dio, hinge


def build_tower(C, M):
    tw = coll("WATER_TOWER", C["root"])
    root = empty("TOWER_ROOT", (TOWER_XY[0], TOWER_XY[1], ROOF_Z), tw, "ARROWS", 0.03)
    parts = []
    leg_h = 0.04
    R_TANK, H_TANK = 0.035, 0.07
    legs = []
    for i, a in enumerate((45, 135, 225, 315)):
        r = 0.026
        x, y = math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r
        legs.append((x, y))
        parts.append(cyl(f"tower_leg_{i}", 0.0018, leg_h, (x, y, leg_h / 2), M["rust"], tw, verts=8))
        parts.append(box(f"tower_footplate_{i}", (0.007, 0.007, 0.0012), (x, y, 0.0006), M["rust"], tw))
    # X-bracing between neighbouring legs
    for i in range(4):
        (x0, y0), (x1, y1) = legs[i], legs[(i + 1) % 4]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        span = math.hypot(x1 - x0, y1 - y0)
        yaw = math.atan2(y1 - y0, x1 - x0)
        diag = math.atan2(leg_h * 0.7, span)
        for sgn in (1, -1):
            parts.append(box(f"tower_brace_{i}_{sgn:+d}", (math.hypot(span, leg_h * 0.7), 0.0008, 0.0008),
                             (mx, my, leg_h * 0.5), M["rust"], tw, rot=(0, sgn * diag, yaw)))
        parts.append(box(f"tower_ring_{i}", (span, 0.0009, 0.0009), (mx, my, leg_h * 0.15), M["rust"], tw, rot=(0, 0, yaw)))
    parts.append(cyl("tower_tank", R_TANK, H_TANK, (0, 0, leg_h + H_TANK / 2), M["tank_metal"], tw, verts=40))
    # riveted hoop bands + rivet heads
    for k, zb in enumerate((0.004, H_TANK * 0.36, H_TANK * 0.68, H_TANK - 0.004)):
        bpy.ops.mesh.primitive_torus_add(major_radius=R_TANK + 0.0004, minor_radius=0.0009, major_segments=48,
                                         minor_segments=6, location=(0, 0, leg_h + zb))
        band = bpy.context.active_object
        band.name = f"tower_band_{k}"
        band.data.materials.append(M["rust"] if k in (0, 3) else M["tank_metal"])
        parts.append(link(band, tw))
        for n in range(18):
            a = n / 18 * math.tau
            parts.append(cyl(f"tower_rivet_{k}_{n:02d}", 0.0006, 0.0008,
                             (math.cos(a) * (R_TANK + 0.0011), math.sin(a) * (R_TANK + 0.0011), leg_h + zb),
                             M["rust"], tw, verts=6, rot=(math.pi / 2, 0, a + math.pi / 2)))
    # domed lid with hatch and two bent pipe handles
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R_TANK + 0.001, segments=40, ring_count=12,
                                         location=(0, 0, leg_h + H_TANK))
    roof = bpy.context.active_object
    roof.name = "tower_roof"
    roof.scale = (1, 1, 0.32)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(roof.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-5], context="VERTS")
    bm.to_mesh(roof.data)
    bm.free()
    roof.data.materials.append(M["tank_metal"])
    parts.append(link(roof, tw))
    top = leg_h + H_TANK + (R_TANK + 0.001) * 0.32
    parts.append(cyl("tower_hatch", 0.008, 0.004, (0, 0, top + 0.001), M["tank_metal"], tw, verts=24))
    parts.append(cyl("tower_hatch_knob", 0.002, 0.003, (0, 0, top + 0.004), M["rust"], tw, verts=10))
    for k, a in enumerate((60, 120)):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.004, minor_radius=0.0006, major_segments=16, minor_segments=6,
                                         location=(math.cos(math.radians(a)) * 0.022, math.sin(math.radians(a)) * 0.022, top - 0.003),
                                         rotation=(math.pi / 2, 0, math.radians(a)))
        h = bpy.context.active_object
        h.name = f"tower_lid_handle_{k}"
        h.data.materials.append(M["rust"])
        parts.append(link(h, tw))
    # ladder on the front (-Y) side so Rin reads to the S07/S08 camera
    for side in (-1, 1):
        parts.append(box(f"ladder_rail_{side}", (0.0012, 0.0012, 0.11), (side * 0.006, -0.037, 0.055), M["rust"], tw))
        parts.append(box(f"ladder_standoff_{side}", (0.0008, 0.004, 0.0008), (side * 0.006, -0.0355, 0.09), M["rust"], tw))
        bpy.ops.mesh.primitive_torus_add(major_radius=0.004, minor_radius=0.0006, major_segments=16, minor_segments=6,
                                         location=(side * 0.006, -0.034, 0.111), rotation=(0, math.pi / 2, 0))
        g = bpy.context.active_object
        g.name = f"ladder_grab_{side}"
        g.data.materials.append(M["rust"])
        parts.append(link(g, tw))
    for i in range(14):
        parts.append(box(f"ladder_rung_{i:02d}", (0.012, 0.001, 0.001), (0, -0.037, 0.004 + i * 0.0075), M["rust"], tw))
    for p in parts:
        p.parent = root
    return root


def swept_bar(name, pts, w0, t0, w1, t1, material, collection):
    """Rectangular bar swept along a polyline in the local YZ plane (x = width), tapering w0/t0 -> w1/t1."""
    import bmesh
    from mathutils import Vector
    bm = bmesh.new()
    rings = []
    n = len(pts)
    for k, (y, z) in enumerate(pts):
        a_ = Vector((0, *pts[max(k - 1, 0)]))
        b_ = Vector((0, *pts[min(k + 1, n - 1)]))
        tan = (b_ - a_).normalized()
        nrm = Vector((0, -tan.z, tan.y))
        f = k / (n - 1)
        w, t = w0 + (w1 - w0) * f, t0 + (t1 - t0) * f
        c = Vector((0, y, z))
        rings.append([bm.verts.new(c + Vector((sx * w / 2, 0, 0)) + nrm * (sy * t / 2))
                      for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for r0, r1 in zip(rings, rings[1:]):
        for q in range(4):
            bm.faces.new((r0[q], r0[(q + 1) % 4], r1[(q + 1) % 4], r1[q]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    o = bpy.data.objects.new(name, me)
    collection.objects.link(o)
    return o


def build_claw(C, M):
    cl = coll("CLAW", C["root"])
    root = empty("CLAW_ROOT", (TOWER_XY[0], TOWER_XY[1], 1.80), cl, "ARROWS", 0.04)
    ch = M["chrome"]
    # stacked chrome body (reference: collar, two drums, a ribbed neck, black cap)
    stack = [("claw_cap", 0.007, 0.012, 0.085, M["black"]), ("claw_neck", 0.009, 0.020, 0.069, ch),
             ("claw_collar", 0.012, 0.005, 0.0565, M["metal_dull"]), ("claw_drum", 0.014, 0.026, 0.041, ch),
             ("claw_hub", 0.020, 0.010, 0.023, ch), ("claw_base_ring", 0.022, 0.004, 0.016, M["metal_dull"])]
    for name, r, h, z, mat_ in stack:
        o = cyl(name, r, h, (0, 0, z), mat_, cl, verts=32)
        o.parent = root
    for k in range(4):
        o = cyl(f"claw_neck_rib_{k}", 0.0098, 0.0012, (0, 0, 0.062 + k * 0.0045), M["metal_dull"], cl, verts=32)
        o.parent = root
    # black corrugated cable up to the gantry
    cable = cyl("claw_cable", 0.005, 0.8, (0, 0, 0.49), M["cable"], cl, verts=16)
    cable.parent = root
    glow = cyl("claw_neon_ring", 0.0205, 0.0015, (0, 0, 0.0285), M["neon_purple"], cl, verts=32)
    glow.parent = root
    pivots = []
    for i, a in enumerate((90, 210, 330)):
        pv = empty(f"prong_pivot_{i}", (0, 0, 0.018), cl, "SINGLE_ARROW", 0.02)
        pv.parent = root
        pv.rotation_euler = (0, 0, math.radians(a))
        # pivot local +Y points outward; arm goes out, knuckle, then a curved finger hooking inward
        # one continuous curved finger (pivot local: +Y outward, -Z down), tapering toward an inward hook
        pts = [(0.004, 0.000), (0.026, -0.012), (0.040, -0.036), (0.043, -0.062),
               (0.038, -0.084), (0.028, -0.098), (0.016, -0.104)]
        o = swept_bar(f"prong_{i}", pts, 0.0085, 0.0055, 0.0045, 0.0028, ch, cl)
        o.parent = pv
        for k, (py, pz) in enumerate((pts[1], pts[3])):
            o = cyl(f"prong_{i}_knuckle_{k}", 0.0036, 0.0105, (0, py, pz), M["metal_dull"], cl, verts=16, rot=(0, math.pi / 2, 0))
            o.parent = pv
        o = cyl(f"prong_{i}_bolt", 0.0034, 0.0105, (0, 0.004, 0.0), M["metal_dull"], cl, verts=16, rot=(0, math.pi / 2, 0))
        o.parent = pv
        pivots.append(pv)
    # purple rim light that rides with the claw (reference glow)
    L = bpy.data.lights.new("L_claw_rim", "POINT")
    L.energy, L.color, L.shadow_soft_size = 0.15, (0.6, 0.3, 1.0), 0.01
    lo = bpy.data.objects.new(L.name, L)
    lo.location = (0.05, 0.04, 0.03)
    lo.parent = root
    cl.objects.link(lo)
    # gantry rails under the cabinet roof
    for x in (-0.40, 0.40):
        box(f"gantry_rail_{x:+.1f}", (0.015, 0.88, 0.015), (x, 0, 1.855), ch, cl)
    box("gantry_bridge", (0.82, 0.03, 0.02), (0, TOWER_XY[1], 1.845), ch, cl)
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
        o = sprite(name, fn, h, (PIN_XY[0], PIN_XY[1] + dy, ROOF_Z + 0.002), ch, face, col)   # sit ON the 2 mm roof tiles
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
        ("nova_hand_coin",     "nova_hand_coin.png",     ["S17a_coin"],        (0.26, -0.56, 0.78), 0.16),
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


def prop_root(name, loc, rotz, collection):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.rotation_euler = (0, 0, rotz)
    collection.objects.link(e)
    return e


def parented(objs, parent):
    for o in objs:
        o.parent = parent
    return objs


def neighbour_claw_machine(ar, M, name, loc, rotz, body, accent, rnd):
    """Generic plush claw machine for the background (pink/white stars or yellow)."""
    root = prop_root(name, loc, rotz, ar)
    parts = [
        box(f"{name}_body", (0.9, 0.85, 0.9), (0, 0, 0.45), M[body], ar),
        box(f"{name}_belt", (0.92, 0.87, 0.04), (0, 0, 0.92), M[accent], ar),
        box(f"{name}_glass", (0.86, 0.81, 0.85), (0, 0, 1.36), M["glass"], ar),
        box(f"{name}_top", (0.92, 0.87, 0.10), (0, 0, 1.84), M[body], ar),
        box(f"{name}_sign", (0.80, 0.02, 0.07), (0, -0.44, 1.84), M[accent], ar),
        box(f"{name}_plush_card", (0.82, 0.004, 0.42), (0, 0.38, 1.15), M["plush_card"], ar),
        box(f"{name}_ctrl", (0.30, 0.12, 0.08), (-0.15, -0.48, 0.82), M["cab_trim"], ar),
        box(f"{name}_coin", (0.08, 0.01, 0.12), (0.2, -0.43, 0.78), M["coin_mech"], ar),
        box(f"{name}_door", (0.18, 0.01, 0.14), (0.2, -0.43, 0.22), M["black"], ar),
    ]
    for sx in (-1, 1):
        parts.append(box(f"{name}_neon_{sx}", (0.012, 0.012, 1.8), (sx * 0.455, -0.43, 0.95), M[accent], ar))
    for k in range(14):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rnd.uniform(0.05, 0.08), segments=12, ring_count=8,
                                             location=(rnd.uniform(-0.33, 0.33), rnd.uniform(-0.25, 0.3), 0.98 + rnd.uniform(0, 0.12)))
        b = bpy.context.active_object
        b.name = f"{name}_plush_{k}"
        b.data.materials.append(M["plush_card"])
        parts.append(link(b, ar))
    parented(parts, root)
    return root


def arcade_cabinet(ar, M, name, loc, rotz):
    root = prop_root(name, loc, rotz, ar)
    parts = [
        box(f"{name}_body", (0.6, 0.7, 1.75), (0, 0, 0.875), M["black"], ar),
        box(f"{name}_screen", (0.48, 0.02, 0.40), (0, -0.33, 1.30), M["arcade_screen"], ar, rot=(math.radians(-15), 0, 0)),
        box(f"{name}_marquee", (0.58, 0.04, 0.16), (0, -0.33, 1.68), M["neon_pink"], ar),
        box(f"{name}_deck", (0.6, 0.25, 0.06), (0, -0.45, 0.98), M["cab_trim"], ar, rot=(math.radians(-10), 0, 0)),
    ]
    parented(parts, root)
    return root


# --------------------------------------------------------------------------
# Arcade detail pass: real fixtures, more machines, props (outside the claw machine, real-world metres)
# --------------------------------------------------------------------------
def linear_light(name, loc, length, M, ar, rz=0.0, color=(0.85, 0.92, 1.0), energy=40):
    """Suspended LED batten: aluminium housing on two drop wires, glowing diffuser underneath."""
    root = prop_root(name, loc, rz, ar)
    parts = [box(f"{name}_housing", (length, 0.09, 0.05), (0, 0, 0), M["cab_trim"], ar),
             box(f"{name}_diffuser", (length - 0.03, 0.07, 0.012), (0, 0, -0.03), M["led_cool"], ar)]
    for s in (-1, 1):
        parts.append(cyl(f"{name}_wire_{s}", 0.002, 3.4 - loc[2], (s * length * 0.4, 0, (3.4 - loc[2]) / 2 + 0.025), M["black"], ar, verts=4))
    parented(parts, root)
    L = bpy.data.lights.new(f"L_{name}", "AREA")
    L.shape, L.size, L.size_y = "RECTANGLE", length, 0.07
    L.energy, L.color = energy, color
    lo = bpy.data.objects.new(L.name, L)
    lo.location = (loc[0], loc[1], loc[2] - 0.04)
    lo.rotation_euler = (0, 0, rz)
    ar.objects.link(lo)
    return root


def track_light(name, loc, aim, M, ar, energy=25, color=(1.0, 0.85, 0.65)):
    """Ceiling track spot: stem, yoke and cylindrical can aimed at `aim`, with a spot light inside."""
    from mathutils import Vector
    d = (Vector(aim) - Vector(loc)).normalized()
    rot = d.to_track_quat("-Z", "Y").to_euler()
    cyl(f"{name}_stem", 0.008, 0.08, (loc[0], loc[1], loc[2] + 0.06), M["black"], ar, verts=8)
    can = cyl(f"{name}_can", 0.035, 0.11, loc, M["black"], ar, verts=16, rot=tuple(rot))
    lens_pos = Vector(loc) + d * 0.056
    cyl(f"{name}_lens", 0.028, 0.004, tuple(lens_pos), M["led_warm"], ar, verts=16, rot=tuple(rot))
    L = bpy.data.lights.new(f"L_{name}", "SPOT")
    L.energy, L.color, L.spot_size, L.spot_blend = energy, color, math.radians(35), 0.4
    lo = bpy.data.objects.new(L.name, L)
    lo.location = tuple(lens_pos + d * 0.01)
    lo.rotation_euler = rot
    ar.objects.link(lo)
    return can


def exit_sign(name, loc, rz, M, ar):
    """Green emergency-exit lightbox: frame, glowing face, white pictogram bars (no text)."""
    root = prop_root(name, loc, rz, ar)
    parts = [box(f"{name}_case", (0.36, 0.06, 0.16), (0, 0, 0), M["plastic_white"], ar),
             box(f"{name}_face", (0.33, 0.062, 0.13), (0, 0, 0), M["exit_green"], ar),
             box(f"{name}_arrow", (0.10, 0.064, 0.022), (0.08, 0, 0), M["plastic_white"], ar),
             box(f"{name}_door", (0.05, 0.064, 0.09), (-0.10, 0, 0), M["plastic_white"], ar),
             box(f"{name}_runner", (0.02, 0.066, 0.06), (-0.03, 0, 0.0), M["exit_green"], ar, rot=(0, 0.4, 0)),
             cyl(f"{name}_rod", 0.004, 0.25, (0, 0, 0.205), M["metal_dull"], ar, verts=6)]
    parented(parts, root)


def dome_camera(name, loc, M, ar):
    cyl(f"{name}_base", 0.07, 0.02, (loc[0], loc[1], loc[2]), M["plastic_white"], ar, verts=20)
    sphere(f"{name}_dome", 0.055, (loc[0], loc[1], loc[2] - 0.02), M["glass_smoke"], ar, segs=16, scale=(1, 1, 0.8))
    sphere(f"{name}_led", 0.006, (loc[0] + 0.03, loc[1], loc[2] - 0.05), M["red_led"], ar, segs=6)


def gashapon(name, loc, rz, M, ar, rnd):
    """Capsule-toy vending machine: base box with crank and chute, clear globe full of coloured capsules."""
    root = prop_root(name, loc, rz, ar)
    parts = [box(f"{name}_base", (0.34, 0.32, 0.55), (0, 0, 0.275), M[rnd.choice(["machine_pink", "machine_yellow", "cab_body"])], ar),
             cyl(f"{name}_crank_plate", 0.07, 0.01, (0, -0.165, 0.38), M["chrome"], ar, verts=20, rot=(math.pi / 2, 0, 0)),
             box(f"{name}_crank", (0.10, 0.02, 0.025), (0, -0.18, 0.38), M["chrome"], ar),
             box(f"{name}_chute", (0.10, 0.03, 0.08), (0, -0.17, 0.16), M["black"], ar),
             box(f"{name}_card", (0.24, 0.005, 0.12), (0, -0.162, 0.48), M["gacha_card"], ar),
             sphere(f"{name}_globe", 0.17, (0, 0, 0.72), M["glass"], ar, segs=20),
             cyl(f"{name}_cap", 0.06, 0.04, (0, 0, 0.89), M["chrome"], ar, verts=16)]
    for k in range(26):
        a, r = rnd.uniform(0, math.tau), rnd.uniform(0, 0.12)
        z = 0.62 + rnd.uniform(0, 0.12) - r * 0.3
        parts.append(sphere(f"{name}_capsule_{k}", 0.026, (math.cos(a) * r, math.sin(a) * r, z),
                            M[rnd.choice(["capsule_red", "capsule_blue", "capsule_yellow", "capsule_green", "plastic_white"])], ar, segs=10))
    parented(parts, root)
    return root


def racing_cabinet(name, loc, rz, M, ar):
    """Sit-down driving game: bucket seat on rails, big tilted screen, wheel and pedals, lit header."""
    root = prop_root(name, loc, rz, ar)
    parts = [box(f"{name}_base", (0.75, 1.5, 0.12), (0, 0.2, 0.06), M["black"], ar),
             box(f"{name}_tower", (0.75, 0.55, 1.45), (0, -0.30, 0.79), M["cab_body"], ar),
             box(f"{name}_screen", (0.62, 0.03, 0.48), (0, -0.03, 1.12), M["racing_screen"], ar, rot=(math.radians(-12), 0, 0)),
             box(f"{name}_header", (0.75, 0.10, 0.22), (0, -0.05, 1.62), M["neon_cyan"], ar),
             box(f"{name}_dash", (0.70, 0.30, 0.10), (0, 0.10, 0.80), M["black"], ar, rot=(math.radians(-20), 0, 0)),
             box(f"{name}_seat", (0.48, 0.48, 0.10), (0, 0.80, 0.42), M["black"], ar),
             box(f"{name}_seat_back", (0.48, 0.10, 0.62), (0, 1.03, 0.72), M["black"], ar, rot=(math.radians(15), 0, 0)),
             box(f"{name}_seat_post", (0.12, 0.12, 0.30), (0, 0.80, 0.22), M["metal_dull"], ar),
             box(f"{name}_pedals", (0.30, 0.10, 0.05), (0, 0.32, 0.17), M["metal_dull"], ar, rot=(math.radians(30), 0, 0))]
    bpy.ops.mesh.primitive_torus_add(major_radius=0.14, minor_radius=0.018, location=(0, 0.22, 0.92), rotation=(math.radians(70), 0, 0))
    wheel = bpy.context.active_object
    wheel.name = f"{name}_wheel"
    wheel.data.materials.append(M["rubber"])
    link(wheel, ar)
    parts.append(wheel)
    for s in (-1, 1):
        parts.append(box(f"{name}_trim_{s}", (0.012, 0.56, 1.40), (s * 0.38, -0.30, 0.78), M["neon_pink"], ar))
    parented(parts, root)
    return root


def stool(name, loc, M, ar):
    cyl(f"{name}_seat", 0.17, 0.06, (loc[0], loc[1], 0.66), M["rubber"], ar, verts=20)
    cyl(f"{name}_post", 0.025, 0.62, (loc[0], loc[1], 0.32), M["chrome"], ar, verts=10)
    cyl(f"{name}_foot_ring", 0.16, 0.012, (loc[0], loc[1], 0.25), M["chrome"], ar, verts=20)
    cyl(f"{name}_base", 0.20, 0.02, (loc[0], loc[1], 0.01), M["chrome"], ar, verts=20)


def wet_floor_sign(name, loc, rz, M, ar):
    root = prop_root(name, loc, rz, ar)
    parts = [box(f"{name}_a", (0.30, 0.012, 0.62), (0, -0.09, 0.30), M["hazard_yellow"], ar, rot=(math.radians(-16), 0, 0)),
             box(f"{name}_b", (0.30, 0.012, 0.62), (0, 0.09, 0.30), M["hazard_yellow"], ar, rot=(math.radians(16), 0, 0)),
             box(f"{name}_icon", (0.12, 0.014, 0.12), (0, -0.098, 0.33), M["black"], ar, rot=(math.radians(-16), 0.785, 0))]
    parented(parts, root)


def build_arcade_details(ar, M):
    rnd = random.Random(SEED + 31)
    n0 = len(bpy.data.objects)
    # ---- ceiling: cable trays, sprinkler line, LED battens, track spots, exit sign, dome cameras, bunting
    for k, x in enumerate((-1.9, 1.0)):
        box(f"cable_tray_{k}", (0.30, 9.0, 0.06), (x, 1.5, 3.05), M["grating"], ar)
        for j in range(8):
            cyl(f"cable_tray_{k}_rod_{j}", 0.006, 0.33, (x, -2.5 + j * 1.15, 3.24), M["metal_dull"], ar, verts=4)
        for c in range(3):
            tube(f"cable_tray_{k}_run_{c}", [(x - 0.08 + c * 0.08, -3.0, 3.09), (x - 0.08 + c * 0.08, 6.0, 3.09)], 0.012, M["cable"], ar)
    tube("sprinkler_pipe", [(-2.4, -2.5, 3.28), (-2.4, 5.3, 3.28), (2.8, 5.3, 3.28)], 0.025, M["hazard_red"], ar)
    for j in range(7):
        cyl(f"sprinkler_head_{j}", 0.012, 0.05, (-2.4, -2.0 + j * 1.1, 3.24), M["chrome"], ar, verts=8)
    for k, (x, y, rz) in enumerate([(-1.6, -0.6, 0.0), (-1.6, 1.8, 0.0), (2.0, -0.4, math.pi / 2), (2.0, 2.0, math.pi / 2), (-0.6, 3.6, 0.0)]):
        linear_light(f"led_batten_{k}", (x, y, 2.95), 1.2, M, ar, rz=rz, energy=35)
    for k, (x, y, aim) in enumerate([(-0.5, -1.6, (0.0, -0.4, 1.2)), (0.6, -1.6, (0.1, -0.4, 1.0)),
                                     (2.1, 1.4, (2.6, 1.9, 1.0)), (2.1, 3.4, (2.6, 3.9, 1.0)), (-1.4, 1.0, (-1.45, 0.0, 1.3))]):
        track_light(f"track_spot_{k}", (x, y, 3.05), aim, M, ar, energy=30)
    box("track_rail_0", (1.3, 0.04, 0.03), (0.05, -1.6, 3.12), M["black"], ar)
    exit_sign("exit_sign", (-2.2, 2.6, 2.55), 0.0, M, ar)
    for k, loc in enumerate([(-2.0, -1.8, 3.37), (2.3, 4.8, 3.37)]):
        dome_camera(f"dome_cam_{k}", loc, M, ar)
    for k, (a, b) in enumerate([((-2.55, -1.0, 2.95), (2.5, -0.2, 2.95)), ((-2.55, 2.0, 2.9), (2.5, 3.2, 2.9))]):
        pts = sag(a, b, 0.35, 24)
        tube(f"bunting_{k}_line", pts, 0.004, M["black"], ar)
        for j in range(1, 24):
            p = pts[j]
            bpy.ops.mesh.primitive_cone_add(radius1=0.07, radius2=0.0, depth=0.16, vertices=3, location=(p[0], p[1], p[2] - 0.08),
                                            rotation=(math.pi, 0, rnd.uniform(-0.3, 0.3)))
            fl = bpy.context.active_object
            fl.name = f"bunting_{k}_flag_{j}"
            fl.scale = (1, 0.12, 1)
            fl.data.materials.append(M[("neon_pink", "capsule_yellow", "neon_cyan", "plastic_white")[j % 4]])
            link(fl, ar)
    # ---- walls: neon art, wall screens, prize shelves + counter
    tube("neon_wave_back", [(-1.8 + k * 0.15, 5.44, 2.15 + 0.12 * math.sin(k * 0.9)) for k in range(25)], 0.012, M["neon_cyan"], ar)
    tube("neon_star_left", [(-2.565, 1.9 + 0.35 * math.cos(a) * (1 if k % 2 == 0 else 0.45), 2.35 + 0.35 * math.sin(a) * (1 if k % 2 == 0 else 0.45))
                            for k, a in enumerate(math.pi / 2 + i * math.pi / 5 for i in range(10))], 0.012, M["neon_pink"], ar, cyclic=True)
    tube("neon_bolt_left", [(-2.565, -0.9, 2.6), (-2.565, -0.65, 2.25), (-2.565, -0.8, 2.25), (-2.565, -0.55, 1.85)], 0.012, M["neon_purple"], ar)
    for k, y in enumerate((0.0, 3.2)):
        box(f"wall_tv_{k}", (0.04, 0.85, 0.50), (-2.56, y, 2.15), M["black"], ar)
        box(f"wall_tv_{k}_screen", (0.045, 0.78, 0.44), (-2.56, y, 2.15), M["wall_tv"], ar)
        box(f"wall_tv_{k}_mount", (0.06, 0.12, 0.12), (-2.57, y, 2.15), M["metal_dull"], ar)
    for s in range(3):   # prize shelves behind the counter, packed with plush and boxed toys
        z = 1.05 + s * 0.42
        box(f"prize_shelf_{s}", (1.8, 0.35, 0.03), (2.0, 5.28, z), M["plastic_white"], ar)
        for j in range(9):
            if rnd.random() < 0.55:
                sphere(f"prize_plush_{s}_{j}", 0.10, (1.2 + j * 0.2, 5.28, z + 0.11), M[rnd.choice(["capsule_red", "capsule_blue", "capsule_yellow", "machine_pink", "plastic_white"])], ar, segs=10, scale=(1, 0.9, 1.05))
            else:
                box(f"prize_box_{s}_{j}", (0.16, 0.14, 0.24), (1.2 + j * 0.2, 5.28, z + 0.135), M[rnd.choice(["prize_box", "prize_box", "machine_yellow"])], ar)
    box("prize_counter", (2.0, 0.6, 1.0), (2.0, 4.75, 0.5), M["cab_body"], ar)
    box("prize_counter_top", (2.06, 0.66, 0.04), (2.0, 4.75, 1.02), M["cab_trim"], ar)
    box("prize_counter_glow", (1.96, 0.02, 0.03), (2.0, 4.44, 0.95), M["neon_cyan"], ar)
    box("prize_counter_glass", (1.9, 0.5, 0.35), (2.0, 4.75, 1.22), M["glass"], ar)
    box("token_machine", (0.45, 0.40, 1.55), (-1.33, 0.75, 0.775), M["cab_trim"], ar)
    box("token_machine_screen", (0.30, 0.02, 0.22), (-1.33, 0.54, 1.20), M["arcade_screen"], ar)
    box("token_machine_slot", (0.16, 0.03, 0.06), (-1.33, 0.54, 0.95), M["black"], ar)
    box("token_machine_tray", (0.22, 0.08, 0.05), (-1.33, 0.53, 0.55), M["chrome"], ar)
    # ---- floor: more machines, stools, a wet-floor sign, bins, a cable cover
    for k, (x, y) in enumerate([(-1.75, 1.75), (-1.35, 1.75), (-1.55, 2.15)]):
        gashapon(f"gashapon_{k}", (x, y, 0), 0.0 if k < 2 else math.pi, M, ar, rnd)
    for k, x in enumerate((-1.95, -1.15)):
        racing_cabinet(f"racing_cab_{k}", (x, 3.1, 0), 0.0, M, ar)
    arcade_cabinet(ar, M, "arcade_cab_extra_0", (1.35, 4.0, 0), 0)
    for k, (x, y) in enumerate([(0.0, 3.75), (0.7, 3.75), (1.4, 3.45)]):
        stool(f"stool_{k}", (x, y), M, ar)
    wet_floor_sign("wet_floor_sign", (-0.55, 1.55, 0), 0.6, M, ar)
    cyl("mop_bucket", 0.16, 0.30, (-0.35, 1.85, 0.15), M["hazard_yellow"], ar, verts=20)
    cyl("mop_handle", 0.012, 1.3, (-0.33, 1.9, 0.75), M["plastic_white"], ar, verts=6, rot=(0.15, -0.1, 0))
    for k, (x, y) in enumerate([(1.45, -0.05), (-2.3, 0.9)]):
        cyl(f"trash_bin_{k}", 0.17, 0.62, (x, y, 0.31), M["metal_dull"], ar, verts=20)
        cyl(f"trash_bin_{k}_lid", 0.18, 0.04, (x, y, 0.64), M["black"], ar, verts=20)
    box("cable_cover", (0.18, 3.0, 0.015), (-0.9, 2.2, 0.0075), M["hazard_yellow"], ar)
    tube("floor_power_cable", [(-0.9, 3.7, 0.02), (-1.1, 3.9, 0.02), (-1.6, 3.95, 0.02), (-1.9, 3.7, 0.02)], 0.012, M["cable"], ar)
    # LED floor-edge strips under the lane of machines on the right
    box("lane_floor_led", (0.03, 4.0, 0.012), (2.2, 2.4, 0.006), M["neon_cyan"], ar)
    return len(bpy.data.objects) - n0


def build_arcade_room(C, M):
    """Night arcade after the reference: polished wet-look tiles, concrete pillars with hazard guards,
    neighbour claw machines and a lane of cabinets receding to the right, pendant lamps and ducts above."""
    ar = coll("ARCADE_ROOM", C["root"])
    rnd = random.Random(SEED + 3)
    box("floor", (12, 12, 0.01), (0.5, 1.5, -0.005), M["floor"], ar)
    box("ceiling", (12, 12, 0.05), (0.5, 1.5, 3.4), M["ceiling"], ar)
    box("wall_back_far", (12, 0.05, 3.4), (0.5, 5.5, 1.7), M["wall"], ar)
    box("wall_left", (0.05, 12, 3.4), (-2.6, 1.5, 1.7), M["wall"], ar)
    box("wall_back_neon", (6.0, 0.03, 0.05), (0.8, 5.47, 2.6), M["neon_pink"], ar)
    # ceiling services: ducts, a cassette AC
    for k, x in enumerate((-1.2, 0.6, 2.2)):
        box(f"duct_{k}", (0.25, 9.0, 0.25), (x, 1.5, 3.2), M["metal_dull"], ar)
    box("ceiling_ac", (0.7, 0.7, 0.08), (1.6, 2.2, 3.33), M["cab_trim"], ar)
    # pendant lamps (warm pools on the floor)
    for k, (x, y) in enumerate([(-0.9, -1.2), (1.2, -0.8), (1.4, 1.2), (1.5, 3.0), (-0.2, 2.4), (0.6, 4.4)]):
        cyl(f"pendant_cord_{k}", 0.004, 0.5, (x, y, 3.15), M["black"], ar, verts=6)
        bpy.ops.mesh.primitive_cone_add(radius1=0.22, radius2=0.05, depth=0.14, vertices=24, location=(x, y, 2.85))
        sh = bpy.context.active_object
        sh.name = f"pendant_shade_{k}"
        sh.data.materials.append(M["lamp_shade"])
        link(sh, ar)
        cyl(f"pendant_bulb_{k}", 0.15, 0.01, (x, y, 2.78), M["led_warm"], ar, verts=24)
        L = bpy.data.lights.new(f"L_pendant_{k}", "SPOT")
        L.energy, L.color, L.spot_size, L.spot_blend = 60, (1.0, 0.78, 0.5), math.radians(80), 0.6
        lo = bpy.data.objects.new(L.name, L)
        lo.location = (x, y, 2.76)
        ar.objects.link(lo)
    # concrete pillars with yellow/black hazard corner guards and a poster
    for k, (x, y) in enumerate([(-0.85, 0.55), (0.95, 2.4)]):
        box(f"pillar_{k}", (0.5, 0.5, 3.4), (x, y, 1.7), M["pillar"], ar)
        box(f"pillar_guard_{k}", (0.12, 0.12, 0.9), (x + 0.22, y - 0.22, 0.45), M["hazard"], ar)
        box(f"pillar_poster_{k}", (0.36, 0.006, 0.52), (x, y - 0.253, 1.75), M["poster"], ar)
    # neighbours: pink/white star machine to the left, a lane of yellow + pink machines to the right
    neighbour_claw_machine(ar, M, "machine_left", (-1.45, 0.0, 0), 0, "machine_pink", "neon_pink", rnd)
    for k, y in enumerate((0.9, 1.9, 2.9, 3.9)):
        body = "machine_yellow" if k % 2 == 0 else "machine_pink"
        neighbour_claw_machine(ar, M, f"machine_lane_{k}", (2.6, y, 0), math.pi / 2, body, "neon_pink", rnd)
    for k, x in enumerate((0.0, 0.7)):
        arcade_cabinet(ar, M, f"arcade_cab_{k}", (x, 4.3, 0), 0)
    box("vending_machine", (0.9, 0.8, 1.9), (-1.0, 4.6, 0.95), M["machine_pink"], ar)
    box("vending_front", (0.7, 0.01, 1.3), (-1.0, 4.195, 1.15), M["arcade_screen"], ar)
    for name, col, loc, energy in [
        ("L_neon_pink", (1.0, 0.2, 0.7), (-0.9, -1.2, 1.8), 120),
        ("L_neon_cyan", (0.2, 0.8, 1.0), (1.0, -1.0, 1.6), 120),
    ]:
        L = bpy.data.lights.new(name, "AREA")
        L.energy, L.color, L.size = energy, col, 0.8
        L.specular_factor = 0.1    # fill only: keep the big pink/cyan softboxes out of the cabinet glass
        o = bpy.data.objects.new(name, L)
        o.location = loc
        o.rotation_euler = (math.radians(70), 0, math.atan2(-loc[0], 1.0))
        ar.objects.link(o)


# --------------------------------------------------------------------------
# Decals (V4 atlases, 4x4 cells, transparent PNG). Missing atlas -> those decals are skipped.
# --------------------------------------------------------------------------
DECAL_ATLAS = {
    "graffiti": ("decal_graffiti_atlas.png", 0.55),   # (file, brightness: keep to the night palette)
    "posters":  ("decal_posters_atlas.png", 0.45),
    "signs":    ("decal_signs_atlas.png", 0.60),
    "stains":   ("decal_stains_atlas.png", 1.00),
    "cracks":   ("decal_cracks_atlas.png", 1.00),
}
# signs atlas cells: 0 hazard triangle, 1 yellow stripe, 2 "03", 3 no-hand, 4 electric box, 5 cyan pipe arrow,
# 6 "07", 7 orange stripe, 8 fire, 9 green pipe arrow, 10 "12", 11 wrench, 12 "08", 13 wet floor,
# 14 red/white stripe, 15 chevron up


def decal_material(kind):
    name = "decal_" + kind
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    fn, value = DECAL_ATLAS[kind]
    path = first_texture(fn)
    if not path:
        return None
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = node_of_type(nt, "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.extension = "CLIP"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["UV"], tex.inputs["Vector"])
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Value"].default_value = value
    nt.links.new(tex.outputs["Color"], hsv.inputs["Color"])
    nt.links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.75
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"    # alpha-hashed: no sorting problems between stacked decals
    m.diffuse_color = (0.3, 0.3, 0.3, 0.6)
    return m


def decal(name, kind, cell, size, loc, normal, collection, spin=0.0, lift=0.0003):
    """A thin card showing one 4x4 atlas cell, lying flat on a surface (normal = the surface's outward
    direction). On walls the image's up = world up; on floors `spin` turns it."""
    from mathutils import Matrix, Vector
    m = decal_material(kind)
    if not m:
        return None
    w, h = size
    me = bpy.data.meshes.new("ME_" + name)
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    c, r, p = cell % 4, cell // 4, 0.004
    u0, u1, v0, v1 = c / 4 + p, (c + 1) / 4 - p, 1 - (r + 1) / 4 + p, 1 - r / 4 - p
    for i, co in enumerate(((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        uv.data[i].uv = co
    me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    n = Vector(normal).normalized()
    upv = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((0, 1, 0))
    x = upv.cross(n).normalized()
    y = n.cross(x)
    rot = Matrix((x, y, n)).transposed().to_4x4() @ Matrix.Rotation(spin, 4, "Z")
    o.matrix_world = Matrix.Translation(Vector(loc) + n * lift) @ rot
    o.visible_shadow = False
    collection.objects.link(o)
    return o


def build_decals(C):
    """Graffiti, posters, signs, stains and cracks after the reference boards. Diorama decals are cm-sized
    (1:60), arcade ones are real size. Placed between windows/doors so nothing is covered."""
    if not any(first_texture(fn) for fn, _ in DECAL_ATLAS.values()):
        return 0
    rnd = random.Random(SEED + 11)
    dd = coll("DECALS_DIORAMA", bpy.data.collections["DIORAMA"])
    da = coll("DECALS_ARCADE", bpy.data.collections["ARCADE_ROOM"])
    S, N, E, W, UP = (0, -1, 0), (0, 1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1)
    R = ROOF_Z
    placed = []

    def put(kind, cell, size, loc, normal, col, spin=0.0, lift=0.0003):
        o = decal(f"decal_{kind}_{len(placed):03d}", kind, cell, size, loc, normal, col, spin, lift)
        if o:
            placed.append(o)

    # hero building (36 cm block, centre (0, 0.05)): ground floor beside the shutter, upper floors between windows
    put("graffiti", 0, (0.026, 0.020), (-0.088, -0.13, BED_Z + 0.022), S, dd)
    put("graffiti", 6, (0.024, 0.018), (0.088, -0.13, BED_Z + 0.021), S, dd)
    put("posters", 2, (0.013, 0.018), (0.0, -0.13, 1.030), S, dd)
    put("posters", 9, (0.013, 0.018), (-0.090, -0.13, 1.030), S, dd)
    put("graffiti", 9, (0.022, 0.016), (0.090, -0.13, 1.080), S, dd)
    put("graffiti", 4, (0.024, 0.018), (-0.18, 0.05, 0.976), W, dd)
    put("posters", 13, (0.013, 0.018), (-0.18, -0.04, 1.030), W, dd)
    put("graffiti", 13, (0.022, 0.016), (0.18, 0.05, 0.976), E, dd)
    put("graffiti", 2, (0.020, 0.012), (0.18, 0.14, 1.080), E, dd)
    # parapet inner faces (the side the rooftop cameras see)
    put("graffiti", 1, (0.016, 0.011), (-0.02, 0.224, R + 0.009), S, dd)
    put("graffiti", 3, (0.012, 0.012), (0.165, 0.224, R + 0.009), S, dd)
    put("graffiti", 10, (0.016, 0.011), (0.174, -0.05, R + 0.009), W, dd)
    put("graffiti", 12, (0.014, 0.011), (0.174, 0.08, R + 0.009), W, dd)
    # stair shed: signs beside the door, a big tag on the east wall
    put("signs", 3, (0.009, 0.009), (-0.138, 0.105, R + 0.030), S, dd)
    put("signs", 2, (0.008, 0.008), (-0.083, 0.105, R + 0.032), S, dd)
    put("signs", 0, (0.008, 0.008), (-0.083, 0.105, R + 0.020), S, dd)
    put("graffiti", 8, (0.030, 0.022), (-0.07, 0.135, R + 0.022), E, dd)
    # rooftop floor: stains and cracks (keep clear of the stair shed)
    k = 0
    while k < 9:
        x, y = rnd.uniform(-0.15, 0.15), rnd.uniform(-0.11, 0.20)
        if x < -0.06 and y > 0.09:
            continue
        s = rnd.uniform(0.015, 0.035)
        put("stains", rnd.randrange(16), (s, s), (x, y, R + 0.0022 + k * 0.00002), UP, dd, rnd.uniform(0, math.tau), 0)
        k += 1
    for k in range(5):
        x, y = rnd.uniform(-0.15, 0.15), rnd.uniform(-0.11, 0.08)
        s = rnd.uniform(0.03, 0.05)
        put("cracks", rnd.randrange(16), (s, s), (x, y, R + 0.0023 + k * 0.00002), UP, dd, rnd.uniform(0, math.tau), 0)
    # street in front of the block
    for k in range(6):
        x, y = rnd.uniform(-0.28, 0.28), rnd.uniform(-0.30, -0.15)
        s = rnd.uniform(0.02, 0.04)
        kind = "stains" if k % 2 == 0 else "cracks"
        put(kind, rnd.randrange(16), (s, s), (x, y, BED_Z + 0.0052 + k * 0.00002), UP, dd, rnd.uniform(0, math.tau), 0)
    # ruins: posters and tags on the camera-facing (south) faces of the city blocks
    for ob in sorted((o for o in bpy.data.objects if o.name.startswith("city_") and o.name[5:].isdigit()), key=lambda o: o.name):
        if rnd.random() > 0.45:
            continue
        w, dpt, h = ob.dimensions
        if h < 0.04:
            continue
        s = min(w * 0.45, 0.03)
        kind = "posters" if rnd.random() < 0.5 else "graffiti"
        aspect = 1.35 if kind == "posters" else 0.75
        z = BED_Z + rnd.uniform(0.012, min(h - 0.015, 0.06))
        put(kind, rnd.randrange(16), (s, s * aspect), (ob.location.x + rnd.uniform(-w, w) * 0.2,
                                                        ob.location.y - dpt / 2, z), S, dd)
    # ---- arcade (real scale)
    k = 0
    while k < 10:
        x, y = rnd.uniform(-2.2, 2.2), rnd.uniform(-2.0, 4.0)
        if abs(x) < 0.65 and abs(y) < 0.65:      # under the hero cabinet
            continue
        if any(abs(x - px) < 0.4 and abs(y - py) < 0.4 for px, py in ((-0.85, 0.55), (0.95, 2.4))):
            continue
        s = rnd.uniform(0.25, 0.6)
        put("stains", rnd.randrange(16), (s, s), (x, y, 0.0008 + k * 0.00005), UP, da, rnd.uniform(0, math.tau), 0)
        k += 1
    for k, (px, py) in enumerate(((-0.85, 0.55), (0.95, 2.4))):
        put("cracks", rnd.randrange(16), (0.7, 0.7), (px + 0.45, py - 0.35, 0.0012 + k * 0.00005), UP, da, rnd.uniform(0, math.tau), 0)
    for k, y in enumerate((-1.2, 0.2, 1.6, 3.0)):
        put("posters", rnd.randrange(16), (0.45, 0.6), (-2.575, y, rnd.uniform(1.4, 1.8)), E, da, lift=0.002)
    for k, x in enumerate((-2.0, 0.35, 1.5, 2.2)):
        put("posters", rnd.randrange(16), (0.45, 0.6), (x, 5.475, 2.35), S, da, lift=0.002)
    # pillars: floor-number plates and a fire sign
    put("signs", 6, (0.22, 0.22), (-0.85, 0.55 - 0.25, 1.15), S, da, lift=0.002)
    put("signs", 10, (0.22, 0.22), (0.95, 2.4 - 0.25, 1.15), S, da, lift=0.002)
    put("signs", 8, (0.2, 0.2), (-0.85 + 0.25, 0.55, 1.45), E, da, lift=0.002)
    # the hero cabinet: stickers on the sides and front
    put("signs", 12, (0.12, 0.12), (0.5, -0.2, 0.60), E, da, lift=0.001)
    put("signs", 0, (0.12, 0.12), (-0.5, -0.25, 0.55), W, da, lift=0.001)
    put("signs", 3, (0.09, 0.09), (0.25, -0.5, 0.46), S, da, lift=0.001)
    print(f"decals: {len(placed)} placed")
    return len(placed)


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
        cd.dof.focus_object = bpy.data.objects.get(SHOT_FOCUS.get(sid, "")) or aim
        # at 1:60 scale f/1.4 blurs everything; f/2.8-4 still reads as tilt-shift miniature
        cd.dof.aperture_fstop = 8.0 if sid in ("S01_door_bang", "S03_lost_boot", "S12_impact", "S13a_pinned", "S13b_pinned_face", "S17b_reset_loop") else 2.8
        if sid == "S06_light_above":    # 3 cm from her: needs deep focus to keep face and the light above readable
            cd.dof.aperture_fstop = 22.0
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
        "cab_body":      mat("cab_body", (0.11, 0.15, 0.25), 0.42, 0.45),     # dark blue painted steel
        "cab_trim":      mat("cab_trim", (0.62, 0.64, 0.68), 0.28, 0.9),      # brushed steel frame
        "belt":          mat("belt", (0.65, 0.05, 0.55), 0.25, 0.3, emit=(0.85, 0.08, 0.7), strength=0.6),
        "led_warm":      mat("led_warm", (1.0, 0.85, 0.6), 0.3, 0, emit=(1.0, 0.82, 0.55), strength=15),
        "vent_grille":   mat("vent_grille", (0.04, 0.05, 0.07), 0.5, 0.6),
        "louver":        mat("louver", (0.06, 0.08, 0.13), 0.5, 0.4),
        "coin_mech":     mat("coin_mech", (0.55, 0.57, 0.6), 0.3, 0.9),
        "pillar":        mat("pillar", (0.28, 0.28, 0.29), 0.85),
        "hazard":        mat("hazard", (0.8, 0.65, 0.05), 0.6),
        "poster":        mat("poster", (0.5, 0.3, 0.6), 0.6, 0, emit=(0.5, 0.3, 0.6), strength=0.3),
        "arcade_screen": mat("arcade_screen", (0.2, 0.4, 0.9), 0.2, 0, emit=(0.3, 0.5, 1.0), strength=4),
        "plush_card":    mat("plush_card", (0.9, 0.6, 0.8), 0.7, 0, emit=(0.9, 0.6, 0.8), strength=0.6),
        "machine_pink":  mat("machine_pink", (0.95, 0.8, 0.9), 0.4, 0.1),
        "machine_yellow":mat("machine_yellow", (0.95, 0.7, 0.1), 0.4, 0.1),
        "ceiling":       mat("ceiling", (0.02, 0.02, 0.025), 0.8),
        "lamp_shade":    mat("lamp_shade", (0.05, 0.05, 0.05), 0.4, 0.8),
        "wood":          mat("wood", (0.22, 0.15, 0.09), 0.85),
        "plastic_white": mat("plastic_white", (0.55, 0.56, 0.55), 0.5),
        "rubber":        mat("rubber", (0.015, 0.015, 0.015), 0.75),
        "cardboard":     mat("cardboard", (0.30, 0.22, 0.13), 0.9),
        "trash_bag":     mat("trash_bag", (0.01, 0.01, 0.012), 0.2),
        "tarp":          mat("tarp", (0.05, 0.16, 0.35), 0.6),
        "sleeping_bag":  mat("sleeping_bag", (0.45, 0.16, 0.05), 0.7),
        "cloth_a":       mat("cloth_a", (0.35, 0.33, 0.30), 0.9),
        "cloth_b":       mat("cloth_b", (0.30, 0.05, 0.05), 0.9),
        "paper":         mat("paper", (0.45, 0.44, 0.40), 0.9),
        "brick":         mat("brick", (0.30, 0.10, 0.06), 0.9),
        "grass":         mat("grass", (0.08, 0.17, 0.05), 0.8),
        "leaf":          mat("leaf", (0.25, 0.13, 0.04), 0.8),
        "ember":         mat("ember", (0.3, 0.05, 0.0), 0.6, 0, emit=(1.0, 0.3, 0.05), strength=6),
        "red_led":       mat("red_led", (0.3, 0.0, 0.0), 0.4, 0, emit=(1.0, 0.02, 0.02), strength=10),
        "chrome":        mat("chrome", (0.85, 0.85, 0.9), 0.12, 1.0),
        "black":         mat("black", (0.01, 0.01, 0.01), 0.5),
        "glass":         mat("glass", (0.75, 0.85, 1.0), 0.02, 0.0, alpha=0.04),
        "acrylic":       mat("acrylic_base", (0.9, 0.95, 1.0), 0.05, 0.0, alpha=0.25),
        "marquee":       mat("marquee", (0.3, 0.05, 0.3), 0.4, 0, emit=(1.0, 0.25, 0.8), strength=6),
        "neon_pink":     mat("neon_pink", (1.0, 0.2, 0.7), 0.3, 0, emit=(1.0, 0.2, 0.7), strength=5),
        "neon_cyan":     mat("neon_cyan", (0.1, 0.85, 1.0), 0.3, 0, emit=(0.05, 0.8, 1.0), strength=5),
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
        "floor":         mat("floor", (0.07, 0.07, 0.08), 0.12, 0.1),   # wet-looking polished tiles
        "wall":          mat("wall", (0.03, 0.02, 0.05), 0.6),
        "facade":        mat("facade", (0.33, 0.34, 0.34), 0.85),
        "parapet":       mat("parapet", (0.30, 0.31, 0.30), 0.85),
        "window_broken": mat("window_broken", (0.015, 0.02, 0.025), 0.15),
        "window_boarded":mat("window_boarded", (0.22, 0.18, 0.14), 0.8),
        "window_lit":    mat("window_lit", (0.1, 0.3, 0.15), 0.4, 0, emit=(0.35, 1.0, 0.45), strength=3),
        "shutter":       mat("shutter", (0.18, 0.22, 0.20), 0.6, 0.5),
        "cable":         mat("cable", (0.01, 0.01, 0.012), 0.45),
        "neon_purple":   mat("neon_purple", (0.6, 0.2, 1.0), 0.3, 0, emit=(0.6, 0.25, 1.0), strength=10),
        "street_lamp":   mat("street_lamp", (0.3, 1.0, 0.45), 0.4, 0, emit=(0.35, 1.0, 0.45), strength=20),
        "street_lamp_flicker": mat("street_lamp_flicker", (0.3, 1.0, 0.45), 0.4, 0, emit=(0.35, 1.0, 0.45), strength=20),
        "lamp_off":      mat("lamp_off", (0.04, 0.05, 0.05), 0.15, 0.0),
        "amber_blink":   mat("amber_blink", (0.4, 0.2, 0.0), 0.3, 0, emit=(1.0, 0.55, 0.05), strength=12),
        "bulb_warm":     mat("bulb_warm", (1.0, 0.8, 0.5), 0.3, 0, emit=(1.0, 0.72, 0.4), strength=14),
        "window_warm":   mat("window_warm", (0.3, 0.2, 0.1), 0.4, 0, emit=(1.0, 0.65, 0.3), strength=2.5),
        "sign_panel":    mat("sign_panel", (0.6, 0.2, 0.4), 0.4, 0, emit=(1.0, 0.3, 0.6), strength=2.0),
        "billboard":     mat("billboard", (0.42, 0.40, 0.36), 0.8),
        "grating":       mat("grating", (0.22, 0.22, 0.23), 0.55, 0.7),
        "awning":        mat("awning", (0.35, 0.08, 0.08), 0.8),
        "led_cool":      mat("led_cool", (0.9, 0.95, 1.0), 0.3, 0, emit=(0.85, 0.92, 1.0), strength=8),
        "exit_green":    mat("exit_green", (0.1, 0.6, 0.25), 0.3, 0, emit=(0.15, 1.0, 0.4), strength=6),
        "glass_smoke":   mat("glass_smoke", (0.02, 0.02, 0.025), 0.05, 0.0),
        "capsule_red":   mat("capsule_red", (0.85, 0.08, 0.10), 0.25),
        "capsule_blue":  mat("capsule_blue", (0.10, 0.30, 0.90), 0.25),
        "capsule_yellow":mat("capsule_yellow", (0.95, 0.80, 0.10), 0.25),
        "capsule_green": mat("capsule_green", (0.15, 0.75, 0.30), 0.25),
        "hazard_yellow": mat("hazard_yellow", (0.95, 0.75, 0.05), 0.45),
        "hazard_red":    mat("hazard_red", (0.65, 0.05, 0.04), 0.5, 0.2),
        "racing_screen": mat("racing_screen", (0.2, 0.4, 0.9), 0.2, 0, emit=(0.3, 0.5, 1.0), strength=4),
        "wall_tv":       mat("wall_tv", (0.3, 0.2, 0.6), 0.2, 0, emit=(0.5, 0.3, 0.9), strength=3),
        "gacha_card":    mat("gacha_card", (0.9, 0.6, 0.8), 0.6, 0, emit=(0.9, 0.6, 0.8), strength=0.4),
        "prize_box":     mat("prize_box", (0.6, 0.5, 0.8), 0.6),
    }
    for key, period, on_frac, hi in (("amber_blink", FPS, 0.5, 12.0), ("street_lamp_flicker", None, 0, 20.0)):
        em = node_of_type(M[key].node_tree, "BSDF_PRINCIPLED").inputs["Emission Strength"]
        if period:
            for k in range(0, 60 * FPS, period):
                em.default_value = hi
                em.keyframe_insert("default_value", frame=k + 1)
                em.default_value = 0.0
                em.keyframe_insert("default_value", frame=k + 1 + int(period * on_frac))
        else:   # same stutter pattern as the light in street_lamp(... "flicker")
            r = random.Random(sum(map(ord, "street_lamp_5")))
            fr = 1
            while fr < 60 * FPS:
                for e, d in ((hi, r.randint(30, 90)), (hi * 0.08, r.randint(2, 5)), (hi, r.randint(2, 4)), (0.0, r.randint(3, 8))):
                    em.default_value = e
                    em.keyframe_insert("default_value", frame=fr)
                    fr += d
        set_interp(M[key].node_tree, "CONSTANT")
    found = [k for k, (fn, tile, bump) in SURFACE_TEX.items() if apply_surface_texture(M[k], fn, tile, bump)]
    add_puddles(M["roof_wet"])
    for k, s in PRINT_MATS.items():
        add_fingerprints(M[k], SURFACE_TEX[k][1], s)
    # thin, clean cabinet glass: keep raytraced reflections from turning it into a pink mirror
    node_of_type(M["glass"].node_tree, "BSDF_PRINCIPLED").inputs["Specular IOR Level"].default_value = 0.06
    print(f"surface textures: {len(found)}/{len(SURFACE_TEX)} found", found)
    print(f"weathering masks: {len(MASK_FOUND)}/{len(MASK_TEX)} found", sorted(MASK_FOUND))
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
    print("arcade detail objects:", build_arcade_details(bpy.data.collections["ARCADE_ROOM"], M))
    # S17a coin close-up: the chrome coin plate only mirrors the dark room, so give it a soft key light
    # of its own, switched on for that shot only so it never spills into the wider arcade shots
    from mathutils import Vector
    L = bpy.data.lights.new("L_coin_key", "AREA")
    L.energy, L.color, L.size = 6.0, (0.85, 0.92, 1.0), 0.25
    lo = bpy.data.objects.new(L.name, L)
    lo.location = (0.42, -0.78, 1.02)
    lo.rotation_euler = (Vector((0.22, -0.52, 0.84)) - lo.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(lo)
    s17 = [x for x in SHOTS if x[0] == "S17a_coin"][0]
    for fr, e in ((1, 0.0), (f(s17[1]), 6.0), (f(s17[2]), 0.0)):
        L.energy = e
        L.keyframe_insert("energy", frame=fr)
    for fc in fcurves_of(L):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"
    build_decals(C)
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
