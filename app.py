import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# --- NASTAVENIA ---
MOJ_EMAIL = "petermarkuska@gmail.com"  # <--- SEM DOPLŇ SVOJ EMAIL
SHEET_ID = '13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY'

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

try:
    # 1. NAČÍTANIE DÁT
    df_p = load_data("Platby")
    df_v = load_data("Vydavky")
    try:
        df_h = load_data("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas", "Datum"])

    # 2. FINANČNÉ VÝPOČTY
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    p_stlpce = [c for c in df_p.columns if "/26" in c]
    
    # Mesačné sumy príjmov
    m_prijmy = df_p[p_stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    
    # Mesačné sumy výdavkov (vyžaduje stĺpec 'Mesiac' v hárku Vydavky)
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    if "Mesiac" in df_v.columns:
        m_vydavky = df_v.groupby("Mesiac")["Suma"].sum()
    else:
        m_vydavky = pd.Series(0, index=m_prijmy.index)

    # Celkové metriky
    c_prijmy = m_prijmy.sum()
    c_vydavky = df_v["Suma"].sum()
    akt_zostatok = c_prijmy - c_vydavky

    # 3. ZOBRAZENIE METRÍK
    st.title("🏡 Portál Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Fond celkom", f"{c_prijmy:.2f} €")
    c2.metric("Výdavky", f"{c_vydavky:.2f} €")
    c3.metric("Zostatok", f"{akt_zostatok:.2f} €")

    # 4. GRAF REÁLNEHO ZOSTATKU
    st.subheader("📈 Vývoj zostatku na účte")
    
    # Vytvorenie časovej osi zostatku
    df
