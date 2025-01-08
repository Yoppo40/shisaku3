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

# 各行のデータを個別にグラフ化
for i in range(len(df)):
    st.write(f"データ行 {i+1} のグラフ")
    row_data = df.iloc[i]
    for column in df.columns:
        chart_data = pd.DataFrame({
            "Column": [column],
            "Value": [row_data[column]]
        })
        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(
                x=alt.X("Column", title="項目"),
                y=alt.Y("Value", title="値"),
                tooltip=["Column", "Value"]
            )
            .properties(title=f"{column} の値 (行 {i+1})", width=400, height=300)
        )
        st.altair_chart(chart)
