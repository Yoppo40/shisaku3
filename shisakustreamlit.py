import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import numpy as np
import requests
import altair as alt
from scipy.signal import find_peaks

# Google Sheets 認証
json_str = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
creds_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)

# シートデータ取得
spreadsheet = client.open("Shisaku")
worksheet = spreadsheet.get_worksheet(2)  # 3番目のシート (0-indexed)

st.title("情動検出 & LINE 通知システム")
st.write("Google Sheets から取得したデータを解析し、異常検出結果をLINE通知します。")

# データ取得関数 (キャッシュ)
@st.cache_data(ttl=60)
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

df = fetch_data()

# 列名の設定
column_mapping = {
    "PPG": "PPG",
    "Resp": "Resp",
    "EDA": "EDA",
    "SCL": "SCL",
    "SCR": "SCR",
    "WristNorm": "WristNorm",
    "WaistNorm": "WaistNorm",
}

df.rename(columns=column_mapping, inplace=True)

# 数値データに変換
for col in column_mapping.values():
    df[col] = pd.to_numeric(df[col], errors="coerce")

df.dropna(inplace=True)

# MATLABに基づいた異常検知関数
def detect_abnormalities(df):
    anomalies = {}

    ## 1️⃣ PPG 異常検出 (MATLAB の方法に基づく)
    sampling_rate = 30
    min_peak_height = 0.3 * np.median(df["PPG"])
    min_peak_distance = sampling_rate * 0.5  # 0.5秒以上間隔
    
    peaks, _ = find_peaks(df["PPG"], height=min_peak_height, distance=min_peak_distance)
    heart_rates = 60 * sampling_rate / np.diff(peaks)
    
    hr_mean = np.mean(heart_rates)
    hr_std = np.std(heart_rates)
    hr_threshold = hr_mean + 2.5 * hr_std
    abnormal_hr_indices = np.where(heart_rates > hr_threshold)[0]
    
    anomalies["PPG"] = df.iloc[peaks[abnormal_hr_indices]]

    ## 2️⃣ 呼吸周期異常 (Resp)
    diff_resp = np.diff(df["Resp"])
    resp_std = np.std(diff_resp)
    resp_mean = np.mean(diff_resp)
    resp_threshold = resp_mean + 1.9 * resp_std
    abnormal_resp_indices = np.where(diff_resp > resp_threshold)[0]
    
    anomalies["Resp"] = df.iloc[abnormal_resp_indices]

    ## 3️⃣ 皮膚電気反応 (EDA: SCL, SCR)
    scl_std = np.std(df["SCL"])
    scl_mean = np.mean(df["SCL"])
    scl_threshold = scl_mean - 2.0 * scl_std
    abnormal_scl_indices = np.where(df["SCL"] < scl_threshold)[0]
    
    anomalies["SCL"] = df.iloc[abnormal_scl_indices]

    scr_std = np.std(df["SCR"])
    scr_mean = np.mean(df["SCR"])
    scr_threshold = scr_mean + 2.0 * scr_std
    abnormal_scr_indices = np.where(df["SCR"] > scr_threshold)[0]
    
    anomalies["SCR"] = df.iloc[abnormal_scr_indices]

    return anomalies

# 異常検知
anomalies = detect_abnormalities(df)

# 異常点を表示
st.subheader("異常検知結果")
for key, value in anomalies.items():
    if not value.empty:
        st.write(f"**{key} の異常点:**")
        st.dataframe(value)

# LINE 通知
def send_line_notification(message):
    LINE_NOTIFY_TOKEN = os.environ.get("LINE_NOTIFY_TOKEN")
    if not LINE_NOTIFY_TOKEN:
        st.error("LINE Notify のトークンが設定されていません。")
        return

    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    payload = {"message": message}

    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        st.success("LINE に通知を送信しました！")
    else:
        st.error(f"通知送信エラー: {response.status_code}")

# 異常が検出された場合に通知
for key, value in anomalies.items():
    if not value.empty:
        message = f"⚠️ {key} の異常検出\n\n異常データ:\n{value.to_string(index=False)}"
        send_line_notification(message)

# 可視化
st.subheader("データ可視化")
for col in column_mapping.values():
    st.write(f"**{col} の時系列データ**")
    
    chart_data = pd.DataFrame({"Index": df.index, "Value": df[col]})
    line_chart = (
        alt.Chart(chart_data)
        .mark_line()
        .encode(
            x="Index",
            y="Value",
            tooltip=["Index", "Value"]
        )
        .properties(width=700, height=400)
    )
    
    st.altair_chart(line_chart)
