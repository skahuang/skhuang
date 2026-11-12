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
# Everything below is authored in STORY seconds; f() maps them to FILM seconds. The first full render
# (4562d37) felt slow in Act 2 and short on the arcade, so S07-S09 lose 2 s and Act 4 gains 2 s.
STORY_MAP = [(0.0, 0.0), (18.0, 18.0), (30.0, 28.0), (62.0, 60.0)]
STORY_END = STORY_MAP[-1][0]
RES_X, RES_Y = 1080, 1920
SEED = 7

ROOF_Z = 1.10          # rooftop surface height (diorama bed is at 0.95)
BED_Z = 0.95
TOWER_XY = (0.10, 0.14)
SHED_XY = (-0.11, 0.13)
DOOR_XY = (-0.11, 0.105)   # door face of the stair shed (faces -Y)
RIN_H = 0.023              # Rin standee height
ZOMBIE_H = 0.033            # adults: ~1.1-1.3x Rin standing (was 0.026, shorter than her)
NOVA_XY = (0.25, -0.85)
NOVA_H = 1.62
PIN_XY = (0.02, 0.0)       # where Rin lands and gets pinned
PIN_H = 0.0156             # (legacy 512x256 pin cells; unused since the v2 square canvas)
# v2 pin art (sprite_list_v2.md): every pin / takedown / grabbed-down layer shares ONE square 512 px canvas,
# so all layers use the same plane size and position and overlay 1:1. Scale is set from sitting Rin
# (rin_grabbed_down cell 1, 157 px) matching her sitting size in S12 (~1.0 cm); the art's ground line
# sits 52 px above the cell bottom, so the planes drop by that much to put her on the tiles.
PIN_SQ_H = 0.0333
PIN_SQ_Z = ROOF_Z + 0.002 - PIN_SQ_H * 52 / 512
CHUTE_XY = (0.30, -0.30)   # prize chute (front-right, above the outside pickup door)
PRIZE_TRAY = (0.29, -0.45, 0.19)   # where the dropped tower ends up, behind the outside pickup flap (scene thread's chute shaft)
RESET_S = 58.0             # story seconds (film 56 s)
DOOR_BANGS_S = (1.45, 1.85, 2.2)   # story s: the horde hammers the door Rin slammed (S01b); shared with dent_door()
TIMER_START = 32           # story seconds (film 30 s): overlay countdown hits 00:00 the moment her grip fails

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
    "pin_face_closeup":    (4, 3, 12, 8, "once"),
    "pin_hand_press":      (3, 2, 6, 12, "once"),      # S13c macro: hand slams, closes, presses, drags, tightens, she goes limp      # S13b face ECU: grit teeth -> eyes to tower -> cry -> defiance
    "pin_layer_back":      (4, 3, 12, 8, "loop"),      # Z03 + Z04 gripping hood and ankle; same square canvas as pin_layer_rin
    "pin_layer_front":     (4, 3, 12, 8, "loop"),      # pressing down; frame-locked to pin_layer_rin (same clock, phase 0)
    "pin_layer_contact":   (4, 3, 12, 8, "loop"),      # baked contact shadow of the front pair (tools/make_contact_shadows.py)
    "rin_reset_lookup":    (4, 2, 8, 12, "once"),      # slowly tilts head up to the lens
    # S12b-S12d grab-and-pin sequence (sprite_list_v1.md B1-B5); placeholders until the art lands
    "rin_scoot_back":      (4, 2, 8, 12, "once"),      # S12b sitting, scoots back, bumps into legs, looks up
    "rin_grabbed_down":    (4, 3, 12, 12, "once"),     # S12c ankle grabbed, yanked, rolled onto her stomach
    "pin_takedown_rin":    (3, 2, 6, 12, "once"),      # S12d cheek pressed to the tiles; last cell = pin_layer_rin cell 1
    "pin_takedown_back":   (3, 2, 6, 12, "once"),      # S12d Z03 + Z04 lunge in; last cell = pin_layer_back cell 1
    "pin_takedown_front":  (3, 2, 6, 12, "once"),      # S12d Z01 + Z02 slam her down; last cell = pin_layer_front cell 1
    "pin_takedown_contact": (3, 2, 6, 12, "once"),     # baked contact shadow of the takedown front pair
    "rin_run_to_ladder":   (3, 2, 6, 12, "once"),      # S04 opening: scrambles up, two strides, leaps onto the ladder
    "rin_burst_door":      (4, 2, 8, 12, "once"),      # S01a (old art: reads as backing away; superseded by rin_door_slam)
    "rin_door_slam":       (4, 3, 12, 12, "once"),     # S01a shoulder-slams the door open, stumbles out, spins, heaves it shut
    "nova_joystick_hand":  (4, 2, 8, 12, "once"),      # S15n ECU: Nova's hand nudges the ball-top joystick over the chute
    "nova_button_slam":    (3, 2, 6, 12, "once"),      # S15m ECU: her palm slams the magenta drop button (drawn button)
    "nova_button_hand":    (3, 2, 6, 12, "once"),      # same sheet with the drawn button erased (tools/strip_drawn_button.py)
    "rin_run_chase":       (4, 2, 8, 12, "loop"),      # S02b front-3/4 sprint cycle, terrified
    "rin_look_back":       (4, 2, 8, 12, "once"),      # S02c running, twists to look back over her shoulder
    "nova_back_joystick":  (4, 2, 8, 12, "loop"),      # joystick jiggle, shoulders tense
    "nova_profile_almost": (4, 3, 12, 8, "once"),      # wince, exhale, glance at the chute
    "nova_hand_coin":      (4, 2, 8, 12, "once"),      # flip token, push it into the slot
}
# Per-cell exposure sheets ("timing charts"): (cell 1-based, hold in 24 fps frames).
# They replace the flat fps for these sprites so each action fills its shot instead of
# finishing early and freezing. "once" holds the last cell, "loop" repeats the chart.
TIMING = {
    "door_fingers":     [(1, 2), (2, 2), (3, 2), (4, 3), (5, 3), (6, 4), (5, 2), (4, 2), (3, 3), (2, 2), (1, 4)],
    "rin_boot_grab":    [(1, 4), (2, 4), (3, 5), (4, 3), (5, 3), (6, 4), (7, 4), (8, 5), (9, 6), (10, 6), (11, 7), (12, 9)],   # 60 = S03
    "rin_cling_scared": [(1, 2), (2, 2), (1, 2), (2, 2), (3, 6), (4, 8), (1, 2), (2, 2), (1, 2), (2, 2), (1, 2), (2, 2),
                         (3, 8), (4, 10), (2, 2), (1, 2), (2, 2), (1, 2), (2, 2), (1, 2), (2, 4)],             # 72 = S05, irregular tremble
    "rin_look_up":      [(1, 3), (2, 3), (3, 6), (4, 8), (5, 10), (6, 10), (7, 12), (8, 20)],                  # 72 = S06
    # S07-S09 share ONE clock (see CONTINUOUS): fear -> looks at light (S07), hope (S08), relieved smile (S09)
    "rin_cling_hope":   [(2, 13), (1, 7), (2, 20), (3, 40), (4, 27), (5, 27), (4, 7), (5, 20), (6, 27), (7, 26), (8, 26)],   # 240 = S07+S08+S09 (film)
    "rin_slip_shock":   [(1, 6), (2, 4), (3, 4), (4, 5), (5, 5), (6, 6), (7, 6), (8, 12)],                     # 48 = S10
    "rin_impact":       [(1, 2), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 4)],                      # 24 = S12
    "rin_scoot_back":   [(1, 2), (2, 3), (3, 3), (4, 2), (5, 3), (6, 4), (7, 3), (8, 4)],                      # 24 = S12b
    "rin_grabbed_down": [(1, 3), (2, 3), (3, 4), (4, 2), (5, 2), (6, 3), (7, 2), (8, 2), (9, 2), (10, 4), (11, 4), (12, 5)],   # 36 = S12c
    "pin_takedown_rin": [(1, 3), (2, 3), (3, 2), (4, 6), (5, 4), (6, 6)],                                      # 24 = S12d
    "pin_hand_press":   [(1, 2), (2, 3), (3, 3), (4, 3), (5, 3), (6, 4)],                                      # 18 = S13c
    "pin_takedown_back": [(1, 3), (2, 3), (3, 2), (4, 6), (5, 4), (6, 6)],                                     # same clock as the Rin layer
    "pin_takedown_front": [(1, 3), (2, 3), (3, 2), (4, 6), (5, 4), (6, 6)],
    "pin_takedown_contact": [(1, 3), (2, 3), (3, 2), (4, 6), (5, 4), (6, 6)],
    "rin_run_to_ladder": [(1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 2)],                                    # 17 = S04 opening
    # the three pin layers share one 12-cell clock (8 fps)
    "pin_layer_rin":   [(i, 3) for i in range(1, 13)],
    "pin_layer_back":  [(i, 3) for i in range(1, 13)],
    "pin_layer_front": [(i, 3) for i in range(1, 13)],
    "pin_layer_contact": [(i, 3) for i in range(1, 13)],
    "pin_face_closeup": [(i, 4) for i in range(1, 13)],                                                       # 48 = S13b
    "nova_profile_almost": [(1, 6), (2, 6), (3, 6), (4, 6), (5, 8), (6, 8), (7, 8), (8, 8), (9, 6), (10, 6), (11, 6), (12, 10)],  # 84 = S16
    "nova_hand_coin":   [(1, 4), (2, 4), (3, 4), (4, 6), (5, 8), (6, 6), (7, 6), (8, 10)],                     # 48 = S17a
    # S01a, frame-locked to the door keys in animate_story: cell 1 on the burst (film f7), cell 9 on the slam (f23)
    "rin_door_slam":    [(1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (10, 2), (11, 2), (12, 1)],   # 23
    # S15n: cells 2-3 nudge left, 5-6 nudge forward (claw keys follow), 8 lets go = 17 frames
    "nova_joystick_hand": [(1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 3)],
    # S15m: cell 3 = impact on frame 5 of the shot (thump + 3D button travel on the same frame) = 12 frames
    "nova_button_slam": [(1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2)],
    "nova_button_hand": [(1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2)],
    "rin_reset_lookup": [(1, 10), (2, 8), (3, 8), (4, 8), (5, 8), (6, 8), (7, 10), (8, 12)],                   # 72 = S17b
}
# Sheets whose clock runs on across several shots instead of restarting in each one
CONTINUOUS = {"rin_cling_hope"}
SPRITE_FALLBACK = {"rin_door_slam": "rin_burst_door", "rin_burst_door": "rin_run_to_ladder", "rin_run_chase": "rin_run_to_ladder", "rin_look_back": "rin_backing_away"}
# GPT drew Rin at different sizes inside the cells (standing figure 330-458 px of 512).
# Height multipliers, judged from her head size against rin_reset_lookup, so she keeps one size across cuts.
SHEET_SCALE = {
    "rin_backing_away": 1.17, "rin_boot_grab": 1.5, "rin_climb_back": 1.12, "rin_cling_scared": 0.88,
    "rin_look_up": 0.97, "rin_slip_shock": 1.2, "rin_falling": 1.17, "rin_impact": 1.12,
    "rin_burst_door": 1.17, "rin_door_slam": 0.96,   # square 512 cells, figure ~410 px tall (run sheets: ~335 of 512)
    "rin_run_chase": 1.17, "rin_look_back": 1.17,
}
ZOMBIE_ANIM = {
    "walk":  (4, 2, 8, 12, "loop"),
    "reach": (3, 2, 6, 8, "pingpong"),
    "climb": (3, 2, 6, 12, "loop"),
    "run":   (4, 2, 8, 12, "loop"),      # chasers (sprite_list_v3_chase.md C4/C5); falls back to the walk sheet
}


def story_to_film(sec):
    for (s0, t0), (s1, t1) in zip(STORY_MAP, STORY_MAP[1:]):
        if sec <= s1 or (s1, t1) == STORY_MAP[-1]:
            return t0 + (sec - s0) * (t1 - t0) / (s1 - s0)
    return sec


def f(sec):
    """story seconds -> film frame number (1-based)."""
    return int(round(story_to_film(sec) * FPS)) + 1


# Shot list — must match README.md §3. (id, start_s, end_s, lens, cam_from, cam_to, aim_from, aim_to)
SHOTS = [
    # ---- Act 1: trapped (0-15 s)
    # S01a: the door flies open and Rin bursts out straight at the lens (rin_burst_door)
    ("S01a_door_burst",   0.0,  1.2, 35, (-0.092, 0.040, 1.108), (-0.106, 0.046, 1.109), (-0.106, 0.092, 1.114), (-0.117, 0.089, 1.112)),   # stays on her at the door through the slam
    # S01b: she has slammed it behind her; fingers squirm out of the gap, she backs off in the foreground
    ("S01b_door_bang",    1.2,  2.5, 50, (-0.052, -0.025, 1.114), (-0.060, -0.010, 1.116), (-0.101, 0.107, 1.124), (-0.101, 0.107, 1.122)),   # ~21 deg off-axis so the dents read; fingers centred
    # S02: medium crane-down as the door bursts and the horde pours out after her (was a static wide)
    ("S02_establish",     2.5,  4.0, 35, (0.000, -0.020, 1.140), (0.010, -0.030, 1.135), (-0.062, 0.046, 1.115), (-0.045, 0.027, 1.115)),   # on her as she backs off, the horde bursting out behind
    # S02b: low tracking shot ahead of her as she runs, zombies chasing behind (rin_run_chase)
    ("S02b_chase_low",    4.0,  5.0, 24, (-0.011, 0.007, 1.106), (0.019, -0.012, 1.106), (-0.045, 0.027, 1.110), (-0.015, 0.008, 1.110)),
    # S02c: close-up, she looks back over her shoulder at the horde closing in (rin_look_back)
    ("S02c_look_back",    5.0,  6.0, 50, (0.025, 0.030, 1.113),  (0.065, 0.052, 1.113),  (-0.015, 0.008, 1.115), (0.025, 0.030, 1.115)),   # leads her (chasers stay behind her, not in the lens)
    # S04a: she reaches the tower and jumps on the ladder, the chasers right behind her
    ("S04a_run_climb",    6.0,  7.3, 35, (0.040, 0.000, 1.160),  (0.075, 0.050, 1.145),  (0.075, 0.065, 1.120), (0.100, 0.095, 1.130)),
    # S03: they drag her back down off the ladder and tear the boot off (rin_boot_grab, at the tower foot)
    ("S03_lost_boot",     7.3,  9.8, 50, (0.124, 0.030, 1.106),  (0.118, 0.039, 1.105),  (0.098, 0.088, 1.113), (0.098, 0.088, 1.113)),
    # S04b: she kicks free and scrambles back up, hands clawing at her heels; low angle up the ladder
    ("S04b_climb_escape", 9.8, 12.0, 35, (0.108, 0.040, 1.112),  (0.106, 0.047, 1.140),  (0.100, 0.100, 1.128), (0.100, 0.100, 1.165)),   # low angle up the ladder, clawing hands either side
    # S05: high 3/4 down the ladder at her clinging, the pile clawing up below (was top-down on the tank lid)
    ("S05_pile_topdown", 12.0, 15.0, 35, (0.150, 0.050, 1.215),  (0.145, 0.058, 1.210),  (0.100, 0.101, 1.185), (0.100, 0.101, 1.180)),   # 3/4 at her height, the pile clawing below
    ("S06_light_above",  15.0, 18.0, 16, (0.106, 0.060, 1.165),  (0.106, 0.062, 1.167),  (0.10, 0.100, 1.200), (0.10, 0.100, 1.205)),   # whole figure clear of the bottom UI zone
    ("S07_claw_descends",18.0, 22.0, 35, (0.32, -0.16, 1.42),    (0.30, -0.15, 1.38),    (0.10, 0.14, 1.62),   (0.10, 0.14, 1.26)),   # opens on the claw, tilts down with it
    ("S08_grip_lift",    22.0, 26.0, 35, (0.28, -0.20, 1.34),    (0.30, -0.22, 1.47),    (0.10, 0.14, 1.20),   (0.10, 0.14, 1.42)),
    # S09 split in two (local to TOWER_ROOT): her face, then a low angle up past her to the light
    ("S09a_false_hope",  26.0, 28.0, 85, (0.010, -0.110, 0.093), (0.008, -0.100, 0.094), (0.0, -0.041, 0.093), (0.0, -0.041, 0.094)),
    ("S09b_hope_low",    28.0, 30.0, 35, (0.022, -0.085, 0.060), (0.018, -0.080, 0.064), (0.0, -0.041, 0.090), (0.0, -0.041, 0.096)),
    ("S10_slip",         30.0, 32.0, 50, (0.060, 0.020, 1.500),  (0.066, 0.030, 1.495),  (0.10, 0.10, 1.460),  (0.10, 0.10, 1.455)),   # close enough to see the fingers slide
    # ---- Act 3: fall, grabbed, pinned, pull-back (32-46 s) — the tower stays in the claw, only Rin falls
    ("S11_fall",         32.0, 34.5, 35, (0.28, -0.22, 1.42),    (0.090, -0.075, 1.150),   (0.10, 0.10, 1.40),   (0.030, 0.010, 1.130)),   # SHOT_MID keeps her framed
    ("S12_impact",       34.5, 35.5, 50, (0.060, -0.052, 1.113), (0.060, -0.052, 1.113), (0.02, 0.0, 1.111),   (0.02, 0.0, 1.111)),   # aim up: less blurred foreground
    # S12b-S12d: the horde closes in, grabs her bare ankle and hood, drags her down and presses her flat
    ("S12b_surrounded",  35.5, 36.5, 24, (0.040, -0.042, 1.118), (0.034, -0.034, 1.116), (0.018, 0.008, 1.112), (0.018, 0.006, 1.111)),   # wider + deep focus: the lunge reads, Rin ~25% of frame
    ("S12c_grabbed",     36.5, 38.0, 50, (0.046, -0.056, 1.108), (0.041, -0.050, 1.106), (0.02, 0.0, 1.106),   (0.02, 0.0, 1.106)),
    ("S12d_pressed",     38.0, 39.0, 35, (0.070, -0.060, 1.135), (0.064, -0.055, 1.130), (0.02, 0.0, 1.114),   (0.02, 0.0, 1.114)),   # high side angle: no near-jump-cut into the frontal S13a
    ("S13a_pinned",      39.0, 40.5, 50, (0.028, -0.070, 1.107), (0.024, -0.054, 1.108), (0.02, 0.0, 1.116),   (0.021, 0.0, 1.115)),   # aim up: zombie heads in, less ground
    # S13c: macro insert, Z02's huge hand clamps her forearm to the tiles (pin_hand_press, 6 cells on twos)
    ("S13c_hand_press",  40.5, 41.25, 50, (0.0245, -0.072, 1.116), (0.0245, -0.069, 1.1158), (0.0245, -0.013, 1.116), (0.0245, -0.013, 1.1158)),   # 9:16 crop: both cell edges out of frame, her fingers in
    ("S13b_pinned_face", 41.25, 43.0, 50, (0.0178, -0.050, 1.1112), (0.0178, -0.046, 1.1102), (0.0178, -0.013, 1.1112), (0.0178, -0.013, 1.1102)),   # frame bottom at 86.5% of the cell, just above the art's cut-off (92%)
    ("S14_pullback",     43.0, 46.0, 24, (0.024, -0.054, 1.108), (0.14, -0.44, 1.37),    (0.02, 0.0, 1.114),   (0.08, 0.10, 1.34)),   # ends framing the pile AND the empty tower in the claw
    # ---- Act 4: reveal + loop (46-60 s)
    ("S15_glass_reveal", 46.0, 48.6, 35, (0.14, -0.44, 1.37),    (-0.85, -3.40, 1.95),   (0.08, 0.10, 1.34),   (0.20, -0.20, 1.40)),   # out through the glass as the claw carries the tower to the chute, ends on the arcade + Nova
    # S15b: the aisle with Nova at our machine (more arcade)
    ("S15b_arcade_aisle",48.6, 49.6, 24, (1.40, -2.60, 1.55),    (1.10, -2.20, 1.45),    (0.20, -0.60, 1.10),  (0.25, -0.70, 1.15)),
    # S15n/S15m: Nova at the controls - her hand lines the claw up over the chute, then slams the drop button
    ("S15n_nova_joystick",49.6, 50.3, 50, (-0.05, -0.98, 1.22),  (-0.08, -0.93, 1.19),   (-0.25, -0.58, 0.975), (-0.25, -0.58, 0.975)),
    ("S15m_nova_button", 50.3, 50.8, 50, (0.10, -0.86, 1.10),    (0.085, -0.835, 1.085), (-0.08, -0.58, 0.93), (-0.08, -0.58, 0.925)),
    # S15d: through the front glass, the claw opens and the empty tower drops down the prize hole
    ("S15d_chute_drop",  50.8, 51.7, 35, (0.40, -0.86, 1.64),    (0.39, -0.82, 1.50),    (0.30, -0.30, 1.52),  (0.30, -0.30, 0.97)),   # through the front glass, clear of the corner post
    # S15c: outside, low at the pickup flap - the tower tumbles out into the prize tray
    ("S15c_prize_tray",  51.7, 52.5, 50, (0.53, -1.04, 0.42),    (0.50, -0.98, 0.40),    (PRIZE_TRAY[0], PRIZE_TRAY[1] - 0.01, PRIZE_TRAY[2] + 0.02), (PRIZE_TRAY[0], PRIZE_TRAY[1] - 0.01, PRIZE_TRAY[2] + 0.02)),
    ("S16_nova_almost",  52.5, 56.0, 85, (1.00, -1.74, 1.23),    (0.90, -1.62, 1.21),    (0.24, -0.86, 1.115), (0.24, -0.86, 1.12)),   # slow push-in on her face (eyes ~1.15 m)
    ("S17a_coin",        56.0, 58.0, 50, (0.53, -1.04, 1.02),    (0.50, -0.98, 1.00),    (0.28, -0.54, 0.87),  (0.28, -0.54, 0.87)),   # hand + coin mid-frame, sleeve edge below frame
    ("S17b_reset_loop",  58.0, 62.0, 35, (0.010, -0.060, 1.116), (-0.092, 0.040, 1.108), (0.0, -0.01, 1.112),  (-0.106, 0.092, 1.114)),   # whole figure clear of the UI zone, ends EXACTLY on the S01a frame (loop seam)
]


# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------
# Shots whose camera + aim ride with a moving object (coordinates above are then local to it)
SHOT_PARENT = {"S09a_false_hope": "TOWER_ROOT", "S09b_hope_low": "TOWER_ROOT"}
# Shots that aim past the subject but must keep her sharp
SHOT_FOCUS = {"S01a_door_burst": "rin_door_slam", "S06_light_above": "rin_look_up", "S04a_run_climb": "rin_run_to_ladder", "S05_pile_topdown": "rin_cling_scared",
              "S09a_false_hope": "rin_cling_hope", "S09b_hope_low": "rin_cling_hope"}
# Extra in-between camera keys: sid -> [(fraction of the shot, cam, aim)]
SHOT_MID = {
    # the tower only leaves the roof at 24.5 s: keep the aim on the tank until then, then ride up with it
    "S08_grip_lift": [(0.5, (0.29, -0.21, 1.36), (0.10, 0.14, 1.20)), (0.75, (0.295, -0.215, 1.41), (0.10, 0.14, 1.33))],
    # keep the pinned group in frame while we rise: the aim lingers on her, then tilts up to the hanging tower
    "S14_pullback": [(0.45, (0.06, -0.15, 1.17), (0.025, 0.01, 1.135)), (0.75, (0.10, -0.30, 1.27), (0.06, 0.07, 1.28))],
    # follow her down (she eases out of the slow-mo hang, then drops) and get close enough to read her
    "S11_fall": [(0.3, (0.17, -0.06, 1.42), (0.088, 0.085, 1.425)), (0.55, (0.14, -0.035, 1.37), (0.077, 0.07, 1.375)),
                 (0.8, (0.105, -0.060, 1.27), (0.050, 0.038, 1.25))],
    # hold on Rin looking up into the lens, then whip back to the door for the loop
    "S17b_reset_loop": [(0.6, (0.006, -0.046, 1.115), (0.0, -0.01, 1.112)),
                        (0.88, (-0.092, 0.040, 1.108), (-0.106, 0.092, 1.114))],   # whip done early: the door settles for the seam
    # follow her round the open leaf to the hinge side and hold on her shoving it shut (start frame = loop seam, untouched)
    "S01a_door_burst": [(0.4, (-0.094, 0.041, 1.108), (-0.108, 0.088, 1.113)), (0.55, (-0.106, 0.043, 1.108), (-0.129, 0.080, 1.112)),
                        (0.68, (-0.108, 0.044, 1.109), (-0.120, 0.086, 1.112)),   # door leaf + her fists both in frame
                        (0.8, (-0.107, 0.045, 1.109), (-0.119, 0.090, 1.112))],
    # get out of the cabinet fog fast: outside the glass by a quarter of the shot
    "S15_glass_reveal": [(0.25, (-0.15, -1.30, 1.55), (0.15, 0.05, 1.52))],
    # hold on the opening claw, then tilt down with the falling tower
    "S15d_chute_drop": [(0.2, (0.398, -0.852, 1.62), (0.30, -0.30, 1.52)), (0.38, (0.396, -0.845, 1.59), (0.30, -0.30, 1.38)),
                        (0.48, (0.394, -0.840, 1.57), (0.30, -0.30, 1.14)), (0.6, (0.393, -0.835, 1.55), (0.30, -0.30, 1.00))],   # tilt keeps the falling tank in frame
}


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
    # V7 (TEXTURES_V7.md): one whole picture per big object instead of a repeating tile
    "arcade_side":    ("tex_arcade_cab_side.png",                              None, 0.05),
    "racing_seat":    ("tex_racing_seat.png",                                  None, 0.25),
    "control_panel":  ("tex_control_panel_top.png",                            None, 0.05),
    "machine_yellow": ("tex_claw_machine_yellow.png",                          None, 0.05),
    "racing_base":    ("tex_racing_base.png",                                  None, 0.20),
    "racing_dash":    ("tex_racing_dash.png",                                  None, 0.05),
    "ceiling":        ("tex_ceiling_whole.png",                                None, 0.10),
    "tarp":           ("tex_tarp_patched.png",                                 None, 0.15),
    "sleeping_bag":   ("tex_sleeping_bag.png",                                 None, 0.25),
    "ac_fan":         ("tex_ac_fan_top.png",                                   None, 0.30),
    "crate":          ("tex_crate_side.png",                                   None, 0.25),
    # V8 (TEXTURES_V8.md): laundry; until it arrives the line borrows fabric pictures we already have
    "cloth_shirt":    (["tex_cloth_shirt.png", "tex_awning_torn.png"],         None, 0.20),
    "cloth_shirt_b":  (["tex_cloth_shirt_b.png", "tex_tarp_patched.png"],      None, 0.20),
    "cloth_pants":    (["tex_cloth_pants.png", "tex_tarp_patched.png"],        None, 0.25),
    "cloth_towel":    (["tex_cloth_towel.png", "tex_sleeping_bag.png"],        None, 0.25),
    "cloth_blanket":  (["tex_cloth_blanket.png", "tex_sleeping_bag.png"],      None, 0.25),
    "cloth_blanket_b":(["tex_cloth_blanket_b.png", "tex_tarp_patched.png"],    None, 0.25),
    "marquee_pink":   (["tex_marquee_neighbour_pink.png", "tex_marquee_logo.png"],   None, 0.00),
    "marquee_yellow": (["tex_marquee_neighbour_yellow.png", "tex_marquee_logo.png"], None, 0.00),
}


SURFACE_TINT = {"facade": 0.3, "parapet": 0.45, "concrete": 0.6, "pillar": 0.7, "cab_body": 1.8, "arcade_side": 1.4}   # brightness multipliers


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
    "metal_dull":    {"grime": 0.40, "chip": 0.12, "rust": 0.40, "vary": 0.10},
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
    for ch in o.children:             # the acrylic base is a child: hide it with its standee
        if ch.name.endswith("_base"):
            ch.animation_data_clear()
            key_visible(ch, visible_ranges)


# Close-ups where the clear acrylic bases read as glowing discs / pale ellipses on the tiles (host check 4)
BASE_HIDDEN_SHOTS = ("S01a_door_burst", "S12_impact", "S12b_surrounded", "S12c_grabbed", "S12d_pressed",
                     "S13a_pinned", "S13c_hand_press", "S13b_pinned_face")


def hide_bases_in_close_shots():
    for o in bpy.data.objects:
        if not (o.name.endswith("_base") and o.parent and o.parent.constraints.get("Locked Track")):
            continue
        fcs = {fc.data_path: fc for fc in fcurves_of(o)} if o.animation_data else {}
        for sid, a, b, *_ in SHOTS:
            if sid not in BASE_HIDDEN_SHOTS:
                continue
            fa, fb = f(a), f(b)
            for prop in ("hide_render", "hide_viewport"):
                fc = fcs.get(prop)
                after = bool(fc.evaluate(fb) > 0.5) if fc else bool(getattr(o, prop))
                if fc:
                    for i in reversed(range(len(fc.keyframe_points))):
                        if fa <= fc.keyframe_points[i].co.x <= fb:
                            fc.keyframe_points.remove(fc.keyframe_points[i])
                setattr(o, prop, True)
                o.keyframe_insert(prop, frame=fa)
                setattr(o, prop, after)
                o.keyframe_insert(prop, frame=fb)
            set_interp(o, "CONSTANT")
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


def animate_sheet(mat, ranges, phase=0, timing=None, continuous=False):
    """Step the sheet's UV window through its cells inside each visible range.
    Default: flat 2s/3s (12 or 8 fps). timing=[(cell 1-based, hold frames), ...] plays an exposure chart
    instead (mode "loop" repeats it, otherwise the last cell holds). continuous=True carries the clock
    over from one range to the next instead of restarting it in every shot."""
    cols, rows, frames, fps = [int(v) for v in mat["sheet"]]
    if frames <= 1:
        return
    mode = mat["sheet_mode"]
    mp = mat.node_tree.nodes["SHEET_MAPPING"]

    def put(i, fr):
        i = max(0, min(frames - 1, i))
        c, r = i % cols, i // cols
        mp.inputs["Location"].default_value = (c / cols, (rows - 1 - r) / rows, 0.0)
        mp.inputs["Location"].keyframe_insert("default_value", frame=fr)

    if timing:
        n, k = len(timing), phase
        for a, b in ranges:
            if not continuous:
                k = phase
            fr = a
            while fr <= b:
                j = k % n if mode == "loop" else min(k, n - 1)
                cell, hold = timing[j]
                put(cell - 1, fr)
                if mode != "loop" and k >= n - 1:
                    break            # last cell holds to the end of the range
                fr += hold
                k += 1
        set_interp(mat.node_tree, "CONSTANT")
        return
    step = max(1, round(FPS / fps))
    k = phase
    for a, b in ranges:
        if not continuous:
            k = phase
        fr = a
        while fr <= b:
            if mode == "once":
                i = min(k, frames - 1)
            elif mode == "pingpong":
                period = 2 * frames - 2
                i = k % period
                i = i if i < frames else period - i
            else:
                i = k % frames
            put(i, fr)
            fr += step
            k += 1
    set_interp(mat.node_tree, "CONSTANT")


