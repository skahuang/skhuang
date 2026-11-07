# 差一點 / ALMOST — GPT 素材生成清單

**用法：** 每次生成都**附上對應的參考圖**（你現有的 Rin / Nova / 喪屍設定圖），再貼上「風格鎖定」+ 該素材的提示詞。
產出的 PNG 用**表格裡的檔名**放進 `assets/sprites/` 或 `assets/textures/`，重跑 Blender 腳本就會自動套用。

- ★ = 最優先，先做這 6 張驗證風格
- 角色圖：**1024×1536 直式、透明背景 PNG、全身不裁切、腳底貼齊畫面下緣**（Blender 立牌以圖片底部為站立點）
- 提示詞用英文（GPT 生圖對英文的遵循度比較穩定），中文說明寫在表格裡

---

## 0. 風格鎖定（每次都貼在最前面）

### 機台內角色（Rin、喪屍）

```text
STYLE LOCK: stylized 3D-animated feature-film character look (soft subsurface skin, big expressive eyes, chunky readable shapes),
rendered as a single clean cutout figure for a 2D acrylic standee. Full body, entire figure visible, feet touching the bottom edge.
TRANSPARENT BACKGROUND, no floor, no cast shadow, no text, no border.
Lighting: cool blue moonlight key from upper-left, thin green rim light from the right, subtle warm orange bounce from below.
Camera: slightly high angle, about 25 degrees looking down, three-quarter view unless stated.
Keep the outfit, colours and proportions EXACTLY the same as the attached reference sheet.
```

### 現實世界（Nova）

```text
STYLE LOCK: stylized 3D-animated feature-film character look, same character as the attached NOVA reference sheet
(short lavender-grey bob, lime-green square hair clip on the same side as in the reference, small silver hoop earrings, oversized purple satin bomber jacket
with a sleeve zip pocket, black turtleneck, wide black cargo pants with a lavender side stripe, chunky purple-white sneakers).
TRANSPARENT BACKGROUND, no text, no border. Lighting: arcade neon — magenta key from the left, cyan rim from the right, soft purple fill.
```

---

## 1. 參考設定圖修正版（先做，之後所有圖都拿它當參考）

| 檔名 | 說明 | 提示詞 |
|---|---|---|
| ★ `ref_rin_sheet_v2.png` | Rin 設定圖修正：**布料破邊改成乾的磨損鬚邊、移除血跡**；做兩種腳的版本 | `Character turnaround sheet of RIN, same girl as the attached reference: a young girl, messy shoulder-length black hair, big brown eyes, small dusty scrape on her left cheek. Outfit: faded crimson zip hoodie with DRY frayed fabric edges and loose threads (NOT dripping, NOT liquid, no blood anywhere), dusty cream t-shirt with small holes, charcoal cargo pants torn at the knees, dark brown lace-up combat boots. Show FRONT, RIGHT SIDE, BACK, plus a second front view where her LEFT boot is missing and that foot is bare and dusty. Neutral grey background, labels under each view. Clean, readable, family-friendly survival look: dirt and scrapes only, no gore.` |
| `ref_zombies_v2.png` | 4 種喪屍統一規則：觸手**只從肩膀 / 背部**長出來 | `Lineup sheet of 4 cartoon-horror zombies for a family-friendly animated short, same designs as the attached reference: Z01 orange mechanic coveralls with tool belt; Z02 teal tourist shirt with khaki shorts; Z03 huge police officer in navy uniform with badge; Z04 torn yellow raincoat. Rule for all: pale grey-green skin with purple lumps, white blank eyes, 2-4 pink-purple tentacles that grow ONLY from the shoulders and upper back. Both feet in the same footwear for each zombie. No blood, no exposed organs. Neutral grey background, front three-quarter view, labels Z01-Z04.` |

---

## 2. Rin 姿勢立牌（`assets/sprites/`）

所有提示詞前面先貼「機台內角色」風格鎖定，並附上 `ref_rin_sheet_v2.png`。

