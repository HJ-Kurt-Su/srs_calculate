# srs_calculate
Calulate SRS profile by input time domain G level
# srs_calculate (Shock Response Spectrum Calculator)

這是一個基於 Python Streamlit 的衝擊響應頻譜 (SRS) 分析工具。
它可以根據輸入的加速度時域訊號 (Time Domain Acceleration)，利用 Smallwood 遞迴演算法計算衝擊響應頻譜 (SRS)，並支援虛擬速度 (Pseudo Velocity) 與相對位移 (Relative Displacement) 的轉換。

## 主要功能

1.  **波形產生器 (Waveform Generator)**
    *   內建標準衝擊波形模擬：半正弦波 (Half-Sine)、後峰鋸齒波 (Terminal Peak Sawtooth)、方波 (Square Wave)、梯形波 (Trapezoidal)。
    *   可自訂峰值加速度 (Peak G) 與持續時間 (Duration)。

2.  **外部資料匯入**
    *   支援上傳 CSV 或 Excel 檔案。
    *   格式要求：第一欄為時間 (Time, s)，第二欄為加速度 (Acceleration, g)。

3.  **多模式頻譜分析**
    *   **SRS (Acceleration)**: 絕對加速度響應 (g)。
    *   **Pseudo Velocity**: 虛擬速度響應 (m/s)，常用於評估衝擊能量。
    *   **Relative Displacement**: 相對位移響應 (mm)，用於評估元件碰撞風險。

4.  **互動式圖表與報告**
    *   使用 Plotly 繪製可縮放的時域圖與頻譜圖。
    *   支援調整品質因子 (Q Factor) 與頻率分析範圍。
    *   可下載計算後的頻譜數據 (.csv)。

## 安裝需求

請確保您的環境已安裝 Python 3.8+，並安裝以下套件：

```bash
pip install streamlit pandas numpy plotly openpyxl
```

## 使用方法

1.  **啟動應用程式**
    在終端機執行以下指令：
    ```bash
    streamlit run srs_app.py
    ```

2.  **操作流程**
    *   **選擇數據來源**：在側邊欄選擇「模擬標準波形」或「上傳外部檔案」。
    *   **設定參數**：調整 Q Factor (預設 10) 與頻率範圍。
    *   **選擇分析類型**：切換 SRS、Velocity 或 Displacement 視圖。
    *   **下載結果**：點擊下載按鈕儲存分析數據。

## 理論基礎

*   **Smallwood Algorithm**: 使用遞迴數位濾波器 (IIR Filter) 來模擬單自由度 (SDOF) 系統對基礎激振的響應。這是目前計算 SRS 最標準且快速的方法。
