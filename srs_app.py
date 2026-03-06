import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- SRS 計算核心函數 (Smallwood Algorithm) ---
def calculate_srs(time, accel, damping_ratio=0.05, f_min=10, f_max=2000, points_per_octave=12):
    dt = np.mean(np.diff(time))
    fn = f_min * (2 ** (np.arange(0, np.log2(f_max / f_min) + 1/points_per_octave, 1/points_per_octave)))
    
    omega_n = 2 * np.pi * fn
    omega_d = omega_n * np.sqrt(1 - damping_ratio**2)
    
    E = np.exp(-damping_ratio * omega_n * dt)
    K = omega_d * dt
    C = E * np.cos(K)
    S = E * np.sin(K)
    S_prime = S / K
    
    b0 = 1 - S_prime
    b1 = 2 * (S_prime - C)
    b2 = E**2 - S_prime
    a1 = 2 * C
    a2 = - (E**2)
    
    srs_abs_max = []
    for i in range(len(fn)):
        y = np.zeros_like(accel)
        # 向量化遞迴計算優化 (或是簡單迴圈)
        for n in range(2, len(accel)):
            y[n] = (b0[i] * accel[n] + b1[i] * accel[n-1] + b2[i] * accel[n-2] 
                    + a1[i] * y[n-1] + a2[i] * y[n-2])
        srs_abs_max.append(np.max(np.abs(y)))
        
    return fn, np.array(srs_abs_max)

# --- 新增：生成半弦波函數 ---
def generate_half_sine(peak_g, duration_ms, fs=100000):
    duration_s = duration_ms / 1000
    # 為了 SRS 準確性，我們需要包含一段「零墊片 (Padding)」時間，讓低頻震盪器完整反應
    total_time = max(0.5, duration_s * 10) 
    t = np.linspace(0, total_time, int(total_time * fs))
    g = np.zeros_like(t)
    
    pulse_mask = t <= duration_s
    g[pulse_mask] = peak_g * np.sin(np.pi * t[pulse_mask] / duration_s)
    
    return t, g

# --- Streamlit UI ---
st.set_page_config(page_title="SRS 分析 & 模擬工具", layout="wide")
st.title("🚀 SRS 分析 & 理想半弦波模擬器")

# 側邊欄：模式切換
st.sidebar.header("數據來源")
mode = st.sidebar.radio("選擇模式", ["上傳檔案", "模擬理想半弦波 (Half-Sine)"])

# 側邊欄：分析參數
st.sidebar.header("SRS 分析參數")
q_factor = st.sidebar.slider("品質因子 (Q)", 5, 50, 10)
damping = 1 / (2 * q_factor)
f_range = st.sidebar.slider("頻率範圍 (Hz)", 10, 5000, (10, 2000))
octave_res = st.sidebar.selectbox("頻率解析度 (Octave)", [1/6, 1/12, 1/24], index=1)

t, g = None, None

if mode == "上傳檔案":
    uploaded_file = st.file_uploader("上傳 CSV 或 Excel (第一欄時間, 第二欄加速度)", type=["csv", "xlsx"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        t, g = df.iloc[:, 0].values, df.iloc[:, 1].values
else:
    st.sidebar.header("半弦波參數")
    sim_peak_g = st.sidebar.number_input("Peak G Level (g)", value=50.0)
    sim_duration_ms = st.sidebar.number_input("Duration (ms)", value=11.0)
    if st.sidebar.button("生成波形"):
        t, g = generate_half_sine(sim_peak_g, sim_duration_ms)

# --- 顯示與分析 ---
if t is not None and g is not None:
    col1, col2 = st.columns(2)
    
    # 1. 時域圖
    with col1:
        st.subheader("時域波形 (Time History)")
        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(x=t, y=g, mode='lines', name='Acceleration'))
        fig_time.update_layout(xaxis_title="Time (s)", yaxis_title="Acceleration (g)")
        # 若是模擬模式，縮小 X 軸範圍方便觀察脈衝
        if mode == "模擬理想半弦波 (Half-Sine)":
            fig_time.update_xaxes(range=[0, (sim_duration_ms/1000)*3])
        st.plotly_chart(fig_time, use_container_width=True)

    # 2. 計算 SRS
    with st.spinner('計算 SRS 中...'):
        freqs, srs_values = calculate_srs(
            t, g, damping_ratio=damping, 
            f_min=f_range[0], f_max=f_range[1], 
            points_per_octave=int(1/octave_res)
        )

    # 3. SRS 頻譜圖
    with col2:
        st.subheader("SRS 分析結果")
        fig_srs = go.Figure()
        fig_srs.add_trace(go.Scatter(x=freqs, y=srs_values, mode='lines+markers', name=f'SRS (Q={q_factor})'))
        fig_srs.update_layout(
            xaxis_type="log", yaxis_type="log",
            xaxis_title="Frequency (Hz)", yaxis_title="Peak Acceleration (g)",
            hovermode="x unified"
        )
        fig_srs.update_xaxes(showgrid=True, gridcolor='lightgrey')
        fig_srs.update_yaxes(showgrid=True, gridcolor='lightgrey')
        st.plotly_chart(fig_srs, use_container_width=True)

    # 下載區域
    res_df = pd.DataFrame({'Frequency_Hz': freqs, 'Peak_Accel_g': srs_values})
    st.download_button("下載 SRS 數據", res_df.to_csv(index=False), "srs_output.csv")
else:
    st.info("請上傳檔案或點擊『生成波形』開始分析。")