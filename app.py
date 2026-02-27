import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURÁCIA A NASTAVENIA ---
MAIL = "tvoj@email.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "ŽIADNA ANKETA" # Tu zmeň text otázky alebo napíš "ŽIADNA ANKETA"

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
        df_h["VS"] = df_h["VS"].astype(str).str.zfill(4)
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # 2. FINANČNÁ LOGIKA
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce_m = [c for c in df_p.columns if "/26" in c]
    p_mesacne = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    if "Dátum" in df_v.columns:
        df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
        df_v["m_fmt"] = df_v["dt"].dt.strftime('%m/%y')
        v_mesacne = df_v.groupby("m_fmt")["Suma"].sum().reindex(stlpce_m, fill_value=0)
    else:
        v_mesacne = pd.Series(0, index=stlpce_m)

    df_graf = pd.DataFrame({
        "Mesiac": stlpce_m,
        "Zostatok": (p_mesacne.values - v_mesacne.values).cumsum()
    })
    df_graf = df_graf[p_mesacne.values > 0]

    # --- ZOBRAZENIE ---
    st.markdown("<h1 style='text-align: center;'>🏡 Portál správcu VICTORY PORT</h1>", unsafe_allow_html=True)
    st.write("---")

    # METRIKY A GRAF
    c1, c2, c3 = st.columns(3)
    c_p, c_v = p_mesacne.sum(), df_v["Suma"].sum()
    c1.metric("Fond celkom", f"{c_p:.2f} €")
    c2.metric("Výdavky celkom", f"{c_v:.2f} €")
    c3.metric("Aktuálny zostatok", f"{(c_p - c_v):.2f} €")

    st.subheader("📈 Vývoj zostatku fondu")
    if not df_graf.empty:
        fig = px.area(df_graf, x="Mesiac", y="Zostatok", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
        st.plotly_chart(fig, use_container_width=True)

    # IDENTIFIKÁCIA
    st.write("---")
    st.subheader("🔐 IDENTIFIKUJ SA")
    vs_in = st.text_input("Zadajte váš variabilný symbol (4 číslice):")

    if vs_in:
        v = vs_in.zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == v]
        
        if not moje.empty:
            st.success(f"Overenie úspešné. Vitajte, VS {v}")
            st.dataframe(moje, hide_index=True)
            
            # --- PODMIENENÝ MODUL ANKETY ---
            if OTAZKA.upper() != "SKUSKA":
                st.divider()
                st.subheader("🗳️ Aktuálna anketová otázka")
                
                # Zobrazenie hlasu ak existuje
                ex_hlas = df_h[df_h["VS"] == v]
                if not ex_hlas.empty:
                    st.warning(f"📢 Váš evidovaný hlas: **{ex_hlas.iloc[-1]['Hlas'].upper()}**")
                
                st.info(f"**Otázka:** {OTAZKA}")
                
                # Štatistiky
                za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
                ni = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
                
                s1, s2 = st.columns(2)
                s1.metric("Priebežne ZA", za)
                s2.metric("Priebežne PROTI", ni)

                # Tlačidlá
                l1 = f"mailto:{MAIL}?subject=HLAS_ANO_{v}&body=Hlasujem_ANO_za_{v}"
                l2 = f"mailto:{MAIL}?subject=HLAS_NIE_{v}&body=Hlasujem_NIE_za_{v}"
                
                b1, b2 = st.columns(2)
                b1.link_button("👍 HLASUJEM ZA", l1, use_container_width=True)
                b2.link_button("👎 HLASUJEM PROTI", l2, use_container_width=True)
                
                with st.expander("Manuálny návod pre Gmail"):
                    st.write(f"Pošlite mail na **{MAIL}** s predmetom `HLAS_ANO_VS_{v}`")
            else:
                # Ak nie je anketa, vypíšeme len decentné info
                st.write("*(Momentálne neprebieha žiadne hlasovanie)*")
        else:
            st.error("VS sa nenašiel.")

    # VÝDAVKY
    st.write("---")
    with st.expander("📜 Zobraziť detailný zoznam výdavkov"):
        st.dataframe(df_v[["Dátum", "Účel", "Suma"]], hide_index=True, use_container_width=True)

except Exception as e:
    st.info(f"Načítavam systém... (Dáta sa synchronizujú)")

