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
# Názov portálu: Správa areálu Victory Port
MAIL_SPRAVCA = "petermarkuska@gmail.com"
SID = "13gFwOsSO0Di5sL_P-mBXDhmxu3K3W6Mcmcv3aoaXSgY"

# SEM VLOŽTE SKUTOČNÝ IBAN (Bez neho banky nenačítajú VS)
IBAN_FONDU = "SK0000000000000000000000" 

# KONFIGURÁCIA ANKETY
OTAZKA = "Súhlasíte s jednorazovým vkladom do fondu areálu?" 
DATUM_VYHLASENIA = "2026-03-01" 

HLAVNE_HESLO = "Victory2026" 
MESACNY_PREDPIS = 10.0 

# FIXNÁ ŠÍRKA STRÁNKY (Centered)
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
    st.markdown("<h2 style='text-align: center;'>🔐 Vstup do portálu</h2>", unsafe_allow_html=True)
    heslo_vstup = st.text_input("Zadajte prístupové heslo:", type="password")
    if st.button("Pokračovať", use_container_width=True):
        if heslo_vstup == HLAVNE_HESLO:
            st.session_state["auth_pass"] = True
            st.rerun()
        else: st.error("Nesprávne heslo!")
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
                else: st.error(f"VS {target_vs} nebol nájdený v adresári.")
    st.stop()

