import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

# --- KONFIGURÁCIA ---
MAIL = "petermarkuska@gmail.com"
S_ID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

def get_df(name):
    u = f"https://docs.google.com/spreadsheets/d/{S_ID}/gviz/tq?tqx=out:csv&sheet={name}"
    return pd.read_csv(u)

try:
    # 1. DATA
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    try:
        df_h = get_df("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # 2. LOGIKA
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce = [c for c in df_p.columns if "/26" in c]
    
    m_p = df_p[stlpce].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    m_v = df_v.groupby("Mesiac")["Suma"].sum() if "Mesiac" in df_v.columns else pd.Series(0, index=m_p.index)

    c_p = m_p.sum()
    c_v = df_v["Suma"].sum()
    zost = c_p - c_v

    # 3. VIZUÁL - HLAVIČKA
    st.markdown("<h1 style='text-align:center;'>🏡 Victory Port</h1>", unsafe_allow_html=True)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Príjmy", f"{c_p:.2f} €")
    k2.metric("Výdavky", f"{c_v:.2f} €")
    k3.metric("Zostatok", f"{zost:.2f} €")

    # 4. GRAF
    st.write("---")
    st.subheader("📈 Vývoj zostatku")
    
    df_g = pd.DataFrame(index=m_p.index)
    df_g["B"] = m_p.values - m_v.reindex(m_p.index, fill_value=0).values
    df_g["Z"] = df_g["B"].cumsum()
    df_g = df_g[m_p > 0].reset_index()
    df_g.columns = ["M", "B", "Z"]

    if not df_g.empty:
        fig = px.area(df_g, x="M", y="Z", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40,167,69,0.2)', markers=True)
        st.plotly_chart(fig, use_container_width=True)

    # 5. KONTROLA
    st.write("---")
    vs_in = st.text_input("Zadajte váš VS (napr. 0101):")
    
    if vs_in:
        vs_c = vs_in.zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == vs_c]
        if not moje.empty:
            st.success(f"Dáta pre VS {vs_c}")
            st.table(moje)
            
            st.subheader("🗳️ Hlasovanie")
            za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
            pr = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
            st.info(f"Stav: 👍 ZA: {za} | 👎 PROTI: {pr}")

            l_za = f"mailto:{MAIL}?subject=HLAS_ANO_{vs_c}&body=Hlasujem_ZA"
            l_pr = f"mailto:{MAIL}?subject=HLAS_NIE_{vs_c}&body=Hlasujem_PROTI"

            c_a, c_b = st.columns(2)
            c_a.link_button("👍 HLASUJEM ZA", l_za, use_container_width=True)
            c_b.link_button("👎 HLASUJEM PROTI", l_pr, use_container_width=True)
        else:
            st.error("VS nenájdený.")

    # 6. DLŽNÍCI
    if stlpce:
        st.write("---")
        p_m = stlpce[-1]
        dlz = df_p[pd.to_numeric(df_p[p_m], errors="coerce").fillna(0) == 0][["Identifikácia VS"]]
        if not dlz.empty:
            st.warning(f"🚨 Chýba platba za {p_m}:")
            st.dataframe(dlz, hide_index=True, use_container_width=True)

    # 7. VÝDAVKY
    st.write("---")
    st.subheader("📜 Detail výdavkov")
    st.dataframe(df_v, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Chyba: {e}")
