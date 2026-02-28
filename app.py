import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time

# --- KONFIGURÁCIA ---
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Postaviť heliport?"
HLAVNE_HESLO = "Victory2026" 

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# --- FUNKCIA NA NAČÍTANIE DÁT ---
def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- MODUL PRIHLÁSENIA (HESLO + VS) ---
if "auth_pass" not in st.session_state:
    st.session_state["auth_pass"] = False
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# 1. KROK: Hlavné heslo
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

# 2. KROK: Identifikácia cez hárok "Adresár"
if st.session_state["auth_pass"] and st.session_state["user_data"] is None:
    st.markdown("<h2 style='text-align: center;'>🔑 Identifikácia majiteľa</h2>", unsafe_allow_html=True)
    vs_vstup = st.text_input("Zadajte váš Variabilný symbol (VS):", placeholder="Napr. 0101")
    
    if st.button("Prihlásiť sa"):
        df_a = get_df("Adresar") # Načítame samostatný hárok Adresár
        if not df_a.empty:
            # Čistenie VS v Adresári
            df_a["VS"] = df_a["VS"].astype(str).str.strip().str.zfill(4)
            user_row = df_a[df_a["VS"] == vs_vstup.strip().zfill(4)]
            
            if not user_row.empty:
                st.session_state["user_data"] = {
                    "vs": vs_vstup.strip().zfill(4),
                    "meno": user_row.iloc[0].get("Meno a priezvisko", "Neznámy majiteľ"),
                    "email": user_row.iloc[0].get("Email", "Neuvedený mail")
                }
                st.rerun()
            else:
                st.error("Zadaný VS sa v Adresári nenašiel. Skontrolujte prosím údaje.")
        else:
            st.error("Nepodarilo sa načítať hárok Adresár. Skontrolujte názov hárku v Google Sheets.")
    st.stop()

