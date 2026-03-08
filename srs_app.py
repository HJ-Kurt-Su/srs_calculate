import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- SRS 計算核心 (Smallwood Algorithm) ---
def calculate_srs(time, accel, damping_ratio=0.05, f_min=10, f_max=2000, points_per_octave=12):
    dt = np.mean(np.diff(time))
    fn = f_min * (2 ** (np.arange(0, np.log2(f_max / f_min) + 1/points_per_octave, 1/points_per_octave)))
    
    omega_n = 2 * np.pi * fn
    omega_d = omega_n * np.sqrt(1 - damping_ratio**2)
    
    E = np.exp(-damping_ratio * omega_n * dt)
    K = omega_d * dt
    C, S = E * np.cos(K), E * np.sin(K)
    S_prime = S / K
    
    b0, b1, b2 = 1 - S_prime, 2 * (S_prime - C), E**2 - S_prime
    a1, a2 = 2 * C, -(E**2)
    
    srs_abs_max = []
    for i in range(len(fn)):
        y = np.zeros_like(accel)
        for n in range(2, len(accel)):
            y[n] = (b0[i]*accel[n] + b1[i]*accel[n-1] + b2[i]*accel[n-2] 
                    + a1[i]*y[n-1] + a2[i]*y[n-2])
        srs_abs_max.append(np.max(np.abs(y)))
        
    return fn, np.array(srs_abs_max)

# --- 波形生成器 ---
def generate_shock_wave(wave_type, peak_g, duration_ms, fs=100000, **kwargs):
    d_sec = duration_ms / 1000
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
        r_s, f_s = kwargs.get('rise_ms', 2)/1000, kwargs.get('fall_ms', 2)/1000
        for i, val in enumerate(t[mask]):
            if val < r_s: g[i] = peak_g * (val / r_s)
            elif val < (d_sec - f_s): g[i] = peak_g
            else: g[i] = peak_g * (d_sec - val) / f_s
                
    return t, g

# --- UI 介面 ---
st.set_page_config(page_title="Professional Shock Analysis Tool", layout="wide")
st.title("🛡️ 衝擊響應分析系統 (SRS / PVSS / Relative Displacement)")

st.sidebar.header("1. 數據與波形配置")
mode = st.sidebar.radio("數據來源", ["模擬標準波形", "上傳外部檔案"])

t, g = None, None
if mode == "模擬標準波形":
    wave_type = st.sidebar.selectbox("理想波形種類", ["Half-Sine", "Terminal Peak Sawtooth", "Square Wave", "Trapezoidal"])
    peak_g = st.sidebar.number_input("Peak G (g)", value=100.0)
    duration_ms = st.sidebar.number_input("Duration (ms)", value=11.0)
    extra = {'rise_ms': 2.0, 'fall_ms': 2.0} if wave_type == "Trapezoidal" else {}
    if st.sidebar.button("執行計算"):
        t, g = generate_shock_wave(wave_type, peak_g, duration_ms, **extra)
else:
    uploaded_file = st.file_uploader("上傳 CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        t, g = df.iloc[:, 0].values, df.iloc[:, 1].values

# 縱軸單位切換
st.sidebar.header("2. 分析類型與單位")
plot_type = st.sidebar.radio("選擇縱軸指標", 
                             ["SRS: Acceleration (g)", "Pseudo Velocity (m/s)", "Relative Displacement (mm)"])
q_val = st.sidebar.slider("Quality Factor (Q)", 5, 50, 10)
f_range = st.sidebar.slider("頻率範圍 (Hz)", 10, 10000, (10, 2000))

# --- 計算與圖表渲染 ---
if t is not None:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Time Domain Profile")
        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(x=t, y=g, mode='lines', line=dict(color='#00CC96', width=2)))
        zoom = (duration_ms/1000)*3 if mode == "模擬標準波形" else t[-1]
        fig_time.update_layout(
            xaxis_title="Time (s)", yaxis_title="Acceleration (g)",
            xaxis=dict(range=[0, zoom], showgrid=True, gridcolor='LightGray'),
            yaxis=dict(showgrid=True, gridcolor='LightGray'),
            template="plotly_white"
        )
        st.plotly_chart(fig_time, use_container_width=True)

    with col2:
        st.subheader(f"Spectrum: {plot_type}")
        with st.spinner("計算中..."):
            fn, srs_g = calculate_srs(t, g, damping_ratio=1/(2*q_val), f_min=f_range[0], f_max=f_range[1])
            
            # --- 物理量轉換邏輯 ---
            if plot_type == "Pseudo Velocity (m/s)":
                y_vals = (srs_g * 9.80665) / (2 * np.pi * fn)
                y_label = "Pseudo Velocity (m/s)"
            elif plot_type == "Relative Displacement (mm)":
                # D = A / (2*pi*f)^2，再將 m 換成 mm (*1000)
                y_vals = (srs_g * 9.80665 * 1000) / ((2 * np.pi * fn)**2)
                y_label = "Relative Displacement (mm)"
            else:
                y_vals = srs_g
                y_label = "Peak Acceleration (g)"

        fig_spec = go.Figure()
        fig_spec.add_trace(go.Scatter(x=fn, y=y_vals, mode='lines+markers', 
                                     marker=dict(size=4), line=dict(color='#EF553B', width=2)))
        
        fig_spec.update_layout(
            xaxis_type="log", yaxis_type="log",
            xaxis_title="Natural Frequency (Hz)", yaxis_title=y_label,
            xaxis=dict(showgrid=True, gridcolor='LightGray'),
            yaxis=dict(showgrid=True, gridcolor='LightGray'),
            template="plotly_white", hovermode="x unified"
        )
        st.plotly_chart(fig_spec, use_container_width=True)
    
    st.divider()
    res_df = pd.DataFrame({'Freq_Hz': fn, 'Value': y_vals})
    st.download_button(f"📥 下載 {plot_type} 數據", res_df.to_csv(index=False), "shock_analysis_results.csv")
else:
    st.info("💡 請在側邊欄設定參數並執行模擬。")