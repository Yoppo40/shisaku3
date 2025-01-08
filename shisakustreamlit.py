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

# 横軸の列ごとにグラフを描画
for x_axis in df.columns:
    st.write(f"横軸を{x_axis}に設定したグラフを以下に表示します。")
    for column in df.columns:
        if column != x_axis:
            chart = (
                alt.Chart(df)
                .mark_line()
                .encode(
                    x=alt.X(x_axis, title=x_axis),
                    y=alt.Y(column, title=column),
                    tooltip=[x_axis, column]
                )
                .properties(title=f"{column} の推移 ({x_axis}軸)", width=700, height=400)
            )
            st.altair_chart(chart)