def animate_named(o, name, ranges, phase=0):
    """animate_sheet with this sprite's TIMING chart / CONTINUOUS clock, if it has one."""
    animate_sheet(o.data.materials[0], ranges, phase, TIMING.get(name), name in CONTINUOUS)


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
    r = height * 0.22
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
    height *= SHEET_SCALE.get(name, 1.0)
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
    scn.frame_end = f(STORY_END) - 1   # 1440
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
    # lit marquee header on the top front edge (tex_marquee_logo): reads as a claw machine in the S15 reveal
    box("cab_marquee_back", (1.0, 0.05, 0.19), (0, -0.475, H + 0.095), M["cab_body"], cab)
    box("cab_marquee", (0.94, 0.006, 0.15), (0, -0.503, H + 0.095), M["marquee"], cab)
    box("cab_marquee_neon_t", (1.0, 0.012, 0.012), (0, -0.505, H + 0.186), M["neon_cyan"], cab)
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
    box("ctrl_box_top", (0.32, 0.14, 0.004), (-0.17, -0.575, 0.902), M["control_panel"], cab)
    box("joystick_plate", (0.07, 0.07, 0.004), (-0.25, -0.58, 0.905), M["black"], cab)
    shaft = cyl("joystick_shaft", 0.007, 0.07, (-0.25, -0.58, 0.94), M["chrome"], cab, verts=32)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, segments=64, ring_count=32, location=(-0.25, -0.58, 0.98))
    ball = bpy.context.active_object
    ball.name = "joystick_ball"
    for o in (ball, shaft):     # S15n macro close-up: no visible facets
        for poly in o.data.polygons:
            poly.use_smooth = True
    ball.data.materials.append(M["red_glossy"])
    link(ball, cab)
    # S15m hero button (modelled, the hand card presses it): glossy black bezel, saturated magenta domed cap
    bez = cyl("button_bezel", 0.036, 0.012, (-0.08, -0.58, 0.908), M["button_bezel"], cab, verts=64)
    btn = cyl("button_grab", 0.028, 0.016, (-0.08, -0.58, 0.914), M["button_magenta"], cab, verts=64)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0, location=(-0.08, -0.58, 0.922))
    dome = bpy.context.active_object
    dome.name = "button_grab_dome"
    dome.scale = (0.0278, 0.0278, 0.006)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    dome.data.materials.append(M["button_magenta"])
    link(dome, cab)
    dome.parent = btn
    dome.matrix_parent_inverse = btn.matrix_world.inverted()
    for poly in dome.data.polygons:
        poly.use_smooth = True
    # coin mechanism (right of the control box)
    box("coin_slot_plate", (0.10, 0.012, 0.16), (0.22, -0.506, 0.84), M["coin_mech"], cab)
    box("coin_slot", (0.004, 0.012, 0.05), (0.22, -0.513, 0.87), M["black"], cab)
    box("coin_return", (0.04, 0.012, 0.025), (0.22, -0.513, 0.79), M["black"], cab)
    # LED timer on the glass header: dark face with lit seven-segment "00:00" (a flat red slab read as a
    # blank placeholder sign in the S15 reveal, render1 audit #43)
    box("led_timer", (0.16, 0.01, 0.05), (0.0, -0.505, H - 0.12), M["black"], cab)
    zc, yf, t = H - 0.12, -0.5108, 0.0035
    for k, dx in enumerate((-0.054, -0.024, 0.024, 0.054)):
        w, h = 0.020, 0.034
        for sname, size, off in (("t", (w, 0.001, t), (0, h / 2)), ("b", (w, 0.001, t), (0, -h / 2)),
                                 ("ul", (t, 0.001, h / 2), (-w / 2, h / 4)), ("ur", (t, 0.001, h / 2), (w / 2, h / 4)),
                                 ("ll", (t, 0.001, h / 2), (-w / 2, -h / 4)), ("lr", (t, 0.001, h / 2), (w / 2, -h / 4))):
            box(f"led_timer_d{k}_{sname}", size, (dx + off[0], yf, zc + off[1]), M["led_red"], cab)
    for dz in (-0.007, 0.007):
        box(f"led_timer_colon_{dz:+.3f}", (0.004, 0.001, 0.004), (0.0, yf, zc + dz), M["led_red"], cab)
    # lower front: speaker grille (left) and the prize pickup door (right)
    box("vent_grille_front", (0.17, 0.006, 0.17), (-0.30, -0.503, 0.24), M["vent_grille"], cab)
    box("vent_grille_frame", (0.19, 0.004, 0.19), (-0.30, -0.5005, 0.24), M["cab_trim"], cab)
    # pickup door frame: four bars round the opening (build_prize_chute cuts the pocket behind it)
    for nm, size, off in (("t", (0.24, 0.008, 0.02), (0, 0.075)), ("b", (0.24, 0.008, 0.02), (0, -0.075)),
                          ("l", (0.02, 0.008, 0.17), (-0.11, 0)), ("r", (0.02, 0.008, 0.17), (0.11, 0))):
        box(f"prize_door_frame_{nm}", size, (CHUTE_XY[0] + off[0], -0.504, 0.24 + off[1]), M["cab_trim"], cab)
    box("prize_tray", (0.16, 0.10, 0.02), (CHUTE_XY[0], -0.46, 0.175), M["cab_trim"], cab)
    # tiny single boots in the prize tray: earlier failed rounds (dark-humour clue)
    # Rin's lost boots from earlier failed rounds (dark-humour clue), clear of the tower lying in the tray
    # standing ones turned side-on to the S15c camera show the boot profile; one lies toppled in front
    for i, (bx, by, rz, pose) in enumerate(((0.228, -0.497, 0.15, "up"), (0.372, -0.497, 2.95, "up"),
                                            (0.300, -0.503, 0.6, "side"), (0.385, -0.430, 1.4, "up"))):
        root = make_boot(f"lost_boot_{i}", M, cab)
        root.scale = (1.5, 1.5, 1.5)    # read at the S15c distance
        root.location = (bx, by, 0.185 + (0.0 if pose == "up" else 0.0048))
        root.rotation_euler = (math.radians(90) if pose == "side" else 0.0, 0.0, rz)
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
    box("crate_seat", (0.007, 0.007, 0.006), (0.100, -0.022, Z + 0.003), M["crate"], dio, rot=(0, 0, 0.4))
    # festoon of warm bulbs strung over the camp between two scavenged poles
    for k, (px, py) in enumerate([(0.078, -0.088), (0.152, -0.026)]):
        cyl(f"festoon_pole_{k}", 0.0005, 0.028, (px, py, Z + 0.014), M["rust"], dio, verts=6)
    string_lights("camp_festoon", (0.078, -0.088, Z + 0.027), (0.152, -0.026, Z + 0.027), 0.007, 8, M, dio)
    # clothesline on the west side (inside the S02 frame): T-poles, two sagging lines, laundry that sways
    LX, Y0, Y1, LZ, DROP = -0.135, -0.046, 0.056, Z + 0.026, 0.0025
    for k, y in enumerate((Y0, Y1)):
        cyl(f"line_pole_{k}", 0.0005, 0.028, (LX, y, Z + 0.014), M["rust"], dio, verts=6)
        box(f"line_pole_{k}_cross", (0.011, 0.0007, 0.0007), (LX, y, LZ + 0.0004), M["rust"], dio)
        box(f"line_pole_{k}_foot", (0.004, 0.004, 0.0012), (LX, y, Z + 0.0006), M["concrete"], dio)   # cinder-block foot
        for j, sx_ in enumerate((-1, 1)):   # guy-wire brace
            tube(f"line_pole_{k}_brace_{j}", [(LX, y, Z + 0.016), (LX + sx_ * 0.008, y, Z + 0.0005)], 0.00012, M["rust"], dio)
    def line_z(y, drop=DROP):
        t = (y - Y0) / (Y1 - Y0)
        return LZ - drop * 4 * t * (1 - t)
    for j, ox in enumerate((-0.004, 0.004)):
        tube(f"clothesline_{j}", sag((LX + ox, Y0, LZ), (LX + ox, Y1, LZ), DROP + j * 0.0006), 0.00013, M["cable"], dio)
    laundry = [   # (line, y centre, kind, material)
        (0, -0.036, "shirt",   "cloth_shirt"),
        (0, -0.022, "towel",   "cloth_towel"),
        (0, -0.006, "pants",   "cloth_pants"),
        (0, 0.012,  "shirt",   "cloth_shirt_b"),
        (0, 0.030,  "socks",   "cloth_towel"),
        (0, 0.044,  "towel",   "cloth_shirt"),
        (1, -0.028, "blanket", "cloth_blanket"),
        (1, 0.000,  "shirt",   "cloth_shirt_b"),
        (1, 0.024,  "blanket", "cloth_blanket_b"),
    ]
    wind = random.Random(SEED + 77)
    for k, (li, yc, kind, mn) in enumerate(laundry):
        ox = (-0.004, 0.004)[li]
        piv = prop_root(f"cloth_{k}", (LX + ox, yc, line_z(yc, DROP + li * 0.0006) - 0.0001), 0.0, dio)
        cm, parts = M[mn], []
        if kind == "shirt":
            parts += [box(f"cloth_{k}_body", (0.0005, 0.009, 0.010), (0, 0, -0.0052), cm, dio)]
            for sgn in (-1, 1):
                parts.append(box(f"cloth_{k}_sleeve_{sgn}", (0.0005, 0.0035, 0.004), (0, sgn * 0.0053, -0.0022), cm, dio, rot=(sgn * 0.55, 0, 0)))
        elif kind == "pants":
            parts += [box(f"cloth_{k}_waist", (0.0006, 0.008, 0.0016), (0, 0, -0.0008), cm, dio)]
            for sgn in (-1, 1):
                parts.append(box(f"cloth_{k}_leg_{sgn}", (0.0006, 0.0036, 0.013), (0, sgn * 0.0021, -0.0078), cm, dio, rot=(-sgn * 0.05, 0, 0)))
        elif kind == "towel":
            parts += [box(f"cloth_{k}_towel", (0.0005, 0.008, 0.012), (0, 0, -0.006), cm, dio)]
        elif kind == "socks":
            for j in range(2):
                parts.append(box(f"cloth_{k}_sock_{j}", (0.0006, 0.0018, 0.0055), (0, -0.0016 + j * 0.0032, -0.0028), cm, dio, rot=(0.1 - j * 0.2, 0, 0)))
        elif kind == "blanket":   # thrown over the line, hanging down both sides
            for sgn in (-1, 1):
                parts.append(box(f"cloth_{k}_side_{sgn}", (0.0006, 0.016, 0.011), (sgn * 0.0012, 0, -0.0055), cm, dio, rot=(0, -sgn * 0.20, 0)))
        if kind != "blanket":   # clothes pegs
            span = {"shirt": 0.0035, "pants": 0.0035, "towel": 0.0035, "socks": 0.0016}[kind]
            for sgn in (-1, 1):
                parts.append(box(f"cloth_{k}_peg_{sgn}", (0.0007, 0.0004, 0.0013), (0, sgn * span, 0.0001), M[("capsule_blue", "capsule_red", "wood_old")[(k + sgn) % 3]], dio))
        parented(parts, piv)
        piv.rotation_euler = (wind.uniform(-0.04, 0.04), wind.uniform(-0.1, 0.1), 0)
        piv.keyframe_insert("rotation_euler", frame=1)
        for fc in fcurves_of(piv):   # breeze: slow swing about the line, a little twist
            if fc.array_index in (0, 1):
                nz = fc.modifiers.new("NOISE")
                nz.scale = wind.uniform(18, 30)
                nz.strength = (0.10, 0.25)[fc.array_index] * (0.5 if kind == "blanket" else 1.0)
                nz.phase = wind.uniform(0, 100)
    # laundry basket under the line with a folded sheet
    box("laundry_basket", (0.010, 0.007, 0.005), (LX + 0.010, 0.020, Z + 0.0025), M["capsule_blue"], dio, rot=(0, 0, 0.3))
    box("laundry_basket_sheet", (0.009, 0.006, 0.0012), (LX + 0.010, 0.020, Z + 0.0052), M["cloth_towel"], dio, rot=(0.05, 0, 0.35))
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
            while fr < f(STORY_END):
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
        # roof: wet slab over the window texture, a broken parapet, then 2-4 pieces of rooftop life
        top = BED_Z + h
        box(f"city_{i:02d}_roofcap", (w - 0.001, d - 0.001, 0.0008), (x, y, top + 0.0003), M["roof_wet"], dio)
        PT, PH = 0.0016, rnd.uniform(0.003, 0.006)
        for side, (px, py, sx_, sy_) in enumerate([(x, y - d / 2 + PT / 2, w, PT), (x, y + d / 2 - PT / 2, w, PT),
                                                   (x - w / 2 + PT / 2, y, PT, d), (x + w / 2 - PT / 2, y, PT, d)]):
            if rnd.random() < 0.2:
                continue                                   # that side has fallen away
            box(f"city_{i:02d}_parapet_{side}", (sx_, sy_, PH), (px, py, top + PH / 2), M["parapet"], dio)
        def spot(margin=0.006):
            return (x + rnd.uniform(-1, 1) * max(0.0, w / 2 - margin), y + rnd.uniform(-1, 1) * max(0.0, d / 2 - margin))
        pool = ["tank", "antenna", "ac", "shed", "dish", "vents", "junk", "garden", "hatch", "solar"]
        for k, kind in enumerate(rnd.sample(pool, rnd.randint(2, 4))):
            px, py = spot()
            tag = f"city_{i:02d}_{kind}"
            if kind == "tank":
                water_tank_small(tag, (px, py, top), M, dio)
            elif kind == "antenna":
                ah = rnd.uniform(0.012, 0.03)
                cyl(f"{tag}_mast", 0.0004, ah, (px, py, top + ah / 2), M["metal_dull"], dio, verts=6)
                for j in range(3):
                    box(f"{tag}_bar_{j}", (0.006 - j * 0.0015, 0.0004, 0.0004), (px, py, top + ah * (0.5 + j * 0.18)), M["metal_dull"], dio)
                sphere(f"{tag}_led", 0.0007, (px, py, top + ah + 0.0006), M["red_led"], dio, segs=8)
            elif kind == "ac":
                for j in range(rnd.randint(1, 3)):
                    ax, ay = px + j * 0.0115, py
                    if abs(ax - x) > w / 2 - 0.006:
                        break
                    box(f"{tag}_{j}", (0.010, 0.008, 0.006), (ax, ay, top + 0.003), M["metal_dull"], dio)
                    box(f"{tag}_{j}_fan", (0.006, 0.006, 0.0004), (ax, ay, top + 0.0062), M["ac_fan"], dio)
            elif kind == "shed":
                sw = min(0.014, w * 0.35)
                sh = box(f"{tag}", (sw, 0.010, 0.010), (px, py, top + 0.005), M["concrete"], dio, rot=(0, 0, rnd.choice((0, math.pi / 2))))
                box(f"{tag}_roof", (sw + 0.002, 0.012, 0.0008), (px, py, top + 0.0104), M["metal_dull"], dio, rot=sh.rotation_euler)
                c, sn = math.cos(sh.rotation_euler.z), math.sin(sh.rotation_euler.z)
                box(f"{tag}_door", (0.005, 0.0005, 0.0075), (px + 0.00525 * sn, py - 0.00525 * c, top + 0.00375), M["door_green"], dio, rot=sh.rotation_euler)
            elif kind == "dish":
                cyl(f"{tag}_post", 0.0003, 0.004, (px, py, top + 0.002), M["metal_dull"], dio, verts=6)
                cone(f"{tag}_bowl", 0.0035, 0.0008, 0.0012, (px, py, top + 0.0045), M["plastic_white"], dio, verts=16,
                     rot=(rnd.uniform(0.6, 1.0), 0, rnd.uniform(0, math.tau)))
            elif kind == "vents":
                for j in range(rnd.randint(2, 4)):
                    vh = rnd.uniform(0.003, 0.008)
                    vx, vy = px + rnd.uniform(-0.005, 0.005), py + rnd.uniform(-0.005, 0.005)
                    cyl(f"{tag}_{j}", 0.0008, vh, (vx, vy, top + vh / 2), M["rust"], dio, verts=8)
                    cone(f"{tag}_{j}_cap", 0.0013, 0.0002, 0.0008, (vx, vy, top + vh + 0.0004), M["metal_dull"], dio, verts=8)
            elif kind == "junk":
                box(f"{tag}_pile", (0.010, 0.008, 0.003), (px, py, top + 0.0015), M["concrete_dark"], dio, rot=(0, 0, rnd.uniform(0, 3)))
                box(f"{tag}_tarp", (0.011, 0.009, 0.0006), (px, py, top + 0.0033), M["tarp"], dio,
                    rot=(rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), rnd.uniform(0, 3)))
                box(f"{tag}_crate", (0.004, 0.004, 0.0035), (px + 0.007, py, top + 0.00175), M["crate"], dio, rot=(0, 0, rnd.uniform(0, 3)))
                cyl(f"{tag}_barrel", 0.0018, 0.005, (px - 0.007, py + 0.002, top + 0.0025), M["rust"], dio, verts=12)
            elif kind == "garden":
                for j in range(rnd.randint(3, 5)):
                    gx, gy = px + rnd.uniform(-0.006, 0.006), py + rnd.uniform(-0.004, 0.004)
                    cyl(f"{tag}_pot_{j}", 0.0013, 0.002, (gx, gy, top + 0.001), M["brick"], dio, verts=10)
                    sphere(f"{tag}_plant_{j}", 0.0016, (gx, gy, top + 0.0027), M["grass"], dio, segs=8, scale=(1, 1, 0.8))
            elif kind == "hatch":
                box(f"{tag}_curb", (0.007, 0.007, 0.0015), (px, py, top + 0.00075), M["concrete"], dio)
                box(f"{tag}_lid", (0.0065, 0.0065, 0.0004), (px, py + 0.002, top + 0.0032), M["metal_dull"], dio, rot=(0.9, 0, 0))
            elif kind == "solar":
                for j in range(2):
                    box(f"{tag}_{j}", (0.010, 0.006, 0.0005), (px, py + j * 0.007, top + 0.003), M["window_broken"], dio, rot=(0.5, 0, 0))
                    box(f"{tag}_{j}_leg", (0.0005, 0.0005, 0.003), (px, py + j * 0.007 + 0.002, top + 0.0015), M["rust"], dio)
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


