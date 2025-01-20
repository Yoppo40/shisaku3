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

# 定期的に更新するためにStreamlitのタイマーを使用
@st.cache_data(ttl=60)  # 60秒ごとにデータをキャッシュ更新
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# データ取得
df = fetch_data()

# データ表示
st.dataframe(df)

# 各列のデータを個別のグラフとして表示
df_numeric = df.select_dtypes(include=['number'])  # 数値データのみ選択
for column in df_numeric.columns:
    # 最後の200行を取得
    last_200_data = df.iloc[-200:] if len(df) > 200 else df
    chart_data = pd.DataFrame({
        "Index": last_200_data.index,
        "Value": last_200_data[column]
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
        .properties(title=f"{column} のデータ (最後の200件)", width=700, height=400)
    )
    st.altair_chart(chart)
