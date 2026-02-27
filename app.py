import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURÁCIA ---
MAIL = "tvoj@email.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Súhlasíte s investíciou do modernizácie osvetlenia?"
HLAVNE_HESLO = "Victory2026" 

st.set_page_config(page_title="Victory Port", layout="centered", page_icon="🏡")

# --- ZÁMOK STRÁNKY ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h2 style='text-align: center;'>🔐 Victory Port - Vstup</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Heslo:", type="password")
    if st.button("Vstúpiť"):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Nesprávne heslo!")
    st.stop()

# --- NAČÍTANIE DÁT ---
def get_df(sheet):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}"
        return pd.read_csv(url).dropna(how='all')
    except:
        return pd.DataFrame()

try:
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie") # Tabuľka z Make.com

    # ČISTENIE DÁT
    df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.strip().str.zfill(4)
    stlpce_m = [c for c in df_p.columns if "/26" in c]
    p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
    
    # Grafika a Metriky (zjednodušené pre prehľadnosť)
    st.title("🏡 Victory Port")
    if st.button("Odhlásiť"):
        st.session_state["authenticated"] = False
        st.rerun()
    st.write("---")

    m1, m2, m3 = st.columns(3)
    m1.metric("Fond", f"{p_mes.sum():.2f} €")
    m2.metric("Výdavky", f"{df_v['Suma'].sum():.2f} €")
    m3.metric("Zostatok", f"{(p_mes.sum() - df_v['Suma'].sum()):.2f} €")

    # --- SEKČIA POUŽÍVATEĽA ---
    st.write("---")
    vs_in = st.text_input("Zadajte VS (4 číslice):")
    if vs_in:
        v_c = vs_in.strip().zfill(4)
        moje = df_p[df_p["Identifikácia VS"] == v_c]
        
        if not numpy.empty(moje): # Malá oprava pre stabilitu
            st.success(f"Overené: VS {v_c}")
            
            if OTAZKA.upper() != "ŽIADNA ANKETA":
                st.divider()
                st.subheader("🗳️ Anketa")
                st.info(OTAZKA)
                
                # --- NOVÁ LOGIKA HLASOVANIA (Hľadá VS v texte zo stĺpca Hlas) ---
                if not df_h.empty:
                    # Prevedieme stĺpec Hlas na text a veľké písmená pre ľahšie hľadanie
                    df_h["Hlas_Text"] = df_h["Hlas"].astype(str).str.upper()
                    
                    # Spočítame hlasy globálne
                    celkom_za = len(df_h[df_h["Hlas_Text"].str.contains("ANO")])
                    celkom_proti = len(df_h[df_h["Hlas_Text"].str.contains("NIE")])
                    
                    s1, s2 = st.columns(2)
                    s1.metric("Priebežne ZA", celkom_za)
                    s2.metric("Priebežne PROTI", celkom_proti)

                    # Nájdeme konkrétny hlas pre zadaný VS
                    # Hľadáme riadky, ktoré v stĺpci Hlas obsahujú zadané VS (napr. "0001")
                    moj_riadok = df_h[df_h["Hlas_Text"].str.contains(v_c)]
                    
                    if not moj_riadok.empty:
                        posledny_zaznam = moj_riadok.iloc[-1]["Hlas_Text"]
                        vysledok = "ÁNO 👍" if "ANO" in posledny_zaznam else "NIE 👎"
                        st.warning(f"Váš zaevidovaný hlas: **{vysledok}**")
                    else:
                        st.info("Zatiaľ ste nehlasovali.")
                
                # Tlačidlá (predmet upravený pre tvoj Make.com filter)
                st.link_button("👍 HLASUJEM ZA", f"mailto:{MAIL}?subject=HLAS_ANO_{v_c}&body=Hlas_ANO_{v_c}")
                st.link_button("👎 HLASUJEM PROTI", f"mailto:{MAIL}?subject=HLAS_NIE_{v_c}&body=Hlas_NIE_{v_c}")

    # Zoznam výdavkov na konci
    with st.expander("📜 Zobraziť výdavky"):
        st.dataframe(df_v, hide_index=True)

except Exception as e:
    st.error(f"Chyba pri načítaní: {e}")
