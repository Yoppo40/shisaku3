import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from scipy.interpolate import interp1d

# **Streamlit のための matplotlib の設定**
import matplotlib
matplotlib.use("Agg")  # Streamlit での描画を最適化

# **Google Sheets API の設定**
SHEET_NAME = "ASD_Monitoring_Data"
CREDENTIALS = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])

# **プロットの作成**
fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)

# PPG Levels
axes[0].plot(interpolated_data["timestamp"], interpolated_data["ppg_level"], '-o', label="PPG Level")
axes[0].set_ylabel("PPG Level")
axes[0].legend()
axes[0].grid()

# SRL Levels
axes[1].plot(interpolated_data["timestamp"], interpolated_data["srl_level"], '-o', label="SRL Level", color="green")
axes[1].set_ylabel("SRL Level")
axes[1].legend()
axes[1].grid()

# SRR Levels
axes[2].plot(interpolated_data["timestamp"], interpolated_data["srr_level"], '-o', label="SRR Level", color="red")
axes[2].set_ylabel("SRR Level")
axes[2].legend()
axes[2].grid()

# Respiration Levels
axes[3].plot(interpolated_data["timestamp"], interpolated_data["resp_level"], '-o', label="Resp Level", color="blue")
axes[3].set_ylabel("Resp Level")
axes[3].set_xlabel("Time")
axes[3].legend()
axes[3].grid()

plt.xticks(rotation=45)
plt.tight_layout()

# **Streamlit でプロットを表示**
st.pyplot(fig)
