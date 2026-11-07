# 差一點 / ALMOST — GPT 素材生成清單（2D 逐幀版）

**用法：** 每次生成都**附上參考圖**（你原本的 Rin 設定圖、Rin 六姿勢圖、Nova 設定圖、喪屍設定圖），先貼「風格鎖定」，再貼該素材的提示詞。
產出的 PNG 用**表格裡的檔名**放進 `assets/sprites/` 或 `assets/textures/`，重跑 Blender 腳本就會自動套用並開始逐格播放。

- ★ = 最優先，先做這 5 組，確認動作和風格
- **調性：驚悚、有受傷感、不血腥。** 可以有擦傷、瘀青、髒污、撕破的衣服、紅腫的抓痕；**不要有流血、血跡、血滴、傷口特寫**
- **Rin 維持原本的風格**：你上傳的 RIN 設定圖和六姿勢圖就是標準，不做任何修改

---

## 0. 逐幀組圖怎麼做

每個動作是**一張 PNG 組圖**，格子由左到右、由上到下排列，檔名是 `<名稱>_sheet.png`。Blender 會自動切格，用每秒 12 張或 8 張播放。

| 規則 | 內容 |
|---|---|
| 格子 | 依表格的「格數」排列，例如 `4×2` = 4 欄 2 列共 8 格 |
| 尺寸 | 每格 256×512（直式角色）；橫式的壓制圖層每格 512×256 |
| 背景 | **透明**，格子之間不要有框線、數字或文字 |
| 位置 | 每一格角色的**腳底都對齊格子下緣、身體在格子中央**，否則播放時會跳動 |
| 一致性 | **同一張圖裡畫完整組動作**，GPT 在同一張圖裡比較能保持服裝和臉一致 |
| 預留邊界 | 角色不要碰到格子邊緣（四周留 5% 空白），避免切格時被切到 |

> **如果組圖一直對不齊：** 先只生成第 1 格和最後一格（關鍵姿勢），確認後再請 GPT「在這兩張之間補 6 張中間動作，排成 4×2」。也可以放單張 `<名稱>.png`，腳本會當成靜止圖使用，之後再換成組圖。

> **張數、速度與播放方式**都寫在 `blender/build_almost_scene.py` 開頭的 `ANIM` 表。播放方式有三種：`loop`（循環）、`once`（播一次後停在最後一格）、`pingpong`（來回播放，適合呼吸、掙扎這類動作）。

---

## 1. 風格鎖定（每次都貼在最前面）

### 機台內角色（Rin、喪屍）

```text
STYLE LOCK: same look as the attached RIN reference sheet and pose sheet — stylized 3D-animated feature-film character
(soft skin, big expressive brown eyes, chunky readable shapes). Each figure is a clean cutout for a 2D acrylic standee.
TRANSPARENT BACKGROUND, no floor, no cast shadow, no grid lines, no numbers, no text.
Lighting: cool blue moonlight key from upper-left, thin green rim light from the right, subtle warm orange bounce from below.
Keep the outfit, colours, face and proportions EXACTLY the same as the reference. Do not age her up or redesign her.
Tone: survival horror with INJURIES BUT NO BLOOD — scrapes, bruises, dirt, reddened scratch marks, torn clothes are fine;
absolutely no blood, no dripping liquid, no open wounds. The torn red hoodie edges are DRY FABRIC fringe, not liquid.
```

### 現實世界（Nova）

```text
STYLE LOCK: stylized 3D-animated feature-film character look, same character as the attached NOVA reference sheet
(short lavender-grey bob, lime-green square hair clip on the same side as in the reference, small silver hoop earrings, oversized purple satin bomber jacket
with a sleeve zip pocket, black turtleneck, wide black cargo pants with a lavender side stripe, chunky purple-white sneakers).
TRANSPARENT BACKGROUND, no grid lines, no numbers, no text.
Lighting: arcade neon — magenta key from the left, cyan rim from the right, soft purple fill.
```

### 組圖開頭（每張組圖的提示詞前都加）

```text
SPRITE SHEET for frame-by-frame 2D animation: {COLS} columns x {ROWS} rows, {N} frames read left-to-right, top-to-bottom.
Every cell is the same size, the character is the same size and centred in every cell, feet aligned to the bottom of the cell,
5% empty margin around the figure. Consecutive frames change only slightly so the motion is smooth.
```

---

## 2. 參考圖（直接用你現有的，不用重做）

| 參考圖 | 用途 |
|---|---|
| 你的 **RIN 設定圖** | 所有 Rin 組圖都附上：服裝、臉、比例的標準 |
| 你的 **Rin 六姿勢圖** | 關鍵姿勢參考，對應如下表 |
| 你的 **NOVA 設定圖** | 所有 Nova 組圖都附上 |
| 你的 **ROOFTOP ZOMBIES / Z01 設定圖** | 所有喪屍組圖都附上 |

