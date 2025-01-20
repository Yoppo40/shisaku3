import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import altair as alt

# 環境変数からGoogle Sheets API認証情報を取得
json_str = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
creds_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)

# スプレッドシートのデータを取得
spreadsheet = client.open("Shisaku")
worksheet = spreadsheet.sheet1  # 1つ目のシートを使用

# Streamlitアプリケーションの設定
st.title("Google Sheets Data Visualization")
st.write("以下はGoogle Sheetsから取得したデータです。")

# データをキャッシュして取得
@st.cache_data(ttl=60)
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# データ取得
df = fetch_data()

# 数値データを抽出
df_numeric = df.select_dtypes(include=['number'])  # 数値データのみ選択

# スライダーをサイドバーに配置
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

# 選択された範囲のデータを抽出
filtered_df = df.iloc[start_index:end_index]

# 各グラフの作成
for column in df_numeric.columns:
    st.write(f"**{column} のデータ (範囲: {start_index} - {end_index})**")

    # グラフデータ準備
    chart_data = pd.DataFrame({
        "Index": filtered_df.index,
        "Value": filtered_df[column]
    })

    # Y軸スケールの範囲を計算（データの最小値と最大値を基準に余白を加える）
    min_val = chart_data["Value"].min()  # 最小値
    max_val = chart_data["Value"].max()  # 最大値
    padding = (max_val - min_val) * 0.1  # 余白を10%加える
    scale = alt.Scale(domain=[min_val - padding, max_val + padding])  # Y軸範囲設定

    # グラフ作成
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("Index:O", title="行インデックス"),
            y=alt.Y("Value:Q", title=column, scale=scale),
            tooltip=["Index", "Value"]
        )
        .properties(width=700, height=400)
    )

    # グラフ表示
    st.altair_chart(chart)
