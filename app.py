import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time

# --- KONFIGURÁCIA ---
MAIL = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Postaviť heliport?"
HLAVNE_HESLO = "Victory2026" 

# Nastavenie stránky a názvu v prehliadači
st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# --- ZÁMOK STRÁNKY (Login) ---
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

# --- POMOCNÁ FUNKCIA NA NAČÍTANIE DÁT (Google Sheets) ---
def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except Exception:
        return pd.DataFrame()

# --- HLAVNÁ APLIKÁCIA ---
try:
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")

    # Hlavný titulok aplikácie
    st.title("🏡 Správa areálu Victory Port")
    
    # HLAVNÉ MENU ROZDELENÉ DO 4 ZÁLOŽIEK
    tab_home, tab_fin, tab_user, tab_vote = st.tabs([
        "📢 Nástenka", 
        "📊 Financie", 
        "🔑 Moja zóna", 
        "🗳️ Aktuálna anketa"
    ])

    # --- ZÁLOŽKA 1: NÁSTENKA A PODNETY ---
    with tab_home:
        st.markdown("### 📢 Aktuálne oznamy")
        if not df_n.empty:
            # Zobrazenie najnovších správ navrchu
            st.table(df_n.iloc[::-1])
        else:
            st.info("Momentálne nie sú na nástenke žiadne nové oznamy.")
        
        st.divider()
        st.markdown("### 🛠️ Podnet pre správcu")
        msg_text = st.text_area("Napíšte váš podnet, otázku alebo nahláste poruchu:", placeholder="Napr. Nesvieti lampa, nefunguje brána...")
        
        if msg_text:
            mail_subj = "Podnet z portálu Správa areálu Victory Port"
            mail_link = f"mailto:{MAIL}?subject={urllib.parse.quote(mail_subj)}&body={urllib.parse.quote(msg_text)}"
            st.link_button("🚀 Odoslať správu správcovi", mail_link, use_container_width=True)
        
        st.info(f"Ak tlačidlo vyššie nefunguje, pošlite e-mail manuálne na: **{MAIL}**")

    # --- ZÁLOŽKA 2: FINANCIE AREÁLU (Grafy a Výdavky) ---
    with tab_fin:
        if not df_p.empty:
            # Formátovanie VS na 4 číslice
            df_p["Identifikácia VS"] = df_p["Identifikácia VS"].astype(str).str.strip().str.zfill(4)
            stlpce_m = [c for c in df_p.columns if "/26" in c]
            
            # Výpočet súm platieb z Google Tabuľky
            p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
            
            # Výpočet výdavkov
            df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
            v_sum = df_v["Suma"].sum() if not df_v.empty else 0
            
            # Hlavné metriky (boxíky hore)
            m1, m2, m3 = st.columns(3)
            m1.metric("Fond celkom", f"{p_mes.sum():.2f} €")
            m2.metric("Výdavky celkom", f"{v_sum:.2f} €")
            m3.metric("Aktuálny zostatok", f"{(p_mes.sum() - v_sum):.2f} €")

            # Logika pre graf (kumulatívny zostatok)
            if "Dátum" in df_v.columns and not df_v.empty:
                df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
                df_v["m_fmt"] = df_v["dt"].dt.strftime('%m/%y')
                v_mes = df_v.groupby("m_fmt")["Suma"].sum().reindex(stlpce_m, fill_value=0)
                
                df_graf = pd.DataFrame({
                    "Mesiac": stlpce_m, 
                    "Zostatok": (p_mes.values - v_mes.values).cumsum()
                }).reset_index(drop=True)
                
                # Zobraziť len tie mesiace, ktoré už prebehli
                df_graf = df_graf[p_mes.values > 0]
                
                if not df_graf.empty:
                    fig = px.area(df_graf, x="Mesiac", y="Zostatok", title="Vývoj zostatku vo fonde", template="plotly_dark")
                    fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
                    st.plotly_chart(fig, use_container_width=True)

        # Tabuľka všetkých výdavkov schovaná pod expanderom
        with st.expander("📜 Zobraziť podrobný zoznam všetkých výdavkov", expanded=False):
            if not df_v.empty:
                cols_to_show = [c for c in df_v.columns if c not in ['dt', 'm_fmt']]
                st.dataframe(
                    df_v[cols_to_show], 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={"Doklad": st.column_config.LinkColumn("Doklad")}
                )
            else:
                st.info("Žiadne výdavky neboli zaevidované.")

    # --- ZÁLOŽKA 3: MOJA ZÓNA (Osobné platby) ---
    with tab_user:
        st.markdown("### 🔑 Prístup k osobným platbám")
        vs_in = st.text_input("Zadajte váš VS (4 číslice) pre zobrazenie vašich platieb:", placeholder="Napr. 0101")
        
        if vs_in:
            v_c = vs_in.strip().zfill(4)
            moje = df_p[df_p["Identifikácia VS"] == v_c]
            
            if not moje.empty:
                st.success(f"Overené pre VS: {v_c}")
                st.markdown("#### 💰 Tvoje platby do fondu")
                st.dataframe(moje, hide_index=True)
            else:
                st.error("Zadaný VS sa nenašiel v databáze platieb.")

    # --- ZÁLOŽKA 4: AKTUÁLNA ANKETA ---
    with tab_vote:
        if OTAZKA.upper() != "ŽIADNA ANKETA":
            st.markdown(f"### 🗳️ {OTAZKA}")
            
            # Priebežné výsledky (viditeľné pre všetkých)
            if not df_h.empty:
                df_h.columns = [c.strip() for c in df_h.columns]
                h_col = next((c for c in df_h.columns if "HLAS" in c.upper()), df_h.columns[-1])
                za = len(df_h[df_h[h_col].astype(str).str.upper().str.contains("ANO")])
                ni = len(df_h[df_h[h_col].astype(str).str.upper().str.contains("NIE")])
                
                c1, c2 = st.columns(2)
                c1.metric("Priebežne ZA", za)
                c2.metric("Priebežne PROTI", ni)
            
            st.divider()
            st.markdown("#### Overenie a odoslanie hlasu")
            vs_vote = st.text_input("Zadajte váš VS pre hlasovanie:", placeholder="Napr. 0101", key="vs_vote")
            
            if vs_vote:
                v_c_v = vs_vote.strip().zfill(4)
                # Overíme, či VS vôbec existuje medzi majiteľmi
                if any(df_p["Identifikácia VS"] == v_c_v):
                    v_c_clean = v_c_v.lstrip('0')
                    # Kontrola, či už je hlas v databáze
                    moj_h = df_h[df_h.apply(lambda row: any(str(x).strip().lstrip('0') == v_c_clean for x in row), axis=1)]
                    
                    if not moj_h.empty:
                        posledny_zapis = moj_h.iloc[-1]
                        vysledok_ikona = "ÁNO 👍" if "ANO" in str(posledny_zapis[h_col]).upper() else "NIE 👎"
                        st.warning(f"📢 **Váš zaevidovaný hlas k tejto ankete je:** {vysledok_ikona}")
                    else:
                        st.info("Zatiaľ ste v tejto ankete nehlasovali.")
                    
                    st.write("Vyberte vašu voľbu (otvorí e-mailovú správu):")
                    subj_za = f"HLAS_ANO_{v_c_v}: {OTAZKA}"
                    subj_ni = f"HLAS_NIE_{v_c_v}: {OTAZKA}"
                    
                    b1, b2 = st.columns(2)
                    b1.link_button("👍 HLASUJEM ZA", f"mailto:{MAIL}?subject={urllib.parse.quote(subj_za)}&body=Hlas_ANO_{v_c_v}", use_container_width=True)
                    b2.link_button("👎 HLASUJEM PROTI", f"mailto:{MAIL}?subject={urllib.parse.quote(subj_ni)}&body=Hlas_NIE_{v_c_v}", use_container_width=True)
                    
                    # Manuálne inštrukcie (navrátené formátovanie)
                    st.info("Ak tlačidlá vyššie nefungujú, pošlite e-mail manuálne:")
                    st.markdown(f"""
                    * 📧 Adresát: **{MAIL}**
                    * 🟢 Predmet pre ZA: `{subj_za}`
                    * 🔴 Predmet pre PROTI: `{subj_ni}`
                    """)
                else:
                    st.error("Zadaný VS sa nenašiel v zozname majiteľov.")
        else:
            st.info("Momentálne neprebieha žiadna nová anketa.")

    # Pätička portálu
    st.write("---")
    if st.button("Odhlásiť z portálu"):
        st.session_state["authenticated"] = False
        st.rerun()

except Exception as e:
    st.error(f"Kritická chyba pri spracovaní dát: {e}")

st.caption("© 2026 Správa areálu Victory Port")
