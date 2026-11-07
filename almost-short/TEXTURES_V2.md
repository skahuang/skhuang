# 差一點 / ALMOST — 第二批材質需求（照參考圖升級）

放進 `almost-short/assets/textures/`，檔名照表格。腳本找到新檔就自動換上，找不到就繼續用第一批的材質，所以可以分批做。

## 風格鎖定（每張都貼在提示詞最前面）

```text
TEXTURE LOCK: match the attached reference images — rainy night in a ruined city, cold blue moonlight, sickly green
emergency lights, everything wet. Photographed straight-on, orthographic, flat EVEN lighting (no baked shadows,
no strong highlights, no perspective), NO text, NO watermark, NO people.
For tileable maps: SEAMLESS TILEABLE square texture, left edge matches right edge, top matches bottom.
```

附上參考圖：做牆、窗、鐵捲門時附建築那幾張；做水塔附水塔圖；做夾爪附兩張夾爪圖。

## 清單

| # | 檔名 | 尺寸 | 平鋪 | 套在哪裡 | 提示詞（接在風格鎖定後面） |
|---|---|---|---|---|---|
| ★1 | `tex_facade_stained.png` | 1024×1024 | 是 | 主建築外牆 | `Weathered pale grey concrete apartment wall, large patches of peeled plaster showing darker concrete, long black rain streaks running down, green-black moss and creeping ivy patches near the bottom, small cracks and chips. No windows, no doors.` |
| ★2 | `tex_window_broken.png` | 512×512 | 否（整張） | 主建築窗戶（隨機約七成） | `Front view of ONE old apartment window filling the whole frame: rusty dark metal frame with a cross mullion, glass mostly shattered with jagged shards, pitch-black interior behind, grime on the sill. Square.` |
| 3 | `tex_window_boarded.png` | 512×512 | 否 | 主建築窗戶（隨機約三成） | `Front view of ONE old window filling the whole frame, boarded up with 3-4 weathered grey-brown planks nailed diagonally and horizontally, gaps showing black interior, rusty nails. Square.` |
| ★4 | `tex_shutter_rolling.png` | 1024×512 | 否 | 一樓鐵捲門 | `Front view of a closed, dented corrugated metal roller shutter filling the whole frame, horizontal ribs, dark grey-green paint, rust streaks, dirty bottom edge, faint graffiti-free. Wide 2:1.` |
| ★5 | `tex_roof_puddle_mask.png` | 1024×1024 | 是 | 屋頂積水（控制反光） | `GREYSCALE MASK ONLY: irregular puddle shapes in pure BLACK on a WHITE background, organic rain-puddle outlines of varying size covering about 35% of the area, soft 2-pixel edges, no other detail.` |
| ★6 | `tex_tank_galvanized.png` | 1024×1024 | 是 | 水塔桶身、蓋子 | `Galvanized steel water-tank sheet: mottled silver-grey zinc spangle pattern, horizontal riveted seams, orange rust blooming around the rivets and dripping down in streaks, a faint green tint from grime.` |
| ★7 | `tex_chrome_scratched.png` | 1024×1024 | 是 | 夾爪機身與爪子、軌道 | `Polished chrome steel surface with fine circular brushing and light scratches, a few fingerprint smudges and tiny dents, neutral grey (no coloured reflections baked in).` |
| 8 | `tex_cable_corrugated.png` | 512×512 | 是 | 夾爪的黑色波紋管 | `Black corrugated plastic conduit hose seen from the side, evenly spaced horizontal ribs filling the frame, slightly dusty, satin sheen.` |
| 9 | `tex_parapet_moss.png` | 1024×1024 | 是 | 屋頂女兒牆、樓梯間 | `Top surface and side of a thick concrete roof parapet: rough grey concrete, dark water stains, bright green moss growing in the cracks and along edges, a few fallen leaves.` |
| ★10 | `tex_backdrop_ruins_fog.png` | 1024×1024 | 否 | 櫃體背板（取代第一批的天空背板） | `Flat printed backdrop painting: endless ruined city at night seen from a rooftop, collapsed skyscrapers and broken apartment blocks fading into thick blue fog, a few sickly GREEN street lights and windows glowing, low heavy clouds, NO moon, NO fire. Painterly matte painting, straight-on, fills the frame.` |
| 11 | `tex_ruins_facade.png` | 1024×1024 | 是 | 遠方廢墟大樓 | `Facade of a dark derelict apartment block: grid of small black broken windows, one or two faint green lit windows, collapsed balcony slabs, soot and water stains, blue-grey concrete.` |

★ = 先做，影響最大的 6 張。

## 小提醒
- 平鋪的圖做好後排成 2×2 看接縫，有明顯接縫就請 GPT「make the edges wrap seamlessly」重做。
- `tex_roof_puddle_mask.png` 只要黑白圖，不要有顏色，黑色是積水（會變成鏡面反光）。
- 窗戶、鐵捲門是整張貼在單一物件上，不需要無縫。
