import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURÁCIA ---
MAIL = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

def get_df(sheet):
    url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}"
    return pd.read_csv(url)

try:
    # 1. NAČÍTANIE DÁT
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    try:
        df_h = get_df("Hlasovanie")
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # 2. LOGIKA PRÍJMOV A VÝDAVKOV
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce_m = [c for c in df_p.columns if "/26" in c]
    m_prijmy = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()

    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    if "Dátum" in df_v.columns:
        df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
        df_v["Mes_Fmt"] = df_v["dt"].dt.strftime('%m/%y')
        m_vydavky = df_v.groupby("Mes_Fmt")["Suma"].sum().reindex(stlpce_m, fill_value=0)
    else:
        m_vydavky = pd.Series(0, index=stlpce_m)

    df_graf = pd.DataFrame({
        "Mesiac": stlpce_m,
        "Zostatok": (m_prijmy.values - m_vydavky.values).cumsum()
    })
    df_graf = df_graf[m_prijmy > 0]

    # --- ZOBRAZENIE ---

    # 1. Názov
    st.markdown("<h1 style='text-align: center;'>🏡 Portál správcu VICTORY PORT</h1>", unsafe_allow_html=True)
    st.write("---")

    # 2. Súčty a graf
    c1, c2, c3 = st.columns(3)
    c_p = m_prijmy.sum()
    c_v = df_v["Suma"].sum()
    c1.metric("Fond celkom", f"{c_p:.2f} €")
    c2.metric("Výdavky celkom", f"{c_v:.2f} €")
    c3.metric("Aktuálny zostatok", f"{(c_p - c_v):.2f} €")

    st.subheader("📈 Vývoj zostatku fondu")
    if not df_graf.empty:
        fig = px.area(df_graf, x="Mesiac", y="Zostatok", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
        st.plotly_chart(fig, use_container_width=True)

    # 3. IDENTIFIKUJ SA
    st.write("---")
    st.subheader("🔐 IDENTIFIKUJ SA")
    vstup = st.text_input("Zadajte váš variabilný symbol pre prístup k hlasovaniu:")

    if vstup:
        vs_c = vstup.zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == vs_c]
        
        if not moje.empty:
            st.success(f"Overenie úspešné. Vitajte, používateľ VS {vs_c}.")
            st.table(moje)
            
            # 4. Anketová otázka a hlasovanie (Otvorí sa pod tým)
            st.divider()
            st.subheader("🗳️ Aktuálna anketová otázka")
            st.write("**Súhlasíte s navrhovanou investíciou do modernizácie spoločných priestorov?**")
            
            za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
            nie = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
            
            col_info1, col_info2 = st.columns(2)
            col_info1.info(f"Priebežné ÁNO: {za}")
            col_info2.error(f"Priebežné NIE: {nie}")

            st.write("### Odošlite váš hlas kliknutím:")
            l1 = f"mailto:{MAIL}?subject=HLAS_ANO_VS_{vs_c}&body=Hlasujem_ANO"
            l2 = f"mailto:{MAIL}?subject=HLAS_NIE_VS_{vs_c}&body=Hlasujem_NIE"
            
            btn_a, btn_b = st.columns(2)
            btn_a.link_button("👍 HLASUJEM ÁNO", l1, use_container_width=True)
            btn_b.link_button("👎 HLASUJEM NIE", l2, use_container_width=True)
        else:
            st.error("Zadaný variabilný symbol nebol nájdený. Skontrolujte prosím údaje.")

    # 5. Zoznam výdavkov (úplne naspodku)
    st.write("---")
    with st.expander("📜 Zobraziť detailný zoznam výdavkov"):
        st.dataframe(df_v[["Dátum", "Účel", "Suma"]], hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"Vyskytla sa chyba: {e}")