# --- HLAVNÁ APLIKÁCIA (PO PRIHLÁSENÍ) ---
try:
    user = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")

    # Sidebar s vizitkou
    st.sidebar.markdown(f"### 👤 Prihlásený")
    st.sidebar.info(f"**{user['meno']}**\n\nVS: {user['vs']}\n\n{user['email']}")
    
    if st.sidebar.button("Odhlásiť sa"):
        st.session_state["auth_pass"] = False
        st.session_state["user_data"] = None
        st.rerun()

    st.title("🏡 Správa areálu Victory Port")
    
    tab_home, tab_fin, tab_user, tab_vote = st.tabs([
        "📢 Nástenka", "📊 Financie areálu", "💰 Moje platby", "🗳️ Aktuálna anketa"
    ])

    # --- ZÁLOŽKA 1: NÁSTENKA A PODNETY ---
    with tab_home:
        st.markdown("### 📢 Aktuálne oznamy")
        if not df_n.empty:
            st.table(df_n.iloc[::-1])
        
        st.divider()
        st.markdown("### 🛠️ Podnet pre správcu")
        msg_text = st.text_area("Napíšte váš podnet:", placeholder="Popíšte situáciu...")
        if msg_text:
            mail_body = f"Odosielateľ: {user['meno']} (VS: {user['vs']})\nEmail: {user['email']}\n\nSpráva:\n{msg_text}"
            mail_subj = f"Podnet - Victory Port - {user['meno']}"
            mail_link = f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(mail_subj)}&body={urllib.parse.quote(mail_body)}"
            st.link_button("🚀 Odoslať podnet správcovi", mail_link, use_container_width=True)

    # --- ZÁLOŽKA 2: FINANCIE AREÁLU ---
    with tab_fin:
        if not df_p.empty:
            df_p["VS"] = df_p["VS"].astype(str).str.strip().str.zfill(4)
            stlpce_m = [c for c in df_p.columns if "/26" in c]
            p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
            df_v["Suma"] = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0)
            v_sum = df_v["Suma"].sum() if not df_v.empty else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Fond celkom", f"{p_mes.sum():.2f} €")
            m2.metric("Výdavky celkom", f"{v_sum:.2f} €")
            m3.metric("Aktuálny zostatok", f"{(p_mes.sum() - v_sum):.2f} €")

            if "Dátum" in df_v.columns and not df_v.empty:
                df_v["dt"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
                df_v["m_fmt"] = df_v["dt"].dt.strftime('%m/%y')
                v_mes = df_v.groupby("m_fmt")["Suma"].sum().reindex(stlpce_m, fill_value=0)
                df_graf = pd.DataFrame({"Mesiac": stlpce_m, "Zostatok": (p_mes.values - v_mes.values).cumsum()}).reset_index(drop=True)
                df_graf = df_graf[p_mes.values > 0]
                if not df_graf.empty:
                    fig = px.area(df_graf, x="Mesiac", y="Zostatok", title="Vývoj zostatku vo fonde", template="plotly_dark")
                    fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
                    st.plotly_chart(fig, use_container_width=True)

        with st.expander("📜 Podrobný zoznam výdavkov", expanded=False):
            if not df_v.empty:
                st.dataframe(df_v[[c for c in df_v.columns if c not in ['dt', 'm_fmt']]], hide_index=True, use_container_width=True,
                             column_config={"Doklad": st.column_config.LinkColumn("Doklad")})

    # --- ZÁLOŽKA 3: MOJE PLATBY ---
    with tab_user:
        st.markdown(f"### 💰 Tvoje platby do fondu (VS: {user['vs']})")
        df_p["VS"] = df_p["VS"].astype(str).str.strip().str.zfill(4)
        moje = df_p[df_p["VS"] == user['vs']]
        if not moje.empty:
            st.dataframe(moje, hide_index=True, use_container_width=True)
        else:
            st.warning("Pre váš VS neboli nájdené žiadne platby v hárku Platby.")

    # --- ZÁLOŽKA 4: ANKETA ---
    with tab_vote:
        if OTAZKA.upper() != "ŽIADNA ANKETA":
            st.markdown(f"### 🗳️ {OTAZKA}")
            if not df_h.empty:
                df_h.columns = [c.strip() for c in df_h.columns]
                h_col = next((c for c in df_h.columns if "HLAS" in c.upper()), df_h.columns[-1])
                za = len(df_h[df_h[h_col].astype(str).str.upper().str.contains("ANO")])
                ni = len(df_h[df_h[h_col].astype(str).str.upper().str.contains("NIE")])
                c1, c2 = st.columns(2); c1.metric("ZA", za); c2.metric("PROTI", ni)

                v_c_clean = user['vs'].lstrip('0')
                moj_h = df_h[df_h.apply(lambda row: any(str(x).strip().lstrip('0') == v_c_clean for x in row), axis=1)]
                if not moj_h.empty:
                    vysledok = "ÁNO 👍" if "ANO" in str(moj_h.iloc[-1][h_col]).upper() else "NIE 👎"
                    st.warning(f"📢 **Váš zaevidovaný hlas k tejto ankete je:** {vysledok}")

            st.divider()
            subj_za = f"HLAS_ANO_{user['vs']}: {OTAZKA}"
            subj_ni = f"HLAS_NIE_{user['vs']}: {OTAZKA}"
            b1, b2 = st.columns(2)
            b1.link_button("👍 HLASUJEM ZA", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(subj_za)}&body=Meno: {user['meno']}", use_container_width=True)
            b2.link_button("👎 HLASUJEM PROTI", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(subj_ni)}&body=Meno: {user['meno']}", use_container_width=True)
            
            st.info(f"Hlasujete ako: **{user['meno']}**")
        else:
            st.info("Momentálne neprebieha žiadna anketa.")

except Exception as e:
    st.error(f"Kritická chyba: {e}")

st.caption("© 2026 Správa areálu Victory Port")
