import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time

# --- KONFIGURÁCIA ---
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Súhlasíte s výstavbou nového detského ihriska?" # Tu meň otázku podľa potreby
HLAVNE_HESLO = "Victory2026" 

# Fixná šírka a nastavenie stránky
st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# --- FUNKCIA NA NAČÍTANIE DÁT S CACHE BUSTINGOM ---
def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except Exception as e:
        return pd.DataFrame()

# --- AUTENTIFIKÁCIA V STAVE SESSION ---
if "auth_pass" not in st.session_state:
    st.session_state["auth_pass"] = False
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# 1. ÚROVEŇ: HLAVNÉ HESLO PORTÁLU
if not st.session_state["auth_pass"]:
    st.markdown("<h2 style='text-align: center;'>🔐 Vstup do portálu</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Zadajte prístupové heslo:", type="password")
    if st.button("Pokračovať", use_container_width=True):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["auth_pass"] = True
            st.rerun()
        else:
            st.error("Nesprávne heslo!")
    st.stop()

# 2. ÚROVEŇ: IDENTIFIKÁCIA MAJITEĽA PODĽA VS
if st.session_state["auth_pass"] and st.session_state["user_data"] is None:
    st.markdown("<h2 style='text-align: center;'>🔑 Identifikácia majiteľa</h2>", unsafe_allow_html=True)
    vs_vstup = st.text_input("Zadajte váš Variabilný symbol (VS):", placeholder="Napr. 1007")
    if st.button("Prihlásiť sa", use_container_width=True):
        df_a = get_df("Adresar")
        if not df_a.empty:
            vs_col = next((c for c in df_a.columns if "VS" in c.upper()), None)
            if vs_col:
                df_a[vs_col] = df_a[vs_col].astype(str).str.strip().str.zfill(4)
                target_vs = vs_vstup.strip().zfill(4)
                user_row = df_a[df_a[vs_col] == target_vs]
                if not user_row.empty:
                    st.session_state["user_data"] = {
                        "vs": target_vs,
                        "meno": str(user_row.iloc[0].get("Meno a priezvisko", "Vlastník")),
                        "email": str(user_row.iloc[0].get("Email", "Neuvedený"))
                    }
                    st.rerun()
                else: st.error(f"VS {target_vs} nenájdený v adresári.")
    st.stop()

