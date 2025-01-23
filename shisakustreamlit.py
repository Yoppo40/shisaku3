import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import altair as alt
import numpy as np

# 環境変数からGoogle Sheets API認証情報を取得
json_str = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
creds_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict,
    ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)

# スプレッドシートのデータを取得
spreadsheet = client.open("Shisaku")
try:
    worksheet = spreadsheet.get_worksheet(2)
except gspread.exceptions.APIError as e:
    st.error(f"Google Sheetsへのアクセス中にエラーが発生しました: {e}")

# Streamlitアプリケーションの設定
st.title("EDAからの瞬時脈拍計算")
st.write("以下はGoogle Sheetsから取得したデータです。")

# データをキャッシュして取得
@st.cache_data(ttl=60)
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# データ取得
df = fetch_data()

# 列名を固定的に設定
custom_column_titles = ["PPG", "Resp", "EDA", "SCL", "SCR", "WristNorm", "WaistNorm"]
if len(df.columns) >= len(custom_column_titles):
    rename_mapping = {df.columns[i]: custom_column_titles[i] for i in range(len(custom_column_titles))}
    df.rename(columns=rename_mapping, inplace=True)

# EDA列を確認
if "EDA" not in df.columns:
    st.error("EDA列がスプレッドシートに存在しません。")
    st.stop()

# 瞬時脈拍を計算する関数
def calculate_instantaneous_pulse(eda_data, sampling_rate=100):
    """
    瞬時脈拍を計算します。
    
    Parameters:
        eda_data (pd.Series): EDA信号データ
        sampling_rate (int): サンプリング周波数（Hz）
    
    Returns:
        pd.DataFrame: 瞬時脈拍を含むデータフレーム
    """
    # 差分で変化量を計算
    diff = np.diff(eda_data)
    
    # 簡易ピーク検出 (正の変化のみ)
    peak_indices = np.where(diff > 0)[0]
    peak_times = peak_indices / sampling_rate  # 時間（秒）に変換

    # ピーク間の時間差を計算
    ibi = np.diff(peak_times)  # Inter-Beat Interval（秒）
    instantaneous_pulse = 60 / ibi  # 瞬時脈拍（bpm）

    # 瞬時脈拍データフレームを作成
    pulse_df = pd.DataFrame({
        "Time (s)": peak_times[1:],
        "Instantaneous Pulse (bpm)": instantaneous_pulse
    })
    return pulse_df

# 瞬時脈拍を計算
sampling_rate = 100  # サンプリング周波数（Hz）
pulse_df = calculate_instantaneous_pulse(df["EDA"], sampling_rate)

# グラフ表示 (EDAと瞬時脈拍を統合)
st.write("### 瞬時脈拍 (EDAから計算)")
combined_df = pd.DataFrame({
    "Time (s)": np.arange(len(df["EDA"])) / sampling_rate,
    "EDA": df["EDA"]
}).merge(pulse_df, on="Time (s)", how="left")

# Altairプロット
base_chart = alt.Chart(combined_df).mark_line().encode(
    x=alt.X("Time (s)", title="時間 (秒)"),
    y=alt.Y("EDA", title="EDA信号 (μS)")
)

pulse_chart = alt.Chart(combined_df.dropna()).mark_line(color="red").encode(
    x="Time (s):Q",
    y=alt.Y("Instantaneous Pulse (bpm)", title="瞬時脈拍 (bpm)")
)

# 複合グラフを表示
st.altair_chart(base_chart + pulse_chart, use_container_width=True)

# 瞬時脈拍データを表示
st.write("### 瞬時脈拍データ")
st.dataframe(pulse_df)

# CSVダウンロードオプション
csv = pulse_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="瞬時脈拍データをダウンロード (CSV)",
    data=csv,
    file_name="instantaneous_pulse.csv",
    mime="text/csv"
)
