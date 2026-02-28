import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
from datetime import datetime

# ==========================================
# 1. ZÁKLADNÁ KONFIGURÁCIA A NASTAVENIA
# ==========================================
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"
OTAZKA = "Súhlasíte s výstavbou nového detského ihriska?" 
HLAVNE_HESLO = "Victory2026" 
MESACNY_PREDPIS = 10.0  # Suma, ktorú má majiteľ mesačne platiť

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# --- FUNKCIA NA NAČÍTANIE DÁT Z GOOGLE SHEETS ---
def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        # Očistíme názvy stĺpcov od medzier
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except Exception:
        return pd.DataFrame()

# ==========================================
# 2. SYSTÉM PRIHLASOVANIA (AUTH)
# ==========================================
if "auth_pass" not in st.session_state:
    st.session_state["auth_pass"] = False
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- KROK 1: Hlavné heslo do portálu ---
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

# --- KROK 2: Identifikácia podľa VS ---
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
                else: st.error(f"VS {target_vs} nebol v adresári nájdený.")
    st.stop()

# ==========================================
# 3. HLAVNÝ OBSAH PORTÁLU (PO PRIHLÁSENÍ)
# ==========================================
try:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")

    st.markdown(f"<h1 style='text-align: center;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    
    # Tlačidlo na odhlásenie
    if st.button("Odhlásiť sa"):
        st.session_state.update({"auth_pass": False, "user_data": None})
        st.rerun()

    st.divider()
    tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa"])

    # --- TAB 1: NÁSTENKA ---
    with tabs[0]:
        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty:
            st.table(df_n.iloc[::-1])
        else:
            st.info("Momentálne nie sú žiadne nové oznamy.")

    # --- TAB 2: CELKOVÉ FINANCIE AREÁLU ---
    with tabs[1]:
        if not df_p.empty:
            stlpce_2026 = [c for c in df_p.columns if "/26" in c]
            suma_prijmy = df_p[stlpce_2026].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
            suma_vydavky = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Fond celkom", f"{suma_prijmy:.2f} €")
            c2.metric("Výdavky celkom", f"{suma_vydavky:.2f} €")
            c3.metric("Zostatok", f"{(suma_prijmy - suma_vydavky):.2f} €")
        
        st.subheader("📜 Detailný zoznam výdavkov")
        if not df_v.empty:
            st.dataframe(df_v, hide_index=True, use_container_width=True,
                column_config={"Doklad": st.column_config.LinkColumn("Doklad 🔗", display_text="Otvoriť")})

    # --- TAB 3: MOJE PLATBY (INTELIGENTNÁ KUMULATÍVNA LOGIKA) ---
    with tabs[2]:
        st.subheader(f"💰 Moje platby (VS: {u['vs']})")
        vs_col_p = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
        df_p[vs_col_p] = df_p[vs_col_p].astype(str).str.strip().str.zfill(4)
        moje_riadky = df_p[df_p[vs_col_p] == u['vs']]

        if not moje_riadky.empty:
            # Zobrazenie tabuľky platieb hore
            st.dataframe(moje_riadky, hide_index=True, use_container_width=True)
            
            # Výpočet očakávanej sumy k dnešnému dňu
            aktualny_mesiac = datetime.now().month
            suma_ktoru_mal_mat = aktualny_mesiac * MESACNY_PREDPIS
            
            # Súčet všetkých jeho úhrad v stĺpcoch /26
            stlpce_mesiace = [c for c in moje_riadky.columns if "/26" in c]
            suma_ktoru_realne_ma = pd.to_numeric(moje_riadky.iloc[0][stlpce_mesiace], errors='coerce').fillna(0).sum()
            
            rozdiel = suma_ktoru_realne_ma - suma_ktoru_mal_mat

            st.divider()
            if rozdiel < 0:
                # KONTRASTNÉ UPOZORNENIE NA DLH
                st.markdown(f"""
                <div style="background-color:#fff5f5; padding:20px; border-radius:12px; border:3px solid #e53e3e; text-align:center;">
                    <h3 style="color:#c53030; margin-top:0;">⚠️ Evidujeme nedoplatok: {abs(rozdiel):.2f} €</h3>
                    <p style="color:#2d3748;">K dnešnému dňu by malo byť uhradených spolu: <b>{suma_ktoru_mal_mat:.2f} €</b></p>
                    <p style="color:#2d3748;">Vaša celková suma úhrad v systéme: <b>{suma_ktoru_realne_ma:.2f} €</b></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                # KONTRASTNÉ POTVRDENIE O BEZDŽNOSTI
                st.markdown(f"""
                <div style="background-color:#f0fff4; padding:20px; border-radius:12px; border:3px solid #38a169; text-align:center;">
                    <h3 style="color:#2f855a; margin-top:0;">✅ Platby sú v poriadku</h3>
                    <p style="color:#2d3748;">Vaša bilancia k dnešnému dňu je: <b>+{rozdiel:.2f} €</b></p>
                    <p style="color:#2d3748;">Všetky záväzky máte vyrovnané (aj v prípade predplatného).</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Pre váš variabilný symbol sa nenašli žiadne záznamy.")

    # --- TAB 4: ANKETA A HISTÓRIA HLASOVANIA ---
    with tabs[3]:
        st.subheader(f"🗳️ Aktuálna otázka: {OTAZKA}")
        v_vs_cisty = u['vs'].lstrip('0')
        
        # Flexibilné hľadanie názvov stĺpcov
        c_h_vs = next((c for c in df_h.columns if "VS" in c.upper()), "VS")
        c_h_ot = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
        c_h_hl = next((c for c in df_h.columns if "HLAS" in c.upper()), "Hlas")

        uz_hlasoval = False
        if not df_h.empty and c_h_ot in df_h.columns:
            mask = (df_h[c_h_vs].astype(str).str.strip().str.lstrip('0') == v_vs_cisty) & (df_h[c_h_ot].astype(str).str.strip() == OTAZKA.strip())
            uz_hlasoval = any(mask)

        if uz_hlasoval:
            st.success("✅ Váš hlas k tejto otázke bol už úspešne zaznamenaný.")
        else:
            st.write("Vyjadrite svoj súhlas alebo nesúhlas kliknutím na tlačidlo:")
            col1, col2 = st.columns(2)
            subj_ano = f"HLAS:ANO | VS:{u['vs']} | {OTAZKA}"
            subj_nie = f"HLAS:NIE | VS:{u['vs']} | {OTAZKA}"
            
            col1.link_button("👍 SÚHLASÍM (ZA)", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(subj_ano)}", use_container_width=True)
            col2.link_button("👎 NESÚHLASÍM (PROTI)", f"mailto:{MAIL_SPRAVCA}?subject={urllib.parse.quote(subj_nie)}", use_container_width=True)

        st.divider()
        st.subheader("📜 Moja história hlasovaní")
        if not df_h.empty:
            moje_h = df_h[df_h[c_h_vs].astype(str).str.strip().str.lstrip('0') == v_vs_cisty]
            if not moje_h.empty:
                st.dataframe(moje_h, hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"Vyskytla sa neočakávaná systémová chyba: {e}")

# PÄTIČKA
st.markdown("<p style='text-align: center; font-size: 0.8em; color: gray; margin-top: 50px;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
