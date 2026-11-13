# 差一點 / ALMOST — 第六批材質需求（電玩店新道具）

給娃娃機外電玩店新加的賽車機、扭蛋機、獎品盒和牆上電視用。
做好後放進 `almost-short/assets/textures/`（或像之前一樣打包上傳），檔名照表格。
腳本有圖就用，沒圖就維持現在的純色（賽車機和電視會先借用現有的街機畫面）。★ = 先做。

## 風格鎖定（每張都貼在提示詞最前面）

```text
STYLE LOCK: match the night arcade reference — cyan and magenta neon, dark blue steel, glossy plastic, slightly worn.
Straight-on orthographic view, image FILLS THE FRAME edge to edge, flat even lighting, no perspective.
NO readable real-world text, NO real brand logos or existing game characters, NO watermark. Invented glyphs and original characters only.
```

## 清單

| # | 檔名 | 尺寸 | 用在哪裡 | 提示詞（接在 STYLE LOCK 後面） |
|---|---|---|---|---|
| ★1 | `tex_racing_screen.png` | 1024×768 | 兩台賽車機的螢幕（會發光） | `In-game screenshot of an original retro-futuristic racing game: neon city highway at night seen from behind a hover car, speed lines, a simple HUD with invented symbols and a speed bar, 16:12 aspect.` |
| ★2 | `tex_gashapon_card.png` | 1024×512 | 扭蛋機正面的說明卡（會微微發光） | `Front display card of a capsule-toy machine, landscape 2:1: a row of six cute original mini figures (a round robot, a cloud cat, a mushroom, a ghost, a star, a dumpling) on a pastel pink and cyan background, invented glyph title, price-coin icon.` |
| 3 | `tex_prize_boxes.png` | 512×768 | 兌換櫃台後面架上的盒裝獎品 | `Front face of a toy prize box, portrait 2:3: window showing an original plush creature, bold invented-glyph logo, star bursts, pastel colours, slightly crushed corners.` |
| 4 | `tex_wall_tv_promo.png` | 1024×576 | 左牆兩台電視的畫面（會發光） | `Arcade promo screen, 16:9: a glowing claw machine icon, falling plush silhouettes, a big coin symbol and invented glyph headline, magenta and cyan gradients, scanlines.` |

## 小提醒

- 這四張都是**整張貼在一個面上**，請填滿畫面，不要留白邊或外框。
- 角色和標誌請用**原創設計**（上次的海報很像卡比，這次避開）。
