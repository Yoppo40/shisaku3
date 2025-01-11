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
data = worksheet.get_all_records()

# データフレームに変換
df = pd.DataFrame(data)

# Streamlitアプリケーションの設定
st.title("Google Sheets Data Visualization")
st.write("以下はGoogle Sheetsから取得したデータです。")

# データ表示
st.dataframe(df)

# 各行のデータをグラフ化（データの各列を個別に表示）
for i in range(len(df)):
    st.write(f"データ行 {i+1} のグラフ")
    row_data = df.iloc[i]
    chart_data = pd.DataFrame({
        "Index": df.columns,
        "Value": row_data.values
    })
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True)  # 折れ線グラフに変更
        .encode(
            x=alt.X("Index", title="項目"),
            y=alt.Y("Value", title="値"),
            tooltip=["Index", "Value"]
        )
        .properties(title=f"行 {i+1} のデータ", width=700, height=400)
    )
    st.altair_chart(chart)
