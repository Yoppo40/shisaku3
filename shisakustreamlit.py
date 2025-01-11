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

# 数値データの縦の列を1つのグラフとして表示
df_numeric = df.select_dtypes(include=['number'])  # 数値データのみ選択
chart_data = df_numeric.reset_index().melt(id_vars=['index'], var_name='Category', value_name='Value')
chart = (
    alt.Chart(chart_data)
    .mark_line(point=True)
    .encode(
        x=alt.X('index:O', title='行インデックス'),
        y=alt.Y('Value:Q', title='値'),
        color=alt.Color('Category:N', title='カテゴリ'),
        tooltip=['index', 'Category', 'Value']
    )
    .properties(title="数値データの折れ線グラフ", width=700, height=400)
)
st.altair_chart(chart)