# ==========================================
# 3. HLAVNÝ PORTÁL
# ==========================================
try:
    u = st.session_state["user_data"]
    df_p = get_df("Platby")
    df_v = get_df("Vydavky")
    df_h = get_df("Hlasovanie")
    df_n = get_df("Nastenka")
    df_o = get_df("Odkazy")

    je_zadana_otazka = bool(OTAZKA and OTAZKA.strip() != "" and "ŽIADNA" not in OTAZKA.upper())
    anketa_aktivna = False
    dni_do_konca = 0
    koniec_dt = datetime.now()
    if je_zadana_otazka:
        zostava, koniec_dt = ziskaj_odpocet(DATUM_VYHLASENIA)
        if zostava.total_seconds() > 0:
            anketa_aktivna = True
            dni_do_konca = zostava.days

    st.markdown(f"<h1 style='text-align: center;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    
    c_out1, c_out2, c_out3 = st.columns([1,1,1])
    with c_out2:
        if st.button("Odhlásiť sa", use_container_width=True):
            st.session_state.update({"auth_pass": False, "user_data": None})
            st.rerun()

    st.divider()
    tabs = st.tabs(["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa", "💬 Miestny pokec"])

    # --- TAB 1: NÁSTENKA ---
    with tabs[0]:
        if je_zadana_otazka and anketa_aktivna:
            st.markdown(f"""<div style="background-color:#fff3cd; padding:20px; border-radius:15px; border-left:8px solid #ffc107; margin-bottom:25px;">
                <h3 style="color:#856404; margin-top:0;">🗳️ Prebieha hlasovanie!</h3>
                <p style="font-size:1.1em; color:#856404;"><b>Otázka:</b> {OTAZKA}</p>
                <p style="font-size:1.2em; font-weight:bold; color:#d9534f;">⏳ Koniec o: {dni_do_konca} dní ({koniec_dt.strftime('%d.%m.%Y')})</p>
                <p style="font-size:1.0em; color:#856404;">Svoj hlas odovzdajte v záložke <b>Anketa</b>.</p>
            </div>""", unsafe_allow_html=True)

        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty: st.table(df_n.iloc[::-1])
        
        st.divider()
        st.subheader("🛠️ Podnet pre správcu")
        pod_msg = st.text_area("Váš súkromný podnet (uvidí len správca):")
        p_subj = urllib.parse.quote(f"Podnet VP {u['vs']}")
        p_body = urllib.parse.quote(f"Od: {u['meno']} (VS: {u['vs']})\n\nPodnet:\n{pod_msg}")
        st.link_button("🚀 Odoslať podnet automaticky", f"mailto:{MAIL_SPRAVCA}?subject={p_subj}&body={p_body}", use_container_width=True)
        
        st.markdown(f"""<div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border:1px solid #dee2e6; margin-top:15px;">
            <p style="color:#6c757d; font-size:0.9em; margin-bottom:0;"><b>Manuálny návod:</b> Ak nefunguje tlačidlo, pošlite e-mail na <b>{MAIL_SPRAVCA}</b> s predmetom <b>Podnet VP {u['vs']}</b>.</p>
        </div>""", unsafe_allow_html=True)

    # --- TAB 2: FINANCIE ---
    with tabs[1]:
        if not df_p.empty:
            stlpce_m = [c for c in df_p.columns if "/26" in c]
            p_sum = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
            v_sum = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Prijmy fondu", f"{p_sum:.2f} €")
            c2.metric("Výdavky fondu", f"{v_sum:.2f} €")
            c3.metric("Čistý zostatok", f"{(p_sum - v_sum):.2f} €")
            
            if not df_v.empty and "Dátum" in df_v.columns:
                df_v["dt_p"] = pd.to_datetime(df_v["Dátum"], dayfirst=True, errors='coerce')
                v_mes = df_v.groupby(df_v["dt_p"].dt.strftime('%m/%y'))["Suma"].sum().reindex(stlpce_m, fill_value=0)
                p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                df_g = pd.DataFrame({"Mesiac": stlpce_m, "Zostatok": (p_mes.values - v_mes.values).cumsum()})
                fig = px.area(df_g, x="Mesiac", y="Zostatok", title="Vývoj zostatku vo fonde")
                fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.3)')
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("📜 Zoznam výdavkov")
        if not df_v.empty:
            cols_to_show = [c for c in df_v.columns if c != "dt_p"]
            st.dataframe(df_v[cols_to_show], hide_index=True, use_container_width=True,
                         column_config={"Doklad": st.column_config.LinkColumn("Doklad 🔗", display_text="Otvoriť")})

    # --- TAB 3: MOJE PLATBY + QR ---
    with tabs[2]:
        st.subheader(f"💰 Moja bilancia (VS: {u['vs']})")
        vs_final = str(u['vs']).strip().zfill(4)
        vs_p_col = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
        df_p[vs_p_col] = df_p[vs_p_col].astype(str).str.strip().str.zfill(4)
        moje = df_p[df_p[vs_p_col] == vs_final]

        if not moje.empty:
            st.dataframe(moje, hide_index=True, use_container_width=True)
            zaplatene = pd.to_numeric(moje.iloc[0][stlpce_m], errors='coerce').fillna(0).sum()
            predpis = datetime.now().month * MESACNY_PREDPIS
            bilancia = zaplatene - predpis

            st.divider()
            if bilancia < 0:
                nedoplatok = abs(bilancia)
                suma_str = "{:.2f}".format(nedoplatok)
                st.markdown(f"""<div style="background-color:#fff5f5; padding:20px; border-radius:12px; border:2px solid #e53e3e; text-align:center;">
                    <h3 style="color:#c53030; margin-top:0;">⚠️ Evidujeme nedoplatok: {suma_str} €</h3>
                    <p style="color:#2d3748;">Naskenujte QR kód pre rýchlu úhradu:</p>
                </div>""", unsafe_allow_html=True)

                qr_payload = f"SPD*1.0*ACC:{IBAN_FONDU}*AM:{suma_str}*CUR:EUR*VS:{vs_final}*MSG:VictoryPort"
                qr = segno.make(qr_payload)
                buff = io.BytesIO()
                qr.save(buff, kind='png', scale=10)
                
                cq1, cq2, cq3 = st.columns([1, 2, 1])
                with cq2:
                    st.image(buff.getvalue(), caption=f"QR Platba: {suma_str} € | VS: {vs_final}")
                
                st.markdown(f"""<div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border:1px solid #dee2e6;">
                    <p style="color:#6c757d; font-size:0.9em; margin-bottom:0;"><b>Manuálna platba:</b> IBAN: {IBAN_FONDU}, VS: {vs_final}, Suma: {suma_str} €</p>
                </div>""", unsafe_allow_html=True)
            else:
                st.success(f"✅ Vaše platby sú v poriadku. Máte preplatok {bilancia:.2f} €.")

    # --- TAB 4: ANKETA ---
    with tabs[3]:
        if not je_zadana_otazka:
            st.info("Momentálne neprebieha žiadna anketa.")
        else:
            st.subheader(f"🗳️ {OTAZKA}")
            if not df_h.empty:
                za = len(df_h[(df_h.iloc[:,1].astype(str).str.strip() == OTAZKA) & (df_h.iloc[:,2].astype(str).str.upper().str.contains("ZA|ANO"))])
                ni = len(df_h[(df_h.iloc[:,1].astype(str).str.strip() == OTAZKA) & (df_h.iloc[:,2].astype(str).str.upper().str.contains("PROTI|NIE"))])
                r1, r2, r3 = st.columns(3)
                r1.metric("ZA 👍", za); r2.metric("PROTI 👎", ni); r3.metric("Spolu", za+ni)

            st.divider()
            if anketa_aktivna:
                s_za = urllib.parse.quote(f"HLAS:ZA | VS:{u['vs']} | {OTAZKA}")
                s_ni = urllib.parse.quote(f"HLAS:PROTI | VS:{u['vs']} | {OTAZKA}")
                b1, b2 = st.columns(2)
                b1.link_button("👍 HLASUJEM ZA", f"mailto:{MAIL_SPRAVCA}?subject={s_za}", use_container_width=True)
                b2.link_button("👎 HLASUJEM PROTI", f"mailto:{MAIL_SPRAVCA}?subject={s_ni}", use_container_width=True)
                
                st.markdown(f"""<div style="background-color:#f0fff4; padding:15px; border-radius:10px; border:1px solid #38a169; margin-top:20px;">
                    <p style="color:#2f855a; font-size:0.9em; margin-bottom:0;"><b>Manuálne hlasovanie:</b> Pošlite e-mail na {MAIL_SPRAVCA} s predmetom <b>HLAS:ZA (alebo PROTI) | VS:{u['vs']}</b></p>
                </div>""", unsafe_allow_html=True)
            else:
                st.error("⌛ Táto anketa už bola uzatvorená.")

    # --- TAB 5: MIESTNY POKEC ---
    with tabs[4]:
        st.subheader("💬 Verejná nástenka odkazov")
        pokec_txt = st.text_area("Napíšte odkaz susedom:")
        if pokec_txt:
            s_pk = urllib.parse.quote(f"ODKAZ NASTENKA | VS:{u['vs']}")
            b_pk = urllib.parse.quote(f"Dátum: {datetime.now().strftime('%d.%m.%Y')}\nOd: {u['meno']}\n\nOdkaz:\n{pokec_txt}")
            st.link_button("✉️ Odoslať odkaz na schválenie", f"mailto:{MAIL_SPRAVCA}?subject={s_pk}&body={b_pk}", use_container_width=True)
        
        st.divider()
        if not df_o.empty:
            for _, r in df_o.iloc[::-1].iterrows():
                with st.chat_message("user"):
                    st.write(f"**{r.get('Meno','Neznámy')}** ({r.get('Dátum','')})")
                    st.info(r.get('Odkaz','...'))

except Exception as e:
    st.error(f"⚠️ Systémová chyba: {e}")

st.markdown("<p style='text-align: center; color: gray; margin-top: 50px; font-size: 0.8em;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