def dent_door(door):
    """Each bang in S01 punches the steel panel further out (cumulative shape keys), it stays dented
    through the burst-open, and snaps flat again on the loop reset."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(door.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=14, use_grid_fill=True)
    bm.to_mesh(door.data)
    bm.free()
    for poly in door.data.polygons:
        poly.use_smooth = True
    door.shape_key_add(name="Basis", from_mix=False)
    hx, hz = 0.012, 0.019
    # (centre x, centre z, radius, depth) in door-local metres; outside is -Y
    blows = [[(0.003, 0.008, 0.0065, 0.0022)],
             [(-0.004, -0.004, 0.0060, 0.0019), (0.003, 0.008, 0.0075, 0.0010)],
             [(0.0, 0.003, 0.0120, 0.0034), (0.006, 0.012, 0.0050, 0.0012)]]
    keys = []
    for k, dents in enumerate(blows):
        kb = door.shape_key_add(name=f"dent_{k}", from_mix=False)
        for v, base in zip(kb.data, door.data.vertices):
            x, z = base.co.x, base.co.z
            edge = min(1.0, (hx - abs(x)) / 0.003) * min(1.0, (hz - abs(z)) / 0.003)   # rim stays in the frame
            edge = max(0.0, edge)
            d = sum(dep * math.exp(-((x - cx) ** 2 + (z - cz) ** 2) / (r * r)) for cx, cz, r, dep in dents)
            v.co.y = base.co.y - d * edge
        keys.append(kb)
    R = f(RESET_S)
    for kb, sec in zip(keys, DOOR_BANGS_S):
        b = f(sec)
        for fr, val in ((1, 0.0), (b - 1, 0.0), (b + 1, 1.25), (b + 3, 0.9), (b + 5, 1.0), (R - 1, 1.0), (R, 0.0)):
            kb.value = val
            kb.keyframe_insert("value", frame=fr)
    ad = door.data.shape_keys.animation_data
    if ad and ad.action:
        for fc in fcurves_of(door.data.shape_keys):
            for kp in fc.keyframe_points:
                if int(kp.co.x) in (R - 1, R):
                    kp.interpolation = "CONSTANT"


CHUTE_HOLE = 0.15          # square opening in the bed at CHUTE_XY (the tower drops through it)
CHUTE_BOTTOM_Z = 0.21      # the shaft ends just above the prize tray behind the pickup door


def make_boot(name, M, coll):
    """Rin's lace-up ankle boot as a little 3D model (sole on z=0, toe toward +X, about 0.013 long x 0.015
    tall): tapered shaft with a folded cuff, rounded toe cap, lugged sole with a heel step, dark lace
    strip with eyelets. Returns the root empty; place and rotate that."""
    root = empty(name, (0, 0, 0), coll, "PLAIN_AXES", 0.006)
    leather = []
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.0033, radius2=0.0029, depth=0.0105,
                                    location=(-0.0018, 0, 0.0085))
    leather.append(bpy.context.active_object)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0, location=(0.0024, 0, 0.0031))
    toe = bpy.context.active_object
    toe.scale = (0.0068, 0.0033, 0.0029)
    leather.append(toe)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1.0, location=(-0.0022, 0, 0.0036))
    heel = bpy.context.active_object
    heel.scale = (0.0036, 0.0033, 0.0034)
    leather.append(heel)
    for o in leather:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in leather:
        o.select_set(True)
    bpy.context.view_layer.objects.active = leather[0]
    bpy.ops.object.join()
    body = bpy.context.active_object
    body.name = f"{name}_leather"
    body.data.materials.append(M["boot_leather"])
    for poly in body.data.polygons:
        poly.use_smooth = True
    sub = body.modifiers.new("soft", "SUBSURF")
    sub.levels, sub.render_levels = 1, 2
    link(body, coll)
    body.parent = root
    # folded cuff
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0031, minor_radius=0.0008, major_segments=24, minor_segments=8,
                                     location=(-0.0018, 0, 0.0136))
    cuff = bpy.context.active_object
    cuff.name = f"{name}_cuff"
    cuff.data.materials.append(M["boot_leather"])
    for poly in cuff.data.polygons:
        poly.use_smooth = True
    link(cuff, coll)
    cuff.parent = root
    # lugged sole + heel step (dark rubber)
    parts = [box(f"{name}_sole", (0.0132, 0.0062, 0.0011), (0.0012, 0, 0.00055), M["black"], coll),
             box(f"{name}_heel", (0.0040, 0.0060, 0.0012), (-0.0033, 0, 0.0015), M["black"], coll)]
    for k in range(5):
        parts.append(box(f"{name}_lug_{k}", (0.0007, 0.0058, 0.0004), (-0.004 + k * 0.0021, 0, 0.0001), M["black"], coll))
    # lace strip and eyelets down the front of the shaft
    parts.append(box(f"{name}_laces", (0.0005, 0.0014, 0.0085), (0.0013, 0, 0.0085), M["black"], coll,
                     rot=(0, math.radians(-4), 0)))
    for k in range(4):
        parts.append(sphere(f"{name}_eyelet_{k}", 0.00032, (0.00145, (-1) ** k * 0.0009, 0.0055 + (k // 2) * 0.0035 + (k % 2) * 0.0017),
                            M["metal_dull"], coll, segs=8))
    for o in parts:
        o.parent = root
    return root


def build_prize_chute(C, M):
    """A real hole in the diorama bed at CHUTE_XY: open-topped glass surround, dark shaft down through the
    cabinet body to the pickup door, so the claw can drop the tower INTO the machine (topi, 2026-11-12)."""
    from mathutils import Vector
    cab = bpy.data.collections["CABINET"]
    cx, cy = CHUTE_XY
    hw = CHUTE_HOLE / 2
    # anything of the miniature city standing where the hole goes is removed first
    gone = []
    for o in list(bpy.data.collections["DIORAMA"].all_objects):
        try:
            o.name
        except ReferenceError:      # already removed as a child of an earlier hit
            continue
        if o.type != "MESH" or o.name == "bed" or o.parent is not None:
            continue
        xs = [(o.matrix_world @ Vector(b)).x for b in o.bound_box]
        ys = [(o.matrix_world @ Vector(b)).y for b in o.bound_box]
        if max(xs) - min(xs) > 0.3 or max(ys) - min(ys) > 0.3:   # the fog box and other bed-wide volumes stay
            continue
        if min(xs) < cx + hw + 0.01 and max(xs) > cx - hw - 0.01 and min(ys) < cy + hw + 0.01 and max(ys) > cy - hw - 0.01:
            gone.append(o.name)
            for ch in list(o.children_recursive):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(o, do_unlink=True)
    print("prize chute: cleared", gone)
    # cut the opening through the bed and the cabinet body below it
    cutter = box("chute_cutter", (CHUTE_HOLE, CHUTE_HOLE, BED_Z), (cx, cy, BED_Z / 2 + CHUTE_BOTTOM_Z / 2 + 0.02), M["black"], cab)
    cutter.scale.z = 1.0
    for name in ("bed", "cab_body"):
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        mod = ob.modifiers.new("chute_hole", "BOOLEAN")
        mod.operation, mod.object = "DIFFERENCE", cutter
        try:
            mod.solver = "EXACT"
        except Exception:
            pass
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    # shaft: four dark steel walls with a lip, down to the tray
    depth = BED_Z - CHUTE_BOTTOM_Z
    zc = CHUTE_BOTTOM_Z + depth / 2
    t = 0.006
    for nm, size, off in (("n", (CHUTE_HOLE + 2 * t, t, depth), (0, hw + t / 2)), ("s", (CHUTE_HOLE + 2 * t, t, depth), (0, -hw - t / 2)),
                          ("e", (t, CHUTE_HOLE, depth), (hw + t / 2, 0)), ("w", (t, CHUTE_HOLE, depth), (-hw - t / 2, 0))):
        box(f"chute_shaft_{nm}", size, (cx + off[0], cy + off[1], zc), M["black"], cab)
    # sloped floor at the bottom steering prizes forward to the pickup door
    box("chute_ramp", (CHUTE_HOLE, CHUTE_HOLE * 1.25, 0.006), (cx, cy - 0.03, CHUTE_BOTTOM_Z + 0.04), M["cab_trim"], cab,
        rot=(math.radians(-32), 0, 0))
    # open-topped acrylic surround on the bed with a lit rim (it reads as "the hole" from the reveal shots)
    gh = 0.06
    for nm, size, off in (("n", (CHUTE_HOLE + 0.012, 0.004, gh), (0, hw + 0.004)), ("s", (CHUTE_HOLE + 0.012, 0.004, gh), (0, -hw - 0.004)),
                          ("e", (0.004, CHUTE_HOLE + 0.012, gh), (hw + 0.004, 0)), ("w", (0.004, CHUTE_HOLE + 0.012, gh), (-hw - 0.004, 0))):
        box(f"prize_chute_glass_{nm}", size, (cx + off[0], cy + off[1], BED_Z + 0.005 + gh / 2), M["glass"], cab)
        rim = (size[0], size[1], 0.004)
        box(f"prize_chute_rim_{nm}", rim, (cx + off[0], cy + off[1], BED_Z + 0.005 + gh), M["neon_cyan"], cab)
    # pickup opening: a real cavity in the cabinet front (S15c looks in at the tower lying in the tray)
    px, pz0, pz1, py0, py1 = cx, 0.175, 0.305, -0.52, -0.37
    pw = 0.20      # tower lying in the tray is ~0.15 long: keep clear of both side walls
    pocket = box("pickup_cutter", (pw, py1 - py0, pz1 - pz0), (px, (py0 + py1) / 2, (pz0 + pz1) / 2), M["black"], cab)
    ob = bpy.data.objects["cab_body"]
    mod = ob.modifiers.new("pickup_pocket", "BOOLEAN")
    mod.operation, mod.object = "DIFFERENCE", pocket
    try:
        mod.solver = "EXACT"
    except Exception:
        pass
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(pocket, do_unlink=True)
    t = 0.004
    box("pickup_back", (pw, t, pz1 - pz0), (px, py1 + t / 2, (pz0 + pz1) / 2), M["metal_dull"], cab)
    box("pickup_ceiling", (pw, py1 - py0, t), (px, (py0 + py1) / 2, pz1 - t / 2), M["black"], cab)
    for sx in (-1, 1):
        box(f"pickup_side_{sx:+d}", (t, py1 - py0, pz1 - pz0), (px + sx * (pw / 2 - t / 2), (py0 + py1) / 2, (pz0 + pz1) / 2), M["cab_trim"], cab)
    # the chute ramp drops into the pocket through a slot in its ceiling
    box("pickup_slot_lip", (pw - 0.02, 0.006, 0.006), (px, -0.40, pz1 - 0.006), M["metal_dull"], cab)
    # smoked flap hinged at the top, pushed open inward
    hinge = empty("pickup_flap_hinge", (px, -0.506, pz1 - 0.004), cab, "PLAIN_AXES", 0.02)
    flap = box("pickup_flap", (pw - 0.01, 0.003, 0.12), (0, 0, -0.06), M["glass"], cab)
    flap.parent = hinge
    hinge.rotation_euler = (math.radians(80), 0, 0)    # tucked under the ceiling: clears the tower lying in the tray
    # small warm lamp inside so the prize reads from outside
    L = bpy.data.lights.new("L_pickup_tray", "POINT")
    L.energy, L.color, L.shadow_soft_size = 6.0, (1.0, 0.75, 0.45), 0.03
    lo = bpy.data.objects.new(L.name, L)
    lo.location = (px, -0.42, pz1 - 0.02)
    cab.objects.link(lo)
    # soft cool fill on the lower cabinet front: S15c looks at it from knee height and every arcade light
    # points down at the floor, so the casing round the pickup went pure black (render4 check)
    L = bpy.data.lights.new("L_cab_front_low", "AREA")
    L.energy, L.color, L.size = 25.0, (0.55, 0.7, 1.0), 0.6
    lo = bpy.data.objects.new(L.name, L)
    lo.location = (0.35, -1.15, 0.45)
    lo.rotation_euler = (math.radians(90), 0, 0)     # area light faces -Z by default: turn it to face +Y (the cabinet)
    cab.objects.link(lo)
    # black void just below the lip so the shaft reads as deep even under the arcade lights
    box("chute_void", (CHUTE_HOLE, CHUTE_HOLE, 0.002), (cx, cy, BED_Z - 0.12), M["black"], cab)


def build_stairwell(dio, M, hero, roof_tiles):
    """Hollow stair shed + a real stairwell behind the rooftop door (1:60): the door frame opens onto a
    landing, a flight drops away from the door, turns at a half-landing and keeps going into the dark.
    Barricade boards the horde smashed through, a flickering caged lamp, pipes, fuse box, clutter."""
    rnd = random.Random(SEED + 41)
    sx, sy = SHED_XY[0], SHED_XY[1] + 0.005            # shed centre
    W, D, H, T = 0.08, 0.06, 0.05, 0.003                # outer size + wall thickness
    x0, x1, y0, y1 = sx - W / 2, sx + W / 2, sy - D / 2, sy + D / 2
    dx0, dx1, dz = DOOR_XY[0] - 0.0125, DOOR_XY[0] + 0.0125, 0.039   # door opening
    wall = M["parapet"]
    # shell: back, sides, front split around the doorway
    box("stair_shed_back", (W, T, H), (sx, y1 - T / 2, ROOF_Z + H / 2), wall, dio)
    box("stair_shed_west", (T, D, H), (x0 + T / 2, sy, ROOF_Z + H / 2), wall, dio)
    box("stair_shed_east", (T, D, H), (x1 - T / 2, sy, ROOF_Z + H / 2), wall, dio)
    box("stair_shed_front_l", (dx0 - x0, T, H), ((x0 + dx0) / 2, y0 + T / 2, ROOF_Z + H / 2), wall, dio)
    box("stair_shed_front_r", (x1 - dx1, T, H), ((x1 + dx1) / 2, y0 + T / 2, ROOF_Z + H / 2), wall, dio)
    box("stair_shed_lintel", (dx1 - dx0, T, H - dz), ((dx0 + dx1) / 2, y0 + T / 2, ROOF_Z + dz + (H - dz) / 2), wall, dio)
    box("stair_shed_ceiling", (W - 2 * T, D - 2 * T, 0.002), (sx, sy, ROOF_Z + H - 0.001), M["concrete"], dio)
    # cut the shaft through the roof slab and the hero block
    DEPTH = 0.085
    ix0, ix1, iy0, iy1 = x0 + T, x1 - T, y0 + T, y1 - T
    bpy.ops.mesh.primitive_cube_add(size=1, location=(sx, (iy0 + iy1) / 2 + 0.003, ROOF_Z - DEPTH / 2 + 0.002))
    cutter = bpy.context.active_object
    cutter.name = "stairwell_cutter"
    cutter.scale = (ix1 - ix0, iy1 - iy0 - 0.006 + 0.0001, DEPTH + 0.004)
    for target in (hero, roof_tiles):
        md = target.modifiers.new("stairwell_hole", "BOOLEAN")
        md.operation, md.object = "DIFFERENCE", cutter
        try:
            md.solver = "EXACT"
        except TypeError:
            pass
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    sh_y0 = iy0 + 0.0035                                 # narrow threshold so the first steps show from the doorway
    shaft = M["concrete"]
    box("shaft_wall_back", (ix1 - ix0, 0.001, DEPTH), (sx, iy1 - 0.0005, ROOF_Z - DEPTH / 2), shaft, dio)
    box("shaft_wall_front", (ix1 - ix0, 0.001, DEPTH), (sx, sh_y0 + 0.0005, ROOF_Z - DEPTH / 2), shaft, dio)
    box("shaft_wall_west", (0.001, iy1 - sh_y0, DEPTH), (ix0 + 0.0005, (sh_y0 + iy1) / 2, ROOF_Z - DEPTH / 2), shaft, dio)
    box("shaft_wall_east", (0.001, iy1 - sh_y0, DEPTH), (ix1 - 0.0005, (sh_y0 + iy1) / 2, ROOF_Z - DEPTH / 2), shaft, dio)
    box("shaft_floor", (ix1 - ix0, iy1 - sh_y0, 0.001), (sx, (sh_y0 + iy1) / 2, ROOF_Z - DEPTH), M["black"], dio)
    # straight flight that drops AWAY from the door (+Y), so the treads line up in the doorway view,
    # ending on a bottom landing along the back wall that turns west into the dark
    box("stair_landing_top", (dx1 - dx0 + 0.004, sh_y0 - iy0 + 0.0005, 0.002), ((dx0 + dx1) / 2, (iy0 + sh_y0) / 2, ROOF_Z + 0.001), M["concrete"], dio)
    rise, run = 0.0028, 0.0065                          # shallower than the eye line from the door, so no tread hides behind the lip
    fx0, fx1 = dx0 - 0.002, dx1 + 0.002                 # flight as wide as the door + a little
    yl0 = iy1 - 0.013                                   # bottom landing starts here
    n1 = int((yl0 - sh_y0) / run)
    for k in range(n1):
        z = ROOF_Z - (k + 1) * rise
        y = sh_y0 + k * run
        box(f"stair_a_{k}", (fx1 - fx0, run, 0.0016), ((fx0 + fx1) / 2, y + run / 2, z + 0.0008), M["concrete"], dio)
        box(f"stair_a_{k}_nose", (fx1 - fx0, 0.0008, 0.0004), ((fx0 + fx1) / 2, y + 0.0004, z + 0.0017), M["hazard_yellow"], dio)   # worn safety paint so each tread reads from the door
        box(f"stair_a_{k}_riser", (fx1 - fx0, 0.0006, rise), ((fx0 + fx1) / 2, y, z + rise / 2 + 0.0016), M["concrete"], dio)
    zl = ROOF_Z - n1 * rise
    yl0 = sh_y0 + n1 * run
    box("stair_bottom_landing", (ix1 - ix0, iy1 - yl0, 0.002), (sx, (yl0 + iy1) / 2, zl + 0.001), M["concrete"], dio)
    for side, x_ in enumerate((fx0 - 0.0006, fx1 + 0.0006)):   # stringers under both edges
        box(f"stair_stringer_{side}", (0.0012, yl0 - sh_y0, rise * 2), (x_, (sh_y0 + yl0) / 2, (ROOF_Z + zl) / 2 - rise), M["concrete"], dio,
            rot=(math.atan2(ROOF_Z - zl, yl0 - sh_y0), 0, 0))
    for k in range(4):   # next flight starts down to the west along the back wall, into the dark
        box(f"stair_b_{k}", (run, iy1 - yl0 - 0.002, 0.0016), (fx0 - 0.004 - (k + 0.5) * run, (yl0 + iy1) / 2, zl - (k + 1) * rise + 0.0008), M["concrete"], dio)
    # handrails down both sides + newels
    for side, x_ in enumerate((fx0 - 0.0008, fx1 + 0.0008)):
        tube(f"stair_rail_{side}", [(x_, sh_y0, ROOF_Z + 0.009), (x_, yl0, zl + 0.009)], 0.00035, M["rust"], dio)
        for j, (yy, zz) in enumerate([(sh_y0, ROOF_Z), (yl0, zl)]):
            cyl(f"stair_newel_{side}_{j}", 0.0005, 0.009, (x_, yy, zz + 0.0045), M["rust"], dio, verts=6)
        for j in range(1, n1, 2):
            yy, zz = sh_y0 + j * run, ROOF_Z - j * rise
            cyl(f"stair_baluster_{side}_{j}", 0.00018, 0.008, (x_, yy, zz + 0.0035), M["rust"], dio, verts=4)
    # smashed barricade: boards still nailed on one side of the frame, the rest thrown on the landing
    for k in range(3):
        box(f"barricade_board_hang_{k}", (0.014, 0.0008, 0.0025), (dx0 + 0.006, iy0 + 0.001, ROOF_Z + 0.012 + k * 0.009), M["wood_old"], dio,
            rot=(0, rnd.uniform(-0.6, -0.2), 0))
        cyl(f"barricade_nail_{k}", 0.0002, 0.001, (dx0 + 0.0015, iy0 + 0.0005, ROOF_Z + 0.012 + k * 0.009), M["metal_dull"], dio, verts=4, rot=(math.pi / 2, 0, 0))
    for k in range(2):   # thrown down the stairs: they ended up on the bottom landing
        box(f"barricade_board_floor_{k}", (0.014, 0.0026, 0.0008), (ix1 - 0.009, yl0 + 0.004 + k * 0.004, zl + 0.0025 + k * 0.001),
            M["wood_old"], dio, rot=(rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 1.3 + rnd.uniform(-0.2, 0.2)))
    # lighting: flickering caged lamp on the back wall, bare bulb hanging over the stairs, glow from below
    wall_lamp("stair_lamp", (sx + 0.012, iy1 - 0.0004, ROOF_Z + 0.036), (0, -1), M, dio, glow="stair_lamp_flicker", light=None)
    sl = point_light("L_stair_lamp", (sx + 0.012, iy1 - 0.008, ROOF_Z + 0.033), 0.05, (0.45, 1.0, 0.55), dio, 0.002)
    r = random.Random(sum(map(ord, "stair_lamp")))
    fr = 1
    while fr < 60 * FPS:
        for e, d in ((0.05, r.randint(30, 90)), (0.004, r.randint(2, 5)), (0.05, r.randint(2, 4)), (0.0, r.randint(3, 8))):   # same stutter as the lamp glass
            sl.data.energy = e
            sl.data.keyframe_insert("energy", frame=fr)
            fr += d
    for fc in fcurves_of(sl.data):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"
    bx, by = (fx0 + fx1) / 2, sh_y0 + n1 * run * 0.45   # bare bulb hangs over the middle of the flight so the treads catch light
    cyl("stair_bulb_cord", 0.00012, 0.016, (bx, by, ROOF_Z + H - 0.010), M["cable"], dio, verts=4)
    sphere("stair_bulb", 0.0012, (bx, by, ROOF_Z + H - 0.0195), M["bulb_warm"], dio, segs=10, scale=(1, 1, 1.3))
    point_light("L_stair_bulb", (bx, by, ROOF_Z + H - 0.023), 0.16, (1.0, 0.7, 0.4), dio, 0.002)
    point_light("L_stair_below", (sx - 0.02, sh_y0 + 0.01, ROOF_Z - 0.06), 0.12, (0.3, 0.9, 0.5), dio, 0.01)
    # services on the inside walls: riser pipes, conduit, an open fuse box, a fire extinguisher on its side
    for k, px in enumerate((ix0 + 0.0022, ix0 + 0.0048)):
        cyl(f"stair_riser_pipe_{k}", 0.0009 - k * 0.0002, H + DEPTH - 0.01, (px, iy1 - 0.0025, ROOF_Z + (H - DEPTH) / 2), M["rust"], dio, verts=8)
    tube("stair_conduit", [(ix1 - 0.0008, iy1 - 0.004, ROOF_Z + H - 0.004), (ix1 - 0.0008, iy0 + 0.008, ROOF_Z + H - 0.004),
                           (ix1 - 0.0008, iy0 + 0.008, ROOF_Z + 0.026)], 0.0003, M["metal_dull"], dio)
    box("stair_fusebox", (0.0018, 0.010, 0.013), (ix1 - 0.001, iy0 + 0.009, ROOF_Z + 0.019), M["metal_dull"], dio)
    box("stair_fusebox_door", (0.010, 0.0006, 0.013), (ix1 - 0.006, iy0 + 0.0035, ROOF_Z + 0.019), M["metal_dull"], dio, rot=(0, 0, 0.5))
    for k in range(3):
        box(f"stair_fuse_{k}", (0.0006, 0.0015, 0.0025), (ix1 - 0.0021, iy0 + 0.006 + k * 0.003, ROOF_Z + 0.020), M["black"], dio)
    cyl("stair_extinguisher", 0.0016, 0.0085, (ix1 - 0.006, iy1 - 0.004, zl + 0.0036), M["hazard_red"], dio, verts=12, rot=(math.pi / 2, 0, 0.7))
    # debris: paper, a shoe, scattered bricks on the steps
    for k in range(10):
        if k % 2 == 0:   # on the treads
            step = rnd.randint(0, n1 - 1)
            x, y, z = rnd.uniform(fx0 + 0.002, fx1 - 0.002), sh_y0 + (step + 0.5) * run, ROOF_Z - (step + 1) * rise + 0.0017
        elif k % 4 == 1:  # threshold
            x, y, z = rnd.uniform(dx0, dx1), rnd.uniform(iy0 + 0.001, sh_y0), ROOF_Z + 0.0021
        else:             # bottom landing
            x, y, z = rnd.uniform(ix0 + 0.002, ix1 - 0.002), rnd.uniform(yl0 + 0.002, iy1 - 0.002), zl + 0.0021
        box(f"stair_debris_{k}", (0.004, 0.003, 0.0003) if k % 3 else (0.0032, 0.0016, 0.0011), (x, y, z),
            M["paper"] if k % 3 else M["brick"], dio, rot=(0, 0, rnd.uniform(0, 3)))
    box("stair_lost_shoe", (0.0028, 0.0055, 0.0025), (fx0 + 0.004, sh_y0 + 3.5 * run, ROOF_Z - 4 * rise + 0.0029), M["black"], dio, rot=(0, 0, 0.6))
    # scrawls on the inside walls (decal atlases, skipped if missing)
    for k, (kind, cell, size, loc, nrm) in enumerate([
            ("graffiti", 3, (0.012, 0.012), (ix0 + 0.0002, sy + 0.004, ROOF_Z + 0.030), (1, 0, 0)),
            ("graffiti", 9, (0.010, 0.010), (sx - 0.014, iy1 - 0.0002, ROOF_Z + 0.022), (0, -1, 0)),
            ("signs", 13, (0.006, 0.006), (ix1 - 0.0002, sy + 0.012, ROOF_Z + 0.032), (-1, 0, 0)),
            ("stains", 4, (0.012, 0.012), (sx, (yl0 + iy1) / 2, zl + 0.0022), (0, 0, 1))]):
        decal(f"stair_decal_{k}", kind, cell, size, loc, nrm, dio)


def build_diorama(C, M):
    dio = coll("DIORAMA", C["root"])
    rnd = random.Random(SEED)
    box("bed", (0.90, 0.90, 0.01), (0, 0, BED_Z), M["street"], dio)
    # ---- hero building: 3 storeys (3 m each at 1:60), shed back-left, tower back-right
    HB, HC = 0.36, (0, 0.05)
    hero = box("hero_building", (HB, HB, ROOF_Z - BED_Z), (HC[0], HC[1], (ROOF_Z + BED_Z) / 2), M["facade"], dio)
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
    roof_tiles = box("roof_tiles", (0.35, 0.35, 0.002), (0, 0.05, ROOF_Z + 0.001), M["roof_wet"], dio)
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
    build_stairwell(dio, M, hero, roof_tiles)
    box("stair_shed_roof", (0.088, 0.068, 0.004), (SHED_XY[0], SHED_XY[1] + 0.005, ROOF_Z + 0.052), M["parapet"], dio)
    for x in (-0.0135, 0.0135):
        box(f"door_frame_{x:+.3f}", (0.003, 0.003, 0.041), (DOOR_XY[0] + x, DOOR_XY[1] - 0.0005, ROOF_Z + 0.0205), M["metal_dull"], dio)
    box("door_frame_top", (0.030, 0.003, 0.003), (DOOR_XY[0], DOOR_XY[1] - 0.0005, ROOF_Z + 0.0405), M["metal_dull"], dio)
    hinge = empty("door_hinge", (DOOR_XY[0] - 0.012, DOOR_XY[1] - 0.001, ROOF_Z), dio)
    door = box("shed_door", (0.024, 0.002, 0.038), (0.012, 0, 0.019), M["door_green"], dio)
    door.parent = hinge
    dent_door(door)
    wall_lamp("door_lamp", (DOOR_XY[0], DOOR_XY[1] - 0.0004, ROOF_Z + 0.0455), (0, -1), M, dio, light=None)   # lit by L_door_green
    for i, (x, y) in enumerate([(0.05, 0.17), (0.05, -0.10), (0.15, 0.0)]):
        box(f"ac_unit_{i}", (0.022, 0.016, 0.016), (x, y, ROOF_Z + 0.008), M["metal_dull"], dio)
        box(f"ac_fan_{i}", (0.012, 0.012, 0.001), (x, y, ROOF_Z + 0.0165), M["ac_fan"], dio)
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
    # density fades out toward the top and the side walls: a uniform box showed a hard horizontal
    # edge across the backdrop print in S15 (render1 audit #40)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    fz = nt.nodes.new("ShaderNodeMapRange")
    fz.interpolation_type = "SMOOTHERSTEP"
    fz.inputs["From Min"].default_value, fz.inputs["From Max"].default_value = 1.0, 0.25
    nt.links.new(sep.outputs["Z"], fz.inputs["Value"])
    dens = fz.outputs["Result"]
    for ax in ("X", "Y"):
        d = nt.nodes.new("ShaderNodeMath")
        d.operation = "PINGPONG"          # 0 at both walls, 0.5 in the middle
        d.inputs[1].default_value = 0.5
        nt.links.new(sep.outputs[ax], d.inputs[0])
        fx = nt.nodes.new("ShaderNodeMapRange")
        fx.interpolation_type = "SMOOTHSTEP"
        fx.inputs["From Min"].default_value, fx.inputs["From Max"].default_value = 0.0, 0.12
        nt.links.new(d.outputs[0], fx.inputs["Value"])
        m = nt.nodes.new("ShaderNodeMath")
        m.operation = "MULTIPLY"
        nt.links.new(dens, m.inputs[0])
        nt.links.new(fx.outputs["Result"], m.inputs[1])
        dens = m.outputs[0]
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = 0.42
    nt.links.new(dens, k.inputs[0])
    nt.links.new(k.outputs[0], vol.inputs["Density"])
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
    # pivot +Y points along a+90 deg in plan, so the fingers sit at 0 / 120 / 240 deg: the S07-S10 cameras (about -62 deg)
    # look into the gap between two fingers instead of straight down one (render2 check: a finger seen end-on read
    # as a rod through the tank)
    for i, a in enumerate((-90, 30, 150)):
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
    # S01a, frame-locked to the rin_door_slam cells (film frames; S01a is before any STORY_MAP stretch):
    # a first shoulder hit rattles it (f4), the second bursts it open (f7, cell 1) and it bangs into the wall,
    # she stumbles out, spins back to the hinge side and shoves the leaf shut with her fists (cells 7-8, f19-22), slam on f23
    for fr, deg in ((1, 0), (3, 0), (4, -6), (6, 0), (7, -20), (9, -128), (12, -100), (16, -107),
                    (18, -95), (20, -55), (22, -12), (23, 0), (25, -3), (27, 0)):
        key_rot(hinge, fr, (0, 0, math.radians(deg)))
    for sec in DOOR_BANGS_S:
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
    # pivot X rotation: + opens the fingers outward. At +4 deg (old "closed") the hooks sat ~1.2 cm inside the
    # tank and the old "open" (-38) crossed them through it. grip_a leaves ~3 mm between finger and wall.
    open_a, closed_a, grip_a = math.radians(35), math.radians(4), math.radians(13)
    HOLD = 0.135

    def prongs(frame, ang):
        for pv in pivots:
            key_rot(pv, frame, (ang, 0, pv.rotation_euler.z))

    def both(frame, x, y, cz, tilt=0.0):
        """Tower hangs from the claw: tilt swings it about the grip point, not about its own feet."""
        t = math.radians(tilt)
        key_loc(claw, frame, (x, y, cz))
        key_loc(tower, frame, (x, y + HOLD * math.sin(t), cz - HOLD * math.cos(t)))
        key_rot(tower, frame, (t, 0, 0))

    key_loc(claw, 1, (tx, ty, 1.80))
    prongs(1, closed_a)
    key_loc(claw, f(15.0), (tx, ty, 1.80))
    key_loc(claw, f(18.0), (tx, ty, 1.72))
    prongs(f(18.0), closed_a)
    prongs(f(19.0), open_a)
    key_loc(claw, f(22.0), (tx, ty, ROOF_Z + HOLD))
    prongs(f(23.0), open_a)
    prongs(f(24.0), grip_a)
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
    both(f(48.4), CHUTE_XY[0] + 0.03, CHUTE_XY[1] + 0.02, 1.70)
    # S15n: Nova's joystick nudges (cells 2-3 left, 5-6 forward) line it up over the hole
    both(f(49.75), CHUTE_XY[0] + 0.03, CHUTE_XY[1] + 0.02, 1.70)
    both(f(49.85), CHUTE_XY[0] + 0.004, CHUTE_XY[1] + 0.02, 1.70, -2)
    both(f(49.95), CHUTE_XY[0], CHUTE_XY[1] + 0.02, 1.70, 1)
    both(f(50.05), CHUTE_XY[0], CHUTE_XY[1] + 0.002, 1.70, 2)
    both(f(50.15), CHUTE_XY[0], CHUTE_XY[1], 1.70, -1)
    both(f(50.85), CHUTE_XY[0], CHUTE_XY[1], 1.70, 0)
    # S15m slam (50.5) -> S15d: the prongs spring open and the EMPTY tower drops down the prize hole: wrong prize
    prongs(f(50.85), grip_a)
    prongs(f(51.0), open_a)
    key_loc(claw, f(51.0), (CHUTE_XY[0], CHUTE_XY[1], 1.70))
    key_loc(claw, f(51.15), (CHUTE_XY[0], CHUTE_XY[1], 1.715))   # springs up a touch as the weight lets go
    key_loc(claw, f(51.4), (CHUTE_XY[0], CHUTE_XY[1], 1.70))
    z0 = 1.70 - HOLD
    t_open = 50.95
    drop = z0 - (BED_Z - 0.30)
    t_fall = math.sqrt(2 * drop / 9.81)                     # real gravity: ~0.43 s from the claw to inside the cabinet
    key_rot(tower, f(t_open), (0, 0, 0))
    for k in range(7):                                      # key the parabola so it accelerates instead of easing
        u = k / 6
        t = t_open + u * t_fall
        key_loc(tower, max(f(t), f(t_open) + k), (CHUTE_XY[0], CHUTE_XY[1], z0 - drop * u * u))
    key_rot(tower, f(t_open + t_fall), (math.radians(14), 0, math.radians(20)))   # catches the hole's lip as it goes
    # S15c: it tumbles out of the shaft into the pickup tray and settles on its side
    tray = PRIZE_TRAY
    # tower is ~0.115 tall x 0.07 wide; it ends lying on its side along X (feet left), centred on the tray
    for sec, (dx, dy, dz), (ry, rz) in ((51.69, (-0.02, 0.10, 0.12), (40, 20)), (51.80, (-0.045, 0.03, 0.06), (75, 15)),
                                        (51.90, (-0.055, 0.0, 0.035), (92, 10)), (52.0, (-0.055, 0.0, 0.039), (86, 10)),
                                        (52.15, (-0.055, 0.0, 0.035), (90, 10))):
        key_loc(tower, f(sec), (tray[0] + dx, tray[1] + dy, tray[2] + dz))
        key_rot(tower, f(sec), (0, math.radians(ry), math.radians(rz)))
    key_loc(tower, R - 1, (tray[0] - 0.055, tray[1], tray[2] + 0.035))
    key_rot(tower, R - 1, (0, math.radians(90), math.radians(10)))
    for fc in fcurves_of(tower):                            # the free fall is keyed densely: no Bezier easing on it
        for kp in fc.keyframe_points:
            if f(t_open) <= kp.co.x <= f(51.69):
                kp.interpolation = "LINEAR"
    # the hand in S15n/S15m drives the real controls too (seen in S15b and whenever the close-up art is missing)
    jb, bg = bpy.data.objects.get("joystick_ball"), bpy.data.objects.get("button_grab")
    if jb:
        b0 = tuple(jb.location)
        for sec, dx, dy in ((49.75, 0, 0), (49.83, -0.012, 0), (49.95, 0, 0), (50.03, 0, 0.012), (50.15, 0, 0), (50.3, 0, 0)):
            key_loc(jb, f(sec), (b0[0] + dx, b0[1] + dy, b0[2] - 0.002 * (dx != 0 or dy != 0)))
    if bg:
        g0 = tuple(bg.location)
        a5 = f(50.3)
        for off, dz in ((0, 0), (3, 0), (4, -0.008), (8, -0.008), (10, 0)):
            key_loc(bg, a5 + off, (g0[0], g0[1], g0[2] + dz))
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
        for frac, cm, _am in SHOT_MID.get(sid, []):
            key_loc(face, f(a + (b - a) * frac), cm)
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
        ("rin_backing_away",  "rin_backing_away.png",  ["S01b_door_bang", "S02_establish"], (0.0, -0.03, ROOF_Z), None),
        ("rin_boot_grab",     "rin_boot_grab.png",     ["S03_lost_boot"],                 (TOWER_XY[0], TOWER_XY[1] - 0.052, ROOF_Z), None),
        ("rin_climb_back",    "rin_climb_back.png",    ["S04a_run_climb", "S04b_climb_escape"], (0.0, -0.0385, 0.035), tower_root),
        ("rin_cling_scared",  "rin_cling_scared.png",  ["S05_pile_topdown"],              (0.0, -0.0385, 0.075), tower_root),
        ("rin_look_up",       "rin_look_up.png",       ["S06_light_above"],               (0.0, -0.0385, 0.075), tower_root),
        ("rin_cling_hope",    "rin_cling_hope.png",    ["S07_claw_descends", "S08_grip_lift", "S09a_false_hope", "S09b_hope_low"], (0.0, -0.0385, 0.075), tower_root),
        ("rin_slip_shock",    "rin_slip_shock.png",    ["S10_slip"],                      (0.0, -0.0385, 0.07), tower_root),
        ("rin_reset_lookup",  "rin_reset_lookup.png",  ["S17b_reset_loop"],               (0.0, -0.01, ROOF_Z), None),
    ]
    for name, fn, shots, loc, parent in defs:
        o = sprite(name, fn, RIN_H, loc, ch, face, RIN, parent=parent, base_mat=None if parent else base)
        rng = [shot_rng[s] for s in shots]
        key_visible(o, rng)
        animate_named(o, name, rng)
        rin[name] = o
    # S02: the backing-away cycle actually travels — about two body lengths away from the door,
    # stumbling faster at the end so the S03 fall reads as a trip
    ba = rin["rin_backing_away"]
    for sec, xy in RIN_TRACK:
        if 1.2 <= sec <= 4.0:
            key_loc(ba, f(sec), (xy[0], xy[1], ROOF_Z))
    set_interp(ba, "LINEAR", "location")
    # S01a burst, S02b chase run, S02c look-back: new sheets; until they land, the ladder run stands in
    for name, sid in (("rin_door_slam", "S01a_door_burst"), ("rin_run_chase", "S02b_chase_low"),
                      ("rin_look_back", "S02c_look_back")):
        key = name
        while not os.path.isfile(os.path.join(ASSET_DIR, key + "_sheet.png")) and key in SPRITE_FALLBACK:
            key = SPRITE_FALLBACK[key]
        m, asp = load_sheet(key, RIN, ANIM[key], mat_name="M_" + name)
        # sprite() multiplies by SHEET_SCALE[name]; a stand-in sheet needs its own scale instead
        o = sprite(name, name + ".png", RIN_H * SHEET_SCALE.get(key, 1.0) / SHEET_SCALE.get(name, 1.0), (0, 0, ROOF_Z),
                   ch, face, RIN, aspect=asp, base_mat=base, material=m)
        a, b = shot_rng[sid]
        if name == "rin_door_slam":      # behind the shut door until it bursts open on f7 (loop seam stays clean)
            a = f(0.25)
        key_visible(o, [(a, b)])
        animate_sheet(m, [(a, b)], 0, TIMING.get(key), False)
        lo, hi = story_to_film((a - 1) / FPS), story_to_film(b / FPS)
        pts = [(sec, xy) for sec, xy in RIN_TRACK if lo - 1e-6 <= sec <= hi + 1e-6]
        for sec, xy in pts:
            key_loc(o, f(sec), (xy[0], xy[1], ROOF_Z))
        set_interp(o, "LINEAR", "location")
        rin[name] = o
    # S04: the climb cycle rises up the ladder (about one rung per cycle) to where she clings in S05
    cb, (a4, b4a) = rin["rin_climb_back"], shot_rng["S04a_run_climb"]
    a4b, b4 = shot_rng["S04b_climb_escape"]
    run_end = a4 + sum(h for _, h in TIMING["rin_run_to_ladder"])
    key_loc(cb, run_end, (0.0, -0.0385, 0.008))
    key_loc(cb, b4a, (0.0, -0.0385, 0.016))     # two rungs up when they grab her ankle (cut to S03)
    key_loc(cb, a4b, (0.0, -0.0385, 0.004))     # back on the bottom rung after the boot is torn off
    key_loc(cb, a4b + 12, (0.0, -0.0385, 0.008)) # yanked once more...
    key_loc(cb, b4, (0.0, -0.0385, 0.072))      # ...then a frantic climb out of reach
    set_interp(cb, "LINEAR", "location")
    for prop in ("hide_render", "hide_viewport"):   # replace the full-shot visibility keyed above
        cb.keyframe_delete(prop, frame=a4)
    key_visible(cb, [(a4b, b4)])     # S04a ends on the run sheet's leap onto the ladder (climb_back has her
                                     # left foot bare, which only becomes true once S03 tears the boot off)
    run = sprite("rin_run_to_ladder", "rin_run_to_ladder.png", RIN_H, (0, 0, ROOF_Z), ch, face, RIN, base_mat=base)
    key_loc(run, a4, (TOWER_XY[0] - 0.040, TOWER_XY[1] - 0.090, ROOF_Z))
    key_loc(run, run_end - 1, (TOWER_XY[0], TOWER_XY[1] - 0.043, ROOF_Z))
    set_interp(run, "LINEAR", "location")
    key_loc(run, b4a, (TOWER_XY[0], TOWER_XY[1] - 0.043, ROOF_Z + 0.006))   # hangs on, feet off the roof
    key_visible(run, [(a4, b4a)])
    animate_named(run, "rin_run_to_ladder", [(a4, b4a)])
    rin["rin_run_to_ladder"] = run
    # falling: leaves the ladder (world pos of the hanging tower) and lands on the roof at PIN_XY
    fall = sprite("rin_falling", "rin_falling.png", RIN_H, (0, 0, 0), ch, face, RIN)
    tx, ty = TOWER_XY
    s11a, s11b = shot_rng["S11_fall"]
    key_loc(fall, s11a, (tx, ty - 0.041, ROOF_Z + 0.42 - 0.135 + 0.07))
    key_loc(fall, f(32.6), (tx - 0.01, ty - 0.05, ROOF_Z + 0.34))      # slow-mo hang
    key_loc(fall, s11b, (PIN_XY[0], PIN_XY[1], ROOF_Z + 0.002))
    for fc in fcurves_of(fall):     # gravity: ease out of the hang, no ease into the ground
        for kp in fc.keyframe_points:
            if int(kp.co.x) == f(32.6):
                kp.interpolation, kp.easing = "QUAD", "EASE_IN"
    key_visible(fall, [shot_rng["S11_fall"]])
    animate_named(fall, "rin_falling", [shot_rng["S11_fall"]])
    rin["rin_falling"] = fall
    imp = sprite("rin_impact", "rin_impact.png", RIN_H, (PIN_XY[0], PIN_XY[1], ROOF_Z), ch, face, RIN)
    key_visible(imp, [shot_rng["S12_impact"]])
    animate_named(imp, "rin_impact", [shot_rng["S12_impact"]])
    # ---- S12b-S12d: surrounded -> ankle + hood grabbed, rolled face down -> pressed flat (sprite_list_v2.md)
    scoot = sprite("rin_scoot_back", "rin_scoot_back.png", RIN_H, (PIN_XY[0], PIN_XY[1], ROOF_Z), ch, face, RIN)
    sb = shot_rng["S12b_surrounded"]
    key_visible(scoot, [sb])
    animate_named(scoot, "rin_scoot_back", [sb])
    key_loc(scoot, sb[0], (PIN_XY[0] - 0.002, PIN_XY[1] - 0.003, ROOF_Z))   # scoots back toward the legs behind her
    key_loc(scoot, sb[1], (PIN_XY[0], PIN_XY[1], ROOF_Z))
    rin["rin_scoot_back"] = scoot
    grab = sprite("rin_grabbed_down", "rin_grabbed_down.png", PIN_SQ_H, (PIN_XY[0], PIN_XY[1], PIN_SQ_Z), ch, face, RIN)
    sc = shot_rng["S12c_grabbed"]
    key_visible(grab, [sc])
    animate_named(grab, "rin_grabbed_down", [sc])
    rin["rin_grabbed_down"] = grab
    # S12d takedown and the S13a/S14 pin: back zombies / Rin / front zombies on the same square canvas.
    # Only a hair of depth between them, so the hands stay on her (GPT drew the contact into the zombie layers).
    stack = [("back", +0.0008, (0.40, 0.30, 0.20)), ("rin", 0.0, RIN), ("contact", -0.0004, (0.0, 0.0, 0.0)),
             ("front", -0.0008, (0.30, 0.45, 0.40))]
    sd = shot_rng["S12d_pressed"]
    for part, dy, col in stack:
        name = "pin_takedown_" + part
        o = sprite(name, name + ".png", PIN_SQ_H, (PIN_XY[0], PIN_XY[1] + dy, PIN_SQ_Z), ch, face, col)
        key_visible(o, [sd])
        animate_named(o, name, [sd])
        if part == "contact":
            shadow_material(o)
        rin[name] = o
    # PINNED GROUP, visible until the reset (hidden during the face ECU, where the close-up sheet carries
    # the same struggle at face size). S14 picks the struggle up at cell 10 (eyes up) to continue S13b's last look.
    s13, s14 = shot_rng["S13a_pinned"], (shot_rng["S14_pullback"][0], R - 1)
    for part, dy, col in stack:
        name = "pin_layer_" + part
        o = sprite(name, name + ".png", PIN_SQ_H, (PIN_XY[0], PIN_XY[1] + dy, PIN_SQ_Z), ch, face, col)
        key_visible(o, [s13, s14])
        animate_named(o, name, [s13])
        animate_sheet(o.data.materials[0], [s14], 9, S14_PIN_TIMING)
        if part == "contact":
            shadow_material(o)
        rin[name] = o
    # Secondary motion on ones: the drawings change every 3 frames, the layers move every frame
    # (a few mm), so the tug / press / struggle reads as continuous force instead of a slideshow.
    for part, _dy, _col in stack:
        o = rin["pin_layer_" + part]
        secondary_motion(o, [(s13, 0), (s14, 9)], PIN_MOTION[part], cycle=36, vary=CYCLE_VARY)
        o = rin["pin_takedown_" + part]
        secondary_motion(o, [(sd, 0)], TAKEDOWN_MOTION[part], cycle=None)
    # Shared press beat: each time the front pair drives down, Rin's layer squashes under the weight
    # and springs back a touch (the camera thumps on the same frames, see PRESS_THUMPS).
    squash_motion(rin["pin_layer_rin"], [(s13, 0), (s14, 9)], PIN_SQUASH, cycle=36, vary=CYCLE_VARY)
    squash_motion(rin["pin_takedown_rin"], [(sd, 0)], TAKEDOWN_SQUASH, cycle=None)
    hand_cu = sprite("pin_hand_press", "pin_hand_press.png", 0.032, (PIN_XY[0], PIN_XY[1] - 0.013, ROOF_Z), ch, face, RIN)
    key_visible(hand_cu, [shot_rng["S13c_hand_press"]])
    animate_named(hand_cu, "pin_hand_press", [shot_rng["S13c_hand_press"]])
    rin["pin_hand_press"] = hand_cu
    face_cu = sprite("pin_face_closeup", "pin_face_closeup.png", 0.017, (PIN_XY[0], PIN_XY[1] - 0.013, ROOF_Z), ch, face, RIN)
    key_visible(face_cu, [shot_rng["S13b_pinned_face"]])
    animate_named(face_cu, "pin_face_closeup", [shot_rng["S13b_pinned_face"]])
    # S01: grey fingers squirming out of the gap on the door's free edge
    fingers = sprite("door_fingers", "door_fingers.png", 0.014,
                     (DOOR_XY[0] + 0.013, DOOR_XY[1] - 0.004, ROOF_Z + 0.010), ch, face, (0.45, 0.55, 0.45))
    key_visible(fingers, [shot_rng["S01b_door_bang"]])
    animate_named(fingers, "door_fingers", [shot_rng["S01b_door_bang"]])
    # (the old 3 mm "lost boot" box on the roof read as a red-brown brick at that blur - audit #8 - so it is
    #  gone; the boot stays in the zombie's hand on the rin_boot_grab sheet, and the prize tray keeps the callback)
    # Nova (real-world scale)
    NOVA = (0.55, 0.40, 0.78)
    nova_defs = [
        ("nova_back_joystick", "nova_back_joystick.png", ["S15_glass_reveal", "S15b_arcade_aisle"], (NOVA_XY[0], NOVA_XY[1], 0.0), NOVA_H),
        ("nova_profile_almost","nova_profile_almost.png",["S16_nova_almost"],  (NOVA_XY[0], NOVA_XY[1], 0.87), 0.75),  # waist-up art
        ("nova_hand_coin",     "nova_hand_coin.png",     ["S17a_coin"],        (0.26, -0.56, 0.69), 0.28),   # cut wrist below frame
    ]
    for name, fn, shots, loc, h in nova_defs:
        o = sprite(name, fn, h, loc, ch, face, NOVA, shape="hand" if "hand" in name else "figure")
        rng = [shot_rng[s] for s in shots]
        key_visible(o, rng)
        animate_named(o, name, rng)
    # S15n/S15m close-ups: the art draws the hand WITH the joystick / button (sprite_list_v4_door_nova.md),
    # so the 3D control it replaces is hidden for that shot. No art yet -> the shot just shows the keyed 3D controls.
    for name, sid, base_xyz, h, hide in (
            ("nova_joystick_hand", "S15n_nova_joystick", (-0.25, -0.58, 0.905), 0.26, ("joystick_ball", "joystick_shaft")),
            # topi: the button should be the MODELLED one -> hand-only sheet, the 3D button stays and presses.
            # The card sits 3 cm toward the lens (just in front of the dome's near edge, r 2.8 cm) and 1.2 cm
            # higher, so her palm lands ON the dome top (~0.928), not on the bezel's front edge.
            ("nova_button_hand", "S15m_nova_button", (-0.066, -0.602, 0.899), 0.276, ())):
        if not os.path.isfile(os.path.join(ASSET_DIR, name + "_sheet.png")):
            continue
        o = sprite(name, name + ".png", h, base_xyz, ch, face, NOVA, shape="hand")
        bs = o.data.materials[0].node_tree.nodes.get("Principled BSDF")
        if bs:   # Nova is a real person, not an acrylic print: no milky sheen under the arcade lights up close
            bs.inputs["Roughness"].default_value = 0.85
            bs.inputs["Specular IOR Level"].default_value = 0.15
            bs.inputs["Emission Strength"].default_value = 0.6    # the art's own colours win over the cyan/magenta arcade light
            if hasattr(o.data.materials[0], "surface_render_method"):
                o.data.materials[0].surface_render_method = "BLENDED"   # true soft alpha; dithered alpha stair-steps up close
            mr = next((n for n in o.data.materials[0].node_tree.nodes if n.type == "MAP_RANGE"), None)
            if mr:   # keep the soft (feathered) alpha edge up close instead of firming it into stair steps
                mr.inputs["From Max"].default_value = 1.0
        rng = [shot_rng[sid]]
        key_visible(o, rng)
        animate_named(o, name, rng)
        a, b = rng[0]
        for hn in hide:
            ob = bpy.data.objects.get(hn)
            if ob:
                key_visible(ob, [(1, a - 1), (b + 1, f(STORY_END))])
    return rin


# Rin's ground track through Act 1 (story s): out of the door, backing off, the chase run, the trip.
# The crowd's chasers follow it with a lag, so the horde visibly runs after her.
RIN_TRACK = [(0.0, (-0.110, 0.118)), (0.25, (-0.109, 0.108)), (0.55, (-0.110, 0.088)), (0.625, (-0.119, 0.073)), (0.71, (-0.133, 0.080)),
             # S01a: round the open leaf's free end (y 0.080), never through it, then on the hinge side
             # she shoves the leaf shut toward +X
             (0.79, (-0.124, 0.088)), (0.92, (-0.114, 0.092)), (1.15, (-0.105, 0.085)),
             (1.2, (-0.072, 0.066)), (2.5, (-0.062, 0.046)),
             (4.0, (-0.045, 0.027)), (5.0, (-0.015, 0.008)), (6.0, (0.025, 0.030)),
             (6.7, (TOWER_XY[0] - 0.040, TOWER_XY[1] - 0.090)), (7.3, (TOWER_XY[0], TOWER_XY[1] - 0.052)),
             (9.8, (TOWER_XY[0], TOWER_XY[1] - 0.052)), (10.3, (TOWER_XY[0], TOWER_XY[1] - 0.043))]


def rin_at(sec):
    if sec <= RIN_TRACK[0][0]:
        return RIN_TRACK[0][1]
    for (s0, p0), (s1, p1) in zip(RIN_TRACK, RIN_TRACK[1:]):
        if sec <= s1:
            u = (sec - s0) / (s1 - s0)
            return (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)
    return RIN_TRACK[-1][1]


# S04: Rin sprints from mid-roof to the ladder. Zombies standing on that run (or between it and the
# high S04 lens) step aside for the shot, so the host's ray test hits her, not zombie_006/010/015.
RUN_PATH = [(0.025, 0.030), (TOWER_XY[0] - 0.040, TOWER_XY[1] - 0.090), (TOWER_XY[0], TOWER_XY[1] - 0.043)]
RUN_CLEAR = 0.026
RUN_WINDOW = (6.0, 12.3)
CHASE_END = 7.5            # chasers run after her until she reaches the ladder, then claw at its foot


def clear_of_run(x, y):
    """Push (x, y) out to RUN_CLEAR from the S04 run polyline; unchanged if already clear."""
    best = None
    for (ax, ay), (bx, by) in zip(RUN_PATH, RUN_PATH[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        px, py = ax + dx * t, ay + dy * t
        d = math.hypot(x - px, y - py)
        if best is None or d < best[0]:
            best = (d, px, py, dx, dy)
    d, px, py, dx, dy = best
    if d >= RUN_CLEAR:
        return x, y
    if d < 1e-6:                      # dead on the line: step off to its right-hand side
        n = math.hypot(dx, dy)
        ux, uy = dy / n, -dx / n
    else:
        ux, uy = (x - px) / d, (y - py) / d
    return px + ux * RUN_CLEAR, py + uy * RUN_CLEAR


def _pulse(c, start, length):
    """0 -> 1 -> 0 sine bump over [start, start+length) of the 24 fps cycle index c."""
    u = (c - start) / length
    return math.sin(math.pi * u) if 0.0 <= u < 1.0 else 0.0


# Per-frame offsets (dx, dy, dz in metres; +y = away from the lens) over the 36-frame pin cycle:
# cells 1-3 push up / press, 4-6 hair yanked + cry, 7-9 twist + kick, 10-12 sag and look up.
PIN_MOTION = {
    "back":  lambda c: (0.0002 * math.sin(c / 36 * math.tau),
                        0.0007 * _pulse(c, 9, 12) + 0.0003 * _pulse(c, 22, 8),          # yank the hood back
                        0.0005 * _pulse(c, 9, 12) + 0.00015 * math.sin(c / 18 * math.tau)),
    "rin":   lambda c: (0.00025 * _pulse(c, 18, 9) * math.sin(c * 2.1),                  # twist / kick shudder
                        0.0,
                        0.0004 * _pulse(c, 9, 10) - 0.0002 * _pulse(c, 30, 6)),        # head yanked up, sag down
    "front": lambda c: (0.0003 * _pulse(c, 18, 10) * math.sin(c * 1.3),
                        -0.0002 * _pulse(c, 0, 9),
                        -0.0005 * _pulse(c, 0, 9) - 0.0006 * _pulse(c, 27, 9)           # lean in and press down
                        + 0.0002 * _pulse(c, 9, 9)),
}
PIN_MOTION["contact"] = PIN_MOTION["front"]      # the baked shadow travels with the hands that cast it


def PIN_SQUASH(c):
    """(scale x, scale z) of Rin's pin layer: squashed on the two presses (c 0-9, 27-36), small rebound after."""
    p = _pulse(c, 0, 9) + _pulse(c, 27, 9)
    r = _pulse(c, 9, 6)
    return 1.0 + 0.015 * p - 0.006 * r, 1.0 - 0.035 * p + 0.012 * r


