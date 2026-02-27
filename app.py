import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse

# --- KONFIGURÁCIA ---
MAIL = "pmarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Súhlasíte s investíciou do modernizácie osvetlenia?"
HLAVNE_HESLO = "Victory2026" 

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

# --- ZÁMOK STRÁNKY ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h2 style='text-align: center;'>🔐 Vstup do portálu</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Zadajte heslo:", type="password")
    if st.button("Vstúpiť", use_container_width=True):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Nesprávne heslo!")
    st.stop()

# --- NAČÍTANIE DÁT ---
def get_df(sheet):
    try:
        import time
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

try:
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")

    # 1. ČISTENIE DÁT FINANCIE
    if not df_p.empty:
        df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.strip().str.zfill(4)
        stlpce_m = [c for c in df_p.columns if "/26" in c]
        p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    else:
        p_mes = pd.Series()

    # --- UI HLAVIČKA ---
    st.title("🏡 Victory Port")
    if st.button("Odhlásiť"):
        st.session_state["authenticated"] = False
        st.rerun()
    st.write("---")

    # METRIKY A GRAF (Zostávajú nezmenené)
    if not p_mes.empty:
        v_sum = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("Fond celkom", f"{p_mes.sum():.2f} €")
        m2.metric("Výdavky celkom", f"{v_sum:.2f} €")
        m3.metric("Aktuálny zostatok", f"{(p_mes.sum() - v_sum):.2f} €")

    # --- SEKČIA POUŽÍVATEĽA ---
    st.write("---")
    vs_in = st.text_input("Zadajte váš VS (4 číslice):")
    
    if vs_in:
        v_c = vs_in.strip().zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == v_c]
        
        if not moje.empty:
            st.success(f"Overené pre VS: {v_c}")
            
            if OTAZKA.upper() != "ŽIADNA ANKETA":
                st.divider()
                st.subheader("🗳️ Aktuálna anketa")
                
                # Grafický box pre otázku
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b;">
                    <p style="color: #1f1f1f; font-size: 22px; font-weight: bold; margin-bottom: 0px;">{OTAZKA}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # SPRACOVANIE HLASOV
                if not df_h.empty:
                    df_h["VS_Check"] = df_h["VS"].astype(str).str.strip().str.zfill(4)
                    df_h["Hlas_Upper"] = df_h["Hlas"].astype(str).str.upper()
                    
                    za = len(df_h[df_h["Hlas_Upper"].str.contains("ANO")])
                    ni = len(df_h[df_h["Hlas_Upper"].str.contains("NIE")])
                    
                    s1, s2 = st.columns(2)
                    s1.metric("Priebežne ZA", za)
                    s2.metric("Priebežne PROTI", ni)

                    # Rozšírené hľadanie hlasu (stĺpec VS alebo text v Hlas)
                    moj_h = df_h[(df_h["VS_Check"] == v_c) | (df_h["Hlas_Upper"].str.contains(v_c))]
                    
                    if not moj_h.empty:
                        posledny = moj_h.iloc[-1]["Hlas_Upper"]
                        vysledok_text = "ÁNO 👍" if "ANO" in posledny else "NIE 👎"
                        st.warning(f"📢 **Váš zaevidovaný hlas:** {vysledok_text}")
                    else:
                        st.info("Zatiaľ ste v tejto ankete nehlasovali.")
                
                # PRÍPRAVA PREDMETU MAILU (Kódovanie pre URL)
                subj_za = urllib.parse.quote(f"HLAS_ANO_{v_c}: {OTAZKA}")
                subj_ni = urllib.parse.quote(f"HLAS_NIE_{v_c}: {OTAZKA}")
                
                st.write("### ✉️ Ako hlasovať?")
                tab1, tab2 = st.tabs(["Rýchle hlasovanie", "Manuálny návod"])
                
                with tab1:
                    st.write("Kliknite na tlačidlo a odošlite vygenerovaný e-mail.")
                    b1, b2 = st.columns(2)
                    b1.link_button("👍 HLASUJEM ZA", f"mailto:{MAIL}?subject={subj_za}&body=Potvrdzujem hlas ZA pre VS {v_c}", use_container_width=True)
                    b2.link_button("👎 HLASUJEM PROTI", f"mailto:{MAIL}?subject={subj_ni}&body=Potvrdzujem hlas PROTI pre VS {v_c}", use_container_width=True)
                
                with tab2:
                    st.info("Ak tlačidlá nefungujú, pošlite e-mail manuálne takto:")
                    st.markdown(f"""
                    1. Adresát: **{MAIL}**
                    2. Predmet (skopírujte presne): **HLAS_ANO_{v_c}: {OTAZKA}**
                    3. Odošlite e-mail (text môže byť prázdny).
                    """)

    with st.expander("📜 Výdavky"):
        st.dataframe(df_v, hide_index=True)

except Exception as e:
    st.error(f"Chyba: {e}")
