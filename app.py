import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# --- SETUP ---
MAIL = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered")

def get_data(name):
    u = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={name}"
    return pd.read_csv(u)

try:
    # 1. NACITANIE
    df_p = get_data("Platby")
    df_v = get_data("Vydavky")
    try:
        df_h = get_data("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # 2. LOGIKA FINANCII
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce = [c for c in df_p.columns if "/26" in c]
    
    # Prijmy a vydavky na casovej osi
    m_p = df_p[stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    if "Mesiac" in df_v.columns:
        m_v = df_v.groupby("Mesiac")["Suma"].sum()
    else:
        m_v = pd.Series(0, index=m_p.index)

    c_prijmy = m_p.sum()
    c_vydavky = df_v["Suma"].sum()
    zost = c_prijmy - c_vydavky

    # 3. VIZUAL - HLAVICKA
    st.title("🏡 Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Prijmy", f"{c_prijmy:.2f} €")
    c2.metric("Vydavky", f"{c_vydavky:.2f} €")
    c3.metric("Zostatok", f"{zost:.2f} €")

    # 4. GRAF REALNEHO ZOSTATKU
    st.write("---")
    st.subheader("📈 Realny stav fondu (po odratani vydavkov)")
    
    # Vypocet: (Prijmy v danom mesiaci - Vydavky v danom mesiaci) a potom sumarny sucet
    df_g = pd.DataFrame(index=m_p.index)
    df_g["Prijem"] = m_p.values
    df_g["Vydaj"] = m_v.reindex(m_p.index, fill_value=0).values
    df_g["Bilancia"] = df_g["Prijem"] - df_g["Vydaj"]
    df_g["Realny_Zostatok"] = df_g["Bilancia"].cumsum()
    
    df_g = df_g[df_g["Prijem"] > 0].reset_index()
    
    if not df_g.empty:
        fig = px.area(df_g, x="index", y="Realny_Zostatok", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
        st.plotly_chart(fig, use_container_width=True)

    # 5. ANKETA (Viditelna hned)
    st.write("---")
    st.subheader("🗳️ Celkove vysledky ankety")
    v_za = len(df_h
