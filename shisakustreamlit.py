import streamlit as st
import pandas as pd
import numpy as np
import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials
from scipy.signal import butter, filtfilt, find_peaks
import altair as alt
import os
import json

# 環境変数からGoogle Sheets API認証情報を取得
try:
    json_str = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if not json_str:
        st.error("環境変数 'GOOGLE_SHEETS_CREDENTIALS' が設定されていません。")
        st.stop()
    creds_dict = json.loads(json_str)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        creds_dict,
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"Google Sheets APIの認証に失敗しました: {e}")
    st.stop()

# スプレッドシートの設定
try:
    spreadsheet = client.open("Shisaku")
    worksheet = spreadsheet.get_worksheet(1)  # シートインデックスを指定
except Exception as e:
    st.error(f"スプレッドシート 'Shisaku' の読み込みに失敗しました: {e}")
    st.stop()

# Streamlitアプリケーションの設定
st.title("EDAを用いた瞬時脈拍の計算と可視化")
st.write("Google Sheetsから取得したEDAデータを使用します。")

# データをキャッシュして取得
@st.cache_data(ttl=60)
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# データ取得
df = fetch_data()

# データの存在確認
if df.empty:
    st.error("スプレッドシートが空です。データを入力してください。")
    st.stop()

# EDA列の存在確認
if "EDA" not in df.columns:
    st.error("スプレッドシートに 'EDA' 列が存在しません。")
    st.stop()

# データ型を数値に変換
df["EDA"] = pd.to_numeric(df["EDA"], errors="coerce").fillna(0)

# サンプリングレートの設定
sampling_rate = 32  # Hz

# MATLABのButterworthフィルタを再現
def butter_filter(data, cutoff, fs, order=4, btype='low'):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype=btype, analog=False)
    y = filtfilt(b, a, data)
    return y

# EDA信号のフィルタリング
low_cut = 0.5  # Hz
high_cut = 14  # Hz
eda_low_filtered = butter_filter(df["EDA"].values, high_cut, sampling_rate, order=4, btype='low')
eda_baseline = butter_filter(eda_low_filtered, low_cut, sampling_rate, order=2, btype='low')
eda_scr = eda_low_filtered - eda_baseline

# 瞬時脈拍の計算
@st.cache_data
def calculate_instantaneous_pulse(eda_signal, sampling_rate):
    peaks, _ = find_peaks(eda_signal, height=0)  # ピーク検出
    if len(peaks) < 2:
        return pd.DataFrame(columns=["Time (s)", "Instantaneous Pulse (bpm)"])
    peak_times = peaks / sampling_rate  # 秒単位
    ibi = np.diff(peak_times)  # ピーク間の時間差
    instantaneous_pulse = 60 / ibi  # bpmに変換

    # 結果をDataFrameにまとめる
    pulse_df = pd.DataFrame({
        "Time (s)": peak_times[1:],  # 最初のピーク間隔は存在しない
        "Instantaneous Pulse (bpm)": instantaneous_pulse
    })
    return pulse_df

# 瞬時脈拍の計算
pulse_df = calculate_instantaneous_pulse(eda_scr, sampling_rate)

# 瞬時脈拍が正常な範囲（60～100 bpm）に収まるか確認
valid_pulse = pulse_df[
    (pulse_df["Instantaneous Pulse (bpm)"] >= 60) &
    (pulse_df["Instantaneous Pulse (bpm)"] <= 100)
]

# EDAと瞬時脈拍のグラフ表示
st.write("### 瞬時脈拍とEDA信号の可視化")
time_axis = np.arange(len(eda_scr)) / sampling_rate  # 時間軸を計算
eda_df = pd.DataFrame({
    "Time (s)": time_axis,
    "EDA (μS)": eda_scr
}).merge(valid_pulse, on="Time (s)", how="left")

if not eda_df.empty:
    # AltairでEDA信号と瞬時脈拍を可視化
    eda_chart = alt.Chart(eda_df).mark_line().encode(
        x="Time (s)",
        y=alt.Y("EDA (μS)", title="EDA信号")
    )

    pulse_chart = alt.Chart(eda_df.dropna()).mark_line(color="red").encode(
        x="Time (s):Q",
        y=alt.Y("Instantaneous Pulse (bpm)", title="瞬時脈拍 (bpm)")
    )

    st.altair_chart(eda_chart + pulse_chart, use_container_width=True)

# 瞬時脈拍データを表示
st.write("### 瞬時脈拍データ")
if not valid_pulse.empty:
    st.dataframe(valid_pulse)

    # CSVダウンロードボタン
    csv = valid_pulse.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="瞬時脈拍データをダウンロード (CSV)",
        data=csv,
        file_name="instantaneous_pulse.csv",
        mime="text/csv"
    )
else:
    st.write("正常な範囲の瞬時脈拍データがありません。")
