import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import json
import io

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

# **Streamlit UI 設定**
st.title("📊 異常レベルのリアルタイム可視化")

# **データ取得**
data = fetch_data()
if not data.empty:
    data = calculate_integrated_level(data)

    # **最新の異常レベルを表示**
    latest_level = data["integrated level"].iloc[-1]
    st.subheader("📢 最新の異常レベル: ")
    st.markdown(f"<h1 style='text-align: center; color: red;'>{latest_level}</h1>", unsafe_allow_html=True)

    # **サイドバーで表示範囲を選択**
    st.sidebar.header("📌 グラフの表示範囲")
    display_option = st.sidebar.radio(
        "表示範囲を選択",
        ["全体", "最新データ"]
    )

    if display_option == "最新データ":
        latest_time = data["timestamp"].max()
        filtered_data = data[data["timestamp"] >= latest_time - 100]
    else:
        filtered_data = data

    # **統合異常レベルのグラフ表示**
    st.subheader("📈 情動変化レベルの推移")
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(filtered_data["timestamp"], filtered_data["integrated level"], "-o", linewidth=2, color="red")
    ax.set_xlabel("Time(s)")
    ax.set_ylabel("Level")
    ax.grid()
    ax.set_yticks([0, 1, 2, 3])
    ax.set_xticks(np.arange(filtered_data["timestamp"].min(), filtered_data["timestamp"].max() + 1, 100))

    st.pyplot(fig)

    # **異常レベルのヒストグラム表示**
    st.subheader("📊 異常レベルの分布")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(data["integrated level"], bins=[-0.5, 0.5, 1.5, 2.5, 3.5], edgecolor="black", alpha=0.7)
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xlabel("Level")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Integrated Abnormal Levels")
    st.pyplot(fig)

    # **異常発生回数の表示**
    st.sidebar.subheader("📌 異常発生回数")
    abnormal_counts = data["integrated level"].value_counts().sort_index()
    for level in [3, 2, 1, 0]:
        count = abnormal_counts.get(level, 0)
        st.sidebar.write(f"レベル {level}: {count} 回")

    # **異常データのダウンロード**
    st.sidebar.subheader("📥 データダウンロード")
    csv_data = data.to_csv(index=False)
    st.sidebar.download_button(
        label="CSVファイルをダウンロード",
        data=io.StringIO(csv_data).getvalue(),
        file_name="abnormal_levels.csv",
        mime="text/csv"
    )

    # **異常レベルの警告**
    if latest_level == 3:
        st.error("⚠️ **注意:** 重大な異常レベル3が検出されました！即対応を検討してください。")

