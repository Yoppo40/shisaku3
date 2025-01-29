import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import json
import datetime
from scipy.interpolate import interp1d
import matplotlib.dates as mdates

# Google Sheets 認証設定
SHEET_NAME = "Shisaku"
CREDENTIALS = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])

# Google Sheets からデータ取得
@st.cache_data(ttl=10)
def fetch_data():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS)
        client = gspread.authorize(creds)
        spreadsheet = client.open(SHEET_NAME)
        sheet = spreadsheet.worksheet("Sheet3")
        data = pd.DataFrame(sheet.get_all_records())

        # **カラム名を小文字に変換**
        data.columns = data.columns.str.strip().str.lower()

        # **カラムのマッピング**
        column_mapping = {
            "ppg level": "ppg level",
            "srl level": "srl level",
            "srr level": "srr level",
            "呼吸周期": "resp level",
            "time": "time"
        }
        data.rename(columns=column_mapping, inplace=True)

        # **時間カラムをdatetimeに変換**
        if "time" in data.columns:
            data["time"] = pd.to_datetime(data["time"], errors="coerce")
            data.dropna(subset=["time"], inplace=True)
        else:
            st.warning("⚠️ 'time' カラムが見つかりません。")

        return data

    except Exception as e:
        st.error(f"❌ データ取得エラー: {e}")
        return pd.DataFrame()

# データ補間関数
def interpolate_data(df):
    if df.empty:
        return df, None

    # **時間データの取得**
    time_values = df["time"].astype(np.int64) / 10**9  # Unixタイム（秒）
    min_time = time_values.min()
    max_time = time_values.max()

    # **時間軸の共通ベクトルを作成**
    timeVector = np.linspace(min_time, max_time, num=len(df))

    # **補間関数を作成**
    interp_ppg = interp1d(time_values, df["ppg level"], kind="nearest", fill_value="extrapolate")
    interp_srl = interp1d(time_values, df["srl level"], kind="nearest", fill_value="extrapolate")
    interp_srr = interp1d(time_values, df["srr level"], kind="nearest", fill_value="extrapolate")
    interp_resp = interp1d(time_values, df["resp level"], kind="nearest", fill_value="extrapolate")

    # **補間データの作成**
    ppg_levels_interp = interp_ppg(timeVector)
    srl_levels_interp = interp_srl(timeVector)
    srr_levels_interp = interp_srr(timeVector)
    resp_levels_interp = interp_resp(timeVector)

    # **時間軸を datetime に変換**
    timeVector_dt = [datetime.datetime.utcfromtimestamp(t) for t in timeVector]

    return {
        "time": timeVector_dt,
        "ppg": ppg_levels_interp,
        "srl": srl_levels_interp,
        "srr": srr_levels_interp,
        "resp": resp_levels_interp
    }

# Streamlit UI 設定
st.title("📊 異常レベルのリアルタイム可視化")

# **データ取得**
data = fetch_data()

if not data.empty:
    # **補間データの取得**
    interpolated_data = interpolate_data(data)

    if interpolated_data:
        timeVector_dt = interpolated_data["time"]
        PPG_levels_interp = interpolated_data["ppg"]
        SRL_levels_interp = interpolated_data["srl"]
        SRR_levels_interp = interpolated_data["srr"]
        Resp_levels_interp = interpolated_data["resp"]

        # **可視化**
        st.subheader("📈 異常レベルの時間推移")
        fig, axs = plt.subplots(4, 1, figsize=(10, 12), sharex=True)

        # **PPG Levels**
        axs[0].plot(timeVector_dt, PPG_levels_interp, '-o', linewidth=1.5, color='red')
        axs[0].set_ylabel("PPG Level")
        axs[0].set_title("PPG Level Over Time")
        axs[0].grid()

        #