# --- PORTÁL (ZOBRAZENIE PO ÚSPEŠNOM PRIHLÁSENÍ) ---
try:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")

    # Personifikovaná hlavička
    st.markdown(f"<h1 style='text-align: center;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray;'>Identifikačné VS: {u['vs']} | {u['email']}</p>", unsafe_allow_html=True)
    
    c_out1, c_out2, c_out3 = st.columns([1,1,1])
    with c_out2:
        if st.button("Odhlásiť sa", use_container_width=True):
            st.session_state["auth_pass"] = False
            st.session_state["user_data"] = None
            st.rerun()

    st.divider()

    tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa"])

    # --- T1: NÁSTENKA ---
    with tabs[0]:
        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty:
            st.table(df_n.iloc[::-1]) # Najnovšie oznamy hore
        else:
            st.info("Žiadne nové oznamy na nástenke.")
        
        st.divider()
        st.subheader("🛠️ Podnet pre správcu")
        podnet = st.text_area("Napíšte váš podnet alebo nahláste poruchu:")
        if podnet:
            m_body = f"Od: {u['meno']} (VS: {u['vs']})\nEmail: {u['email']}\n\nSpráva:\n{podnet}"
            m_url = f"mailto:{MAIL_SPRAVCA}?subject=Podnet VP {u['vs']}&body={urllib.parse.quote(m_body)}"
            st.link_button("🚀 Odoslať podnet e-mailom", m_url, use_container_width=True)

    # --- T2: FINANCIE (FOND A VÝDAVKY) ---
    with tabs[1]:
        if not df_p.empty:
            stlpce_m = [c for c in df_p.columns if "/26" in c]
            p_sum = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
            v_sum = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Fond celkom", f"{p_sum:.2f} €")
            c2.metric("Výdavky celkom", f"{v_sum:.2f} €")
            c3.metric("Zostatok", f"{(p_sum - v_sum):.2f} €")

            # Graf vývoja financií
            if not df_v.empty and "Dátum" in df_v.columns:
                df_v["temp_dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
                v_mes = df_v.groupby(df_v["temp_dt"].dt.strftime('%m/%y'))["Suma"].sum().reindex(stlpce_m, fill_value=0)
                p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                df_g = pd.DataFrame({"Mesiac": stlpce_m, "Zostatok": (p_mes.values - v_mes.values).cumsum()})
                
                fig = px.area(df_g, x="Mesiac", y="Zostatok", title="Stav fondu v čase", template="plotly_dark")
                fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.3)')
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("📜 Detailný zoznam výdavkov")
        if not df_v.empty:
            zobrazit = [c for c in df_v.columns if c.lower() not in ["dt", "temp_dt"]]
            st.dataframe(df_v[zobrazit], hide_index=True, use_container_width=True,
                column_config={
                    "Doklad": st.column_config.LinkColumn("Doklad", display_text="Otvoriť link 🔗"),
                    "Suma": st.column_config.NumberColumn("Suma (€)", format="%.2f")
                })

    # --- T3: MOJE PLATBY ---
    with tabs[2]:
        st.subheader(f"💰 Moje platby (VS: {u['vs']})")
        vs_p = next((c for c in df_p.columns if "VS" in c.upper()), None)
        if vs_p:
            df_p[vs_p] = df_p[vs_p].astype(str).str.strip().str.zfill(4)
            moje = df_p[df_p[vs_p] == u['vs']]
            if not moje.empty:
                st.dataframe(moje, hide_index=True, use_container_width=True)
            else:
                st.warning("Pre váš variabilný symbol neboli nájdené žiadne platby.")

    # --- T4: ANKETA (PLNÁ AUTOMATIZÁCIA) ---
    with tabs[3]:
        if OTAZKA.upper() != "ŽIADNA ANKETA":
            st.subheader(f"🗳️ {OTAZKA}")
            
            # Dynamické hľadanie stĺpcov v tabuľke Hlasovanie
            COL_VS = next((c for c in df_h.columns if "VS" in c.upper()), "VS")
            COL_HLAS = next((c for c in df_h.columns if "HLAS" in c.upper() or "ODPOVEĎ" in c.upper()), "Hlas")
            COL_OTAZKA = next((c for c in df_h.columns if "OTÁZKA" in c.upper() or "OTAZKA" in c.upper()), "Otázka")

            v_c_clean = u['vs'].lstrip('0')
            uz_hlasoval = False
            moje_rozhodnutie = ""

            # 1. Kontrola, či užívateľ hlasoval v aktuálnej ankete
            if not df_h.empty and COL_OTAZKA in df_h.columns:
                current_vote = df_h[
                    (df_h[COL_VS].astype(str).str.strip().str.lstrip('0') == v_c_clean) & 
                    (df_h[COL_OTAZKA].astype(str).str.strip() == OTAZKA.strip())
                ]
                if not current_vote.empty:
                    uz_hlasoval = True
                    moje_rozhodnutie = str(current_vote.iloc[-1][COL_HLAS]).upper()

            # 2. Priebežné výsledky (len pre túto otázku)
            if not df_h.empty and COL_OTAZKA in df_h.columns:
                curr_q_df = df_h[df_h[COL_OTAZKA].astype(str).str.strip() == OTAZKA.strip()]
                za = len(curr_q_df[curr_q_df[COL_HLAS].astype(str).str.upper().str.contains("ANO|ÁNO", na=False)])
                ni = len(curr_q_df[curr_q_df[COL_HLAS].astype(str).str.upper().str.contains("NIE", na=False)])
                
                c1, c2 = st.columns(2)
                c1.metric("CELKOM ZA", f"{za} hlasov")
                c2.metric("CELKOM PROTI", f"{ni} hlasov")

            st.divider()

            # 3. Informácia o hlasovaní a deaktivácia
            if uz_hlasoval:
                volba_label = "ÁNO 👍" if "ANO" in moje_rozhodnutie else "NIE 👎"
                st.success(f"✅ **Váš hlas bol zaevidovaný.** (Vaša voľba: **{volba_label}**)")
                st.info("Zmena hlasu nie je povolená. Hlasovanie k tejto téme je pre vás uzavreté.")
            else:
                st.write("### Odoslať váš hlas:")
            
            # Tlačidlá s parametrom disabled
            b1, b2 = st.columns(2)
            subj_za = f"HLAS:ANO | VS:{u['vs']} | {OTAZKA}"
            subj_ni = f"HLAS:NIE | VS:{u['vs']} | {OTAZKA}"
            
            b1.link_button("👍 ZA", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(subj_za)}&body=Meno: {u['meno']}", 
                           use_container_width=True, disabled=uz_hlasoval)
            b2.link_button("👎 PROTI", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(subj_ni)}&body=Meno: {u['meno']}", 
                           use_container_width=True, disabled=uz_hlasoval)

            # 4. História všetkých hlasovaní vlastníka
            st.divider()
            st.subheader("📜 Vaša história hlasovaní")
            if not df_h.empty:
                moje_vsetky = df_h[df_h[COL_VS].astype(str).str.strip().str.lstrip('0') == v_c_clean]
                if not moje_vsetky.empty:
                    # Zobrazíme stĺpce, ktoré existujú (Otázka, Hlas, prípadne Dátum)
                    dostupne_cols = [c for c in [COL_OTAZKA, COL_HLAS, "Datum", "Dátum"] if c in moje_vsetky.columns]
                    st.dataframe(moje_vsetky[dostupne_cols], hide_index=True, use_container_width=True)
                else:
                    st.write("Zatiaľ ste nehlasovali v žiadnej ankete.")
        else:
