# 差一點 / ALMOST — GPT 素材生成清單

**用法：** 每次生成都**附上對應的參考圖**（你現有的 Rin / Nova / 喪屍設定圖），再貼上「風格鎖定」+ 該素材的提示詞。
產出的 PNG 用**表格裡的檔名**放進 `assets/sprites/` 或 `assets/textures/`，重跑 Blender 腳本就會自動套用。

- ★ = 最優先，先做這 7 張驗證風格
- **調性：成人向、輕度血腥。** 可以有擦傷、血跡、血漬；不要有傷口特寫、咬合、斷肢、內臟，也不要有性暗示的撕衣或裸露
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
Tone: mature horror, MILD gore only — scratches, smeared blood on skin and clothes, blood on zombie fingertips and lips.
No open wounds, no bite close-ups, no dismemberment, no organs, no sexualised clothing damage.
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
| ★ `ref_rin_sheet_v2.png` | Rin 設定圖修正：**改成成年人的比例**（降低平台審查風險）、紅外套破邊改成布料鬚邊、做兩種腳的版本 | `Character turnaround sheet of RIN, same face style as the attached reference but clearly an ADULT woman in her early twenties: adult head-to-body proportions (about 1:6.5), longer limbs, slightly more mature face, still big expressive brown eyes, messy shoulder-length black hair, a scrape and a thin line of dried blood on her left cheek. Outfit: faded crimson zip hoodie with frayed fabric edges and loose threads, a few dark blood smears on the sleeves, dusty cream t-shirt, charcoal cargo pants torn at the knees, dark brown lace-up combat boots. Show FRONT, RIGHT SIDE, BACK, plus a second front view where her LEFT boot is missing and that foot is bare and dirty. Neutral grey background, labels under each view.` |
| `ref_zombies_v2.png` | 4 種喪屍統一規則：觸手**只從肩膀 / 背部**長出來 | `Lineup sheet of 4 stylized horror zombies for a mature animated short, same designs as the attached reference: Z01 orange mechanic coveralls with tool belt; Z02 teal tourist shirt with khaki shorts; Z03 huge police officer in navy uniform with badge; Z04 torn yellow raincoat. Rule for all: pale grey-green skin with purple lumps, white blank eyes, 2-4 pink-purple tentacles that grow ONLY from the shoulders and upper back. Both feet in the same footwear for each zombie. Mild gore: dark blood stains on clothes, blood around the mouth and on fingertips; no exposed organs, no open wounds. Neutral grey background, front three-quarter view, labels Z01-Z04.` |

---

## 2. Rin 姿勢立牌（`assets/sprites/`）

所有提示詞前面先貼「機台內角色」風格鎖定，並附上 `ref_rin_sheet_v2.png`。

| 檔名 | 鏡頭 | 腳 | 提示詞 |
|---|---|---|---|
| `rin_backing_away.png` | S02 | 兩腳都有靴子 | `RIN stepping backwards in fear, weight on her back foot, arms raised defensively in front of her chest, looking toward the left at something terrifying, mouth open.` |
| ★ `rin_boot_grab.png` | S03 | 正在被扯掉 | `Low angle close to the ground. RIN yanking her leg forward while a grey-green zombie hand with bloody fingernails (only the hand and wrist, entering from the left edge) grips her LEFT boot, the boot sliding off her foot, three thin bleeding scratches on her calf. Her face shows panic and effort.` |
| ★ `rin_climb_back.png` | S04 | 左腳光腳 | `BACK VIEW. RIN climbing a ladder: both hands gripping imaginary rungs above her head, right knee raised, left bare foot pushing down. Do NOT draw the ladder. Head turned slightly so we see her cheek.` 想做循環的話，另外生成 `rin_climb_back_01`~`_04`：`same pose sequence, frame 1/4 … 4/4 of a ladder-climb cycle, alternating arms and legs` |
| `rin_cling_scared.png` | S05、S06 | 左腳光腳 | `RIN clinging tightly to a vertical ladder (ladder not drawn), body pressed forward, knees tucked, looking DOWN over her shoulder in terror, tears in her eyes.` |
| ★ `rin_cling_hope.png` | S07–S09 | 左腳光腳 | `RIN holding on to a vertical ladder with one hand (ladder not drawn), the other hand reaching up, looking UP toward a bright light above her, face full of hope, a small relieved smile, light reflected in her eyes.` |
| `rin_slip_shock.png` | S10 | 左腳光腳 | `RIN on a ladder (not drawn), both hands suddenly slipping, smile frozen into shock, eyes wide, looking up.` |
| `rin_falling.png` | S11 | 左腳光腳 | `RIN falling backwards through the air, arms and legs spread, hair and hoodie fluttering upward, one hand reaching UP toward something above her, mouth open in a scream, raindrops around her. Full figure, no ground.` |
| `rin_impact.png` | S12 | 左腳光腳 | `RIN the instant after slamming onto a wet rooftop: lying on her side, propping herself up on one elbow, splash of water spraying around her body, hair wet across her face, wincing in pain. Low camera close to the ground. Water splash included, no floor drawn.` |
| `rin_reset_lookup.png` | S17b | 左腳光腳 | `Slightly HIGH camera above her. RIN standing in the middle of a rooftop (no rooftop drawn), tilting her head all the way back and looking straight UP INTO THE CAMERA, expression of quiet realisation, as if she can see the player outside the glass. Her cheek still has the blood smear from the last round.` |

---

## 2.5 壓制畫面三層立牌（S13–S14，`assets/sprites/`）

把你那三張壓制圖當成**構圖參考**附上，請 GPT 拆成三層、**每層都是透明背景**。三層會在 Blender 裡前後排開，鏡頭拉遠時才有視差。
**同一次對話裡連續生成三層**，比較容易保持一致；三層都要從**同一個低角度、貼近地面的視角**畫。

| 檔名 | 層 | 提示詞 |
|---|---|---|
| ★ `pin_layer_rin.png` | 中層：倒地的 Rin | `Using the attached pinned-scene images as composition reference: ONLY RIN (adult, as in the reference sheet), lying face-down on her side on the ground, cheek pressed to the floor, eyes straining UPWARD, teeth gritted. Her red hoodie is being pulled up and back at the shoulder (the hands pulling it are NOT drawn), one arm stretched forward, one bare foot and one boot visible. Scrapes and blood smears on her face and hands. Low camera very close to the ground. Transparent background, no zombies, no floor, no shadow. Wide landscape framing 1536x1024.` |
| `pin_layer_back.png` | 後層：警察 + 黃雨衣 | `Same scene, same camera. ONLY the two zombies BEHIND her: Z03 the huge police zombie leaning forward, both fists gripping and pulling a red hoodie (show the red fabric in his hands, ending at the bottom edge), and Z04 the yellow raincoat zombie reaching down with tentacles curling downward toward the ground. Both roaring. Blood on their mouths and fingertips. Transparent background, no girl, no floor. Wide landscape framing 1536x1024.` |
| `pin_layer_front.png` | 前層：觀光客 + 工人 | `Same scene, same camera. ONLY the two zombies IN FRONT, closest to the camera: Z02 the teal-shirt tourist zombie on the left, crouched low, both hands pressing down on something at the bottom edge (an arm, not drawn), and Z01 the orange mechanic zombie on the right, one hand pressing down on something at the bottom edge (a head, not drawn). Both snarling at the camera. Transparent background, no girl, no floor. Wide landscape framing 1536x1024.` |
| `pin_keyframe_close.png`（選用） | 單張特寫 | 如果覺得拆層太難對齊，可以直接用新圖 3 的構圖生成一張**完整的 9:16 特寫**（含背景），在合成時當 S13 的 2 秒插入畫面，再接回 Blender 的 S14 拉遠。提示詞：`Recreate the attached pinned close-up as a vertical 1080x1920 frame, adult RIN, same four zombies, rain, wet reflective rooftop tiles, mild gore only, no torn clothing exposing skin, tentacles wrapped around her arm and ankle instead of her neck.` |

> 對齊技巧：三層生成後，在 Blender 裡選 `pin_layer_back / rin / front` 三個物件，調整 Z 高度和左右位置，讓扯外套的手剛好接到 Rin 的肩膀。三張圖的寬高比會自動讀取。

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
| ★ `nova_back_joystick.png` | S15 | `BACK VIEW, full body. NOVA standing at an arcade claw machine (machine NOT drawn), left hand on a joystick, right hand hovering over a button (controls NOT drawn, only her hands in position), shoulders slightly hunched forward in concentration. Feet on the bottom edge.` |
| ★ `nova_profile_almost.png` | S16 | `Three-quarter PROFILE, from the waist up but keep the whole figure to the bottom edge. NOVA looking down to her left, the "ALMOST" expression from the reference sheet: eyebrows pulled together, lips pressed, a tiny exhale, half-lidded eyes. Magenta and cyan neon reflections on her cheek.` |
| `nova_hand_coin.png` | S17a | `Close-up of NOVA's right hand only, black ribbed sleeve cuff and purple jacket cuff visible, pinching a silver arcade token between thumb and index finger, about to push it into a slot (slot NOT drawn). Transparent background.` |
| `nova_smirk_alt.png`（備用） | S16 替代 | `Same framing as the profile shot, but the SMIRK expression: one corner of her mouth up, eyes narrowed, flipping the coin.` 可以拿來做「她其實是故意的」另一個結局版本 |

---

## 5. 背景與貼圖（`assets/textures/`）

這些**不用透明背景**。

| 檔名 | 尺寸 | 用途 | 提示詞 |
|---|---|---|---|
| ★ `tex_backdrop_city_sky.png` | 1024×1024 | 櫃體背板的印刷畫（S06、S09、S14 的天空） | `Flat printed backdrop painting for a miniature diorama: night sky with heavy blue-grey storm clouds, a burning ruined city skyline along the bottom third (dark silhouettes, orange fire glow, a few lit windows). NO MOON (the moon is a real lamp). Painterly matte-painting style, slightly visible print texture, straight-on view, no perspective distortion, fills the entire frame.` |
| `tex_arcade_bokeh_plate.png` | 1024×1820 | S15–S16 Nova 身後的遊樂場背景 | `Out-of-focus arcade interior at night, strong magenta, cyan and purple bokeh circles from other machines and neon signs, dark floor, no readable text, no people, vertical composition.` |
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
| `thumb_cover.png` | 封面 | 用 S09 的算圖成品 + 標題字，最後再做；**不要用壓制畫面**（縮圖的血腥判定比較嚴格） |
| `fx_rain_overlay` | 機台內鏡頭的雨 | 不用生圖：用 OpenMontage 合成時疊上雨的素材影片，或在 Blender 用粒子系統做；S15 穿過玻璃時切掉 |

---

## 7. 品質檢查（每張圖生成後檢查）

- [ ] 透明背景是真的透明（不是畫出來的格子圖案）
- [ ] 全身完整、腳底貼齊畫面下緣
- [ ] Rin：**成人比例**；S03 之後的圖**左腳光腳**；血腥只有擦傷和血漬，沒有傷口特寫
- [ ] 喪屍：觸手只從肩膀 / 背部長出來；觸手纏手臂或腳踝，不纏脖子；沒有內臟
- [ ] 壓制三層：同一個低角度、光線一致；衣服撕扯不露出軀幹
- [ ] Nova：黃綠色髮夾的位置跟設定圖同一側、外套袖口有拉鍊口袋
- [ ] 光線方向一致（冷光從左上、綠色邊光從右側）
- [ ] 圖裡沒有多出來的文字、浮水印、地面、陰影
