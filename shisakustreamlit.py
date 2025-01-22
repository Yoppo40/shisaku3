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
#st.write("修正前のデータ型:", df.dtypes)

# PPG列を数値型に変換
df["PPG"] = pd.to_numeric(df["PPG"], errors="coerce")

# 欠損値の処理（今回は欠損値を削除する方法を採用）
df = df.dropna(subset=["PPG"])

# 修正後のデータ型を確認
#st.write("修正後のデータ型:", df.dtypes)

# 数値データを抽出
df_numeric = df.select_dtypes(include=['number'])  # 数値データのみ選択

# 異常検知対象列
anomaly_detection_columns = ["PPG", "Resp", "EDA", "SCL", "SCR"]
#anomaly_detection_columns = ["PulseDataRaw", "EDAdataRaw", "RespDataRaw"]

# 情動変化検出アルゴリズム
@st.cache_data
def detect_emotion_changes(data, column, window_size=60, adjustment_coefficient=1.5):
    # 移動平均と標準偏差を計算
    rolling_mean = data[column].rolling(window=window_size, min_periods=1).mean()
    rolling_std = data[column].rolling(window=window_size, min_periods=1).std()

    # 閾値を計算
    thresholds = rolling_mean + adjustment_coefficient * rolling_std

    # 情動変化の検出
    emotion_changes = data[column] > thresholds
    return thresholds, emotion_changes

# 各列に対してアルゴリズムを適用
results = {}
adjustment_coefficients = {
    "PPG": 1.5,
    "Resp": 1.4,
    "EDA": 1.2,
    "SCL": 1.3,
    "SCR": 1.3,
}

for column, coeff in adjustment_coefficients.items():
    if column in df_numeric.columns:
        thresholds, changes = detect_emotion_changes(df, column, adjustment_coefficient=coeff)
        results[column] = {
            "thresholds": thresholds,
            "changes": changes,
        }

# サイドバーに設定オプションを追加
total_data_points = len(df)
window_size = 200  # 表示するデータ範囲のサイズ
anomaly_detection_enabled = False
auto_update = False  # 初期値を設定

with st.sidebar:
    st.header("設定")

    # 表示範囲の設定
    with st.expander("表示範囲設定", expanded=True):
        mode = st.radio(
            "表示モードを選択してください",
            options=["スライダーで範囲指定", "最新データを表示"],
            index=0,
            help="現在のスライダー入力で表示するか、最新のデータを表示するか選択します"
        )

        window_size = st.slider(
            "ウィンドウサイズ (表示するデータ数)",
            min_value=50,
            max_value=500,
            value=200,
            step=10,
            help="表示範囲内のデータポイント数を調整します"
        )

        if mode == "スライダーで範囲指定":
            start_index = st.slider(
                "表示開始位置",
                min_value=0,
                max_value=max(0, total_data_points - window_size),
                value=0,
                step=10,
                help="X軸の表示範囲を動かすにはスライダーを調整してください"
            )
            end_index = start_index + window_size
        elif mode == "最新データを表示":
            end_index = total_data_points
            start_index = max(0, total_data_points - window_size)

    # リアルタイム更新設定
    with st.expander("リアルタイム更新設定", expanded=False):
        auto_update = st.checkbox("自動更新を有効化", value=False)
        update_interval = st.slider(
            "更新間隔 (秒)",
            min_value=5,
            max_value=120,
            value=10,
            step=5,
            help="データの自動更新間隔を設定します"
        )

    # フィードバック設定
    with st.expander("フィードバック", expanded=True):
        feedback = st.text_area("このアプリケーションについてのフィードバックをお聞かせください:")
        if st.button("フィードバックを送信"):
            if feedback.strip():
                try:
                    feedback_sheet = spreadsheet.worksheet("Feedback")
                    feedback_sheet.append_row([feedback])
                    st.success("フィードバックを送信しました。ありがとうございます！")
                except Exception as e:
                    st.error(f"フィードバックの送信中にエラーが発生しました: {e}")
            else:
                st.warning("フィードバックが空です。入力してください。")

# 選択された範囲と列のデータを抽出
filtered_df = df.iloc[start_index:end_index]

# 各グラフの作成
for column in df_numeric.columns:
    st.write(f"**{column} のデータ (範囲: {start_index} - {end_index})**")

    # グラフデータ準備
    if column in results and "thresholds" in results[column]:
        chart_data = pd.DataFrame({
            "Index": filtered_df.index,
            "Value": filtered_df[column],
            "Threshold": results[column]["thresholds"].iloc[start_index:end_index],
        })

        # Y軸スケールの設定
        min_val = chart_data["Value"].min()
        max_val = chart_data["Value"].max()
        padding = (max_val - min_val) * 0.1
        y_axis_scale = alt.Scale(domain=[min_val - padding, max_val + padding])

        # 基本グラフ
        base_chart = (
            alt.Chart(chart_data)
            .mark_line(point=True)
            .encode(
                x=alt.X("Index:O", title="行インデックス"),
                y=alt.Y("Value:Q", title=column, scale=y_axis_scale),
                tooltip=["Index", "Value"]
            )
            .properties(width=700, height=400)
        )

        # 閾値のラインを追加
        threshold_chart = (
            alt.Chart(chart_data)
            .mark_line(strokeDash=[5, 5], color="red")
            .encode(
                x="Index:O",
                y="Threshold:Q",
                tooltip=["Index", "Threshold"]
            )
        )

        # 情動変化点をプロット
        if "changes" in results[column]:
            emotion_changes = results[column]["changes"]
            changes_data = filtered_df[emotion_changes.iloc[start_index:end_index]]
            changes_chart = alt.Chart(changes_data).mark_point(color="red", size=60).encode(
                x=alt.X("Index:O"),
                y=alt.Y("Value:Q")
            )
            st.altair_chart(base_chart + threshold_chart + changes_chart)
        else:
            st.altair_chart(base_chart + threshold_chart)

    else:
        # データが存在しない場合でもグラフを表示
        chart_data = pd.DataFrame({
            "Index": filtered_df.index,
            "Value
