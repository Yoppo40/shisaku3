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

# サイドバーの機能をセクション別に折りたたみ形式で整理
with st.sidebar:
    total_data_points = len(df)
    window_size = 200  # 初期ウィンドウサイズ

    with st.expander("表示範囲設定", expanded=True):
        # モード選択
        mode = st.radio(
            "表示モードを選択してください",
            options=["スライダーで範囲指定", "最新データを表示"],
            index=0,
            help="現在のスライダー入力で表示するか、最新のデータを表示するか選択します"
        )

        # 共通のウィンドウサイズ設定
        window_size = st.slider(
            "ウィンドウサイズ (表示するデータ数)",
            min_value=50,
            max_value=500,
            value=200,
            step=10,
            help="表示範囲内のデータポイント数を調整します"
        )

        # スライダーで範囲指定モード
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

        # 最新データを表示モード
        elif mode == "最新データを表示":
            end_index = total_data_points
            start_index = max(0, total_data_points - window_size)

    with st.expander("リアルタイム更新設定", expanded=False):
        st.write("現在、リアルタイム更新機能は未設定です。必要に応じてここに設定を追加できます。")

    with st.expander("データダウンロード", expanded=False):
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

# 選択された範囲と列のデータを抽出
filtered_df = df.iloc[start_index:end_index][df_numeric.columns.tolist()]

# 各グラフの作成
for column in filtered_df.columns:
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
