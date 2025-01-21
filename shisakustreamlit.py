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
worksheet = spreadsheet.sheet1  # 1つ目のシートを使用

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

# 列名を順番に適用（データフレームの最初のカラムに対して適用）
if len(df.columns) >= len(custom_column_titles):
    rename_mapping = {df.columns[i]: custom_column_titles[i] for i in range(len(custom_column_titles))}
    df.rename(columns=rename_mapping, inplace=True)

# 数値データを抽出
df_numeric = df.select_dtypes(include=['number'])  # 数値データのみ選択

# 異常検知対象列
anomaly_detection_columns = ["PulseDataRaw", "EDAdataRaw", "RespDataRaw"]

# サイドバーに設定オプションを追加
total_data_points = len(df)
window_size = 200  # 表示するデータ範囲のサイズ
anomaly_detection_enabled = False
auto_update = False  # 初期値を設定

# サイドバーに設定オプションを追加
with st.sidebar:
    st.header("設定")

    # 表示範囲の設定
    with st.expander("表示範囲設定", expanded=True):
        # 表示モード選択
        mode = st.radio(
            "表示モードを選択してください",
            options=["スライダーで範囲指定", "最新データを表示"],
            index=0,
            help="現在のスライダー入力で表示するか、最新のデータを表示するか選択します"
        )

        # データの表示範囲を動的に計算
        window_size = st.slider(
            "ウィンドウサイズ (表示するデータ数)",
            min_value=50,
            max_value=500,
            value=200,
            step=10,
            help="表示範囲内のデータポイント数を調整します"
        )

        # 必要なデータが有効かをチェック
if total_data_points is None:
    st.error("データがロードされていません。'total_data_points'が未定義です。")
elif window_size is None:
    st.error("ウィンドウサイズが設定されていません。'window_size'が未定義です。")
elif total_data_points <= 0:
    st.error("データポイントがありません。データが空です。")
elif window_size <= 0:
    st.error("ウィンドウサイズが不正です。正の値を設定してください。")
else:

        # 範囲設定の計算
        if mode == "スライダーで範囲指定":
            start_index = st.slider(
                "表示開始位置",
                min_value=0,
                max_value= max(0, total_data_points - window_size),
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

    # 選択された範囲と列のデータを抽出
filtered_df = df.iloc[start_index:end_index]

    # フィードバック設定
    with st.expander("フィードバック", expanded=True):
        feedback = st.text_area("このアプリケーションについてのフィードバックをお聞かせください:")
        if st.button("フィードバックを送信"):
            if feedback.strip():
                try:
                    # Google Sheets のフィードバック用シートに保存
                    feedback_sheet = spreadsheet.worksheet("Feedback")  # "Feedback" シートを使用
                    feedback_sheet.append_row([feedback])  # フィードバック内容を追加
                    st.success("フィードバックを送信しました。ありがとうございます！")
                except Exception as e:
                    st.error(f"フィードバックの送信中にエラーが発生しました: {e}")
            else:
                st.warning("フィードバックが空です。入力してください。")



# 各グラフの作成
for column in df_numeric.columns:
    st.write(f"**{column} のデータ (範囲: {start_index} - {end_index})**")

    # グラフデータ準備
    chart_data = pd.DataFrame({
        "Index": filtered_df.index,
        "Value": filtered_df[column],
    })

    # Y軸スケールの設定
    min_val = chart_data["Value"].min()
    max_val = chart_data["Value"].max()
    padding = (max_val - min_val) * 0.1  # 10%の余白を追加
    y_axis_scale = alt.Scale(domain=[min_val - padding, max_val + padding])


    # グラフ作成
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("Index:O", title="行インデックス"),
            y=alt.Y("Value:Q", title=column, scale=y_axis_scale),
            tooltip=["Index", "Value"]
        )
        .properties(width=700, height=400)
    )

    # グラフ表示
    if anomaly_chart:
        st.altair_chart(chart + anomaly_chart)
    else:
        st.altair_chart(chart)

# 自動更新の処理
if auto_update:
    time.sleep(update_interval)
    st.experimental_rerun()
