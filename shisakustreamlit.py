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

# サイドバーに設定オプションを追加
total_data_points = len(df)
window_size = 200  # 表示するデータ範囲のサイズ

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

        window_size = st.slider(
            "ウィンドウサイズ (表示するデータ数)",
            min_value=50,
            max_value=500,
            value=200,
            step=10,
            help="表示範囲内のデータポイント数を調整します"
        )

    # グラフ表示設定
    with st.expander("グラフ設定", expanded=False):
        chart_width = st.slider("グラフの幅 (px)", min_value=300, max_value=1000, value=700, step=50)
        chart_height = st.slider("グラフの高さ (px)", min_value=200, max_value=800, value=400, step=50)
        unify_y_scale = st.checkbox("同じY軸スケールを使用", value=False)

    # 表示する列の選択
    with st.expander("表示する列を選択", expanded=True):
        selected_columns = st.multiselect(
            "表示したい列を選択してください",
            options=df_numeric.columns.tolist(),
            default=df_numeric.columns.tolist()
        )
        if st.button("すべて選択"):
            selected_columns = df_numeric.columns.tolist()
        if st.button("すべて解除"):
            selected_columns = []

    # リアルタイム更新設定
    with st.expander("リアルタイム更新設定", expanded=False):
        auto_update = st.checkbox("自動更新を有効化", value=False)
        update_interval = st.slider(
            "更新間隔 (秒)",
            min_value=5,
            max_value=120,
            value=60,
            step=5,
            help="データの自動更新間隔を設定します"
        )

# 選択された範囲と列のデータを抽出
filtered_df = df.iloc[start_index:end_index][selected_columns]

# 全グラフのY軸スケールを統一する場合の設定
if unify_y_scale:
    overall_min = filtered_df.min().min()
    overall_max = filtered_df.max().max()
    padding = (overall_max - overall_min) * 0.1
    unified_scale = alt.Scale(domain=[overall_min - padding, overall_max + padding])
else:
    unified_scale = None

# 各グラフの作成
for column in selected_columns:
    st.write(f"**{column} のデータ (範囲: {start_index} - {end_index})**")

    # グラフデータ準備
    chart_data = pd.DataFrame({
        "Index": filtered_df.index,
        "Value": filtered_df[column]
    })

    # Y軸スケール設定
    if unified_scale:
        y_axis_scale = unified_scale
    else:
        min_val = chart_data["Value"].min()
        max_val = chart_data["Value"].max()
        padding = (max_val - min_val) * 0.1
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
        .properties(width=chart_width, height=chart_height)
    )

    st.altair_chart(chart)

# 自動更新の処理
if auto_update:
    st.experimental_rerun()

# フィードバックセクション
st.markdown("---")
st.header("フィードバック")
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
