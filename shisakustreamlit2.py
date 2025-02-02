import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import json
import io

# **Google Sheets 認証設定**
SHEET_NAME = "Shisaku"
CREDENTIALS = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])

# **Google Sheets へのアクセスをグローバルに定義**
def get_spreadsheet():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME)

spreadsheet = get_spreadsheet()  # **Google Sheets にアクセス**

# **Google Sheets からデータ取得**
@st.cache_data(ttl=10)
def fetch_data():
    try:
        sheet = spreadsheet.worksheet("Sheet3")
        data = pd.DataFrame(sheet.get_all_records())

        # **カラム名を統一**
        data.columns = data.columns.str.strip().str.lower()

        # **カラムのマッピング**
        column_mapping = {
            "ppg level": "ppg level",
            "srl level": "srl level",
            "srr level": "srr level",
            "呼吸周期": "resp level",
            "time": "timestamp"
        }
        data.rename(columns=column_mapping, inplace=True)

        # **必須カラムのチェック**
        expected_columns = {"ppg level", "srl level", "srr level", "resp level", "timestamp"}
        missing_columns = expected_columns - set(data.columns)

        if missing_columns:
            st.warning(f"⚠️ 必要なカラムが不足: {missing_columns}")
            return pd.DataFrame()

        # **時間データの確認と修正**
        data["timestamp"] = pd.to_numeric(data["timestamp"], errors='coerce')
        data.dropna(subset=["timestamp"], inplace=True)
        data.sort_values("timestamp", inplace=True)

        return data

    except Exception as e:
        st.error(f"❌ データ取得エラー: {e}")
        return pd.DataFrame()

# **統合異常レベルの計算**
def calculate_integrated_level(df):
    if df.empty:
        return df

    # **数値変換**
    for col in ['ppg level', 'srl level', 'srr level', 'resp level']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.dropna(subset=['ppg level', 'srl level', 'srr level', 'resp level'], inplace=True)

    timestamps = df["timestamp"].values
    levels_list = df[['ppg level', 'srl level', 'srr level', 'resp level']].values

    integrated_levels = []

    for i, (current_time, levels) in enumerate(zip(timestamps, levels_list)):
        count_level3 = np.sum(levels == 3)
        count_level2 = np.sum(levels == 2)
        has_level1 = np.any(levels == 1)
        all_zero = np.all(levels == 0)

        # **5秒以内に別の指標でレベル3があるか**
        future_indices = np.where((timestamps > current_time) & (timestamps <= current_time + 5))[0]

        for j, level in enumerate(levels):
            if level == 3:
                for idx in future_indices:
                    future_levels = levels_list[idx]
                    if any(future_levels[k] == 3 for k in range(4) if k != j):
                        count_level3 += 1
                        break

        # **異常レベルの決定**
        if count_level3 >= 2:
            integrated_levels.append(3)
        elif count_level3 == 1 and count_level2 >= 1:
            integrated_levels.append(2)
        elif count_level2 >= 3:
            integrated_levels.append(2)
        elif has_level1:
            integrated_levels.append(1)
        elif all_zero:
            integrated_levels.append(0)
        else:
            integrated_levels.append(0)

    df["integrated level"] = integrated_levels
    return df

# **ページ切り替え**
st.sidebar.title("📌 ページ切り替え")
page = st.sidebar.radio("移動先を選択", ["異常レベル可視化", "情動変化記録"])

if page == "異常レベル可視化":
    # **異常レベルのリアルタイム可視化ページ**
    st.title("📊 異常レベルのリアルタイム可視化")

    # **データ取得**
    data = fetch_data()
    if not data.empty:
        data = calculate_integrated_level(data)

        # **最新の異常レベルを表示**
        latest_level = data["integrated level"].iloc[-1]
        st.subheader("📢 最新の異常レベル: ")
        st.markdown(f"<h1 style='text-align: center; color: red;'>{latest_level}</h1>", unsafe_allow_html=True)

        # **統合異常レベルのグラフ表示**
        st.subheader("📈 情動変化レベルの推移")
        fig, ax = plt.subplots(figsize=(10, 5))

        ax.plot(data["timestamp"], data["integrated level"], "-o", linewidth=2, color="red")
        ax.set_xlabel("Time(s)")
        ax.set_ylabel("Level")
        ax.grid()
        ax.set_yticks([0, 1, 2, 3])

        st.pyplot(fig)

elif page == "情動変化記録":
    # **情動変化の記録ページ**
    st.title("📖 情動変化の記録")

    # **新規記録の入力**
    with st.form("emotion_form"):
        date = st.date_input("📅 日付を選択")
        location = st.text_input("📍 場所")
        comment = st.text_area("📝 コメント")
        submitted = st.form_submit_button("記録を追加")

        if submitted and date and location and comment:
            record_sheet = spreadsheet.worksheet("EmotionRecords")
            record_sheet.append_row([str(date), location, comment])
            st.success("✅ 記録を追加しました！")

    # **既存の記録を表示**
    st.subheader("📜 過去の記録")
    record_sheet = spreadsheet.worksheet("EmotionRecords")
    records = pd.DataFrame(record_sheet.get_all_records())

    if not records.empty:
        st.dataframe(records)
        st.download_button("📥 記録をダウンロード", records.to_csv(index=False), "emotion_records.csv", "text/csv")
