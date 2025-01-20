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

# データ表示
st.dataframe(df)

# 数値データを抽出
df_numeric = df.select_dtypes(include=['number'])  # 数値データのみ選択
window_size = 200  # 一度に表示するデータ範囲のサイズ

# 各列に対して独立したスライダーと入力フォームを設置
for column in df_numeric.columns:
    st.subheader(f"{column} のデータ範囲を選択")
    
    # 現在のデータ数を取得
    total_data_points = len(df)

    # 入力フィールドとスライダーを組み合わせて開始位置を指定
    col1, col2 = st.columns(2)

    with col1:
        start_input = st.text_input(
            f"{column} の開始位置を入力 (0 ~ {max(0, total_data_points - window_size)})",
            value="0",  # 初期値
            key=f"{column}_input",  # ユニークキー
        )

    with col2:
        start_index = st.slider(
            f"{column} の表示開始位置",
            min_value=0,
            max_value=max(0, total_data_points - window_size),
            value=0,
            step=10,
            key=f"{column}_slider"
        )

    # テキスト入力を優先して反映
    try:
        start_index = max(0, min(int(start_input), total_data_points - window_size))
    except ValueError:
        st.warning(f"{column} の開始位置に有効な数値を入力してください")

    # 終了位置を計算
    end_index = start_index + window_size

    # 選択された範囲のデータを抽出
    filtered_df = df.iloc[start_index:end_index]
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
        .properties(title=f"{column} のデータ (範囲: {start_index} - {end_index})", width=700, height=400)
    )
    st.altair_chart(chart)
