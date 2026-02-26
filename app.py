import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# ==========================================
# 1. NASTAVENIA
# ==========================================
MOJ_EMAIL = "petermarkuska@gmail.com"  # <--- SEM DOPLŇ SVOJ EMAIL
SHEET_ID = '13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY'

st.set_page_config(page_title="Victory Port - Správa", layout="centered", page_icon="🏡")

# Pomocná funkcia na načítanie dát
def load_data(sheet_name):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    return pd.read_csv(url)

# Pomocná funkcia pre dizajn tlačidiel
def html_button(link, text, color):
    return f'''
        <a href="{link}" target="_blank" style="text-decoration: none;">
            <div style="background-color:{color};color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;margin-bottom:10px;border:1px solid rgba(255,255,255,0.1);">{text}</div>
        </a>
    '''

# ==========================================
# 2. HLAVNÝ BLOK PROGRAMU
# ==========================================
try:
    # NAČÍTANIE HÁRKOV
    df_p = load_data('Platby')
    df_v = load_data('Vydavky')
    try:
        df_h = load_data('Hlasovanie')
    except:
        # Ak hárok Hlasovanie ešte neexistuje alebo je prázdny
        df_h = pd.DataFrame(columns=['VS', 'Hlas
