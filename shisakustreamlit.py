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

        # すべてのカラムを小文字化し、前後の空白を削除
        data.columns = data.columns.str.strip().str.lower()

        # **取得したカラムを表示**
        st.write("📌 取得したカラム:", data.columns.tolist())

        # **カラムのマッピング**
        column_mapping = {
            "ppg level": "ppg level",
            "srl level": "srl level",
            "srr level": "srr level",
            "呼吸周期": "resp level"  # ここを修正
        }
        data.rename(columns=column_mapping, inplace=True)

        # **必須カラムが存在するかチェック**
        expected_columns = {"ppg level", "srl level", "srr level", "resp level"}
        missing_columns = expected_columns - set(data.columns)

        if missing_columns:
            st.warning(f"⚠️ 必要なカラムが不足しています: {missing_columns}")
            return pd.DataFrame()  # 空のデータフレームを返す

        return data

    except Exception as e:
        st.error(f"❌ データ取得エラー: {e}")
        return pd.DataFrame()  # エラー時は空のデータを返す

# 数値変換関数（文字列データを排除）
def convert_to_int(value):
    try:
        return int(value)
    except ValueError:
        return np.nan  # 変換できない値は NaN にする

# ルールベースで統合異常レベルを決定
def calculate_integrated_level(df):
    if df.empty:
        return df

    # 各カラムを整数に変換し、変換できないデータを削除
    for col in ['ppg level', 'srl level', 'srr level', 'resp level']:
        df[col] = df[col].apply(convert_to_int)

    # **データ型を表示（デバッグ用）**
    st.write("🔍 データ型情報:")
    st.write(df.dtypes)

    # NaN（無効データ）を含む行を削除
    df.dropna(subset=['ppg level', 'srl level', 'srr level', 'resp level'], inplace=True)

    integrated_levels = []
    for i in range(len(df)):
        ppg = df.loc[i, 'ppg level']
        srl = df.loc[i, 'srl level']
        srr = df.loc[i, 'srr level']
        resp = df.loc[i, 'resp level']

        high_count = sum(x >= 3 for x in [ppg, srl, srr, resp])
        medium_count = sum(x >= 2 for x in [ppg, srl, srr, resp])

        if high_count >= 2:
            integrated_levels.append(3)  # 重度の異常
        elif medium_count >= 3:
            integrated_levels.append(2)  # 中程度の異常
        else:
            integrated_levels.append(max([ppg, srl, srr, resp]))  # 最大の異常レベルを適用

    df['integrated level'] = integrated_levels
    return df

# Streamlit UI 設定
st.title("📊 異常レベルのリアルタイム可視化")

# **データ取得**
data = fetch_data()
if not data.empty:
    data = calculate_integrated_level(data)

    # **可視化**
    st.subheader("📈 異常レベルの可視化")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(data.index, data['integrated level'], '-o', label="統合異常レベル", linewidth=2, color='red')
    ax.set_xlabel("データポイント (時間順)")
    ax.set_ylabel("異常レベル")
    ax.set_title("統合異常レベルの推移")
    ax.legend()
    ax.grid()
    st.pyplot(fig)

    # **最新の異常レベルを表示**
    latest_level = data['integrated level'].iloc[-1]
    st.subheader("📢 最新の異常レベル: ")
    st.write(f"**{latest_level}**")

    # **異常レベルの説明**
    st.markdown("""
    ### 📌 異常レベルの定義:
    - **0**: 正常
    - **1**: 軽度の異常
    - **2**: 中程度の異常（注意が必要）
    - **3**: 重度の異常（即対応が必要）
    """)

    # **データテーブルを表示**
    st.subheader("📊 データ一覧")
    st.dataframe(data)
else:
    st.warning("📌 データが取得できませんでした。Google Sheets のデータ構造を確認してください。")
