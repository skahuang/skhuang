# 差一點 / ALMOST — 第五批材質需求（燈具、招牌、建築細節）

這批是給新加的燈箱、看板、亮窗、防火梯和雨棚用的。
做好後放進 `almost-short/assets/textures/`（或像之前一樣打包上傳），檔名照表格。
腳本有圖就用，沒圖就維持現在的純色，可以分批做。★ = 先做這幾張。

## 風格鎖定（每張都貼在提示詞最前面）

```text
STYLE LOCK: post-apocalyptic rainy night city, cold blue fog palette with sickly green and neon cyan/pink accents,
weathered and grimy. Straight-on orthographic view, flat even lighting, no perspective, no baked glow or shadows.
NO readable real-world text, NO real brand logos, NO watermark. Invented glyphs and icons only.
```

## 清單

| # | 檔名 | 尺寸 | 平鋪 | 用在哪裡 | 提示詞（接在 STYLE LOCK 後面） |
|---|---|---|---|---|---|
| ★1 | `tex_window_lit_interior.png` | 512×512 | 否 | 廢墟大樓裡還亮著的窗（綠光） | `A single apartment window seen from outside at night, filling the frame: cracked glass, torn curtain half drawn, dim green-tinted light inside, a silhouette of a shelf and a hanging bulb.` |
| ★2 | `tex_window_lit_interior_warm.png` | 512×512 | 否 | 亮窗（暖光版） | `A single apartment window seen from outside at night, filling the frame: dirty glass, warm orange candle-like light inside, a blanket nailed up as a curtain, a plant silhouette.` |
| ★3 | `tex_signboard_vertical.png` | 256×1024 | 否 | 主建築轉角的直立燈箱招牌（會發光） | `Vertical backlit shop signboard panel, portrait 1:4, filling the frame: five stacked invented glyph-like characters (not real Chinese, Japanese or Latin letters), magenta and white on a dark plastic panel, cracked plastic, dead pixels of light, dirt at the bottom.` |
| 4 | `tex_billboard_ad.png` | 1024×512 | 否 | 後方大樓頂的廣告看板 | `Weathered rooftop billboard poster, landscape 2:1, filling the frame: faded pre-apocalypse ad for an invented soft drink with a smiling cartoon mascot (original design), peeling paper strips, rain streaks, rust stains from the top edge.` |
| 5 | `tex_metal_grating.png` | 512×512 | 是 | 防火梯的平台和樓梯 | `SEAMLESS TILEABLE. Top-down view of rusty steel bar grating, diamond-pattern expanded metal, dark gaps, orange rust in the joints.` |
| 6 | `tex_awning_torn.png` | 1024×1024 | 是 | 鐵捲門上的雨棚 | `SEAMLESS TILEABLE. Faded red and off-white striped canvas awning fabric, water stains, mould spots, a few small tears.` |

## 小提醒

- 亮窗和招牌是整張貼在一個面上，請讓內容**填滿畫面**，不要留白邊。
- 招牌上的字請用**自創的符號**，不要真的中文或英文字，避免看起來像真實店家。
- 看板吉祥物請用**原創角色**，不要像任何現有的品牌或遊戲角色。
