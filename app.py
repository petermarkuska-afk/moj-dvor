import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURÁCIA ---
MAIL = "tvoj@email.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Súhlasíte s investíciou do modernizácie osvetlenia?"

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

def get_df(sheet):
    url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}"
    return pd.read_csv(url)

try:
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    try:
        df_h = get_df("Hlasovanie")
        df_h["VS"] = df_h["VS"].astype(str).str.zfill(4)
    except:
        df_h = pd.DataFrame(columns=["VS", "Hlas"])

    # LOGIKA FINANCIÍ
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.zfill(4)
    stlpce_m = [c for c in df_p.columns if "/26" in c]
    p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    if "Dátum" in df_v.columns:
        df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
        df_v["m_fmt"] = df_v["dt"].dt.strftime('%m/%y')
        v_mes = df_v.groupby("m_fmt")["Suma"].sum().reindex(stlpce_m, fill_value=0)
    else:
        v_mes = pd.Series(0, index=stlpce_m)

    df_graf = pd.DataFrame({"Mesiac": stlpce_m, "Zostatok": (p_mes.values - v_mes.values).cumsum()})
    df_graf = df_graf[p_mes.values > 0]

    # --- ZOBRAZENIE ---
    st.markdown("<h1 style='text-align: center;'>🏡 Portál správcu VICTORY PORT</h1>", unsafe_allow_html=True)
    st.write("---")

    c1, c2, c3 = st.columns(3)
    c1.metric("Fond celkom", f"{p_mes.sum():.2f} €")
    c2.metric("Výdavky celkom", f"{df_v['Suma'].sum():.2f} €")
    c3.metric("Aktuálny zostatok", f"{(p_mes.sum() - df_v['Suma'].sum()):.2f} €")

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
            
            if OTAZKA.upper() != "ŽIADNA ANKETA":
                st.divider()
                st.subheader("🗳️ Aktuálne hlasovanie")
                st.markdown(f'<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b;"><p style="color: #1f1f1f; font-size: 24px; font-weight: bold; margin-bottom: 0px;">{OTAZKA}</p></div>', unsafe_allow_html=True)
                
                za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
                ni = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
                
                st.write("")
                s1, s2 = st.columns(2)
                s1.metric("Priebežne ZA", za)
                s2.metric("Priebežne PROTI", ni)

                ex_hlas = df_h[df_h["VS"] == v]
                if not ex_hlas.empty:
                    st.warning(f"📢 Váš doteraz evidovaný hlas: **{ex_hlas.iloc[-1]['Hlas'].upper()}**")

                p_skr = (OTAZKA[:30] + '..') if len(OTAZKA) > 30 else OTAZKA
                b1, b2 = st.columns(2)
                b1.link_button("👍 HLASUJEM ZA", f"mailto:{MAIL}?subject=HLAS_ANO_{v}&body=Hlas_ANO_{v}", use_container_width=True)
                b2.link_button("👎 HLASUJEM PROTI", f"mailto:{MAIL}?subject=HLAS_NIE_{v}&body=Hlas_NIE_{v}", use_container_width=True)
            else:
                st.write("*(Momentálne neprebieha žiadne hlasovanie)*")
        else:
            st.error("VS sa nenašiel.")

    # VÝDAVKY (VYLEPŠENÉ O DOKLADY)
    st.write("---")
    with st.expander("📜 Zobraziť detailný zoznam výdavkov s dokladmi"):
        # Ak existuje stĺpec Doklad, Streamlit ho zobrazí ako klikateľný link
        st.write("Kliknutím na odkaz v stĺpci 'Doklad' sa vám otvorí faktúra.")
        
        # Príprava zobrazenia (odstránenie pomocných stĺpcov pre graf)
        cols_to_show = [c for c in df_v.columns if c not in ["dt", "m_fmt"]]
        
        st.dataframe(
            df_v[cols_to_show], 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Doklad": st.column_config.LinkColumn("Odkaz na doklad")
            }
        )

except Exception as e:
    st.info(f"Načítavam systém...")