**Rin 六姿勢圖 → 對應的鏡頭**（上排左→右是 1–3，下排左→右是 4–6）：

| 姿勢 | 動作 | 拿來當哪一組的關鍵格 |
|---|---|---|
| 1 坐倒、伸手擋 | 跌坐在地上往後退 | `rin_impact` 最後一格、`rin_backing_away` |
| 2 躺地踢腳、手遮頭 | 仰躺踢開喪屍 | `rin_boot_grab` 中段 |
| 3 坐地伸手、一腳靴子 | 往後撐、伸手阻擋 | `rin_backing_away` 最後一格 |
| 4 抱膝縮成一團 | 害怕發抖 | `rin_cling_scared`（改成抓梯子的版本） |
| 5 躺地高舉腳踢 | 用力踢 | `rin_boot_grab` 第 3–6 格 |
| 6 趴地往前爬、伸手 | 想爬走 | `pin_layer_rin` 的掙扎動作 |

**鞋子規則：** S03（第 6 秒）以前兩腳都穿靴子；S03 之後**左腳光腳**。

---

## 3. Rin 逐幀組圖（`assets/sprites/`）

先貼「機台內角色」風格鎖定 + 組圖開頭，附上 Rin 設定圖和六姿勢圖。

| 檔名 | 鏡頭 | 格數 / 速度 | 動作（每格描述） |
|---|---|---|---|
| `rin_backing_away_sheet.png` | S02 | 4×2 = 8 格・12fps・循環 | `RIN stumbling BACKWARDS in fear, both boots on. Frames 1-8: a full backwards walk cycle — step back with the left foot, weight shifts, step back with the right foot, arms raised defensively in front of her chest, head turned toward something terrifying on the left, hair bouncing with each step.` |
| ★ `rin_boot_grab_sheet.png` | S03 | 4×3 = 12 格・12fps・播一次 | `Low angle close to the ground. A grey-green zombie hand (only the hand and wrist, entering from the left edge of every cell) grips RIN's LEFT boot. 1-3: she falls onto her back, panicking. 4-6: she kicks hard with her right foot (like pose 5 of the reference). 7-9: she yanks her leg, the boot slides off and stays in the zombie's hand. 10-12: she scrambles backwards on her hands, now barefoot on the left, reddened scratch marks on her calf (no blood).` |
| ★ `rin_climb_back_sheet.png` | S04 | 4×2 = 8 格・12fps・循環 | `BACK VIEW climbing a ladder (do NOT draw the ladder). Frames 1-8: a full climb cycle — right hand reaches up, left foot (bare) pushes, left hand reaches up, right foot (boot) pushes; hoodie fringe and hair sway; head occasionally turns so we see her cheek.` |
| `rin_cling_scared_sheet.png` | S05、S06 | 4×1 = 4 格・12fps・循環 | `RIN clinging tightly to a vertical ladder (ladder not drawn), body pressed forward, knees tucked like pose 4 of the reference. Frames 1-4: trembling — tiny shake of the shoulders, she glances down over her shoulder, eyes wet with tears, then squeezes her eyes shut.` |
| ★ `rin_cling_hope_sheet.png` | S07–S09 | 4×2 = 8 格・8fps・來回 | `RIN holding the ladder with one hand (ladder not drawn), looking UP at a bright light. Frames 1-8: she slowly stretches her free hand upward, chest rising with a deep breath, her face changes from fear to hope to a small relieved smile, light growing in her eyes, hair lifting in the wind.` |
| `rin_slip_shock_sheet.png` | S10 | 4×2 = 8 格・12fps・播一次 | `RIN on the ladder (not drawn). Frames 1-8: the smile freezes, her hands jolt as the ladder shakes, fingers slide off one by one, the last frame shows both hands open, body tipping backwards, eyes wide in shock.` |
| `rin_falling_sheet.png` | S11 | 3×2 = 6 格・12fps・循環 | `RIN falling backwards through the air, full figure, no ground, raindrops around her. Frames 1-6: a flailing loop — arms and legs windmill, one hand keeps reaching up toward something above, hair and hoodie fluttering upward, mouth open screaming.` |
| `rin_impact_sheet.png` | S12 | 4×2 = 8 格・12fps・播一次 | `Low camera near the ground. Frames 1-8: RIN slams onto a wet rooftop on her side with a big WATER SPLASH (frames 1-2), bounces slightly (3), the splash falls (4-5), she winces and pushes herself up on one elbow, ending in pose 1 of the reference (6-8). Draw the water splash, no floor. Scrapes and a bruise on her arm, no blood.` |
| `rin_reset_lookup_sheet.png` | S17b | 4×2 = 8 格・12fps・播一次 | `Slightly HIGH camera above her. RIN standing in the middle of a rooftop (rooftop not drawn). Frames 1-8: she slowly tilts her head back until she is looking straight UP INTO THE CAMERA, expression shifting from confusion to quiet realisation, as if she can see the player outside the glass. Same scrapes and dirt as before, no blood.` |

