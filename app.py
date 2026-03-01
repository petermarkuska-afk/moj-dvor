import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
import io
import segno
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURÁCIA PORTÁLU
# ==========================================
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

# SEM VLOŽTE SKUTOČNÝ IBAN (Kľúčové pre funkčnosť QR kódu v bankách)
IBAN_FONDU = "SK0000000000000000000000" 

# KONFIGURÁCIA ANKETY
OTAZKA = "Súhlasíte s jednorazovým vkladom do fondu areálu?" 
DATUM_VYHLASENIA = "2026-03-01" 

HLAVNE_HESLO = "Victory2026" 
MESACNY_PREDPIS = 10.0 

# Nastavenie šírky na 'centered' pre profesionálny vzhľad
st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# --- POMOCNÉ FUNKCIE ---
def ziskaj_odpocet(start_date_str):
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        koniec_dt = start_dt + timedelta(days=10)
        teraz = datetime.now()
        zostava = koniec_dt - teraz
        return zostava, koniec_dt
    except:
        return timedelta(0), datetime.now()

def get_df(sheet):
    try:
        cache_bust = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# ==========================================
# 2. AUTENTIFIKÁCIA
# ==========================================
if "auth_pass" not in st.session_state: st.session_state["auth_pass"] = False
if "user_data" not in st.session_state: st.session_state["user_data"] = None

if not st.session_state["auth_pass"]:
    st.markdown("<h2 style='text-align: center;'>🔐 Vstup do portálu Victory Port</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Zadajte prístupové heslo:", type="password")
    if st.button("Vstúpiť", use_container_width=True):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["auth_pass"] = True
            st.rerun()
        else:
            st.error("Nesprávne prístupové heslo. Kontaktujte správcu.")
    st.stop()

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
                else:
                    st.error(f"VS {target_vs} nebol nájdený v databáze.")
    st.stop()

