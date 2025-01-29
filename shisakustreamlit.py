import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import altair as alt
import numpy as np
import time
import requests

# 🌟 環境変数から Google Sheets API 認証情報を取得
json_str = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
creds_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)

# 🌟 Google Sheets からデータ取得
spreadsheet = client.open("Shisaku")
worksheet = spreadsheet.get_worksheet(2)

# 🌟 LINE Notify トークン取得
LINE_NOTIFY_TOKEN = os.environ.get("LINE_NOTIFY_TOKEN")

# 🌟 LINE に通知を送る関数
def send_line_notify(message):
    if LINE_NOTIFY_TOKEN:
        url = "https://notify-api.line.me/api/notify"
        headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
        data = {"message": message}
        requests.post(url, headers=headers, data=data)
    else:
        st.error("LINE Notify トークンが設定されていません。")

# Streamlit 設定
st.title("Google Sheets Data Visualization with LINE Alerts")
st.write("異常を検知したら LINE に通知します！")

# 🌟 データ取得 & キャッシュ
@st.cache_data(ttl=60)
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

df = fetch_data()

# 🌟 異常検知ロジック
anomaly_detection_columns = ["PPG", "Resp", "EDA", "SCL", "SCR"]
adjustment_coefficients = {
    "PPG": 1.5, "Resp": 1.4, "EDA": 1.2, "SCL": 1.3, "SCR": 1.3,
}

@st.cache_data
def detect_emotion_changes(data, column, window_size=60, adjustment_coefficient=1.5):
    rolling_mean = data[column].rolling(window=window_size, min_periods=1).mean()
    rolling_std = data[column].rolling(window=window_size, min_periods=1).std()
    thresholds = rolling_mean + adjustment_coefficient * rolling_std
    emotion_changes = data[column] > thresholds
    return thresholds, emotion_changes

results = {}
anomalies = {}

for column, coeff in adjustment_coefficients.items():
    if column in df.columns:
        thresholds, changes = detect_emotion_changes(df, column, adjustment_coefficient=coeff)
        results[column] = {"thresholds": thresholds, "changes": changes}
        anomalies[column] = df[changes]

# 🌟 異常検知 & LINE 通知
for column in anomaly_detection_columns:
    if column in anomalies and not anomalies[column].empty:
        latest_anomaly = anomalies[column].iloc[-1]
        anomaly_message = f"[警告] {column} の異常検知: {latest_anomaly[column]}"
        send_line_notify(anomaly_message)
        st.write(f"📢 LINE 通知送信: {anomaly_message}")

# 🌟 データの可視化
st.subheader("データの可視化")
for column in anomaly_detection_columns:
    if column in df.columns:
        chart_data = pd.DataFrame({"Index": df.index, "Value": df[column]})
        base_chart = alt.Chart(chart_data).mark_line().encode(x="Index:O", y="Value:Q")
        st.altair_chart(base_chart, use_container_width=True)
