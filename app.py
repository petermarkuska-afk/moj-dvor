import streamlit as st
import pandas as pd
import plotly.express as px

# --- SETUP ---
MAIL = "tvoj@email.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered")

def load(sheet):
    url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}"
    return pd.read_csv(url)

try:
    # 1. DATA
    df_p = load("Platby")
    df_v = load("Vydavky")
    try: df_h = load("Hlasovanie")
    except: df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # 2. LOGIKA (FINANCIE)
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce = [c for c in df_p.columns if "/26" in c]
    m_p = df_p[stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)

    if "Dátum" in df_v.columns:
        df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
        df_v["m"] = df_v["dt"].dt.strftime('%m/%y')
        m_v = df_v.groupby("m")["Suma"].sum().reindex(stlpce, fill_value=0)
    else:
        m_v = pd.Series(0, index=stlpce)

    # 3. GRAF (Kumulatívny)
    df_g = pd.DataFrame({"M": stlpce, "Z": (m_p.values - m_v.values).cumsum()})
    df_g = df_g[m_p.values > 0]

    # --- DISPLEJ ---
    st.title("🏡 Portál správcu VICTORY PORT")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Fond", f"{m_p.sum():.2f} €")
    c2.metric("Výdavky", f"{df_v['Suma'].sum():.2f} €")
    c3.metric("Zostatok", f"{(m_p.sum() - df_v['Suma'].sum()):.2f} €")

    if not df_g.empty:
        fig = px.area(df_g, x="M", y="Z", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40,167,69,0.2)')
        st.plotly_chart(fig, use_container_width=True)

    # 4. IDENTIFIKÁCIA A ANKETA
    st.write("---")
    st.subheader("🔐 IDENTIFIKUJ SA")
    vs_in = st.text_input("Zadaj svoj VS (4 číslice):")

    if vs_in:
        v = vs_in.zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == v]
        
        if not moje.empty:
            st.success(f"Vitajte, VS {v}")
            st.dataframe(moje, hide_index=True)
            
            st.divider()
            st.subheader("🗳️ Aktuálne hlasovanie")
            st.info("Súhlasíte s investíciou do modernizácie osvetlenia?")
            
            # Štatistika
            za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
            ni = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
            st.write(f"Priebežne: ✅ ZA: {za} | ❌ PROTI: {ni}")

            # Mailto linky
            l1 = f"mailto:{MAIL}?subject=ANO_VS_{v}&body=Hlasujem_ZA"
            l2 = f"mailto:{MAIL}?subject=NIE_VS_{v}&body=Hlasujem_PROTI"
            
            ca, cb = st.columns(2)
            ca.link_button("👍 HLASUJEM ZA", l1, use_container_width=True)
            cb.link_button("👎 HLASUJEM PROTI", l2, use_container_width=True)
        else:
            st.error("VS sa nenašiel.")

    # 5. VÝDAVKY
    st.write("---")
    with st.expander("📜 Zobraziť zoznam výdavkov"):
        st.dataframe(df_v[["Dátum", "Účel", "Suma"]], hide_index=True)

except Exception as e:
    st.info("Načítavam systém...")
