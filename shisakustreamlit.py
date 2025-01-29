import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import json

# Google Sheets 認証設定
SHEET_NAME = "Shisaku"
CREDENTIALS = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])

# Google Sheets からデータ取得
@st.cache_data(ttl=10)
def fetch_data():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS)
        client = gspread.authorize(creds)
        spreadsheet = client.open(SHEET_NAME)
        sheet = spreadsheet.worksheet("Sheet3")  # シート名を確認して入力
        data = pd.DataFrame(sheet.get_all_records())

        # **カラム名を統一**
        data.columns = data.columns.str.strip().str.lower()

        # **カラムのマッピング**
        column_mapping = {
            "ppg level": "ppg level",
            "srl level": "srl level",
            "srr level": "srr level",
            "呼吸周期": "resp level",  # 修正
            "time": "timestamp"  # 時間情報
        }
        data.rename(columns=column_mapping, inplace=True)

        # **取得したカラムを表示**
        st.write("📌 取得したカラム:", data.columns.tolist())

        # **必須カラムが揃っているかチェック**
        expected_columns = {"ppg level", "srl level", "srr level", "resp level", "timestamp"}
        missing_columns = expected_columns - set(data.columns)

        if missing_columns:
            st.warning(f"⚠️ 必要なカラムが不足しています: {missing_columns}")
            return pd.DataFrame()  # 空のデータフレームを返す

        # **時間データの確認と修正**
        data["timestamp"] = pd.to_numeric(data["timestamp"], errors='coerce')  # 数値化
        data.dropna(subset=["timestamp"], inplace=True)  # NaNを削除
        data.sort_values("timestamp", inplace=True)  # 時間順に並べ替え

        return data

    except Exception as e:
        st.error(f"❌ データ取得エラー: {e}")
        return pd.DataFrame()  # エラー時は空のデータを返す

# ルールベースで統合異常レベルを決定
def calculate_integrated_level(df):
    if df.empty:
        return df

    # **数値変換**
    for col in ['ppg level', 'srl level', 'srr level', 'resp level']:
        df[col] = pd.to_numeric(df[col], errors='coerce')  # 文字列を数値に変換

    # **NaN（無効データ）を削除**
    df.dropna(subset=['ppg level', 'srl level', 'srr level', 'resp level'], inplace=True)

    # **異常レベルの統合判定**
    df["integrated level"] = df[["ppg level", "srl level", "srr level", "resp level"]].max(axis=1)
    st.write("🔍 データ型情報:", df.dtypes)

    return df

# Streamlit UI 設定
st.title("📊 異常レベルのリアルタイム可視化")

# **データ取得**
data = fetch_data()
if not data.empty:
    data = calculate_integrated_level(data)

    # **可視化**
    st.subheader("📈 異常レベルの可視化")
    fig, axes = plt.subplots(5, 1, figsize=(10, 14), sharex=True)

    # PPG Level
    axes[0].plot(data["timestamp"], data["ppg level"], "-o", linewidth=1.5)
    axes[0].set_ylabel("PPG Level")
    axes[0].set_title("PPG Level Over Time")
    axes[0].grid()
    axes[0].set_yticks([0, 1, 2, 3])

    # SRL Level
    axes[1].plot(data["timestamp"], data["srl level"], "-o", linewidth=1.5)
    axes[1].set_ylabel("SRL Level")
    axes[1].set_title("SRL Level Over Time")
    axes[1].grid()
    axes[1].set_yticks([0, 1, 2, 3])

    # SRR Level
    axes[2].plot(data["timestamp"], data["srr level"], "-o", linewidth=1.5)
    axes[2].set_ylabel("SRR Level")
    axes[2].set_title("SRR Level Over Time")
    axes[2].grid()
    axes[2].set_yticks([0, 1, 2, 3])

    # RESP Level
    axes[3].plot(data["timestamp"], data["resp level"], "-o", linewidth=1.5)
    axes[3].set_xlabel("Time (seconds)")
    axes[3].set_ylabel("Resp Level")
    axes[3].set_title("Respiration Level Over Time")
    axes[3].grid()
    axes[3].set_yticks([0, 1, 2, 3])

    # 統合異常レベル
    axes[4].plot(data["timestamp"], data["integrated level"], "-o", linewidth=2, color="red")
    axes[4].set_xlabel("Time (seconds)")
    axes[4].set_ylabel("Integrated Level")
    axes[4].set_title("Integrated Abnormal Level Over Time")
    axes[4].grid()
    axes[4].set_yticks([0, 1, 2, 3])

    st.pyplot(fig)

    # **最新の異常レベルを表示**
    latest_level = data["integrated level"].iloc[-1]
    st.subheader("📢 最新の異常レベル: ")
    st.markdown(f"<h1 style='text-align: center; color: red;'>{latest_level}</h1>", unsafe_allow_html=True)

    # **データテーブルを表示**
    st.subheader("📊 データ一覧")
    st.dataframe(data)
else:
    st.warning("📌 データが取得できませんでした。Google Sheets のデータ構造を確認してください。")
