import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# --- NASTAVENIA ---
MOJ_EMAIL = "petermarkuska@gmail.com"
SHEET_ID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

# Funkcia na načítanie dát
def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

try:
    # 1. NAČÍTANIE
    df_p = load_data("Platby")
    df_v = load_data("Vydavky")
    try:
        df_h = load_data("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # 2. FINANČNÁ LOGIKA
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    p_stlpce = [c for c in df_p.columns if "/26" in c]
    
    # Mesačné sumy
    m_prijmy = df_p[p_stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    if "Mesiac" in df_v.columns:
        m_vydavky = df_v.groupby("Mesiac")["Suma"].sum()
    else:
        m_vydavky = pd.Series(0, index=m_prijmy.index)

    c_prijmy = m_prijmy.sum()
    c_vydavky = df_v["Suma"].sum()
    zostatok = c_prijmy - c_vydavky

    # 3. VIZUÁL - HLAVNÝ PANEL
    st.markdown(f"<h1 style='text-align: center;'>🏡 Portál Victory Port</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Celkové príjmy", f"{c_prijmy:.2f} €")
    col2.metric("Celkové výdavky", f"{c_vydavky:.2f} €")
    col3.metric("Zostatok fondu", f"{zostatok:.2f} €", delta_color="normal")

    # 4. GRAF REÁLNEHO
