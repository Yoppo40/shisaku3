import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import altair as alt
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
st.title("Google Sheets Data Visualization (リアルタイム対応)")
st.write("以下はGoogle Sheetsから取得したデータです。")

# データをキャッシュして取得
@st.cache_data(ttl=60)
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# データ取得関数（リアルタイム用）
def fetch_live_data():
    return pd.DataFrame(worksheet.get_all_records())

# データ取得
df = fetch_data()

# 列名を固定的に設定
custom_column_titles = [
    "PulseDataRaw",
    "EDAdataRaw",
    "XaccDataRaw",
    "YaccDataRaw",
    "ZaccDataRaw",
    "RespDataRaw",
    "XbeltData",
    "YbeltDataRaw",
    "ZbeltDataRaw",
]

# 列名を順番に適用（データフレームの最初のカラムに対して適用）
if len(df.columns) >= len(custom_column_titles):
    rename_mapping = {df.columns[i]: custom_column_titles[i] for i in range(len(custom_column_titles))}
    df.rename(columns=rename_mapping, inplace=True)

# 数値データを抽出
df_numeric = df.select_dtypes(include=['number'])  # 数値データのみ選択

# サイドバーにスライダーとオプションを追加
window_size = 200  # 表示するデータ範囲のサイズ
total_data_points = len(df)

with st.sidebar:
    st.header("表示範囲の設定")
    start_index = st.slider(
        "表示開始位置",
        min_value=0,
        max_value=max(0, total_data_points - window_size),
        value=0,
        step=10,
        help="X軸の表示範囲を動かすにはスライダーを調整してください"
    )
    end_index = start_index + window_size

    # 列ごとのフィルタリング
    st.subheader("表示する列を選択")
    selected_columns = st.multiselect(
        "表示したい列を選択してください",
        options=df_numeric.columns.tolist(),
        default=df_numeric.columns.tolist()
    )

    # リアルタイム表示設定
    st.subheader("リアルタイム表示設定")
    auto_update = st.checkbox("リアルタイム表示を有効化", value=False)
    update_interval = st.slider(
        "更新間隔（秒）",
        min_value=1,
        max_value=60,
        value=10,
        step=1,
        help="リアルタイム更新の間隔を設定してください"
    )

    # 全データダウンロードボタン
    st.download_button(
        label="全データをダウンロード (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="all_data.csv",
        mime="text/csv"
    )

    # 表示データダウンロードボタン
    st.download_button(
        label="表示データをダウンロード (CSV)",
        data=df.iloc[start_index:end_index, :].to_csv(index=False).encode("utf-8"),
        file_name="filtered_data.csv",
        mime="text/csv"
    )

# リアルタイム表示の処理
while auto_update:
    df = fetch_live_data()  # 最新データを取得
    if len(df.columns) >= len(custom_column_titles):
        rename_mapping = {df.columns[i]: custom_column_titles[i] for i in range(len(custom_column_titles))}
        df.rename(columns=rename_mapping, inplace=True)

    df_numeric = df.select_dtypes(include=['number'])
    filtered_df = df.iloc[start_index:end_index][selected_columns]

    # 各グラフの作成（リアルタイム更新に対応）
    for column in selected_columns:
        st.write(f"**{column} のデータ (範囲: {start_index} - {end_index})**")

        # グラフデータ準備
        chart_data = pd.DataFrame({
            "Index": filtered_df.index,
            "Value": filtered_df[column]
        })

        # グラフ作成
        chart = (
            alt.Chart(chart_data)
            .mark_line(point=True)
            .encode(
                x=alt.X("Index:O", title="行インデックス"),
                y=alt.Y("Value:Q", title=column),
                tooltip=["Index", "Value"]
            )
            .properties(width=700, height=400)
        )

        st.altair_chart(chart)

    time.sleep(update_interval)  # 指定された間隔で更新
    st.experimental_rerun()

# 非リアルタイム時のデータ表示
filtered_df = df.iloc[start_index:end_index][selected_columns]

# 各グラフの作成
for column in selected_columns:
    st.write(f"**{column} のデータ (範囲: {start_index} - {end_index})**")

    # グラフデータ準備
    chart_data = pd.DataFrame({
        "Index": filtered_df.index,
        "Value": filtered_df[column]
    })

    # グラフ作成
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("Index:O", title="行インデックス"),
            y=alt.Y("Value:Q", title=column),
            tooltip=["Index", "Value"]
        )
        .properties(width=700, height=400)
    )

    st.altair_chart(chart)