| 檔名 | 鏡頭 | 腳 | 提示詞 |
|---|---|---|---|
| `rin_backing_away.png` | S02 | 兩腳都有靴子 | `RIN stepping backwards in fear, weight on her back foot, arms raised defensively in front of her chest, looking toward the left at something terrifying, mouth open.` |
| ★ `rin_boot_grab.png` | S03 | 正在被扯掉 | `Low angle close to the ground. RIN yanking her leg forward while a grey-green zombie hand (only the hand and wrist, entering from the left edge) grips her LEFT boot, the boot sliding off her foot. Her face shows panic and effort.` |
| ★ `rin_climb_back.png` | S04 | 左腳光腳 | `BACK VIEW. RIN climbing a ladder: both hands gripping imaginary rungs above her head, right knee raised, left bare foot pushing down. Do NOT draw the ladder. Head turned slightly so we see her cheek.` 想做循環的話，另外生成 `rin_climb_back_01`~`_04`：`same pose sequence, frame 1/4 … 4/4 of a ladder-climb cycle, alternating arms and legs` |
| `rin_cling_scared.png` | S05、S06 | 左腳光腳 | `RIN clinging tightly to a vertical ladder (ladder not drawn), body pressed forward, knees tucked, looking DOWN over her shoulder in terror, tears in her eyes.` |
| ★ `rin_cling_hope.png` | S07–S09 | 左腳光腳 | `RIN holding on to a vertical ladder with one hand (ladder not drawn), the other hand reaching up, looking UP toward a bright light above her, face full of hope, a small relieved smile, light reflected in her eyes.` |
| `rin_slip_shock.png` | S10 | 左腳光腳 | `RIN on a ladder (not drawn), both hands suddenly slipping, smile frozen into shock, eyes wide, looking up.` |
| `rin_falling.png` | S11、S12 | 左腳光腳 | `RIN falling backwards through the air, arms and legs spread, hair and hoodie fluttering upward, reaching up with one hand, mouth open in a scream. Full figure, no ground.` |
| `rin_reset_lookup.png` | S15b | 左腳光腳 | `Slightly HIGH camera above her. RIN standing in the middle of a rooftop (no rooftop drawn), tilting her head all the way back and looking straight UP INTO THE CAMERA, expression of quiet realisation, as if she can see the player outside the glass.` |

---

## 3. 喪屍立牌（`assets/sprites/`）

前面貼「機台內角色」風格鎖定 + `ref_zombies_v2.png`。12 張 = 4 種 × 3 個姿勢。

**檔名規則：** `zombie_<變體>_<姿勢>.png`
變體：`z01_mechanic`、`z02_tourist`、`z03_cop_brute`、`z04_raincoat`
姿勢：`walk`、`reach`、`climb`

| 姿勢 | 提示詞（把 `<ZOMBIE>` 換成變體描述，例如 `Z01, the orange-coverall mechanic zombie`） |
|---|---|
| `walk` | `<ZOMBIE> shambling forward, one foot dragging, arms half raised, head tilted, tentacles swaying from shoulders.` |
| ★ `reach`（先做 `zombie_z01_mechanic_reach.png`） | `<ZOMBIE> standing still with BOTH arms stretched straight UP toward the sky, grasping, head thrown back, mouth open, tentacles also reaching upward.` |
| `climb` | `<ZOMBIE> seen from behind three-quarter, climbing over other bodies (not drawn), one arm high, one knee up, tentacles hooking upward.` |

> 小技巧：如果 GPT 一次能做好一整排，可以要求 `4 separate figures in one image, evenly spaced, each fully isolated on transparent background`，再自己裁切成 4 張，比較容易保持一致。

---

## 4. Nova（`assets/sprites/`）

前面貼「現實世界」風格鎖定 + Nova 設定圖。

| 檔名 | 鏡頭 | 提示詞 |
|---|---|---|
| ★ `nova_back_joystick.png` | S13 | `BACK VIEW, full body. NOVA standing at an arcade claw machine (machine NOT drawn), left hand on a joystick, right hand hovering over a button (controls NOT drawn, only her hands in position), shoulders slightly hunched forward in concentration. Feet on the bottom edge.` |
| ★ `nova_profile_almost.png` | S14 | `Three-quarter PROFILE, from the waist up but keep the whole figure to the bottom edge. NOVA looking down to her left, the "ALMOST" expression from the reference sheet: eyebrows pulled together, lips pressed, a tiny exhale, half-lidded eyes. Magenta and cyan neon reflections on her cheek.` |
| `nova_hand_coin.png` | S15a | `Close-up of NOVA's right hand only, black ribbed sleeve cuff and purple jacket cuff visible, pinching a silver arcade token between thumb and index finger, about to push it into a slot (slot NOT drawn). Transparent background.` |
| `nova_smirk_alt.png`（備用） | S14 替代 | `Same framing as the profile shot, but the SMIRK expression: one corner of her mouth up, eyes narrowed, flipping the coin.` 可以拿來做「她其實是故意的」另一個結局版本 |

