import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import altair as alt
import numpy as np
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

# 列名を任意に変更する機能を追加
st.sidebar.header("列名の設定")
column_renaming = {}
for column in df.columns:
    new_name = st.sidebar.text_input(f"{column} の新しい名前を入力", value=column)
    column_renaming[column] = new_name

# 列名を更新
df.rename(columns=column_renaming, inplace=True)

# 数値データを抽出
df_numeric = df.select_dtypes(include=['number'])  # 数値データのみ選択

# Pulsedatarawから脈拍数を計算する関数
def calculate_bpm(pulse_data, sampling_rate):
    """脈拍数を計算"""
    pulse_data = np.array(pulse_data)
    threshold = (np.max(pulse_data) - np.min(pulse_data)) * 0.5 + np.min(pulse_data)
    peaks = np.where((pulse_data[1:-1] > threshold) &
                     (pulse_data[1:-1] > pulse_data[:-2]) &
                     (pulse_data[1:-1] > pulse_data[2:]))[0]

    intervals = np.diff(peaks) / sampling_rate  # ピーク間の時間間隔を計算
    if len(intervals) == 0:
        return 0  # ピークが見つからない場合

    avg_interval = np.mean(intervals)
    bpm = 60 / avg_interval  # BPMを計算
    return round(bpm, 2)

# Pulsedatarawのデータを選択して脈拍数を計算
if 'Pulsedataraw' in df.columns:
    st.subheader("Pulsedataraw の脈拍数 (BPM)")
    sampling_rate = st.sidebar.number_input("サンプリングレート (Hz)", min_value=1, value=100, step=1)
    pulse_data = df['Pulsedataraw']
    bpm = calculate_bpm(pulse_data, sampling_rate)
    st.metric("推定脈拍数 (BPM)", bpm)

# サイドバーにスライダーとオプションを追加
total_data_points = len(df)

with st.sidebar:
    st.header("表示範囲の設定")
    # 動的に範囲を選択できるスライダー
    range_values = st.slider(
        "表示する範囲を選択",
        min_value=0,
        max_value=total_data_points,
        value=(0, 200),  # デフォルトで 0 - 200 を選択
        step=10,
        help="表示するデータの範囲をスライダーで選択してください"
    )
    start_index, end_index = range_values

    # 列ごとのフィルタリング
    st.subheader("表示する列を選択")
    selected_columns = st.multiselect(
        "表示したい列を選択してください",
        options=df_numeric.columns.tolist(),
        default=df_numeric.columns.tolist()
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
        data=df.iloc[start_index:end_index][selected_columns].to_csv(index=False).encode("utf-8"),
        file_name="filtered_data.csv",
        mime="text/csv"
    )

# 選択された範囲と列のデータを抽出
filtered_df = df.iloc[start_index:end_index][selected_columns]

# 各グラフの作成
for column in selected_columns:
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
            y=alt.Y("Value:Q", title=column, scale=scale),
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
