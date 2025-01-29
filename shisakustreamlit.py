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
SHEET_NAME = "Shisaku"
CREDENTIALS = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])

# Google Sheets からデータ取得
@st.cache_data(ttl=10)
def fetch_data():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS)
    client = gspread.authorize(creds)
    spreadsheet = client.open(SHEET_NAME)
    sheet = spreadsheet.worksheet("Sheet3")  # シート名を確認して入力
    data = pd.DataFrame(sheet.get_all_records())
    return data

# ルールベースで統合異常レベルを決定
def calculate_integrated_level(df):
    integrated_levels = []
    for i in range(len(df)):
        ppg = df.loc[i, 'PPG Level']
        srl = df.loc[i, 'SRL Level']
        srr = df.loc[i, 'SRR Level']
        resp = df.loc[i, 'Resp Level']
        
        high_count = sum([ppg, srl, srr, resp] >= 3)
        medium_count = sum([ppg, srl, srr, resp] >= 2)
        
        if high_count >= 2:
            integrated_levels.append(3)
        elif medium_count >= 3:
            integrated_levels.append(2)
        else:
            integrated_levels.append(max([ppg, srl, srr, resp]))
    
    df['Integrated Level'] = integrated_levels
    return df

# Streamlit UI 設定
st.title("異常レベルのリアルタイム可視化")

# データ取得
data = fetch_data()
data = calculate_integrated_level(data)

# 可視化
st.subheader("異常レベルの可視化")
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(data['Time'], data['Integrated Level'], '-o', label="Integrated Level", linewidth=2)
ax.set_xlabel("Time")
ax.set_ylabel("異常レベル")
ax.set_title("統合異常レベルの推移")
ax.legend()
ax.grid()
st.pyplot(fig)

# 最新の異常レベルを表示
latest_level = data['Integrated Level'].iloc[-1]
st.subheader("最新の異常レベル: ")
st.write(f"**{latest_level}**")

# 異常レベルの説明
st.markdown("""
### 異常レベルの定義:
- **0**: 正常
- **1**: 軽度の異常
- **2**: 中程度の異常（注意が必要）
- **3**: 重度の異常（即対応が必要）
""")
