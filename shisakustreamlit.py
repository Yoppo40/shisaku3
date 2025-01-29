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
            "呼吸周期": "resp level"  # 修正
        }
        data.rename(columns=column_mapping, inplace=True)

        # **取得したカラムを表示**
        st.write("📌 取得したカラム:", data.columns.tolist())

        # **必須カラムが揃っているかチェック**
        expected_columns = {"ppg level", "srl level", "srr level", "resp level"}
        missing_columns = expected_columns - set(data.columns)

        if missing_columns:
            st.warning(f"⚠️ 必要なカラムが不足しています: {missing_columns}")
            return pd.DataFrame()  # 空のデータフレームを返す

        # **MATLAB の最大時間を基準にした時間軸を作成**
        if "timestamp" in data.columns:
            time_vector = np.linspace(data["timestamp"].min(), data["timestamp"].max(), len(data))
        else:
            time_vector = np.linspace(0, len(data), len(data))

        data.insert(0, "timestamp", time_vector)

        return data

    except Exception as e:
        st.error(f"❌ データ取得エラー: {e}")
        return pd.DataFrame()  # エラー時は空のデータを返す

# Streamlit UI 設定
st.title("📊 異常レベルのリアルタイム可視化")

# **データ取得**
data = fetch_data()
if not data.empty:
    # **可視化**
    st.subheader("📈 異常レベルの可視化")
    fig, axes = plt.subplots(4, 1, figsize=(10, 12), sharex=True)

    axes[0].plot(data["timestamp"], data["ppg level"], "-o", linewidth=1.5)
    axes[0].set_ylabel("PPG Level")
    axes[0].set_title("PPG Level Over Time")
    axes[0].grid()

    axes[1].plot(data["timestamp"], data["srl level"], "-o", linewidth=1.5)
    axes[1].set_ylabel("SRL Level")
    axes[1].set_title("SRL Level Over Time")
    axes[1].grid()

    axes[2].plot(data["timestamp"], data["srr level"], "-o", linewidth=1.5)
    axes[2].set_ylabel("SRR Level")
    axes[2].set_title("SRR Level Over Time")
    axes[2].grid()

    axes[3].plot(data["timestamp"], data["resp level"], "-o", linewidth=1.5)
    axes[3].set_xlabel("Time (seconds)")
    axes[3].set_ylabel("Resp Level")
    axes[3].set_title("Respiration Level Over Time")
    axes[3].grid()

    plt.tight_layout()
    st.pyplot(fig)

    # **データテーブルを表示**
    st.subheader("📊 データ一覧")
    st.dataframe(data)
else:
    st.warning("📌 データが取得できませんでした。Google Sheets のデータ構造を確認してください。")
