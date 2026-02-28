import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time

# --- KONFIGURÁCIA ---
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Súhlasíte s výstavbou nového detského ihriska?" 
HLAVNE_HESLO = "Victory2026" 

# Nastavenie stránky na fixnú šírku (centered)
st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# --- FUNKCIA NA NAČÍTANIE DÁT ---
def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- AUTENTIFIKÁCIA ---
if "auth_pass" not in st.session_state:
    st.session_state["auth_pass"] = False
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# 1. KROK: HLAVNÉ HESLO
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

# 2. KROK: IDENTIFIKÁCIA MAJITEĽA
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
                        "meno": str(user_row.iloc[0].get("Meno a priezvisko", "Neznámy")),
                        "email": str(user_row.iloc[0].get("Email", "Neuvedený"))
                    }
                    st.rerun()
                else: st.error(f"VS {target_vs} nenájdený.")
    st.stop()

# --- PORTÁL (PO PRIHLÁSENÍ) ---
try:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")

    # DYNAMICKÁ HLAVIČKA (Namiesto statického názvu portálu)
    st.markdown(f"<h1 style='text-align: center;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray;'>VS: {u['vs']} | {u['email']}</p>", unsafe_allow_html=True)
    
    col_out1, col_out2, col_out3 = st.columns([1,1,1])
    with col_out2:
        if st.button("Odhlásiť sa", use_container_width=True):
            st.session_state["auth_pass"] = False
            st.session_state["user_data"] = None
            st.rerun()

    st.divider()

    tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa"])

    # --- T1: NÁSTENKA ---
    with tabs[0]:
        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty: st.table(df_n.iloc[::-1])
        st.divider()
        st.subheader("🛠️ Podnet pre správcu")
        podnet = st.text_area("Napíšte váš podnet:")
        if podnet:
            m_body = f"Od: {u['meno']} (VS: {u['vs']})\nEmail: {u['email']}\n\nSpráva:\n{podnet}"
            m_url = f"mailto:{MAIL_SPRAVCA}?subject=Podnet VP {u['vs']}&body={urllib.parse.quote(m_body)}"
            st.link_button("🚀 Odoslať cez e-mail", m_url, use_container_width=True)

    # --- T2: FINANCIE ---
    with tabs[1]:
        if not df_p.empty:
            stlpce_m = [c for c in df_p.columns if "/26" in c]
            p_sum = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
            v_sum = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Fond celkom", f"{p_sum:.2f} €")
            c2.metric("Výdavky celkom", f"{v_sum:.2f} €")
            c3.metric("Zostatok", f"{(p_sum - v_sum):.2f} €")

            if not df_v.empty and "Dátum" in df_v.columns:
                df_v["temp_dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
                v_mes = df_v.groupby(df_v["temp_dt"].dt.strftime('%m/%y'))["Suma"].sum().reindex(stlpce_m, fill_value=0)
                p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                df_g = pd.DataFrame({"Mesiac": stlpce_m, "Zostatok": (p_mes.values - v_mes.values).cumsum()})
                
                fig = px.area(df_g, x="Mesiac", y="Zostatok", title="Vývoj financií", template="plotly_dark")
                fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.3)')
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("📜 Zoznam výdavkov")
        if not df_v.empty:
            zobrazit = [c for c in df_v.columns if c.lower() not in ["dt", "temp_dt"]]
            st.dataframe(df_v[zobrazit], hide_index=True, use_container_width=True,
                column_config={"Doklad": st.column_config.LinkColumn("Doklad", display_text="Otvoriť link 🔗"),
                               "Suma": st.column_config.NumberColumn("Suma (€)", format="%.2f")})

    # --- T3: MOJE PLATBY ---
    with tabs[2]:
        st.subheader(f"💰 Moje platby (VS: {u['vs']})")
        vs_p = next((c for c in df_p.columns if "VS" in c.upper()), None)
        if vs_p:
            df_p[vs_p] = df_p[vs_p].astype(str).str.strip().str.zfill(4)
            moje = df_p[df_p[vs_p] == u['vs']]
            st.dataframe(moje, hide_index=True, use_container_width=True)

    # --- T4: ANKETA (AUTODEAKTIVÁCIA A MAKE.COM) ---
    with tabs[3]:
        if OTAZKA.upper() != "ŽIADNA ANKETA":
            st.subheader(f"🗳️ {OTAZKA}")
            
            # Identifikácia stĺpcov v tabuľke Hlasovanie
            COL_VS = next((c for c in df_h.columns if "VS" in c.upper()), "VS")
            COL_HLAS = next((c for c in df_h.columns if "HLAS" in c.upper() or "ODPOVEĎ" in c.upper()), "Hlas")
            COL_OTAZKA = next((c for c in df_h.columns if "OTÁZKA" in c.upper() or "OTAZKA" in c.upper()), "Otázka")

            v_c_clean = u['vs'].lstrip('0')
            uz_hlasoval = False
            moje_rozhodnutie = ""

            # Kontrola hlasovania v aktuálnej téme
            if not df_h.empty and COL_OTAZKA in df_h.columns:
                current_vote = df_h[
                    (df_h[COL_VS].astype(str).str.strip().str.lstrip('0') == v_c_clean) & 
                    (df_h[COL_OTAZKA].astype(str) == OTAZKA)
                ]
                if not current_vote.empty:
                    uz_hlasoval = True
                    moje_rozhodnutie = str(current_vote.iloc[-1][COL_HLAS]).upper()

            # Priebežné výsledky
            if not df_h.empty and COL_OTAZKA in df_h.columns:
                curr_q_df = df_h[df_h[COL_OTAZKA].astype(str) == OTAZKA]
                za = len(curr_q_df[curr_q_df[COL_HLAS].astype(str).str.upper().str.contains("ANO|ÁNO")])
                ni = len(curr_q_df[curr_q_df[COL_HLAS].astype(str).str.upper().str.contains("NIE")])
                c1, c2 = st.columns(2)
                c1.metric("AKTUÁLNE ZA", f"{za} hlasov")
                c2.metric("AKTUÁLNE PROTI", f"{ni} hlasov")

            st.divider()

            if uz_hlasoval:
                volba_label = "ÁNO 👍" if "ANO" in moje_rozhodnutie else "NIE 👎"
                st.success(f"✅ **Váš hlas bol zaevidovaný.** (Voľba: **{volba_label}**)")
                st.info("Zmena hlasu nie je povolená.")
            else:
                st.write("### Odoslať váš hlas:")
            
            # Tlačidlá
            b1, b2 = st.columns(2)
            subj_za = f"HLAS:ANO | VS:{u['vs']} | {OTAZKA}"
            subj_ni = f"HLAS:NIE | VS:{u['vs']} | {OTAZKA}"
            
            b1.link_button("👍 ZA", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(subj_za)}&body=Meno: {u['meno']}", 
                           use_container_width=True, disabled=uz_hlasoval)
            b2.link_button("👎 PROTI", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(subj_ni)}&body=Meno: {u['meno']}", 
                           use_container_width=True, disabled=uz_hlasoval)

            # --- HISTÓRIA ---
            st.divider()
            st.subheader("📜 Moja história hlasovaní")
            if not df_h.empty:
                moje_vsetky = df_h[df_h[COL_VS].astype(str).str.strip().str.lstrip('0') == v_c_clean]
                if not moje_vsetky.empty:
                    st.dataframe(moje_vsetky[[COL_OTAZKA, COL_HLAS]], hide_index=True, use_container_width=True)
                else: st.write("Zatiaľ žiadne záznamy.")
        else:
            st.info("Žiadna anketa.")

except Exception as e:
    st.error(f"Vyskytla sa chyba: {e}")

st.markdown("<p style='text-align: center; font-size: 0.8em;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
