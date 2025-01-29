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

# **ルールベースで統合異常レベルを決定**
import numpy as np
import streamlit as st

def calculate_integrated_level(df):
    if df.empty:
        return df

    # **数値変換**
    for col in ['ppg level', 'srl level', 'srr level', 'resp level']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.dropna(subset=['ppg level', 'srl level', 'srr level', 'resp level'], inplace=True)

    timestamps = df["timestamp"].values  # NumPy配列化
    levels_list = df[['ppg level', 'srl level', 'srr level', 'resp level']].values  # NumPy配列化

    # **1データ間の秒数を取得**
    if len(timestamps) > 2:
        time_step = timestamps[2] - timestamps[1]  # 1データ間の秒数
    else:
        time_step = 1  # デフォルト値（データが少ない場合）

    integrated_levels = []

    for i, (current_time, levels) in enumerate(zip(timestamps, levels_list)):
        # **前後5秒に相当するデータ数を計算**
        window_size = int(5 / time_step)

        # **5秒以内の異なる指標データを取得**
        start_idx = max(0, i - window_size)
        end_idx = min(len(timestamps), i + window_size + 1)

        recent_levels = levels_list[start_idx:end_idx]  # 5秒以内のデータ取得

        # **同じ指標を除外**
        filtered_levels = []
        for j, level in enumerate(levels):
            temp_levels = np.delete(recent_levels, j, axis=1)  # 同じ指標を除外
            filtered_levels.append(temp_levels.flatten())  # 1次元配列化

        filtered_levels = np.concatenate(filtered_levels)  # リストを結合

        # **異常レベルのカウント**
        high_count = np.sum(filtered_levels == 3)  # レベル3の異なる指標の数
        medium_count = np.sum(filtered_levels >= 2)  # レベル2以上の異なる指標の数
        has_low = np.any(filtered_levels >= 1)  # 1以上の値があるかどうか

        # **異常レベルの決定**
        if high_count >= 2:
            integrated_levels.append(3)  # 5秒以内に異なる指標でレベル3が2つ以上
        elif high_count == 1 and medium_count >= 1:
            integrated_levels.append(2)  # 5秒以内にレベル3が1つ & レベル2が1つ以上
        elif medium_count >= 3:
            integrated_levels.append(2)  # 5秒以内に異なる指標でレベル2が3つ以上
        elif has_low:
            integrated_levels.append(1)  # 5秒以内に異なる指標でレベル1以上が1つでもある
        else:
            integrated_levels.append(0)  # すべて0の場合

        # **デバッグ確認**
        if i % 50 == 0:  # 50回ごとに出力
            st.write(f"🔍 [デバッグ] Timestamp: {current_time:.2f}, 5秒以内のデータ数: {len(recent_levels)}, 1データ間の秒数: {time_step:.2f}")

    df["integrated level"] = integrated_levels
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

    for ax, col, title in zip(axes, ["ppg level", "srl level", "srr level", "resp level", "integrated level"],
                               ["PPG Level", "SRL Level", "SRR Level", "Respiration Level", "Integrated Abnormal Level"]):
        ax.plot(data["timestamp"], data[col], "-o", linewidth=1.5 if col != "integrated level" else 2, color="red" if col == "integrated level" else None)
        ax.set_ylabel(title)
        ax.set_title(f"{title} Over Time")
        ax.grid()
        ax.set_yticks([0, 1, 2, 3])
    
    axes[-1].set_xlabel("Time (seconds)")
    axes[-1].set_xticks(np.arange(0, data["timestamp"].max() + 1, 100))  # 100秒刻みの横軸設定

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