---

## 4. 壓制畫面三層組圖（S13–S14，`assets/sprites/`）

附上你之前那三張壓制圖當**構圖參考**，三層要在**同一次對話裡**連續生成，用**同一個低角度、貼地的視角**。
三層在 Blender 裡前後排開，鏡頭拉遠時會有視差。格子是**橫式**，每格 512×256。

**動作原則：** 喪屍是**抓、拉、壓住**，不咬、不打、不流血。觸手纏手臂和腳踝，**不纏脖子**；外套被扯但**不露出身體**。

| 檔名 | 層 | 格數 / 速度 | 提示詞 |
|---|---|---|---|
| ★ `pin_layer_rin_sheet.png` | 中層：倒地的 Rin | 4×2 = 8 格・8fps・來回 | `ONLY RIN (exactly as in the reference sheet), lying on her stomach on the ground like pose 6 of the pose sheet, cheek near the floor, eyes straining UPWARD. Her red hoodie is being pulled back at the shoulder (the hands are NOT drawn). Frames 1-8: she struggles — reaches forward, claws at the ground, twists her shoulders, kicks her bare left foot, grits her teeth, glances up. Scrapes, dirt and wet hair, no blood. Transparent background, no zombies, no floor.` |
| `pin_layer_back_sheet.png` | 後層：警察 + 黃雨衣 | 3×2 = 6 格・8fps・來回 | `ONLY the two zombies BEHIND her: Z03 the huge police zombie leaning forward, both fists gripping and tugging a red hoodie (the red fabric runs to the bottom edge of the cell), and Z04 the yellow raincoat zombie reaching down, tentacles curling toward the ground. Frames 1-6: Z03 tugs back and forth, Z04's tentacles writhe and coil, both roar. No blood. Transparent background, no girl, no floor.` |
| `pin_layer_front_sheet.png` | 前層：觀光客 + 工人 | 3×2 = 6 格・8fps・來回 | `ONLY the two zombies IN FRONT, closest to camera: Z02 the teal tourist zombie on the left crouched low, pressing both hands down on something at the bottom edge (an arm, not drawn), and Z01 the orange mechanic zombie on the right pressing down on something at the bottom edge (her head, not drawn). Frames 1-6: they lean and press harder, heads jerk, mouths snap open snarling. No blood. Transparent background, no girl, no floor.` |
| `pin_keyframe_close.png`（選用） | 單張特寫 | — | 如果拆層對不齊，可以生成一張完整的 9:16 特寫（含背景），合成時當 S13 的插入畫面，再接回 Blender 的 S14 拉遠：`Recreate the attached pinned close-up as a vertical 1080x1920 frame with RIN exactly as in her reference sheet, the same four zombies, rain, wet reflective rooftop tiles. Injuries but NO blood. Clothes tugged but not exposing skin, tentacles wrapped around her arm and ankle, not her neck.` |

> **對齊技巧：** 在 Blender 選 `pin_layer_back / pin_layer_rin / pin_layer_front` 三個物件，調整 Z 高度和左右位置，讓扯外套的手剛好接到 Rin 的肩膀。

---

## 5. 喪屍逐幀組圖（`assets/sprites/`）

先貼「機台內角色」風格鎖定 + 組圖開頭，附上喪屍設定圖。

**檔名規則：** `zombie_<變體>_<姿勢>_sheet.png`，共 12 張（4 個變體 × 3 個姿勢）。腳本會自動錯開每隻喪屍的播放時間，看起來不會整齊劃一。
- 變體：`z01_mechanic`、`z02_tourist`、`z03_cop_brute`、`z04_raincoat`
- 姿勢：`walk`、`reach`、`climb`

**通用規則：** 觸手只從肩膀和背部長出來；每個變體兩腳的鞋子一致；可以有腐爛的皮膚和破爛衣服，**不要有血**。

