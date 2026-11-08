# 差一點 / ALMOST — 第八批材質需求（頂樓曬衣繩的衣物）

給樓梯間門外重做的曬衣繩用：兩件上衣、一件褲子、毛巾和襪子、兩條毯子。
做好後放進 `almost-short/assets/textures/`（或像之前一樣打包上傳），檔名照表格。
腳本已經接好：沒圖之前先借用現有的布料圖（雨棚條紋、防水布、睡袋），有圖就自動換上。★ = 先做。

## 風格鎖定（每張都貼在提示詞最前面）

```text
STYLE LOCK: post-apocalyptic rainy night city, cold blue fog palette with sickly green and neon cyan/pink accents, weathered and grimy.
Straight-on orthographic view of ONE flat piece of fabric hanging flat, image FILLS THE FRAME edge to edge, flat even lighting, no perspective, no baked shadows.
NOT a repeating pattern: one complete garment surface with natural edges, seams and wear.
NO readable real-world text, NO real brand logos, NO watermark. Invented glyphs and icons only.
```

## 清單

| # | 檔名 | 尺寸 | 用在哪裡 | 提示詞（接在 STYLE LOCK 後面） |
|---|---|---|---|---|
| ★1 | `tex_cloth_shirt.png` | 512×512 | 上衣（前排第一件、毛巾之一） | `Front of a faded grey-white cotton t-shirt laid flat, square: stretched collar, a small invented-glyph print on the chest, yellowed sweat stains, a mended tear, frayed hem.` |
| ★2 | `tex_cloth_pants.png` | 512×768 | 褲子 | `Front of worn dark blue work trousers laid flat, portrait 2:3: patched knees, faded seams, mud on the cuffs, a stitched pocket.` |
| ★3 | `tex_cloth_blanket.png` | 1024×768 | 掛在繩上的紅色毯子 | `An old dark red wool blanket, landscape 4:3: faded checker weave, blanket-stitch edge, moth holes, a darker water stain.` |
| 4 | `tex_cloth_shirt_b.png` | 512×512 | 第二件上衣（藍色） | `Front of a navy blue hoodie laid flat, square: front pocket, drawstrings, bleached patches, a cyan invented-glyph patch sewn on the sleeve area.` |
| 5 | `tex_cloth_towel.png` | 512×768 | 毛巾、襪子、洗衣籃裡的床單 | `A thin mustard-yellow cotton towel, portrait 2:3: terry texture, two faded stripes near the ends, frayed edges, grey grime.` |
| 6 | `tex_cloth_blanket_b.png` | 1024×768 | 掛在繩上的綠色毯子 | `An olive green army-style blanket, landscape 4:3: coarse wool, a pale stencilled invented-glyph mark, darned holes, a sewn-on patch of different fabric.` |

## 小提醒

- 都是**整張貼在一個面上**，請填滿畫面，不要留白邊、衣架或背景。
- 衣服請**平放正面**，不要有人穿著，不要透視。
