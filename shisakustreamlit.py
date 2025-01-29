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
    creds = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS)
    client = gspread.authorize(creds)
    spreadsheet = client.open(SHEET_NAME)
    sheet = spreadsheet.worksheet("Sheet3")  # シート名を確認して入力
    data = pd.DataFrame(sheet.get_all_records())

    # データの前処理（カラム名の修正）
    if data.shape[0] > 1 and data.iloc[0].apply(lambda x: isinstance(x, str)).all():
        data.columns = data.iloc[0]  # 1行目をカラム名に設定
        data = data[1:].reset_index(drop=True)  # 1行目を削除してリセット

    # すべてのカラム名を小文字に統一し、前後の空白を削除
    data.columns = data.columns.str.strip().str.lower()

    # 期待されるカラム名に修正
    expected_columns = {"time", "ppg level", "srl level", "srr level", "resp level"}
    if not expected_columns.issubset(set(data.columns)):
        st.error("❌ Google Sheets に必要なカラムがありません！")
        st.write("取得したデータのカラム:", data.columns.tolist())
        return pd.DataFrame()  # 空のデータフレームを返す

    return data

# ルールベースで統合異常レベルを決定
def calculate_integrated_level(df):
    if df.empty:
        return df

    integrated_levels = []
    for i in range(len(df)):
        try:
            ppg = int(df.loc[i, 'ppg level'])
            srl = int(df.loc[i, 'srl level'])
            srr = int(df.loc[i, 'srr level'])
            resp = int(df.loc[i, 'resp level'])

            high_count = sum(x >= 3 for x in [ppg, srl, srr, resp])
            medium_count = sum(x >= 2 for x in [ppg, srl, srr, resp])

            if high_count >= 2:
                integrated_levels.append(3)  # 重度の異常
            elif medium_count >= 3:
                integrated_levels.append(2)  # 中程度の異常
            else:
                integrated_levels.append(max([ppg, srl, srr, resp]))  # 最大の異常レベルを適用

        except (ValueError, KeyError) as e:
            st.error(f"⚠️ データ処理エラー: {e}")
            integrated_levels.append(0)  # データエラー時は正常値（0）に設定

    df['integrated level'] = integrated_levels
    return df

# Streamlit UI 設定
st.title("📊 異常レベルのリアルタイム可視化")

# データ取得
data = fetch_data()
if not data.empty:
    data = calculate_integrated_level(data)

    # 可視化
    st.subheader("📈 異常レベルの可視化")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(data['time'], data['integrated level'], '-o', label="統合異常レベル", linewidth=2, color='red')
    ax.set_xlabel("Time")
    ax.set_ylabel("異常レベル")
    ax.set_title("統合異常レベルの推移")
    ax.legend()
    ax.grid()
    st.pyplot(fig)

    # 最新の異常レベルを表示
    latest_level = data['integrated level'].iloc[-1]
    st.subheader("📢 最新の異常レベル: ")
    st.write(f"**{latest_level}**")

    # 異常レベルの説明
    st.markdown("""
    ### 📌 異常レベルの定義:
    - **0**: 正常
    - **1**: 軽度の異常
    - **2**: 中程度の異常（注意が必要）
    - **3**: 重度の異常（即対応が必要）
    """)

    # データテーブルを表示
    st.subheader("📊 データ一覧")
    st.dataframe(data)
else:
    st.warning("📌 データが取得できませんでした。Google Sheets のデータ構造を確認してください。")
