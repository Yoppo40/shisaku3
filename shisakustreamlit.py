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

# データ型の確認
df["PPG"] = pd.to_numeric(df["PPG"], errors="coerce")
df = df.dropna(subset=["PPG"])
df_numeric = df.select_dtypes(include=['number'])

# 異常検知対象列
anomaly_detection_columns = ["PPG", "Resp", "EDA", "SCL", "SCR"]
visualization_only_columns = ["WristNorm", "WaistNorm"]

# 情動変化検出アルゴリズム
@st.cache_data
def detect_emotion_changes(data, column, window_size=60, adjustment_coefficient=1.5, sustained_duration=3, sampling_rate=10):
    rolling_mean = data[column].rolling(window=window_size, min_periods=1).mean()
    rolling_std = data[column].rolling(window=window_size, min_periods=1).std()
    thresholds = rolling_mean + adjustment_coefficient * rolling_std
    above_threshold = data[column] > thresholds
    continuous_count = sustained_duration * sampling_rate
    sustained_changes = above_threshold.rolling(window=continuous_count, min_periods=1).sum() >= continuous_count
    return thresholds, sustained_changes

# サイドバーの設定
with st.sidebar:
    st.header("設定")
    sustained_duration = st.slider(
        "情動変化を検出する最短継続時間 (秒)",
        min_value=1, max_value=10, value=3, step=1,
        help="情動変化を検出するために閾値を超える必要がある最短継続時間を設定します"
    )
    sampling_rate = 10

# 各列に対してアルゴリズムを適用
results = {}
anomalies = {}
adjustment_coefficients = {"PPG": 1.5, "Resp": 1.4, "EDA": 1.2, "SCL": 1.3, "SCR": 1.3}
for column, coeff in adjustment_coefficients.items():
    if column in df_numeric.columns:
        thresholds, changes = detect_emotion_changes(
            df, column, adjustment_coefficient=coeff, sustained_duration=sustained_duration, sampling_rate=sampling_rate
        )
        results[column] = {"thresholds": thresholds, "changes": changes}
        anomalies[column] = df[changes]

# 表示範囲設定
with st.sidebar:
    with st.expander("表示範囲設定", expanded=True):
        mode = st.radio(
            "表示モードを選択してください",
            options=["スライダーで範囲指定", "最新データを表示", "全体表示"],
            index=0
        )
        if mode == "スライダーで範囲指定":
            window_size = st.slider("ウィンドウサイズ (表示するデータ数)", min_value=50, max_value=500, value=200, step=10)
            start_index = st.slider("表示開始位置", min_value=0, max_value=max(0, len(df) - window_size), value=0, step=10)
            end_index = start_index + window_size
        elif mode == "最新データを表示":
            end_index = len(df)
            start_index = max(0, len(df) - window_size)
        elif mode == "全体表示":
            start_index = 0
            end_index = len(df)

# 異常点リスト表示
with st.sidebar:
    with st.expander("異常点リストを表示/非表示", expanded=True):
        st.subheader("異常点リスト (データ列ごと)")
        for column in anomaly_detection_columns:
            if column in anomalies and not anomalies[column].empty:
                st.write(f"**{column}** の異常点:")
                anomaly_df = anomalies[column].reset_index()[["index", column]].rename(
                    columns={"index": "時間", column: "値"}
                )
                st.dataframe(anomaly_df, height=150)
                st.download_button(
                    label=f"{column} の異常点リストをダウンロード (CSV)",
                    data=anomaly_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"{column}_anomalies.csv",
                    mime="text/csv"
                )

# データの範囲を抽出
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
        base_chart = alt.Chart(chart_data).mark_line(point=True).encode(
            x=alt.X("Index:O"), y=alt.Y("Value:Q"), tooltip=["Index", "Value"]
        ).properties(width=700, height=400)
        threshold_chart = alt.Chart(chart_data).mark_line(strokeDash=[5, 5], color="red").encode(
            x="Index:O", y="Threshold:Q", tooltip=["Index", "Threshold"]
        )
        emotion_changes = results[column]["changes"]
        changes_data = filtered_df[emotion_changes.iloc[start_index:end_index]]
        changes_chart = alt.Chart(changes_data).mark_point(color="green", size=60).encode(
            x=alt.X("Index:O"), y=alt.Y("Value:Q")
        )
        st.altair_chart(base_chart + threshold_chart + changes_chart)
    else:
        chart_data = pd.DataFrame({"Index": filtered_df.index, "Value": filtered_df[column]})
        base_chart = alt.Chart(chart_data).mark_line(point=True).encode(
            x=alt.X("Index:O"), y=alt.Y("Value:Q"), tooltip=["Index", "Value"]
        ).properties(width=700, height=400)
        st.altair_chart(base_chart)

# 自動更新の処理
if auto_update:
    time.sleep(update_interval)
    st.experimental_rerun()
