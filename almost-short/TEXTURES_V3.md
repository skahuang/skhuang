# 差一點 / ALMOST — 第三批材質需求（機台與電玩店）

放進 `almost-short/assets/textures/`，檔名照表格。找到新圖就自動換上，找不到就先用純色或舊圖，可以分批做。

## 風格鎖定（每張都貼在提示詞最前面）

```text
TEXTURE LOCK: match the attached claw-machine five-view sheet and the night arcade reference — dark blue painted steel,
brushed stainless trim, cyan and magenta neon, polished dark floor. Photographed straight-on, orthographic,
flat EVEN lighting (no baked shadows, no neon glow baked in, no perspective), NO readable text, NO logos, NO watermark.
For tileable maps: SEAMLESS TILEABLE square texture, left edge matches right edge, top matches bottom.
```

做機台相關的圖附五視圖；做店內的圖附電玩店那張。

## 機台

| # | 檔名 | 尺寸 | 平鋪 | 套在哪裡 | 提示詞（接在風格鎖定後面） |
|---|---|---|---|---|---|
| ★1 | `tex_cab_body_bluesteel.png` | 1024×1024 | 是 | 機身下半部、背板 | `Dark navy-blue powder-coated sheet steel, fine orange-peel texture, light scuffs and edge wear showing grey metal, a few small dents and fingerprints.` |
| ★2 | `tex_steel_brushed.png` | 1024×1024 | 是 | 四角立柱、頂框、控制盒 | `Brushed stainless steel, fine straight horizontal grain, faint scratches, slightly dull satin finish, neutral grey.` |
| ★3 | `tex_vent_grille.png` | 512×512 | 否（整張） | 正面左下的散熱網 | `Front view of a square perforated metal speaker grille filling the frame: dense grid of small square holes, black interior behind, dark gunmetal, thin rounded frame.` |
| 4 | `tex_louver_vent.png` | 512×512 | 否 | 側面、背面的百葉散熱孔 | `Front view of a stamped metal louver vent filling the frame: 8 horizontal angled slats, dark blue painted steel, black gaps.` |
| ★5 | `tex_coin_mech.png` | 512×1024 | 否 | 投幣口面板 | `Front view of an arcade coin-door mechanism plate filling the frame, portrait 1:2: chrome plate with a vertical coin slot near the top, a small coin-return flap below, four corner screws, no text.` |

## 電玩店

| # | 檔名 | 尺寸 | 平鋪 | 套在哪裡 | 提示詞 |
|---|---|---|---|---|---|
| ★6 | `tex_arcade_floor_tiles.png` | 1024×1024 | 是 | 店內地板 | `Top-down dark charcoal porcelain floor tiles, large 2 x 2 grid of square tiles with thin grout lines, polished but worn, faint scuff marks and dried water spots.` |
| 7 | `tex_concrete_pillar.png` | 1024×1024 | 是 | 水泥柱 | `Raw grey concrete column surface with formwork lines, small bug holes, dark stains near the bottom, a few old tape marks.` |
| 8 | `tex_hazard_stripes.png` | 512×512 | 是 | 柱角的黃黑警示護角 | `Worn yellow and black 45-degree diagonal hazard stripes on metal, chipped paint and scratches.` |
| 9 | `tex_poster_arcade.png` | 512×768 | 否 | 柱子上的海報 | `Retro arcade game poster, portrait 2:3: a cute cartoon hero jumping over pixel monsters, bold magenta-cyan colours, decorative frame. NO readable text, NO real game or brand.` |
| 10 | `tex_arcade_screen.png` | 1024×768 | 否 | 街機螢幕、販賣機正面 | `Bright pixel-art arcade attract screen, 4:3: colourful side-scrolling level with platforms and stars, glowing CRT scanlines. NO text, NO real game.` |
| ★11 | `tex_plush_pile.png` | 1024×512 | 否 | 旁邊娃娃機裡的娃娃 | `Front view through glass of a heap of cute generic plush toys (cats, bears, bunnies) in pastel pink, cream and lavender, filling the frame, 2:1. Original designs, NO characters from existing brands.` |
| 12 | `tex_claw_machine_pink.png` | 1024×1024 | 否 | 旁邊娃娃機機身 | `Front panel decal for a pink-and-white claw machine body: white glossy panel with big magenta and lavender stars, soft gradient, square. No text.` |

★ = 先做這 6 張。

## 小提醒
- 平鋪圖排成 2×2 檢查接縫。
- 投幣口、散熱網、海報、螢幕是整張貼在一個面上，不用無縫。
- 不要把霓虹光暈畫進材質裡，光由場景燈光負責。
