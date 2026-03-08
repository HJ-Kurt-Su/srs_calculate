import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- SRS 計算核心 (Smallwood Algorithm) ---
def calculate_srs(time, accel, damping_ratio=0.05, f_min=10, f_max=2000, points_per_octave=12):
    dt = np.mean(np.diff(time))
    # 生成對數間隔的頻率點
    fn = f_min * (2 ** (np.arange(0, np.log2(f_max / f_min) + 1/points_per_octave, 1/points_per_octave)))
    
    omega_n = 2 * np.pi * fn
    omega_d = omega_n * np.sqrt(1 - damping_ratio**2)
    
    # 遞迴係數
    E = np.exp(-damping_ratio * omega_n * dt)
    K = omega_d * dt
    C = E * np.cos(K)
    S = E * np.sin(K)
    S_prime = S / K
    
    b0 = 1 - S_prime
    b1 = 2 * (S_prime - C)
    b2 = E**2 - S_prime
    a1 = 2 * C
    a2 = -(E**2)
    
    srs_abs_max = []
    for i in range(len(fn)):
        y = np.zeros_like(accel)
        # 執行遞迴過濾器
        for n in range(2, len(accel)):
            y[n] = (b0[i]*accel[n] + b1[i]*accel[n-1] + b2[i]*accel[n-2] 
                    + a1[i]*y[n-1] + a2[i]*y[n-2])
        srs_abs_max.append(np.max(np.abs(y)))
        
    return fn, np.array(srs_abs_max)

# --- 強化版波形生成器 ---
def generate_shock_wave(wave_type, peak_g, duration_ms, fs=100000, **kwargs):
    d_sec = duration_ms / 1000
    # 確保結尾有足夠的零填充 (Zero Padding) 供低頻響應發展
    total_time = max(0.5, d_sec * 8)
    t = np.linspace(0, total_time, int(total_time * fs))
    g = np.zeros_like(t)
    mask = t <= d_sec
    
    if wave_type == "Half-Sine":
        g[mask] = peak_g * np.sin(np.pi * t[mask] / d_sec)
    
    elif wave_type == "Terminal Peak Sawtooth":
        g[mask] = peak_g * (t[mask] / d_sec)
        
    elif wave_type == "Square Wave":
        g[mask] = peak_g
        
    elif wave_type == "Trapezoidal":
        rise_ms = kwargs.get('rise_ms', duration_ms * 0.1)
        fall_ms = kwargs.get('fall_ms', duration_ms * 0.1)
        r_s, f_s = rise_ms/1000, fall_ms/1000
        
        for i, val in enumerate(t[mask]):
            if val < r_s:
                g[i] = peak_g * (val / r_s)
            elif val < (d_sec - f_s):
                g[i] = peak_g
            else:
                g[i] = peak_g * (d_sec - val) / f_s
                
    return t, g

# --- Streamlit UI 佈局 ---
st.set_page_config(page_title="Professional SRS Tool", layout="wide")
st.title("🛡️ 高階衝擊模擬與 SRS 分析系統")

# 側邊欄：控制面板
st.sidebar.header("1. 參數配置")
mode = st.sidebar.radio("數據來源", ["模擬標準波形", "上傳外部檔案"])

t, g = None, None

if mode == "模擬標準波形":
    wave_type = st.sidebar.selectbox("理想波形種類", 
                                     ["Half-Sine", "Terminal Peak Sawtooth", "Square Wave", "Trapezoidal"])
    peak_g = st.sidebar.number_input("峰值加速度 Peak G (g)", value=100.0)
    duration_ms = st.sidebar.number_input("持續時間 Duration (ms)", value=11.0)
    
    extra_params = {}
    if wave_type == "Trapezoidal":
        extra_params['rise_ms'] = st.sidebar.number_input("上升時間 (ms)", value=2.0)
        extra_params['fall_ms'] = st.sidebar.number_input("下降時間 (ms)", value=2.0)

    if st.sidebar.button("執行模擬並計算"):
        t, g = generate_shock_wave(wave_type, peak_g, duration_ms, **extra_params)

else:
    uploaded_file = st.file_uploader("請選擇 CSV 或 Excel 檔案", type=["csv", "xlsx"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        t, g = df.iloc[:, 0].values, df.iloc[:, 1].values

# SRS 設定
st.sidebar.header("2. SRS 分析設定")
q_val = st.sidebar.slider("Quality Factor (Q)", 5, 50, 10)
f_min, f_max = st.sidebar.slider("頻率範圍 (Hz)", 10, 10000, (10, 2000))

# --- 圖表展示區域 (純 Plotly 語法) ---
if t is not None:
    col1, col2 = st.columns(2)
    
    # 1. 時域圖
    with col1:
        st.subheader("時域波形 Profile")
        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(x=t, y=g, mode='lines', line=dict(color='#00CC96', width=2), name='Shock Pulse'))
        
        # 設定座標軸與顯示範圍 (縮放至脈衝附近)
        zoom_limit = (duration_ms/1000) * 2.5 if mode == "模擬標準波形" else t[-1]
        fig_time.update_layout(
            xaxis_title="Time (seconds)",
            yaxis_title="Acceleration (g)",
            xaxis=dict(range=[0, zoom_limit], showgrid=True, gridcolor='LightGray'),
            yaxis=dict(showgrid=True, gridcolor='LightGray'),
            margin=dict(l=40, r=40, t=40, b=40),
            template="plotly_white"
        )
        st.plotly_chart(fig_time, use_container_width=True)

    # 2. SRS 頻譜圖
    with col2:
        st.subheader("衝擊響應譜 SRS")
        with st.spinner("Smallwood 演算法計算中..."):
            fn, srs_vals = calculate_srs(t, g, damping_ratio=1/(2*q_val), f_min=f_min, f_max=f_max)
        
        fig_srs = go.Figure()
        fig_srs.add_trace(go.Scatter(x=fn, y=srs_vals, mode='lines+markers', 
                                     marker=dict(size=4), line=dict(color='#EF553B', width=2),
                                     name=f'SRS (Q={q_val})'))
        
        # 嚴格遵循 Plotly 的 Log 座標設定
        fig_srs.update_layout(
            xaxis_type="log",
            yaxis_type="log",
            xaxis_title="Natural Frequency (Hz)",
            yaxis_title="Peak Response (g)",
            xaxis=dict(showgrid=True, gridcolor='LightGray', dtick=np.log10(10)),
            yaxis=dict(showgrid=True, gridcolor='LightGray', dtick=np.log10(10)),
            template="plotly_white",
            margin=dict(l=40, r=40, t=40, b=40),
            hovermode="x unified"
        )
        st.plotly_chart(fig_srs, use_container_width=True)
        
    # 下載分析結果
    st.divider()
    res_df = pd.DataFrame({'Frequency_Hz': fn, 'Max_Response_G': srs_vals})
    st.download_button(
        label="📥 下載 SRS 數據 (CSV)",
        data=res_df.to_csv(index=False).encode('utf-8'),
        file_name="srs_analysis_results.csv",
        mime="text/csv"
    )
else:
    st.info("💡 提示：請在左側選擇波形參數並點擊『執行模擬並計算』。")