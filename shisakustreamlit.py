import streamlit as st
import pandas as pd
import numpy as np
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import datetime
from io import BytesIO
import json

# Google Sheets 認証設定
SHEET_NAME = "ASD_Monitoring_Data"
CREDENTIALS = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])

# Google Sheets からデータ取得
@st.cache_data(ttl=10)
def fetch_data():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    data = pd.DataFrame(sheet.get_all_records())
    return data

# 異常検知ロジック
THRESHOLDS = {"PPG": 100, "EDA": 0.1, "SCL": 1.5, "SCR": 0.5, "Resp": 20}

def detect_abnormalities(data):
    abnormalities = []
    for index, row in data.iterrows():
        abnormal_signals = []
        for key, threshold in THRESHOLDS.items():
            if row[key] > threshold:
                abnormal_signals.append(f"{key}: {row[key]}")
        if abnormal_signals:
            abnormalities.append({"timestamp": row["timestamp"], "details": ", ".join(abnormal_signals)})
    return abnormalities

# UI構築
st.title("ASD児リアルタイムモニタリング")

# データ取得
st.subheader("リアルタイムデータ表示")
data = fetch_data()
st.dataframe(data.tail(10))

# データ可視化
st.subheader("生体データのトレンド分析")
fig, ax = plt.subplots()
for key in ["PPG", "Resp", "EDA", "SCL", "SCR"]:
    ax.plot(data["timestamp"], data[key], label=key)
ax.legend()
st.pyplot(fig)

# 異常検知
st.subheader("異常検知履歴")
abnormalities = detect_abnormalities(data)
if abnormalities:
    df_abnormal = pd.DataFrame(abnormalities)
    st.dataframe(df_abnormal)
else:
    st.write("異常は検出されていません")

# ダッシュボード（現在の状態）
st.subheader("児の状態表示")
latest_values = data.iloc[-1]
status = "通常" if all(latest_values[key] <= THRESHOLDS[key] for key in THRESHOLDS) else "ストレス増加"
color = "green" if status == "通常" else "red"
st.markdown(f"<h2 style='color:{color};'>{status}</h2>", unsafe_allow_html=True)

# メモ機能
st.subheader("支援者のメモ")
user_input = st.text_area("異常発生時の状況を記録してください")
if st.button("保存"):
    with open("supporter_notes.txt", "a") as file:
        file.write(f"{datetime.datetime.now()}: {user_input}\n")
    st.success("メモが保存されました！")

# 異常時の対応ガイドライン
st.subheader("対応ガイドライン")
if status == "ストレス増加":
    st.write("- 静かな環境に移動する\n- 深呼吸を促す\n- 落ち着くまで待つ")

# データエクスポート
st.subheader("データエクスポート")
if st.button("CSVダウンロード"):
    csv = data.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "monitoring_data.csv", "text/csv")

def create_pdf():
    buffer = BytesIO()
    plt.figure()
    for key in ["PPG", "Resp", "EDA", "SCL", "SCR"]:
        plt.plot(data["timestamp"], data[key], label=key)
    plt.legend()
    plt.savefig(buffer, format="pdf")
    buffer.seek(0)
    return buffer

if st.button("PDFダウンロード"):
    pdf = create_pdf()
    st.download_button("Download PDF", pdf, "monitoring_report.pdf", "application/pdf")