def TAKEDOWN_SQUASH(c):
    p, r = _pulse(c, 8, 7), _pulse(c, 15, 6)
    return 1.0 + 0.02 * p - 0.008 * r, 1.0 - 0.05 * p + 0.015 * r


# S12d takedown (24 frames): the front pair slams down at frame 8 (cell 4), she is driven into the tiles
TAKEDOWN_MOTION = {
    "back":  lambda c: (0.0, 0.0006 * _pulse(c, 6, 10), 0.0004 * _pulse(c, 6, 10)),
    "rin":   lambda c: (0.0, 0.0, -0.0004 * _pulse(c, 8, 6)),
    "front": lambda c: (0.0, 0.0, 0.0006 * _pulse(c, 0, 8) - 0.0010 * _pulse(c, 8, 7)),
}
TAKEDOWN_MOTION["contact"] = TAKEDOWN_MOTION["front"]
# Camera thumps on the press peaks: shot -> [(frame offset into the shot, strength 0-1)].
# S13a runs the pin clock from cell 1 (presses peak at c 4 and 31); S14 enters at cell 10 (c 27).
PRESS_THUMPS = {
    "S03_lost_boot":  [(1, 1.0), (30, 0.6), (44, 0.8)],       # dragged off the ladder, the pull, the boot rips off
    "S04b_climb_escape": [(12, 0.7)],                          # yanked once more before she climbs clear
    "S12b_surrounded": [(9, 1.2)],                             # the horde lands on her (pounce keys in build_crowd)
    "S01b_door_bang": [(f(sec) - f(1.2) + 1, 0.8) for sec in DOOR_BANGS_S],   # each bang jolts the lens
    "S12d_pressed": [(11, 1.0)],
    "S13a_pinned":  [(4, 0.8), (31, 1.0)],
    "S13c_hand_press": [(1, 0.7), (5, 1.0)],      # the slam, then the hard press of cell 3
    "S14_pullback": [(4, 0.6), (13, 0.4)],
    "S01a_door_burst": [(7, 1.0), (23, 0.8)],      # shoulder bursts the door open, then she heaves it shut
    "S15m_nova_button": [(5, 9.0)],                # real-world scale: the palm slam (k scales the 1:60 amplitude)
}
THUMP_AMP = 0.0007


