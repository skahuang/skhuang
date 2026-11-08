# 差一點 / ALMOST — 第七批材質需求（大物件單張材質）

場景裡還有幾個體積大、畫面上很顯眼，卻只有純色的物件。
這批**不是平鋪的連續圖**，而是「一個物件一張完整的圖」，整張貼在物件的主要那一面上，所以每台機器、每個座椅都有自己的樣子。
做好後放進 `almost-short/assets/textures/`（或像之前一樣打包上傳），檔名照表格。
腳本已經接好：有圖就用，沒圖就維持現在的純色，可以分批做。★ = 先做（鏡頭最常看到的）。

## 風格鎖定（每張都貼在提示詞最前面）

電玩店物件（#1–#7）：

```text
STYLE LOCK: match the night arcade reference — cyan and magenta neon, dark blue steel, glossy plastic, slightly worn and scuffed.
Straight-on orthographic view of ONE flat face, image FILLS THE FRAME edge to edge, flat even lighting, no perspective, no baked glow or shadows.
NOT a repeating pattern: one complete unique panel with a clear top, bottom and edges.
NO readable real-world text, NO real brand logos or existing game characters, NO watermark. Invented glyphs and original characters only.
```

娃娃機內頂樓物件（#8–#11）：

```text
STYLE LOCK: post-apocalyptic rainy night city, cold blue fog palette with sickly green and neon cyan/pink accents, weathered and grimy.
Straight-on orthographic view of ONE flat face, image FILLS THE FRAME edge to edge, flat even lighting, no perspective, no baked glow or shadows.
NOT a repeating pattern: one complete unique object surface with natural edges.
NO readable real-world text, NO real brand logos, NO watermark. Invented glyphs and icons only.
```

## 電玩店（娃娃機外，真實尺寸）

| # | 檔名 | 尺寸 | 貼在哪裡 | 提示詞（接在 STYLE LOCK 後面） |
|---|---|---|---|---|
| ★1 | `tex_arcade_cab_side.png` | 768×1920 | 三台直立街機的側板（0.7m 深 × 1.75m 高，現在全黑） | `Side panel artwork of an original upright arcade cabinet, tall portrait 2:5: big sweeping cyan and magenta shapes, an original space pilot character silhouette, invented glyph title running vertically, black t-molding edge, scuffs and sticker residue near the bottom kick plate.` |
| ★2 | `tex_claw_machine_yellow.png` | 1024×1024 | 黃色鄰台娃娃機的下半部機身正面 | `Lower front panel of an original yellow claw crane machine, square 1:1: glossy yellow plastic, a dark prize-door opening in the lower middle, a coin slot plate on the right, cute original cartoon plush icons and stars printed on it, invented glyph sticker, scratched corners and kick marks at the bottom.` |
| ★3 | `tex_control_panel_top.png` | 1024×448 | 主角娃娃機的操作台面（俯視，搖桿在左 25%，大按鈕在右 75%） | `Top view of a claw machine control panel overlay, wide 16:7: printed artwork on dark blue plastic, four-direction arrow ring printed around a joystick spot at 25% from the left, a glowing ring printed around a big button spot at 75% from the left, invented glyph instructions as small icons, worn shiny patches where hands rest.` |
| ★4 | `tex_racing_seat.png` | 1024×1024 | 兩台賽車機的座椅面和椅背 | `Front view of a racing-game bucket seat cushion, square 1:1: black faux leather with cyan stitched panels and side bolsters, a magenta invented-glyph emblem in the middle, cracked and peeling vinyl, worn shiny patches, one taped repair.` |
| 5 | `tex_racing_base.png` | 1024×2048 | 賽車機底座頂面（0.75m × 1.5m，人踩的平台） | `Top view of an arcade racing machine floor platform, portrait 1:2: black diamond-plate steel, yellow and black hazard edge strips, a scuffed footrest area, a small invented-glyph warning icon, dirt and gum stains.` |
| 6 | `tex_racing_dash.png` | 1024×448 | 賽車機方向盤前的儀表台面 | `Dashboard panel of an original racing arcade machine, wide 16:7: two round speed and rev gauges with invented symbols, a gear-shift diagram icon, start button ring, glossy black plastic with cyan trim lines, fingerprints and scratches.` |
| 7 | `tex_ceiling_whole.png` | 4096×4096 | 電玩店天花板（12m × 12m 一整張，不重複） | `Bottom view of a whole old arcade ceiling, square: grid of dropped ceiling panels, several water-stained and sagging, two missing panels showing black ducts, a few cable runs and a big rust-brown leak stain, very dark grey overall.` |

## 娃娃機內頂樓（1:60 模型）

| # | 檔名 | 尺寸 | 貼在哪裡 | 提示詞（接在 STYLE LOCK 後面） |
|---|---|---|---|---|
| ★8 | `tex_tarp_patched.png` | 1024×768 | 營地帳篷的兩片防水布 | `A worn blue plastic tarp sheet, landscape 4:3: faded and sun-bleached, grommets along the edges, a large duct-tape patch, a sewn grey canvas patch, mud splashes and dark water stains along the bottom edge.` |
| 9 | `tex_sleeping_bag.png` | 1024×512 | 營地的睡袋 | `Top view of a used orange sleeping bag lying flat, landscape 2:1: quilted nylon channels, a half-open zipper along one side, a dark hood end, grease stains, a blanket patch sewn on.` |
| 10 | `tex_ac_fan_top.png` | 512×512 | 屋頂冷氣外機的風扇頂面 | `Top view of an outdoor air-conditioner fan grille, square: round black wire grille over dark fan blades, rust spots, dead leaves and dirt caught in the grille, a stained metal frame around it.` |
| 11 | `tex_crate_side.png` | 512×512 | 營地當椅子坐的木箱 | `Side face of an old wooden supply crate, square: horizontal planks with dark gaps, a faded stencilled invented-glyph mark and arrow, rusty nails at the corners, damp dark grain and mould at the bottom edge.` |

## 小提醒

- 這批每一張都是**整張貼在一個面上**，請填滿畫面，不要留白邊、外框或投影。
- 請**不要**做成可平鋪的花紋，要有上下左右的「頭尾」，像真的一塊板子。
- 側板和座椅上的角色、標誌請用**原創設計**，不要像任何現有遊戲或品牌。
- #3 操作台面要跟模型對位：搖桿在左邊約 1/4 處、大按鈕在右邊約 3/4 處。
