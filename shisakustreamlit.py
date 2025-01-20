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
st.title("Google Sheets Data Visualization")
st.write("以下はGoogle Sheetsから取得したデータです。")

# データをキャッシュして取得
@st.cache_data(ttl=60)
def fetch_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# データ取得
df = fetch_data()

# 列名を固定的に設定
fixed_column_titles = {
    "Pulsedataraw": "1",
    "Timestamp": "2",
    "SensorValue": "3",
    "2413": "Custom Title for 2413",  # 2413 のカスタムタイトルを設定
    "Column5": "5",
    "Column6": "6",
    "Column7": "7",
    "Column8": "8",
    "Column9": "9",
}
df.rename(columns=fixed_column_titles, inplace=True)

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
        value=2919,  # 初期値を2919に設定
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

    # リアルタイムデータ更新の間隔設定
    st.subheader("リアルタイムデータ更新")
    auto_update = st.checkbox("リアルタイムデータ更新を有効化", value=False)
    update_interval = st.slider(
        "更新間隔（秒）",
        min_value=10,
        max_value=300,
        value=60,
        step=10,
        help="データをリアルタイム更新する間隔を設定してください"
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

# リアルタイムデータ更新の処理
if auto_update:
    while True:
        df = fetch_data()
        time.sleep(update_interval)  # ユーザーが設定した間隔でデータを更新
        st.experimental_rerun()

# 選択された範囲と列のデータを抽出
filtered_df = df.iloc[start_index:end_index][selected_columns]

# 各グラフの作成
for column in selected_columns:
    # タイトルを設定
    graph_title = fixed_column_titles.get(column, column)  # カスタムタイトルまたは列名を取得
    st.write(f"**{graph_title} のデータ (範囲: {start_index} - {end_index})**")

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

    # アノテーションを追加（例: 平均値にラインを表示）
    annotation_line = alt.Chart(chart_data).mark_rule(color='red', strokeWidth=2).encode(
        y='mean(Value):Q',
        tooltip=[alt.Tooltip('mean(Value):Q', title='平均値')]
    )

    # グラフ作成
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("Index:O", title="行インデックス"),
            y=alt.Y("Value:Q", title=graph_title, scale=scale),
            tooltip=["Index", "Value"]
        )
        .properties(width=700, height=400)
    ) + annotation_line  # アノテーションを追加

    # グラフ表示
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
