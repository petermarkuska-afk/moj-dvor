import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# --- NASTAVENIA ---
MOJ_EMAIL = "petermarkuska@gmail.com"  # <--- DOPLŇ SVOJ EMAIL
SHEET_ID = '13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY'

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

# --- PROGRAM ---
try:
    # 1. Načítanie dát
    df_p = load_data("Platby")
    df_v = load_data("Vydavky")
    try:
        df_h = load_data("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas", "Datum"])

    # 2. Formátovanie VS
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)

    # 3. Finančné výpočty pre metriky
    p_stlpce = [c for c in df_p.columns if "/26" in c]
    m_sumy = df_p[p_stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    c_prijmy = m_sumy.sum()
    
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    c_vydavky = df_v["Suma"].sum()
    zostatok_aktualny = c_prijmy - c_vydavky

    # Zobrazenie webu
    st.title("🏡 Portál Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Fond celkom", f"{c_prijmy:.2f} €")
    c2.metric("Výdavky", f"{c_vydavky:.2f} €")
    c3.metric("Aktuálny zostatok", f"{zostatok_aktualny:.2f} €")

    # --- LOGIKA PRE GRAF REÁLNEHO ZOSTATKU ---
    st.subheader("📈 Vývoj zostatku na účte")
    
    # Príprava časovej osi príjmov (kumulatívne)
    df_prijmy_cas = pd.DataFrame({"Suma": m_sumy.values}, index=m_sumy.index)
    df_prijmy_cas["Typ"] = "Príjem"
    
    # Príprava časovej osi výdavkov (pot