# ==========================================
# 3. HLAVNÝ OBSAH (Po prihlásení)
# ==========================================
try:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")
    df_o = get_df("Odkazy")

    # Logika pre Anketu
    je_zadana_otazka = bool(OTAZKA and OTAZKA.strip() != "" and "ŽIADNA" not in OTAZKA.upper())
    anketa_aktivna = False
    dni_do_konca = 0
    koniec_dt = datetime.now()
    if je_zadana_otazka:
        zostava, koniec_dt = ziskaj_odpocet(DATUM_VYHLASENIA)
        if zostava.total_seconds() > 0:
            anketa_aktivna = True
            dni_do_konca = zostava.days

    # Horná navigácia a info
    st.markdown(f"<h1 style='text-align: center; margin-bottom:0;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray;'>Variabilný symbol: {u['vs']}</p>", unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1,1,1])
    with col_l2:
        if st.button("Odhlásiť sa", use_container_width=True):
            st.session_state.update({"auth_pass": False, "user_data": None})
            st.rerun()

    st.divider()
    tabs = st.tabs(["📢 NÁSTENKA", "📊 FINANCIE", "💰 MOJE PLATBY", "🗳️ ANKETA", "💬 POKEC"])

    # --- TAB 1: NÁSTENKA ---
    with tabs[0]:
        if je_zadana_otazka and anketa_aktivna:
            st.markdown(f"""
            <div style="background-color:#fff3cd; padding:20px; border-radius:15px; border-left:8px solid #ffc107; margin-bottom:25px;">
                <h3 style="color:#856404; margin-top:0;">🗳️ Prebieha dôležité hlasovanie!</h3>
                <p style="font-size:1.1em; color:#856404;"><b>Otázka:</b> {OTAZKA}</p>
                <p style="font-size:1.2em; font-weight:bold; color:#d9534f; margin-bottom:5px;">⌛ Koniec o: {dni_do_konca} dní</p>
                <p style="font-size:0.9em; color:#856404; margin-bottom:0;">Svoj hlas odovzdajte v sekcii <b>Anketa</b>.</p>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("📢 Aktuálne oznamy areálu")
        if not df_n.empty:
            st.table(df_n.iloc[::-1])
        else:
            st.info("Momentálne nie sú zverejnené žiadne nové oznamy.")

        st.divider()
        st.subheader("🛠️ Máte podnet alebo problém?")
        p_txt = st.text_area("Napíšte správcovi (napr. oprava brány, osvetlenie...):")
        if p_txt:
            p_s = urllib.parse.quote(f"Podnet Victory Port - VS {u['vs']}")
            p_b = urllib.parse.quote(f"Od: {u['meno']} (VS: {u['vs']})\n\nText podnetu:\n{p_txt}")
            st.link_button("🚀 Odoslať podnet e-mailom", f"mailto:{MAIL_SPRAVCA}?subject={p_s}&body={p_b}", use_container_width=True)
            st.caption("Po kliknutí sa otvorí váš e-mailový klient (Outlook, Gmail...).")

    # --- TAB 2: FINANCIE (PREHĽAD CELKOM) ---
    with tabs[1]:
        if not df_p.empty:
            stlpce_26 = [c for c in df_p.columns if "/26" in c]
            total_p = df_p[stlpce_26].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
            total_v = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Fond celkom", f"{total_p:.2f} €")
            c2.metric("Výdavky celkom", f"{total_v:.2f} €")
            c3.metric("Zostatok fondu", f"{(total_p - total_v):.2f} €", delta_color="normal")

            # Graf vývoja zostatku
            if not df_v.empty and "Dátum" in df_v.columns:
                st.subheader("📈 Vývoj zostatku v čase")
                df_v_graph = df_v.copy()
                df_v_graph["temp_dt"] = pd.to_datetime(df_v_graph["Dátum"], dayfirst=True, errors='coerce')
                v_mesiac = df_v_graph.groupby(df_v_graph["temp_dt"].dt.strftime('%m/%y'))["Suma"].sum().reindex(stlpce_26, fill_value=0)
                p_mesiac = df_p[stlpce_26].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                df_graf_data = pd.DataFrame({"Mesiac": stlpce_26, "Zostatok": (p_mesiac.values - v_mesiac.values).cumsum()})
                
                fig = px.area(df_graf_data, x="Mesiac", y="Zostatok", template="plotly_white")
                fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.2)')
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("📜 Zoznam všetkých výdavkov")
        if not df_v.empty:
            st.dataframe(df_v, hide_index=True, use_container_width=True,
                         column_config={"Doklad": st.column_config.LinkColumn("Faktúra 🔗", display_text="Zobraziť")})

    # --- TAB 3: MOJE PLATBY + QR MODUL ---
    with tabs[2]:
        st.subheader(f"💰 Moja finančná bilancia (VS {u['vs']})")
        vs_clean = str(u['vs']).strip().zfill(4)
        vs_col_p = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
        df_p[vs_col_p] = df_p[vs_col_p].astype(str).str.strip().str.zfill(4)
        moje_data = df_p[df_p[vs_col_p] == vs_clean]

        if not moje_data.empty:
            st.dataframe(moje_data, hide_index=True, use_container_width=True)
            
            zaplatene = pd.to_numeric(moje_data.iloc[0][stlpce_26], errors='coerce').fillna(0).sum()
            mesiac = datetime.now().month
            predpis = mesiac * MESACNY_PREDPIS
            bilancia = zaplatene - predpis

            st.divider()
            if bilancia < 0:
                nedoplatok = abs(bilancia)
                suma_str = "{:.2f}".format(nedoplatok)
                st.markdown(f"""
                <div style="background-color:#fff5f5; padding:25px; border-radius:15px; border:2px solid #e53e3e; text-align:center;">
                    <h2 style="color:#c53030; margin-top:0;">⚠️ Nedoplatok: {suma_str} €</h2>
                    <p style="color:#2d3748; font-size:1.1em; margin-bottom:5px;">Pre vyrovnanie platieb naskenujte tento kód:</p>
                </div>
                """, unsafe_allow_html=True)

                # QR KÓD (Slovenský SPD štandard)
                qr_payload = f"SPD*1.0*ACC:{IBAN_FONDU}*AM:{suma_str}*CUR:EUR*VS:{vs_clean}*MSG:FondVictoryPort"
                qr = segno.make(qr_payload)
                buff = io.BytesIO()
                qr.save(buff, kind='png', scale=10)
                
                cq1, cq2, cq3 = st.columns([1, 1.8, 1])
                with cq2:
                    st.image(buff.getvalue(), caption=f"QR Platba: {suma_str} € (VS: {vs_clean})", use_container_width=True)
                
                st.markdown(f"""
                <div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border:1px solid #dee2e6;">
                    <p style="color:#6c757d; font-size:0.9em; margin-bottom:0;"><b>Manuálna platba:</b> IBAN: {IBAN_FONDU}, VS: {vs_clean}, Suma: {suma_str} €</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.success(f"✅ Všetko máte v poriadku. Evidujeme preplatok {bilancia:.2f} €.")
        else:
            st.warning("Údaje o vašich platbách sa nenašli. Kontaktujte správcu.")

    # --- TAB 4: ANKETA ---
    with tabs[3]:
        if not je_zadana_otazka:
            st.info("Momentálne neprebieha žiadna oficiálna anketa.")
        else:
            st.subheader(f"🗳️ {OTAZKA}")
            if not df_h.empty:
                c_h_ot = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
                c_h_hl = next((c for c in df_h.columns if "HLAS" in c.upper()), "Hlas")
                df_curr = df_h[df_h[c_h_ot].astype(str).str.strip() == OTAZKA.strip()]
                
                za = len(df_curr[df_curr[c_h_hl].astype(str).str.upper().str.contains("ANO|ZA")])
                proti = len(df_curr[df_curr[c_h_hl].astype(str).str.upper().str.contains("NIE|PROTI")])
                
                r1, r2, r3 = st.columns(3)
                r1.metric("ZA 👍", za)
                r2.metric("PROTI 👎", proti)
                r3.metric("Spolu odovzdané", za+proti)

            st.divider()
            if anketa_aktivna:
                st.write("Svoj hlas odošlete kliknutím na tlačidlo (otvorí e-mail):")
                s_za = urllib.parse.quote(f"HLAS:ANO | VS:{u['vs']} | {OTAZKA}")
                s_ni = urllib.parse.quote(f"HLAS:NIE | VS:{u['vs']} | {OTAZKA}")
                
                b1, b2 = st.columns(2)
                b1.link_button("👍 HLASUJEM ZA", f"mailto:{MAIL_SPRAVCA}?subject={s_za}", use_container_width=True)
                b2.link_button("👎 HLASUJEM PROTI", f"mailto:{MAIL_SPRAVCA}?subject={s_ni}", use_container_width=True)
                
                st.markdown(f"""
                <div style="background-color:#f0fff4; padding:15px; border-radius:10px; border:1px solid #38a169; margin-top:20px;">
                    <p style="color:#2f855a; font-size:0.9em; margin-bottom:0;"><b>Tip:</b> Ak tlačidlá nefungujú, pošlite e-mail na {MAIL_SPRAVCA} s textom ZA/PROTI a vaším VS.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("⌛ Čas na hlasovanie v tejto ankete už vypršal.")

    # --- TAB 5: POKEC ---
    with tabs[4]:
        st.subheader("💬 Verejné správy pre susedov")
        pokec_txt = st.text_area("Napíšte odkaz susedom (zobrazí sa po schválení):")
        if pokec_txt:
            s_pk = urllib.parse.quote(f"ODKAZ | VS:{u['vs']}")
            b_pk = urllib.parse.quote(f"Od: {u['meno']}\nText:\n{pokec_txt}")
            st.link_button("✉️ Odoslať odkaz na nástenku", f"mailto:{MAIL_SPRAVCA}?subject={s_pk}&body={b_pk}", use_container_width=True)
        
        st.divider()
        if not df_o.empty:
            for _, r in df_o.iloc[::-1].iterrows():
                with st.chat_message("user"):
                    st.write(f"**{r.get('Meno','Neznámy')}** ({r.get('Dátum','')})")
                    st.info(r.get('Odkaz','...'))

except Exception as e:
    st.error(f"Systémová chyba pri načítaní dát: {e}")

st.markdown("<p style='text-align: center; color: gray; margin-top: 50px;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