---

## 5. 背景與貼圖（`assets/textures/`）

這些**不用透明背景**。

| 檔名 | 尺寸 | 用途 | 提示詞 |
|---|---|---|---|
| ★ `tex_backdrop_city_sky.png` | 1024×1024 | 櫃體背板的印刷畫（S06、S09 的天空） | `Flat printed backdrop painting for a miniature diorama: night sky with heavy blue-grey storm clouds, a burning ruined city skyline along the bottom third (dark silhouettes, orange fire glow, a few lit windows). NO MOON (the moon is a real lamp). Painterly matte-painting style, slightly visible print texture, straight-on view, no perspective distortion, fills the entire frame.` |
| `tex_arcade_bokeh_plate.png` | 1024×1820 | S13–S14 Nova 身後的遊樂場背景 | `Out-of-focus arcade interior at night, strong magenta, cyan and purple bokeh circles from other machines and neon signs, dark floor, no readable text, no people, vertical composition.` |
| `tex_roof_tiles_wet.png` | 1024×1024 可平鋪 | 屋頂地磚（手動貼在 `roof_tiles`） | `Seamless tileable texture, top-down, small square grey-blue concrete roof tiles, wet glossy sheen like resin varnish, cracks, a few dead leaves, orthographic, even lighting.` |
| `tex_concrete_peel.png` | 1024×1024 可平鋪 | 建築外牆（手動貼在 `hero_building`、`city_*`） | `Seamless tileable texture, flat-on, weathered grey concrete wall with peeling paint patches, moss streaks and water stains, orthographic, even lighting.` |
| `tex_rust_metal.png` | 1024×1024 可平鋪 | 水塔、夾爪 | `Seamless tileable texture, riveted steel plate with orange-brown rust streaks and chipped grey paint, orthographic, even lighting.` |
| `tex_marquee_logo.png` | 2048×360 | 機台頂部招牌 | `Arcade claw machine marquee sign, glowing neon tube lettering "差一點 ALMOST" in magenta and cyan, small pixel-art claw icon, dark purple background, straight-on.` |
| `tex_cabinet_decals.png` | 1024×1024 | 控制台貼紙（INSERT COIN、1 PLAY） | `Sticker sheet for an arcade claw machine: "INSERT COIN" with arrow, "1 PLAY = 1 TOKEN", "GRAB!" button label, "PRIZE" with down arrow, retro 90s arcade style, each sticker separated on a white background.` |
| `tex_led_timer.png`（選用） | 512×160 | 揭曉時的 `00:00` 紅色 LED | `Red seven-segment LED display reading "00:00", glowing, black background, straight-on.` |

---

## 6. 合成用圖（交給 OpenMontage compose）

| 檔名 | 用途 | 說明 |
|---|---|---|
| `ui_timer_font` | 全片右上角倒數 | 不用生圖，Remotion 用等寬的七段顯示器字型（例如 DSEG7）即可，跟 LED 同一種風格 |
| `card_last_survivor` / `card_almost` / `card_one_more` | 三張文字卡 | 建議直接用字型排版，不要用生圖（AI 生成的中文字常出錯） |
| `thumb_cover.png` | 封面 | 用 S09 的算圖成品 + 標題字，最後再做 |

---

## 7. 品質檢查（每張圖生成後檢查）

- [ ] 透明背景是真的透明（不是畫出來的格子圖案）
- [ ] 全身完整、腳底貼齊畫面下緣
- [ ] Rin：S03 之後的圖**左腳光腳**；衣服沒有血或液體
- [ ] 喪屍：觸手只從肩膀 / 背部長出來；沒有血腥內臟
- [ ] Nova：黃綠色髮夾的位置跟設定圖同一側、外套袖口有拉鍊口袋
- [ ] 光線方向一致（冷光從左上、綠色邊光從右側）
- [ ] 圖裡沒有多出來的文字、浮水印、地面、陰影
