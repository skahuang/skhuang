# 差一點 / ALMOST — 第四批材質需求（遮罩、疊加層、貼花）

這批不是新的「底圖」，而是疊在現有材質上、讓同一張底圖在不同位置長出不同樣子的素材。
做好後放進 `almost-short/assets/textures/`（或像之前一樣打包上傳），檔名照表格。
腳本會「有圖就用、沒圖就用程式雜訊代替」，所以可以分批做，缺幾張也不會壞。

★ = 先做這幾張，效果最明顯。

## 風格鎖定（每張都貼在提示詞最前面）

遮罩類（#1–#5）：

```text
MASK LOCK: pure GRAYSCALE utility map for 3D texturing, no color at all. White = effect present, black = none.
Flat, evenly lit, no shadows, no perspective, no objects, NO text, NO watermark.
SEAMLESS TILEABLE square texture, left edge matches right edge, top matches bottom.
```

疊加層與貼花（#6–#12）：

```text
DECAL LOCK: post-apocalyptic rainy night city, cold blue palette with sickly green and neon cyan/pink accents,
weathered and grimy. Flat even lighting, orthographic, no baked shadows or glow.
TRANSPARENT BACKGROUND (PNG with alpha), nothing outside the shapes. NO readable real-world text, NO logos, NO watermark.
```

## 遮罩（灰階、無縫）

| # | 檔名 | 尺寸 | 用在哪裡 | 提示詞（接在 MASK LOCK 後面） |
|---|---|---|---|---|
| ★1 | `tex_mask_grime.png` | 2048×2048 | 全部建築與地面：角落、接地處的污垢 | `Irregular dirt patches and dust accumulation, clusters of different sizes, mix of soft blurry and hard-edged blotches, about 40% coverage.` |
| ★2 | `tex_mask_streaks.png` | 2048×2048 | 牆面、女兒牆外側、水塔：雨痕往下流 | `Vertical rain streaks and water run-off stains on a wall, long thin drips of varying length and width, starting at random heights and fading downward.` |
| 3 | `tex_mask_chipping.png` | 2048×2048 | 女兒牆頂、門框、機台邊角：掉漆 | `Chipped and flaking paint, small irregular chips with sharp edges, clustered unevenly, about 20% coverage.` |
| 4 | `tex_height_concrete.png` | 2048×2048 | 混凝土的細部凹凸（不只是顏色） | `Height map of weathered rough concrete: pores, pits, hairline cracks and small spalls. White = high, black = low.` |
| 5 | `tex_mask_fingerprints.png` | 2048×2048 | 機台玻璃、投幣口、按鈕周圍 | `Fingerprints, palm smudges and wipe arcs on a glossy surface, scattered clusters, most dense in the lower middle.` |

## 疊加層（彩色、透明背景、無縫）

| # | 檔名 | 尺寸 | 用在哪裡 | 提示詞（接在 DECAL LOCK 後面） |
|---|---|---|---|---|
| ★6 | `tex_moss_patches.png` | 2048×2048 | 女兒牆頂、棚屋屋頂、水塔底部 | `SEAMLESS TILEABLE. Top-down dark green damp moss and lichen patches, varied clump sizes, a few yellow-green lichen spots, about 35% coverage.` |
| 7 | `tex_rust_streaks.png` | 2048×2048 | 水塔鉚釘下、鐵門鉸鏈下、管線支架下 | `SEAMLESS TILEABLE. Orange-brown rust stains dripping downward as if from bolts and seams, varied lengths, fading at the bottom.` |

## 貼花合集（透明背景、4×4 排列，每格一個圖案）

每張排成 4×4 共 16 格，格子之間留空白，圖案不要碰到格線。

| # | 檔名 | 尺寸 | 用在哪裡 | 提示詞（接在 DECAL LOCK 後面） |
|---|---|---|---|---|
| ★8 | `decal_graffiti_atlas.png` | 2048×2048 | 廢墟立面、棚屋牆、女兒牆 | `Sprite sheet, 4x4 grid of 16 different spray-paint graffiti: abstract tags, arrows, crude symbols, a smiley, faded and dripping, cyan, pink, white and black paint, fictional letter shapes only.` |
| ★9 | `decal_stains_atlas.png` | 2048×2048 | 頂樓地面、電玩店地板 | `Sprite sheet, 4x4 grid of 16 top-down ground stains: oil puddle stains, dried water rings, a scorch mark, muddy footprints, spilled drink stain.` |
| 10 | `decal_posters_atlas.png` | 2048×2048 | 廢墟立面、電玩店牆面 | `Sprite sheet, 4x4 grid of 16 torn and weathered paper posters and flyers, faded colors, ripped edges, water damage, fictional symbols and blurred unreadable text only.` |
| 11 | `decal_cracks_atlas.png` | 2048×2048 | 頂樓地面、立面、柱子 | `Sprite sheet, 4x4 grid of 16 concrete crack patterns, thin branching hairline cracks and wider broken cracks, dark grey.` |
| 12 | `decal_signs_atlas.png` | 2048×2048 | 棚屋門、電箱、管線、機台側面 | `Sprite sheet, 4x4 grid of 16 worn industrial signs and stickers: hazard triangles, stripes, floor-number plates, pipe-label bands, numbered machine stickers, peeling and scratched, icons and numbers only.` |

## 小提醒

- 遮罩一定要是**黑白灰**，帶顏色的話腳本讀起來會不準。
- 貼花一定要**透明背景**。GPT 如果給白底，請要求「transparent background PNG」重生成一次。
- 尺寸 1024 也可以用，只是近景會比較糊。
