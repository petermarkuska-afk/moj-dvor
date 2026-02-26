import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURÁCIA ---
MAIL = "tvoj@email.com"
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
    
    # Mesačné sumy
    p_mesacne = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    # Prepojenie výdavkov s časovou osou cez stĺpec "Dátum"
    if "Dátum" in df_v.columns:
        df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
        df_v["m_fmt"] = df_v["dt"].dt.strftime('%m/%y')
        v_mesacne = df_v.groupby("m_fmt")["Suma"].sum().reindex(stlpce_m, fill_value=0)
    else:
        v_mesacne = pd.Series(0, index=stlpce_m)

    # Kumulatívny zostatok pre graf (Príjem - Výdavok)
    df_graf = pd.DataFrame({
        "Mesiac": stlpce_m,
        "Zostatok": (p_mesacne.values - v_mesacne.values).cumsum()
    })
    df_graf = df_graf[p_mesacne.values > 0]

    # --- ZOBRAZENIE ---

    # 1. NÁZOV
    st.markdown("<h1 style='text-align: center;'>🏡 Portál správcu VICTORY PORT</h1>", unsafe_allow_html=True)
    st.write("---")

    # 2. SÚČTY A GRAF
    c1, c2, c3 = st.columns(3)
    c_p = p_mesacne.sum()
    c_v = df_v["Suma"].sum()
    c1.metric("Fond celkom", f"{c_p:.2f} €")
    c2.metric("Výdavky celkom", f"{c_v:.2f} €")
    c3.metric("Aktuálny zostatok", f"{(c_p - c_v):.2f} €")

    st.subheader("📈 Vývoj zostatku fondu")
    if not df_graf.empty:
        fig = px.area(df_graf, x="Mesiac", y="Zostatok", template="plotly_dark")
        fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
        fig.update_layout(xaxis_title=None, yaxis_title="Suma v €", height=350)
        st.plotly_chart(fig, use_container_width=True)

    # 3. IDENTIFIKUJ SA
    st.write("---")
    st.subheader("🔐 IDENTIFIKUJ SA")
    vs_in = st.text_input("Zadajte váš variabilný symbol (4 číslice) pre prístup k hlasovaniu:")

    if vs_in:
        v = vs_in.zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == v]
        
        if not moje.empty:
            st.success(f"Overenie úspešné. Vitajte, používateľ VS {v}")
            st.dataframe(moje, hide_index=True)
            
            # 4. ANKETA A HLASOVANIE
            st.divider()
            st.subheader("🗳️ Aktuálna anketová otázka")
            st.info("**Súhlasíte s investíciou do modernizácie osvetlenia v spoločných priestoroch?**")
            
            za = len(df_h[df_h["Hlas"].astype(str).str.contains("ANO", na=False, case=False)])
            ni = len(df_h[df_h["Hlas"].astype(str).str.contains("NIE", na=False, case=False)])
            
            col_s1, col_s2 = st.columns(2)
            col_s1.metric("Priebežne ZA", za)
            col_s2.metric("Priebežne PROTI", ni)

            st.write("### Odošlite váš hlas kliknutím:")
            l1 = f"mailto:{MAIL}?subject=HLAS_ANO_VS_{v}&body=Potvrdzujem_hlas_ANO_za_jednotku_{v}"
            l2 = f"mailto:{MAIL}?subject=HLAS_NIE_VS_{v}&body=Potvrdzujem_hlas_NIE_za_jednotku_{v}"
            
            btn_a, btn_b = st.columns(2)
            btn_a.link_button("👍 HLASUJEM ZA", l1, use_container_width=True)
            btn_b.link_button("👎 HLASUJEM PROTI", l2, use_container_width=True)
            
            # MANUÁLNY NÁVOD PRE GMAIL
            with st.expander("Nefungujú vám tlačidlá? Návod pre manuálne hlasovanie:"):
                st.write(f"Ak sa vám po kliknutí neotvorí e-mail, pošlite ho manuálne:")
                st.write(f"1. Príjemca: **{MAIL}**")
                st.write(f"2. Predmet e-mailu: `HLAS_ANO_VS_{v}` (alebo `HLAS_NIE_VS_{v}`)")
                st.write(f"3. Do textu správy napíšte: *Hlasujem za/proti*.")
                st.caption("Dôležité: Predmet e-mailu musí obsahovať váš VS pre správne započítanie.")
        else:
            st.error("Zadaný variabilný symbol nebol nájdený.")

    # 5. VÝDAVKY (Úplne naspodku)
    st.write("---")
    with st.expander("📜 Zobraziť detailný zoznam výdavkov"):
        st.dataframe(df_v[["Dátum", "Účel", "Suma"]], hide_index=True, use_container_width=True)

except Exception as e:
    st.warning(f"Systém je pripravený. Čakám na dáta... (Info: {e})")