# S14 plays the pin loop more than once: every repeat changes force and in-cell rhythm so it never reads
# as the same 1.5 s again (each 3-cell beat still sums to 9 frames, so the motion stays on the drawings).
CYCLE_VARY = [1.0, 0.7, 1.25, 0.8, 1.1]
S14_PIN_TIMING = ([(i, 3) for i in range(1, 13)] +
                  [(1, 2), (2, 3), (3, 4), (4, 4), (5, 3), (6, 2), (7, 2), (8, 2), (9, 5), (10, 3), (11, 4), (12, 2)] +
                  [(1, 4), (2, 3), (3, 2), (4, 2), (5, 2), (6, 5), (7, 3), (8, 3), (9, 3), (10, 2), (11, 2), (12, 5)])


def squash_motion(o, ranges, fn, cycle=36, vary=None):
    """Key o's scale every frame inside each (range, phase_cells) with fn(cycle index) -> (sx, sz)."""
    for (a, b), phase in ranges:
        for fr in range(a, b + 1):
            c = fr - a + phase * 3
            k = vary[(c // cycle) % len(vary)] if (cycle and vary) else 1.0
            if cycle:
                c %= cycle
            sx, sz = fn(c)
            sx, sz = 1.0 + (sx - 1.0) * k, 1.0 + (sz - 1.0) * k
            o.scale = (sx, 1.0, sz)
            o.keyframe_insert("scale", frame=fr)
        o.scale = (1.0, 1.0, 1.0)
        o.keyframe_insert("scale", frame=b + 1)
    set_interp(o, "LINEAR", "scale")


def shadow_material(o):
    """Baked contact shadow: keep its soft alpha (no cut-out firming), no glow, matte."""
    nt = o.data.materials[0].node_tree
    for n in nt.nodes:
        if n.type == "MAP_RANGE":
            n.inputs["From Max"].default_value = 1.0
        elif n.type == "BSDF_PRINCIPLED":
            n.inputs["Emission Strength"].default_value = 0.0
            n.inputs["Roughness"].default_value = 1.0
            n.inputs["Specular IOR Level"].default_value = 0.0


def press_thumps(cam, a, b, thumps):
    """Add a short decaying jolt (mostly downward) at each press peak on top of the camera's own move."""
    fcs = {fc.array_index: fc for fc in fcurves_of(cam) if fc.data_path == "location"}
    if len(fcs) < 3:
        return
    frames = list(range(a, b))
    path = [[fcs[i].evaluate(fr) for i in range(3)] for fr in frames]
    for fr, loc in zip(frames, path):
        dx = dz = 0.0
        for off, k in thumps:
            t = fr - (a + off)
            if t >= 0:
                env = THUMP_AMP * k * math.exp(-t / 2.2)
                dz -= env * math.cos(t * 1.9)
                dx += 0.35 * env * math.sin(t * 2.7)
        key_loc(cam, fr, (loc[0] + dx, loc[1], loc[2] + dz))
    set_interp(cam, "LINEAR", "location")


def secondary_motion(o, ranges, fn, cycle=36, vary=None):
    """Key o's location every frame inside each (range, phase_cells) with base + fn(cycle index)."""
    base = o.location.copy()
    for (a, b), phase in ranges:
        for fr in range(a, b + 1):
            c = fr - a + phase * 3
            k = vary[(c // cycle) % len(vary)] if (cycle and vary) else 1.0
            if cycle:
                c %= cycle
            dx, dy, dz = (v * k for v in fn(c))
            key_loc(o, fr, (base.x + dx, base.y + dy, base.z + dz))
    set_interp(o, "LINEAR", "location")


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
                if pose == "run" and not os.path.isfile(os.path.join(ASSET_DIR, key + "_sheet.png")):
                    key, spec = f"zombie_{vname.lower()}_walk", ZOMBIE_ANIM["walk"]
                m, asp = load_sheet(key, col, spec, mat_name=f"M_zombie_{vname.lower()}_{pose}_ph{ph}")
                animate_sheet(m, [(1, R - 1)], phase=ph * 3)
                mats[(vname, pose, ph)] = (m, asp)
    tx, ty = TOWER_XY
    # 48, not 96: the first render read as a carpet of zombies. The first CHASERS burst out at 2.5 s and
    # run after Rin along her track (RIN_TRACK) with a lag; the rest stream out and head for the tower.
    n, CHASERS = 48, 12
    for i in range(n):
        vname, _ = variants[i % 4]
        spawn = 2.5 + (i / n) * 11.5 if i >= CHASERS else 2.5 + 0.12 * i
        if 5.0 < spawn < RUN_WINDOW[1]:   # nobody crosses her S04 run on the way out: they surge out after it
            spawn = RUN_WINDOW[1] + (spawn - 5.0) * 0.25
        ang = rnd.uniform(0, math.tau)
        rad = rnd.uniform(0.04, 0.14) if i > 20 else rnd.uniform(0.042, 0.06)   # >= tank radius + card: none under the tank
        gx = max(-0.165, min(0.165, tx + math.cos(ang) * rad - 0.03))
        gy = max(-0.115, min(0.215, ty + math.sin(ang) * rad - 0.05))
        pose = "climb" if rad < 0.048 else ("reach" if rad < 0.07 else "walk")   # climbers pile up the tower legs
        if i < CHASERS:
            pose = "reach"           # they end up clawing at her heels at the ladder foot
        m, asp = mats[(vname, pose, i % 3)]
        h = ZOMBIE_H * (1.25 if vname == "Z03_cop_brute" else rnd.uniform(0.93, 1.05))
        o = sprite(f"zombie_{i:03d}", None, h, (0, 0, 0), cr, face, (1, 1, 1), aspect=asp, parent=root,
                   base_mat=M["acrylic"], material=m, mesh_name=f"ME_{vname}_{pose}_{i % 3}_{h:.4f}")
        door = (DOOR_XY[0] + rnd.uniform(-0.01, 0.01), DOOR_XY[1] - 0.01, ROOF_Z)
        key_loc(o, 1, door)
        key_loc(o, f(spawn), door)
        rx, ry = clear_of_run(gx, gy)
        in_run = lambda sec: RUN_WINDOW[0] <= sec <= RUN_WINDOW[1]
        arrive = f(spawn) + rnd.randint(36, 70)
        if i < CHASERS:
            # chase: a separate RUNNING standee trails her track by `lag` seconds, never closer than `gap`
            # behind her, fanned sideways; at CHASE_END it hands over to this one (reach, at the ladder foot)
            rm, rasp = mats[(vname, "run", i % 3)]
            hr = h * (1.15 if vname == "Z03_cop_brute" else 1.0)     # its run sheet is drawn ~15% shorter
            runner = sprite(f"zombie_run_{i:03d}", None, hr, (0, 0, 0), cr, face, (1, 1, 1), aspect=rasp, parent=root,
                            base_mat=M["acrylic"], material=rm, mesh_name=f"ME_{vname}_run_{i % 3}_{hr:.4f}")
            key_visible(runner, [(f(spawn), f(CHASE_END) - 1)])
            key_loc(runner, 1, door)
            key_loc(runner, f(spawn), door)
            lag, gap, side = rnd.uniform(0.5, 1.1), rnd.uniform(0.014, 0.026), rnd.uniform(-0.012, 0.012)
            # their spot at the ladder foot: to either side of it, so the low S04b lens sees her between them
            sgn = -1 if i % 2 else 1
            lx = TOWER_XY[0] + sgn * rnd.uniform(0.014, 0.034)
            ly = TOWER_XY[1] - rnd.uniform(0.040, 0.062)     # not in the S04b lens (0.108, 0.040)
            gx, gy = lx, ly
            t = spawn + 0.25
            while t < CHASE_END:
                px, py = rin_at(max(0.0, t - lag))
                qx, qy = rin_at(t)
                dx, dy = px - qx, py - qy
                d = math.hypot(dx, dy)
                if d < gap:              # too close: hold back along the line to her
                    ux, uy = (dx / d, dy / d) if d > 1e-6 else (-0.7, 0.7)
                    px, py = qx + ux * gap, qy + uy * gap
                key_loc(runner, f(t), (px - side * 0.7, py + side * 0.7, ROOF_Z))
                last = (px - side * 0.7, py + side * 0.7, ROOF_Z)
                t += 0.25
            key_loc(o, f(CHASE_END) - 1, last)
            arrive = f(CHASE_END) + rnd.randint(4, 10)      # lunge in round the ladder foot as she is dragged down
            rx, ry = lx, ly
        key_loc(o, arrive, (rx, ry, ROOF_Z) if in_run((arrive - 1) / FPS) else (gx, gy, ROOF_Z))
        if (rx, ry) != (gx, gy):          # hold the side-step for the whole S04 window
            for sec in RUN_WINDOW:
                if f(sec) > arrive:
                    key_loc(o, f(sec), (rx, ry, ROOF_Z))
        # after Rin lands (35 s) the nearest half of the horde swarms the pin spot and rings it
        swarm = i % 2 == 0
        ring = rnd.uniform(0.022, 0.07)
        sx = PIN_XY[0] + math.cos(ang) * ring
        sy = PIN_XY[1] + abs(math.sin(ang)) * ring * 0.8 + 0.012   # always BEHIND her: the lens is on the -Y side
        t = CHASE_END + 2.0 if i < CHASERS else spawn + 3.0
        while t < RESET_S - 0.5:
            # anyone standing in the lens path (in front of the pin spot) is pushed behind her too
            in_lens = gy < PIN_XY[1] + 0.012 and abs(gx - PIN_XY[0]) < 0.16
            # they start converging while she is still falling (33 s), so by S12b (35.5 s) they ring her
            cx, cy = (sx, sy) if ((swarm or in_lens) and t > 33.0) else ((rx, ry) if in_run(t) else (gx, gy))
            if (swarm or in_lens) and 34.6 < t < 37.2:
                # S12/S12b: they hang back a beat while she lands... then LUNGE in on her together
                k = 1.6 if t < 35.8 else 0.38
                cx, cy = PIN_XY[0] + (sx - PIN_XY[0]) * k, PIN_XY[1] + 0.012 + (sy - PIN_XY[1] - 0.012) * k
            if (swarm or in_lens) and 35.5 <= t < 35.8:
                # the POUNCE (S12b): a crouched beat, then they all leap at her in 4 frames, overshoot and land
                def ring_at(k):
                    return PIN_XY[0] + (sx - PIN_XY[0]) * k, PIN_XY[1] + 0.012 + (sy - PIN_XY[1] - 0.012) * k
                d = rnd.uniform(-0.03, 0.03)                 # not all on exactly the same frame
                # (sec, ring factor, hop height, squash): crouch -> stretch into the leap -> land squashed -> settle
                for sec, k, hop, sq in ((35.60, 1.6, 0.0, 1.0), (35.70, 1.65, 0.0, 0.80), (35.76, 1.25, 0.010, 1.14),
                                        (35.82, 0.75, 0.013, 1.10), (35.88, 0.30, 0.0, 0.84), (35.96, 0.34, 0.0, 1.04),
                                        (36.05, 0.38, 0.0, 1.0)):
                    px, py = ring_at(k)
                    key_loc(o, f(sec + d), (px, py, ROOF_Z + hop))
                    o.scale = (1.0 / math.sqrt(sq), 1.0, sq)
                    o.keyframe_insert("scale", frame=f(sec + d))
                t = 36.3
                continue
            key_loc(o, f(t), (cx + rnd.uniform(-0.004, 0.004), cy + rnd.uniform(-0.004, 0.004), ROOF_Z))
            t += (0.25 if 34.6 < t < 37.2 else rnd.uniform(0.6, 1.0)) if 32.5 < t < 43 else rnd.uniform(1.2, 2.2)
        key_visible(o, [(f(CHASE_END) if i < CHASERS else f(spawn), R - 1)])
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
    """Background plush claw machine: printed body, chrome-posted glass box with gantry + claw,
    prize chute, LED strips, lit marquee, joystick/button deck and a pile of 3D plushies."""
    root = prop_root(name, loc, rotz, ar)
    parts = [
        box(f"{name}_body", (0.9, 0.85, 0.9), (0, 0, 0.45), M[body], ar),
        box(f"{name}_belt", (0.92, 0.87, 0.04), (0, 0, 0.92), M[accent], ar),
        box(f"{name}_glass", (0.86, 0.81, 0.85), (0, 0, 1.365), M["glass"], ar),
        box(f"{name}_top", (0.92, 0.87, 0.10), (0, 0, 1.84), M[body], ar),
        box(f"{name}_marquee", (0.78, 0.02, 0.085), (0, -0.445, 1.84), M["marquee_yellow" if body == "machine_yellow" else "marquee_pink"], ar),
        box(f"{name}_plush_card", (0.82, 0.004, 0.42), (0, 0.38, 1.15), M["plush_card"], ar),
        box(f"{name}_ctrl", (0.42, 0.14, 0.08), (-0.15, -0.49, 0.84), M["cab_trim"], ar),
        box(f"{name}_coin", (0.08, 0.01, 0.12), (0.2, -0.43, 0.70), M["coin_mech"], ar),
        box(f"{name}_door", (0.20, 0.01, 0.16), (0.2, -0.43, 0.24), M["black"], ar),
        box(f"{name}_door_frame", (0.23, 0.008, 0.19), (0.2, -0.427, 0.24), M["chrome"], ar),
        box(f"{name}_kick", (0.90, 0.012, 0.08), (0, -0.43, 0.04), M["metal_dull"], ar),
        box(f"{name}_price", (0.09, 0.004, 0.06), (-0.33, -0.428, 0.72), M["hazard_yellow"], ar),
        # deck: joystick + grab button
        cyl(f"{name}_stick", 0.008, 0.06, (-0.25, -0.50, 0.91), M["black"], ar, verts=8),
        sphere(f"{name}_stick_ball", 0.022, (-0.25, -0.50, 0.945), M["red_glossy"], ar, segs=12),
        cyl(f"{name}_button_bezel", 0.032, 0.012, (-0.06, -0.50, 0.886), M["chrome"], ar, verts=20),
        cyl(f"{name}_button", 0.025, 0.016, (-0.06, -0.50, 0.892), M[accent], ar, verts=20),
        # LED strips inside the roof and the neon edging round the marquee
        box(f"{name}_led_f", (0.80, 0.03, 0.012), (0, -0.37, 1.78), M["led_cool"], ar),
        box(f"{name}_led_b", (0.80, 0.03, 0.012), (0, 0.37, 1.78), M["led_cool"], ar),
        box(f"{name}_marquee_neon_t", (0.82, 0.012, 0.012), (0, -0.448, 1.888), M[accent], ar),
        box(f"{name}_marquee_neon_b", (0.82, 0.012, 0.012), (0, -0.448, 1.792), M[accent], ar),
        # side louvres
        box(f"{name}_louver_l", (0.006, 0.30, 0.14), (-0.452, 0.1, 0.30), M["louver"], ar),
        box(f"{name}_louver_r", (0.006, 0.30, 0.14), (0.452, 0.1, 0.30), M["louver"], ar),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):   # chrome corner posts, rubber feet
            parts.append(cyl(f"{name}_post_{sx}{sy}", 0.016, 0.86, (sx * 0.44, sy * 0.415, 1.365), M["chrome"], ar, verts=12))
            parts.append(cyl(f"{name}_foot_{sx}{sy}", 0.03, 0.02, (sx * 0.38, sy * 0.36, 0.0), M["rubber"], ar, verts=10))
    # gantry: two rails, a cross bar, the carriage, cable and a three-prong claw
    gy, gx = rnd.uniform(-0.2, 0.25), rnd.uniform(-0.25, 0.25)
    drop = rnd.uniform(0.12, 0.35)
    for sx in (-1, 1):
        parts.append(box(f"{name}_rail_{sx}", (0.025, 0.78, 0.025), (sx * 0.39, 0, 1.745), M["chrome"], ar))
    parts += [box(f"{name}_crossbar", (0.80, 0.03, 0.025), (0, gy, 1.725), M["chrome"], ar),
              box(f"{name}_carriage", (0.08, 0.08, 0.05), (gx, gy, 1.69), M["cab_trim"], ar),
              cyl(f"{name}_claw_cable", 0.003, drop, (gx, gy, 1.665 - drop / 2), M["black"], ar, verts=6),
              cyl(f"{name}_claw_hub", 0.028, 0.05, (gx, gy, 1.64 - drop), M["chrome"], ar, verts=12)]
    for j in range(3):
        a_ = j * math.tau / 3
        parts.append(box(f"{name}_claw_prong_{j}", (0.008, 0.008, 0.075),
                         (gx + 0.03 * math.cos(a_), gy + 0.03 * math.sin(a_), 1.595 - drop), M["chrome"], ar,
                         rot=(0.35 * math.sin(a_), -0.35 * math.cos(a_), 0)))
    # prize chute (front-right): clear acrylic box with a chrome lip
    parts.append(box(f"{name}_chute", (0.24, 0.24, 0.22), (0.30, -0.27, 1.05), M["glass"], ar))
    for j, (cx_, cy_, sx_, sy_) in enumerate([(0.30, -0.39, 0.25, 0.012), (0.30, -0.15, 0.25, 0.012),
                                              (0.18, -0.27, 0.012, 0.25), (0.42, -0.27, 0.012, 0.25)]):
        parts.append(box(f"{name}_chute_lip_{j}", (sx_, sy_, 0.012), (cx_, cy_, 1.165), M["chrome"], ar))
    # a heap of 3D plushies (body + head + ears), kept off the chute
    pm = ["plush_pink", "plush_blue", "plush_cream", "plush_mint"]
    for k in range(12):
        while True:
            px, py = rnd.uniform(-0.36, 0.34), rnd.uniform(-0.33, 0.32)
            if not (px > 0.14 and py < -0.11):
                break
        pz = 0.97 + rnd.uniform(0, 0.10)
        r = rnd.uniform(0.045, 0.065)
        m_ = M[rnd.choice(pm)]
        rz = rnd.uniform(0, math.tau)
        hx, hy = px + 0.25 * r * math.cos(rz), py + 0.25 * r * math.sin(rz)
        parts.append(sphere(f"{name}_plush_{k}_body", r, (px, py, pz + r * 0.6), m_, ar, segs=16, scale=(1, 0.9, 0.75)))
        parts.append(sphere(f"{name}_plush_{k}_head", r * 0.75, (hx, hy, pz + r * 1.2), m_, ar, segs=16))
        for e in (-1, 1):
            ex = hx + e * r * 0.45 * math.cos(rz + math.pi / 2)
            ey = hy + e * r * 0.45 * math.sin(rz + math.pi / 2)
            parts.append(sphere(f"{name}_plush_{k}_ear_{e}", r * 0.25, (ex, ey, pz + r * 1.75), m_, ar, segs=10, scale=(1, 0.6, 1.4)))
    for o in parts:   # soft plush and round chrome: no faceting
        if o.type == "MESH" and ("_plush_" in o.name or "_post_" in o.name or "_stick_ball" in o.name):
            for poly in o.data.polygons:
                poly.use_smooth = True
    parented(parts, root)
    return root


def arcade_cabinet(ar, M, name, loc, rotz):
    root = prop_root(name, loc, rotz, ar)
    parts = [
        box(f"{name}_body", (0.6, 0.7, 1.75), (0, 0, 0.875), M["arcade_side"], ar),
        box(f"{name}_screen", (0.48, 0.02, 0.40), (0, -0.33, 1.30), M["arcade_screen"], ar, rot=(math.radians(-15), 0, 0)),
        box(f"{name}_marquee", (0.58, 0.04, 0.16), (0, -0.33, 1.68), M["marquee_yellow" if sum(map(ord, name)) % 2 else "marquee_pink"], ar),
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
             cyl(f"{name}_crank_plate", 0.06, 0.01, (0, -0.165, 0.30), M["chrome"], ar, verts=20, rot=(math.pi / 2, 0, 0)),
             box(f"{name}_crank", (0.09, 0.02, 0.022), (0, -0.18, 0.30), M["chrome"], ar),
             box(f"{name}_chute", (0.10, 0.03, 0.07), (0, -0.17, 0.12), M["black"], ar),
             box(f"{name}_card", (0.26, 0.005, 0.13), (0, -0.162, 0.465), M["gacha_card"], ar),
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
    parts = [box(f"{name}_base", (0.75, 1.5, 0.12), (0, 0.2, 0.06), M["racing_base"], ar),
             box(f"{name}_tower", (0.75, 0.55, 1.45), (0, -0.30, 0.79), M["cab_body"], ar),
             box(f"{name}_screen", (0.62, 0.03, 0.48), (0, -0.03, 1.12), M["racing_screen"], ar, rot=(math.radians(-12), 0, 0)),
             box(f"{name}_header", (0.75, 0.10, 0.22), (0, -0.05, 1.62), M["neon_cyan"], ar),
             box(f"{name}_dash", (0.70, 0.30, 0.10), (0, 0.10, 0.80), M["racing_dash"], ar, rot=(math.radians(-20), 0, 0)),
             box(f"{name}_seat", (0.48, 0.48, 0.10), (0, 0.80, 0.42), M["racing_seat"], ar),
             box(f"{name}_seat_back", (0.48, 0.10, 0.62), (0, 1.03, 0.72), M["racing_seat"], ar, rot=(math.radians(15), 0, 0)),
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
    track_light("track_spot_gashapon", (-1.55, 1.0, 3.05), (-1.55, 1.75, 0.6), M, ar, energy=45)   # lift the dark gashapon corner
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
    box("lane_floor_led", (0.03, 4.0, 0.012), (1.95, 2.4, 0.006), M["neon_cyan"], ar)
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
        neighbour_claw_machine(ar, M, f"machine_lane_{k}", (2.6, y, 0), -math.pi / 2, body, "neon_pink", rnd)   # fronts face the aisle (-X)
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
    for sec in DOOR_BANGS_S:   # the door lamp stutters on every bang
        b = f(sec)
        for fr, e in ((b - 1, 0.04), (b + 1, 0.004), (b + 2, 0.07), (b + 4, 0.01), (b + 6, 0.04)):
            L.energy = e
            L.keyframe_insert("energy", frame=fr)
    L.energy = 0.04
    # spotlight that "comes from heaven" in S06 (the claw's work light)
    L = bpy.data.lights.new("L_claw_spot", "SPOT")
    L.energy, L.color, L.spot_size = 3.0, (0.85, 0.92, 1.0), math.radians(25)
    o = bpy.data.objects.new(L.name, L)
    o.location = (TOWER_XY[0], TOWER_XY[1], 1.78)
    lt.objects.link(o)
    L.energy = 0.0
    L.keyframe_insert("energy", frame=f(15.0))
    for fr_, e in ((f(15.0) + 2, 3.0), (f(15.0) + 5, 0.0), (f(15.0) + 8, 3.0), (f(15.0) + 11, 0.2)):   # double blink
        L.energy = e
        L.keyframe_insert("energy", frame=fr_)
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
        for frac, cm, am in SHOT_MID.get(sid, []):
            key_loc(cam, f(a + (b - a) * frac), cm)
            key_loc(aim, f(a + (b - a) * frac), am)
        # miniature look: shallow DOF focused on the aim point
        cd.dof.use_dof = True
        cd.dof.focus_object = bpy.data.objects.get(SHOT_FOCUS.get(sid, "")) or aim
        # at 1:60 scale f/1.4 blurs everything; f/2.8-4 still reads as tilt-shift miniature
        cd.dof.aperture_fstop = 8.0 if sid in ("S01a_door_burst", "S04a_run_climb", "S01b_door_bang", "S02b_chase_low", "S02c_look_back", "S03_lost_boot", "S15c_prize_tray", "S15n_nova_joystick", "S15m_nova_button", "S15d_chute_drop", "S09a_false_hope", "S09b_hope_low", "S05_pile_topdown", "S12_impact", "S12b_surrounded", "S12c_grabbed", "S12d_pressed", "S13a_pinned", "S13c_hand_press", "S13b_pinned_face", "S17b_reset_loop") else 2.8
        if sid in ("S09a_false_hope", "S09b_hope_low", "S12b_surrounded"):   # a few cm from her: deep focus or she melts
            cd.dof.aperture_fstop = 22.0
        if sid == "S06_light_above":    # 3 cm from her: needs deep focus to keep face and the light above readable
            cd.dof.aperture_fstop = 22.0
        if sid == "S01a_door_burst":    # f/8 at the loop seam, then deep focus so her fists AND the door leaf are sharp
            for fr, stop in ((f(0.5), 8.0), (f(0.74), 22.0)):
                cd.dof.aperture_fstop = stop
                cd.dof.keyframe_insert("aperture_fstop", frame=fr)
        if sid == "S15_glass_reveal":   # rack DOF wider as we exit the glass
            cd.dof.aperture_fstop = 2.0
            cd.keyframe_insert("dof.aperture_fstop", frame=f(a))
            cd.dof.aperture_fstop = 5.6
            cd.keyframe_insert("dof.aperture_fstop", frame=f(b) - 1)
        if sid in ("S12_impact", "S12c_grabbed", "S12d_pressed", "S13a_pinned", "S13b_pinned_face"):    # handheld shake
            amp = 0.0003 if sid == "S13b_pinned_face" else 0.002   # the face ECU frames tight to the art's edges
            for k in range(0, 10):
                key_loc(cam, f(a) + k * 2, (c0[0] + random.uniform(-amp, amp), c0[1], c0[2] + random.uniform(-amp, amp)))
        if sid in PRESS_THUMPS:
            press_thumps(cam, f(a), f(b), PRESS_THUMPS[sid])
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
        "plush_pink":    mat("plush_pink", (0.95, 0.55, 0.70), 1.0),
        "plush_blue":    mat("plush_blue", (0.45, 0.70, 0.95), 1.0),
        "plush_cream":   mat("plush_cream", (0.95, 0.88, 0.70), 1.0),
        "plush_mint":    mat("plush_mint", (0.55, 0.90, 0.75), 1.0),
        "plush_card":    mat("plush_card", (0.9, 0.6, 0.8), 0.7, 0, emit=(0.9, 0.6, 0.8), strength=0.6),
        "machine_pink":  mat("machine_pink", (0.95, 0.8, 0.9), 0.4, 0.1),
        "machine_yellow":mat("machine_yellow", (0.95, 0.7, 0.1), 0.4, 0.1),
        "ceiling":       mat("ceiling", (0.02, 0.02, 0.025), 0.8, 0, emit=(0.02, 0.02, 0.025), strength=0.7),    # all lights point down: faint self-glow so the V7 ceiling art reads
        "lamp_shade":    mat("lamp_shade", (0.05, 0.05, 0.05), 0.4, 0.8),
        "wood":          mat("wood", (0.22, 0.15, 0.09), 0.85),
        "wood_old":      mat("wood_old", (0.10, 0.075, 0.05), 0.9),
        "plastic_white": mat("plastic_white", (0.55, 0.56, 0.55), 0.5),
        "rubber":        mat("rubber", (0.015, 0.015, 0.015), 0.75),
        "cardboard":     mat("cardboard", (0.30, 0.22, 0.13), 0.9),
        "trash_bag":     mat("trash_bag", (0.01, 0.01, 0.012), 0.2),
        "tarp":          mat("tarp", (0.05, 0.16, 0.35), 0.6),
        "sleeping_bag":  mat("sleeping_bag", (0.45, 0.16, 0.05), 0.7),
        "cloth_a":       mat("cloth_a", (0.35, 0.33, 0.30), 0.9),
        "cloth_b":       mat("cloth_b", (0.30, 0.05, 0.05), 0.9),
        "cloth_shirt":   mat("cloth_shirt", (0.35, 0.33, 0.30), 0.9),
        "cloth_shirt_b": mat("cloth_shirt_b", (0.12, 0.18, 0.30), 0.9),
        "cloth_pants":   mat("cloth_pants", (0.10, 0.14, 0.25), 0.9),
        "cloth_towel":   mat("cloth_towel", (0.45, 0.30, 0.15), 0.95),
        "cloth_blanket": mat("cloth_blanket", (0.30, 0.05, 0.05), 0.95),
        "cloth_blanket_b": mat("cloth_blanket_b", (0.20, 0.25, 0.15), 0.95),
        "paper":         mat("paper", (0.45, 0.44, 0.40), 0.9),
        "brick":         mat("brick", (0.30, 0.10, 0.06), 0.9),
        "grass":         mat("grass", (0.08, 0.17, 0.05), 0.8),
        "leaf":          mat("leaf", (0.25, 0.13, 0.04), 0.8),
        "ember":         mat("ember", (0.3, 0.05, 0.0), 0.6, 0, emit=(1.0, 0.3, 0.05), strength=6),
        "red_led":       mat("red_led", (0.3, 0.0, 0.0), 0.4, 0, emit=(1.0, 0.02, 0.02), strength=10),
        "chrome":        mat("chrome", (0.85, 0.85, 0.9), 0.12, 1.0),
        "black":         mat("black", (0.01, 0.01, 0.01), 0.5),
        # V7 per-object materials: same flat colour as before until their picture arrives
        "arcade_side":   mat("arcade_side", (0.01, 0.01, 0.01), 0.5),
        "racing_base":   mat("racing_base", (0.01, 0.01, 0.01), 0.5),
        "racing_dash":   mat("racing_dash", (0.01, 0.01, 0.01), 0.5),
        "racing_seat":   mat("racing_seat", (0.01, 0.01, 0.01), 0.5),
        "control_panel": mat("control_panel", (0.01, 0.01, 0.01), 0.5),
        "ac_fan":        mat("ac_fan", (0.01, 0.01, 0.01), 0.5),
        "crate":         mat("crate", (0.22, 0.15, 0.09), 0.85),
        "glass":         mat("glass", (0.75, 0.85, 1.0), 0.02, 0.0, alpha=0.04),
        "acrylic":       mat("acrylic_base", (0.30, 0.36, 0.42), 0.12, 0.0, alpha=0.10),   # dark, mostly clear: read as a glint, not a white disc
        "marquee":       mat("marquee", (0.3, 0.05, 0.3), 0.4, 0, emit=(1.0, 0.25, 0.8), strength=1.8),
        "marquee_pink":  mat("marquee_pink", (0.3, 0.05, 0.3), 0.4, 0, emit=(1.0, 0.25, 0.8), strength=1.6),
        "marquee_yellow":mat("marquee_yellow", (0.35, 0.25, 0.02), 0.4, 0, emit=(1.0, 0.8, 0.2), strength=1.6),
        "neon_pink":     mat("neon_pink", (1.0, 0.2, 0.7), 0.3, 0, emit=(1.0, 0.2, 0.7), strength=5),
        "button_magenta":mat("button_magenta", (0.55, 0.0, 0.22), 0.12, 0, emit=(1.0, 0.0, 0.42), strength=0.35),   # saturated hot magenta: a strong glow washes out to pastel
        "button_bezel":  mat("button_bezel", (0.02, 0.02, 0.025), 0.25, 0.0),
        "neon_cyan":     mat("neon_cyan", (0.1, 0.85, 1.0), 0.3, 0, emit=(0.05, 0.8, 1.0), strength=5),
        "led_red":       mat("led_red", (0.2, 0.0, 0.0), 0.4, 0, emit=(1.0, 0.05, 0.05), strength=8),
        "moon_lamp":     mat("moon_lamp", (0.9, 0.95, 1.0), 0.2, 0, emit=(0.85, 0.92, 1.0), strength=25),
        "red_glossy":    mat("red_glossy", (0.8, 0.02, 0.05), 0.1),
        "boot":          mat("boot", (0.12, 0.08, 0.06), 0.7),
        "boot_leather":  mat("boot_leather", (0.16, 0.075, 0.035), 0.5),   # Rin's brown lace-up boots (tray models)
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
        "stair_lamp_flicker": mat("stair_lamp_flicker", (0.2, 1, 0.4), 0.5, 0, emit=(0.3, 1, 0.45), strength=4),
        "racing_screen": mat("racing_screen", (0.2, 0.4, 0.9), 0.2, 0, emit=(0.3, 0.5, 1.0), strength=4),
        "wall_tv":       mat("wall_tv", (0.3, 0.2, 0.6), 0.2, 0, emit=(0.5, 0.3, 0.9), strength=3),
        "gacha_card":    mat("gacha_card", (0.9, 0.6, 0.8), 0.6, 0, emit=(0.9, 0.6, 0.8), strength=0.4),
        "prize_box":     mat("prize_box", (0.6, 0.5, 0.8), 0.6),
    }
    for key, period, on_frac, hi in (("amber_blink", FPS, 0.5, 12.0), ("street_lamp_flicker", None, 0, 20.0), ("stair_lamp_flicker", None, 0, 4.0)):
        em = node_of_type(M[key].node_tree, "BSDF_PRINCIPLED").inputs["Emission Strength"]
        if period:
            for k in range(0, 60 * FPS, period):
                em.default_value = hi
                em.keyframe_insert("default_value", frame=k + 1)
                em.default_value = 0.0
                em.keyframe_insert("default_value", frame=k + 1 + int(period * on_frac))
        else:   # same stutter pattern as the light in street_lamp(... "flicker")
            r = random.Random(sum(map(ord, "street_lamp_5" if key == "street_lamp_flicker" else "stair_lamp")))
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


def unlink_cab_front_from_nova_cards():
    # L_cab_front_low's cyan fill lights the pickup tray, but on the S15n/S15m hand cards it turned Nova's
    # lavender sleeve grey-blue: light-link those two cards out of it (every other object keeps the light)
    lo = bpy.data.objects.get("L_cab_front_low")
    cards = [bpy.data.objects.get(n) for n in ("nova_joystick_hand", "nova_button_hand")]
    cards = [o for o in cards if o]
    if not lo or not cards:
        return
    rc = bpy.data.collections.new("LL_cab_front_low_receivers")
    for o in cards:
        rc.objects.link(o)
    for co in rc.collection_objects:      # no string lookup on collection_objects
        co.light_linking.link_state = "EXCLUDE"
    lo.light_linking.receiver_collection = rc


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
    build_prize_chute(C, M)
    tower = build_tower(C, M)
    claw, pivots = build_claw(C, M)
    face = empty("FACE_TARGET", SHOTS[0][4], coll("CAMERAS", C["root"]), "SPHERE", 0.004)
    build_characters(C, M, face, tower)
    unlink_cab_front_from_nova_cards()
    crowd = build_crowd(C, M, face)
    hide_bases_in_close_shots()
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
    for fr, e in ((1, 0.0), (f(s17[1]), 3.0), (f(s17[2]), 0.0)):      # 6 washed the hand out flat
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