| 姿勢 | 格數 / 速度 | 提示詞（把 `<ZOMBIE>` 換成變體描述，例如 `Z01, the orange-coverall mechanic zombie`） |
|---|---|---|
| `walk` | 4×2 = 8 格・12fps・循環 | `<ZOMBIE> shambling forward. Frames 1-8: a full limping walk cycle — one foot drags, arms half raised and swinging loosely, head lolling side to side, tentacles swaying.` |
| ★ `reach`（先做 `zombie_z01_mechanic_reach_sheet.png`） | 3×2 = 6 格・8fps・來回 | `<ZOMBIE> standing still with BOTH arms stretched UP toward the sky. Frames 1-6: grasping — fingers open and close, arms stretch higher, head thrown back, jaw snapping, tentacles reaching upward.` |
| `climb` | 3×2 = 6 格・12fps・循環 | `<ZOMBIE> seen from behind three-quarter, climbing over other bodies (not drawn). Frames 1-6: a climb cycle — one arm hooks high, knee lifts, body heaves up, other arm hooks, tentacles hooking upward.` |

---

## 6. Nova 逐幀組圖（`assets/sprites/`）

先貼「現實世界」風格鎖定 + 組圖開頭，附上 Nova 設定圖。

| 檔名 | 鏡頭 | 格數 / 速度 | 提示詞 |
|---|---|---|---|
| ★ `nova_back_joystick_sheet.png` | S15 | 4×2 = 8 格・12fps・循環 | `BACK VIEW, full body, NOVA at an arcade claw machine (machine NOT drawn). Frames 1-8: left hand jiggles a joystick left and right, right hand hovers then taps a button (controls NOT drawn), shoulders tense and lean forward, hair sways slightly.` |
| `nova_profile_almost_sheet.png` | S16 | 4×3 = 12 格・8fps・播一次 | `Three-quarter PROFILE, waist up but the figure still reaches the bottom of the cell. Frames 1-12: NOVA winces (the ALMOST expression from her sheet), shuts her eyes, lets out a long exhale with slumping shoulders, opens her eyes half-lidded, then glances down to her left at the prize chute with a BORED look. Magenta and cyan neon on her cheek.` |
| `nova_hand_coin_sheet.png` | S17a | 4×2 = 8 格・12fps・播一次 | `Close-up of NOVA's right hand only, ribbed black cuff and purple jacket cuff visible. Frames 1-8: she flips a silver arcade token with her thumb (1-3), catches it (4), pinches it (5), pushes it forward and down into a slot (6-8, slot NOT drawn, the token disappears in frame 8).` |
| `nova_smirk_alt_sheet.png`（備用） | S16 替代 | 4×2 = 8 格・8fps・播一次 | `Same framing as the profile shot: NOVA's face goes from the ALMOST look into the SMIRK from her sheet, one corner of her mouth rising, while she flips a coin.` 可以做「她其實是故意的」另一種結局 |

---

## 7. 背景與貼圖（`assets/textures/`）

這些**不用透明背景**，也不用做成逐幀組圖。

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

## 8. 合成用素材（交給 OpenMontage compose）

| 素材 | 用途 | 說明 |
|---|---|---|
| `ui_timer_font` | 全片右上角倒數 | 不用生圖，Remotion 用七段顯示器字型（例如 DSEG7）即可 |
| `card_last_survivor` / `card_almost` / `card_one_more` | 三張文字卡 | 建議直接用字型排版，不要用生圖（AI 生成的中文字常出錯） |
| `fx_rain_overlay` | 機台內鏡頭的雨 | 合成時疊上雨的素材影片，或在 Blender 用粒子系統做；S15 穿過玻璃時切掉 |
| `thumb_cover.png` | 封面 | 用 S09 的算圖成品 + 標題字，最後再做；不要用壓制畫面 |

---

## 9. 總張數估計

| 類別 | 組圖數 | 總格數 |
|---|---|---|
| Rin | 9 | 70 |
| 壓制三層 | 3 | 20 |
| 喪屍 | 12 | 80 |
| Nova | 3 | 28 |
| **合計** | **27 張組圖** | **約 198 格** |

建議順序：先做 5 組 ★ → 放進 Blender 看動作 → 確認 OK 再生其他組圖。

---

## 10. 品質檢查（每張組圖生成後檢查）

- [ ] 背景是真的透明（不是畫出來的格子圖案）；格子之間沒有框線或數字
- [ ] **每一格角色大小相同、腳底對齊格子下緣**（不然播放時會跳）
- [ ] 格數和排列跟表格一致（例如 4×2 就是 8 格）
- [ ] 前後格的服裝、髮型、臉一致，沒有突然換衣服
- [ ] Rin：**跟原本設定圖一模一樣**；S03 之後左腳光腳；有擦傷、髒污，**沒有血**；紅外套破邊是乾的布料，不像在滴
- [ ] 喪屍：觸手只從肩膀 / 背部長出來；沒有血；壓制畫面只有抓、拉、壓
- [ ] Nova：黃綠色髮夾的位置跟設定圖同一側、外套袖口有拉鍊口袋
- [ ] 光線方向一致（冷光從左上、綠色邊光從右側；Nova 是洋紅色從左、青色從右）
