# 差一點／ALMOST 動作素材 v2

PNG 位於 `almost-short/assets/sprites/`，格序由左到右，再由上到下。P0 為 P1–P3 首格的原比例疊合定稿，放大到 1024×1024 供核對。

| 編號 | 檔名 | 鏡頭 | 整張尺寸 | 格數／單格 |
|---|---|---|---|---|
| P0 | `pin_master_frame.png` | 定稿 | 1024×1024 | 單張 |
| P1 | `pin_layer_rin_sheet.png` | S13a、S14 中層 | 2048×1536 | 4×3／512×512 |
| P2 | `pin_layer_back_sheet.png` | S13a、S14 後層 | 2048×1536 | 4×3／512×512 |
| P3 | `pin_layer_front_sheet.png` | S13a、S14 前層 | 2048×1536 | 4×3／512×512 |
| P4 | `pin_takedown_rin_sheet.png` | S12d 中層 | 1536×1024 | 3×2／512×512 |
| P5 | `pin_takedown_back_sheet.png` | S12d 後層 | 1536×1024 | 3×2／512×512 |
| P6 | `pin_takedown_front_sheet.png` | S12d 前層 | 1536×1024 | 3×2／512×512 |
| P7 | `pin_face_closeup_sheet.png` | S13b 臉部特寫 | 2048×768 | 4×3／512×256 |
| B1 | `rin_scoot_back_sheet.png` | S12b 後挪 | 1024×1024 | 4×2／256×512 |
| B2 | `rin_grabbed_down_sheet.png` | S12c 拖倒 | 2048×1536 | 4×3／512×512 |
| B6 | `rin_slip_shock_sheet.png` | S10 鬆手 | 1024×1024 | 4×2／256×512 |
| B7 | `rin_run_to_ladder_sheet.png` | S04 開頭 | 768×1024 | 3×2／256×512 |

## 疊層與銜接

- S13a、S14 由後至前疊 P2 → P1 → P3，三層共用畫布原點、比例、相位和 12 格循環。接觸手和觸手已包含在殭屍層。
- S12d 由後至前疊 P5 → P4 → P6，三層同格播。三層第 6 格分別與 P2、P1、P3 的首格一致。
- S12c 用方形 12 格 B2，末格與 P1 首格一致。B2 首格承接 B1 末格的姿勢，再依新方格的人物比例定位。
- S13b 使用寬幅 12 格 P7，依原特寫鏡頭配置播放。
- B1、B6、B7 的規格與上一版一致，沿用已複檢畫格。

複檢依方形畫布上的 2D 疊合與交接畫格進行。匯入原場景時，三層使用相同位置和縮放。
