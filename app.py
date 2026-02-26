import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# --- NASTAVENIA ---
MOJ_EMAIL = "petermarkuska@gmail.com"
SHEET_ID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered")

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

    # 2. FINANČNÁ LOGIKA
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    p_stlpce = [c for c in df_p.columns if "/26" in c]
    
    m_prijmy = df_p[p_stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    if "Mesiac" in df_v.columns:
        m_vydavky = df_v.groupby("Mesiac")["Suma"].sum()
    else:
        m_vydavky = pd.Series(0, index=m_prijmy.index)

    c_prijmy = m_prijmy.sum()
    c_vydavky = df_v["Suma"].sum()
    zostatok = c_prijmy - c_vydavky

    # 3. HLAVNÝ PANEL
    st.title("🏡 Portál Victory Port")
    c1, c2, c3 = st.columns(3)
    c1.metric("Príjmy", f"{c_prijmy:.2f} €")
    c2.metric("Výdavky", f"{c_vydavky:.2f} €")
    c3.metric("Zostatok", f"{zostatok:.2f} €")

    # 4. GRAF ZOSTATKU
    st.subheader("📈 Reálny zostatok v čase")
    df_plot = pd.DataFrame(index=m_prijmy.index)
    df_plot["Bilancia"] = m_prijmy.values - m_vydavky.reindex(m_prijmy.index, fill_value=0).values
    df_plot["Zostatok"] = df_plot["Bilancia"].cumsum()
    df_plot = df_plot[m_prijmy > 0].reset_index()
    df_plot.columns = ["Mesiac", "Bilancia", "Zostatok"]

    if not df_plot.empty:
        fig = px.area(df_plot, x="Mesiac", y="Zostatok", template="plotly_dark")
        fig.update_traces(line_color="#1E7E34", fillcolor="rgba(30, 126, 52, 0.2)")
        st.plotly_chart(fig, use_container_width=True)

    # 5. HLASOVANIE A KONTROLA
    st.divider()
    vstup = st.text_input("Zadajte váš VS (napr. 0101):")
    if vstup:
        vs = vstup.zfill(4)
        m_data = df_p[df_p["Identifikácia VS"] == vs]
        if not m_data.empty:
            st.table(m_data)
            st.subheader("🗳️ Anketa")
            
            # Sčítanie hlasov
            za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
            pr = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
            st.info(f"Priebežný stav: 👍 ZA: {za} | 👎 PROTI: {pr}")

            # Príprava Mailto odkazov
            link_za = f"mailto:{MOJ_EMAIL}?subject=HLAS_ANO_VS_{vs}&body=Hlasujem_ZA"
            link_proti = f"mailto:{MOJ_EMAIL}?subject=HLAS_NIE_VS_{vs}&body=Hlasujem_PROTI"

            col_a, col_b = st.columns(2)
            with col_a:
                st.link_button("👍 HLASUJEM ZA", link_za, use_container_width=True)
            with col_b:
                st.link_button("👎 HLASUJEM PROTI", link_proti, use_container_width=True)
        else:
            st.error("VS nenájdený.")

    # 6. ZOZNAM DLŽNÍKOV
    if p_stlpce:
        st.divider()
        posl = p_stlpce[-1]
        dlz = df_p[pd.to_numeric(df_p[posl], errors="coerce").fillna(0) == 0][["Identifikácia VS"]]
        if not dlznici.empty:
            st.warning(f"🚨 Chýba platba za {pos
