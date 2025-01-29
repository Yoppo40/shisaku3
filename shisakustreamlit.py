import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import numpy as np
import requests
import altair as alt
from scipy.signal import find_peaks, butter, filtfilt

# 🌟 Google Sheets 認証
json_str = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
creds_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)

# 🌟 Google Sheets データ取得
spreadsheet = client.open("Shisaku")
worksheet = spreadsheet.get_worksheet(2)

# LINE Notify のアクセストークン
def send_line_notify(message):
    token = "2MJoPuiGzAgULZFEDsIl5zkhkLeOVQSVFgHv4YPNVGe"  # 取得したアクセストークンをセット
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}
    requests.post(url, headers=headers, data=data)

# 例: 通知を送信
send_line_notify("センサーデータに異常値が検出されました！")
# Streamlit 設定
st.title("PPG 異常検知システム")
st.write("MATLAB の手法を使った PPG (心拍数) の異常検知")

# 🌟 データ取得 & キャッシュ
@st.cache_data(ttl=60)
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# データ取得
df = fetch_data()

# 列名を固定的に設定
custom_column_titles = [
    "PPG",
    "Resp",
    "EDA",
    "SCL",
    "SCR",
    "WristNorm",
    "WaistNorm",
]

# 🌟 PPG のデータ前処理
sampling_rate = 30  # 30Hz
dt = len(df)
tt = np.arange(1, dt+1) / sampling_rate

# 🌟 ノルムデータ
norm_wrist = df["WristNorm"] ** (1/3)

# 🌟 PPG の中央値と標準偏差
median_PPG = np.median(df["PPG"])
std_PPG = np.std(df["PPG"])

# 🌟 ピーク検出
min_peak_height = 0.3 * median_PPG
min_peak_distance = int(sampling_rate * 0.5)  # 0.5秒以上の間隔

peaks, properties = find_peaks(df["PPG"], height=min_peak_height, distance=min_peak_distance)
pks = df["PPG"].iloc[peaks]
locs = tt[peaks]

# 🌟 PR (心拍数) 計算
hr5 = 60 * sampling_rate / np.diff(peaks)
hr5_tt = locs[1:]

# 🌟 加速度ノルムの影響を除去
norm_std = pd.Series(norm_wrist - norm_wrist.mean()).rolling(window=10).std()
bad_time = norm_std > 2.3

hr5[bad_time.iloc[1:].values] = np.nan  # ノルムが高い部分を除去

# 🌟 フィルタ適用 (MATLAB の butter フィルタ相当)
def butter_lowpass_filter(data, cutoff=0.09, fs=30, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

hr7 = butter_lowpass_filter(hr5)

# 🌟 異常閾値計算
Mpr = pd.Series(hr7).rolling(window=60).mean()
SDpr = pd.Series(hr7).rolling(window=60).std()
shikiiPR = Mpr + 2.5 * SDpr

# 🌟 異常検知
hitPR = hr7[hr7 > shikiiPR]
hitPR_tt = hr5_tt[hr7 > shikiiPR]

# 🌟 LINE 通知
def send_line_notify(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    data = {"message": message}
    requests.post(url, headers=headers, data=data)

if len(hitPR) > 0:
    for t in hitPR_tt:
        send_line_notify(f"[警告] PPG異常検知: {t:.1f} 秒時点で異常心拍数")

# 🌟 Streamlit で可視化
st.subheader("PPG データの可視化")
chart_data = pd.DataFrame({"Time": tt, "PPG": df["PPG"]})
line_chart = alt.Chart(chart_data).mark_line().encode(x="Time:Q", y="PPG:Q")
st.altair_chart(line_chart, use_container_width=True)

st.subheader("心拍数 (PR) の可視化")
chart_data_hr = pd.DataFrame({"Time": hr5_tt, "HR": hr5})
scatter_chart = alt.Chart(chart_data_hr).mark_point().encode(x="Time:Q", y="HR:Q", color=alt.value("blue"))
st.altair_chart(scatter_chart, use_container_width=True)
