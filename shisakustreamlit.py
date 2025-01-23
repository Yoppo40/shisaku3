import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import altair as alt
import numpy as np
import time

# 環境変数からGoogle Sheets API認証情報を取得
json_str = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
creds_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)

# スプレッドシートのデータを取得
spreadsheet = client.open("Shisaku")
worksheet = spreadsheet.get_worksheet(2)  # シートを取得（0から始まるインデックス）

# Streamlitアプリケーションの設定
st.title("Google Sheets Data Visualization with Enhanced Anomaly Detection")
st.write("以下はGoogle Sheetsから取得したデータです。")

# データをキャッシュして取得
@st.cache_data(ttl=60)
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# データ取得
df = fetch_data()

# 列名を固定的に設定
custom_column_titles = [
    "PPG",
    "Resp",
    "EDA",
    "SCL",
    "SCR",
    "WristNorm",
    "WaistNorm",
]

# 列名を順番に適用
if len(df.columns) >= len(custom_column_titles):
    rename_mapping = {df.columns[i]: custom_column_titles[i] for i in range(len(custom_column_titles))}
    df.rename(columns=rename_mapping, inplace=True)

# PPG列を数値型に変換
df["PPG"] = pd.to_numeric(df["PPG"], errors="coerce")

# 欠損値の処理（今回は欠損値を削除する方法を採用）
df = df.dropna(subset=["PPG"])

# 数値データを抽出
df_numeric = df.select_dtypes(include=['number'])  # 数値データのみ選択

# 異常検知対象列
anomaly_detection_columns = ["PPG", "Resp", "EDA", "SCL", "SCR"]
visualization_only_columns = ["WristNorm", "WaistNorm"]

# 情動変化検出アルゴリズム
@st.cache_data
def detect_emotion_changes(data, column, window_size=60, adjustment_coefficient=1.5, sustained_duration=4, sampling_rate=10):
    """
    閾値を計算し、持続的な閾値越えを検出します。
    """
    # 移動平均と標準偏差を計算
    rolling_mean = data[column].rolling(window=window_size, min_periods=1).mean()
    rolling_std = data[column].rolling(window=window_size, min_periods=1).std()

    # 閾値を計算
    thresholds = rolling_mean + adjustment_coefficient * rolling_std

    # 持続的な閾値越えを検出
    above_threshold = data[column] > thresholds
    continuous_count = sustained_duration * sampling_rate
    sustained_changes = above_threshold.rolling(window=continuous_count, min_periods=1).sum() >= continuous_count

    return thresholds, sustained_changes

# 各列に対してアルゴリズムを適用
results = {}
adjustment_coefficients = {
    "PPG": 1.5,
    "Resp": 1.4,
    "EDA": 1.2,
    "SCL": 1.3,
    "SCR": 1.3,
}

sustained_duration = 4  # 持続時間（秒単位）
sampling_rate = 10  # サンプリングレート（Hz）

for column, coeff in adjustment_coefficients.items():
    if column in df_numeric.columns:
        thresholds, changes = detect_emotion_changes(
            df, column, adjustment_coefficient=coeff, sustained_duration=sustained_duration, sampling_rate=sampling_rate
        )
        results[column] = {"thresholds": thresholds, "changes": changes}

# 選択された範囲と列のデータを抽出
total_data_points = len(df)
start_index, end_index = 0, total_data_points
filtered_df = df.iloc[start_index:end_index]

# 各グラフの作成
for column in anomaly_detection_columns + visualization_only_columns:
    st.write(f"**{column} のデータ (範囲: {start_index} - {end_index})**")

    if column in results and column in anomaly_detection_columns:
        chart_data = pd.DataFrame({
            "Index": filtered_df.index,
            "Value": filtered_df[column],
            "Threshold": results[column]["thresholds"].iloc[start_index:end_index],
        })

        # 基本グラフ
        base_chart = (
            alt.Chart(chart_data)
            .mark_line(point=True)
            .encode(
                x=alt.X("Index:O", title="行インデックス"),
                y=alt.Y("Value:Q", title=column),
                tooltip=["Index", "Value"]
            )
            .properties(width=700, height=400)
        )

        # 閾値ライン
        threshold_chart = (
            alt.Chart(chart_data)
            .mark_line(strokeDash=[5, 5], color="red")
            .encode(
                x="Index:O",
                y="Threshold:Q",
                tooltip=["Index", "Threshold"]
            )
        )

        # 持続的閾値超えを緑の丸でプロット
        emotion_changes = results[column]["changes"]
        changes_data = filtered_df[emotion_changes.iloc[start_index:end_index]]
        sustained_chart = (
            alt.Chart(changes_data)
            .mark_point(color="green", size=60)
            .encode(
                x=alt.X("Index:O"),
                y=alt.Y("Value:Q"),
                tooltip=["Index", "Value"]
            )
        )

        # グラフを表示
        st.altair_chart(base_chart + threshold_chart + sustained_chart)
    else:
        # データがない場合でもグラフを表示
        chart_data = pd.DataFrame({
            "Index": filtered_df.index,
            "Value": filtered_df[column]
        })
        base_chart = (
            alt.Chart(chart_data)
            .mark_line(point=True)
            .encode(
                x=alt.X("Index:O", title="行インデックス"),
                y=alt.Y("Value:Q", title=column),
                tooltip=["Index", "Value"]
            )
            .properties(width=700, height=400)
        )
        st.altair_chart(base_chart)
        
# 自動更新の処理
if auto_update:
    time.sleep(update_interval)
    st.experimental_rerun()
