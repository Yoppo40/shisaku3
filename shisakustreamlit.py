import streamlit as st
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import altair as alt

# Streamlitアプリ設定
st.title("EDAデータを用いた瞬時脈拍の計算")
st.write("MATLABから取得したEDAデータを使用して瞬時脈拍を計算します。")

# ファイルアップロード
uploaded_file = st.file_uploader("EDAデータ（CSV形式）をアップロードしてください", type=["csv"])

if uploaded_file:
    # データ読み込み
    df = pd.read_csv(uploaded_file)
    if "EDA" not in df.columns:
        st.error("EDA列がCSVに存在しません。正しい形式のデータをアップロードしてください。")
        st.stop()

    # サンプリングレート（Hz）を設定
    sampling_rate = st.number_input("サンプリングレート（Hz）", value=32, min_value=1)

    # EDAデータ取得
    eda_signal = df["EDA"].to_numpy()

    # ピーク検出
    peaks, _ = find_peaks(eda_signal, height=0)  # ピークのインデックスを取得
    peak_times = peaks / sampling_rate  # 秒単位の時間

    # ピーク間隔と瞬時脈拍の計算
    ibi = np.diff(peak_times)  # ピーク間隔（秒）
    instantaneous_pulse = 60 / ibi  # bpmに変換

    # 結果のデータフレーム作成
    pulse_df = pd.DataFrame({
        "Time (s)": peak_times[1:],  # 最初のピーク間隔は存在しない
        "Instantaneous Pulse (bpm)": instantaneous_pulse
    })

    # 現在の瞬時脈拍を取得
    current_pulse = instantaneous_pulse[-1] if len(instantaneous_pulse) > 0 else None

    # グラフ表示用データ作成
    time_axis = np.arange(len(eda_signal)) / sampling_rate
    eda_df = pd.DataFrame({
        "Time (s)": time_axis,
        "EDA (μS)": eda_signal
    }).merge(pulse_df, on="Time (s)", how="left")

    # グラフ描画
    st.write("### 瞬時脈拍とEDA信号のグラフ")
    eda_chart = alt.Chart(eda_df).mark_line().encode(
        x="Time (s)",
        y=alt.Y("EDA (μS)", title="EDA信号")
    )

    pulse_chart = alt.Chart(eda_df.dropna()).mark_circle(color="red", size=60).encode(
        x="Time (s):Q",
        y=alt.Y("Instantaneous Pulse (bpm)", title="瞬時脈拍 (bpm)"),
        tooltip=["Time (s):Q", "Instantaneous Pulse (bpm):Q"]
    )

    st.altair_chart(eda_chart + pulse_chart, use_container_width=True)

    # 瞬時脈拍の現在値を大きく表示
    st.write("### 現在の瞬時脈拍")
    if current_pulse:
        st.write(f"### **{current_pulse:.2f} bpm**")
    else:
        st.write("### **データが不足しているため、瞬時脈拍を計算できません。**")

    # 瞬時脈拍データの表示
    st.write("### 瞬時脈拍データ")
    st.dataframe(pulse_df)

    # CSVダウンロード
    csv = pulse_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="瞬時脈拍データをダウンロード (CSV)",
        data=csv,
        file_name="instantaneous_pulse.csv",
        mime="text/csv"
    )
