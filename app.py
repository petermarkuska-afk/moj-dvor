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

    # 2. LOGIKA
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce = [c for c in df_p.columns if "/26" in c]
    m_p = df_p[stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    if "Mesiac" in df_v.columns:
        m_v = df_v.groupby("Mesiac")["Suma"].sum()
    else:
        m_v = pd.Series(0, index=m_p.index)

    zost = m_p.sum() - df_v["Suma"].sum()

    # 3. VIZUAL
    st.title("🏡 Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Prijmy", f"{m_p.sum():.2f} €")
    c2.metric("Vydavky", f"{df_v['Suma'].sum():.2f} €")
    c3.metric("Zostatok", f"{zost:.2f} €")

    # 4. GRAF (BEZ PROBLEMOVEHO 'MARKERS')
    st.write("---")
    df_g = pd.DataFrame(index=m_p.index)
    df_g["Z"] = (m_p.values - m_v.reindex(m_p.index, fill_value=0).values).cumsum()
    df_g = df_g[m_p > 0].reset_index()
    
    if not df_g.empty:
        fig = px.area(df_g, x="index", y="Z", template="plotly_dark")
        fig.update_traces(line_color='#28a745')
        st.plotly_chart(fig, use_container_width=True)

    # 5. KONTROLA
    st.write("---")
    vstup = st.text_input("Zadajte VS:")
    if vstup:
        vs = vstup.zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == vs]
        if not moje.empty:
            st.table(moje)
            za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
            pr = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
            st.info(f"Stav: ZA: {za} | PROTI: {pr}")
            
            l1 = f"mailto:{MAIL}?subject=ANO_{vs}"
            l2 = f"mailto:{MAIL}?subject=NIE_{vs}"
            ca, cb = st.columns(2)
            ca.link_button("HLASUJEM ZA", l1, use_container_width=True)
            cb.link_button("HLASUJEM PROTI", l2, use_container_width=True)

    # 6. DLZNICI A VYDAVKY
    if stlpce:
        st.write("---")
        dlz = df_p[pd.to_numeric(df_p[stlpce[-1]], errors="coerce").fillna(0) == 0]
        if not dlz.empty:
            st.warning("Chybajuce platby:")
            st.dataframe(dlz[["Identifikácia VS"]], hide_index=True)

    st.write("---")
    st.dataframe(df_v, hide_index=True)

except Exception as e:
    st.error(f"Chyba: {e}")
