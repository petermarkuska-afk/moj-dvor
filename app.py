import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
from datetime import datetime
import base64

# ==========================================
# 1. KONFIGURÁCIA (Načítanie zo Secrets)
# ==========================================
try:
    MAIL_SPRAVCA = st.secrets["MAIL_SPRAVCA"]
    SID = st.secrets["SID"]
    HLAVNE_HESLO = st.secrets["HLAVNE_HESLO"]
except Exception as e:
    st.error("⚠️ CHYBA: Chýbajú nastavenia v 'Secrets' na Streamlit Cloud. Skontrolujte MAIL_SPRAVCA, SID a HLAVNE_HESLO.")
    st.stop()

# Nastavenia pre aktuálne hlasovanie (možno meniť manuálne tu)
OTAZKA = "ŽIADNA" 
KONIEC_ANKETY = "2026-03-15"

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# ==========================================
# POMOCNÉ FUNKCIE (DÁTA V REÁLNOM ČASE)
# ==========================================

def get_df(sheet, spreadsheet_id):
    """Načítava dáta vždy nanovo bez použitia cache."""
    try:
        # cache_bust pridáva unikátny parameter do URL, aby sme vynútili čerstvé dáta
        cache_bust = int(time.time() * 1000)
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        # Očistenie názvov stĺpcov od medzier
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except Exception as e:
        return pd.DataFrame()

def get_base64_image(image_path):
    """Kódovanie obrázka do Base64 pre CSS pozadie."""
    try:
        with open(image_path, "rb") as img:
            return base64.b64encode(img.read()).decode()
    except:
        return ""

def vypocitaj_bilanciu(vs_uzivatela, df_platby, df_konfig):
    """Vypočíta sumu úhrad vs. predpisy k dnešnému dňu."""
    teraz = datetime.now()
    akt_m = teraz.month
    akt_r = teraz.year

    if df_konfig.empty:
        return 0.0, 0.0, 0.0

    # 1. Suma predpisov z tabuľky Konfiguracia
    df_k = df_konfig.copy()
    df_k['Mesiac'] = pd.to_numeric(df_k['Mesiac'], errors='coerce')
    df_k['Rok'] = pd.to_numeric(df_k['Rok'], errors='coerce')
    df_k['Predpis'] = pd.to_numeric(df_k['Predpis'], errors='coerce').fillna(0)
    
    mask = (df_k['Rok'] < akt_r) | ((df_k['Rok'] == akt_r) & (df_k['Mesiac'] <= akt_m))
    suma_predpisov = df_k[mask]['Predpis'].sum()

    # 2. Suma všetkých platieb užívateľa z tabuľky Platby
    vs_p = next((c for c in df_platby.columns if "VS" in c.upper()), "VS")
    df_platby[vs_p] = df_platby[vs_p].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(4)
    u_riadok = df_platby[df_platby[vs_p] == vs_uzivatela]

    if u_riadok.empty:
        return 0.0, round(suma_predpisov, 2), round(-suma_predpisov, 2)

    stlpce_historie = [c for c in df_platby.columns if "/" in c]
    suma_uhrad = pd.to_numeric(u_riadok.iloc[0][stlpce_historie], errors='coerce').fillna(0).sum()

    return round(suma_uhrad, 2), round(suma_predpisov, 2), round(suma_uhrad - suma_predpisov, 2)

# ==========================================
# ŠTÝLOVANIE A POZADIE (FULL CSS)
# ==========================================
img_base64 = get_base64_image("image_5.png")

st.markdown(f"""
<style>
.stApp {{
    background-image: url("data:image/png;base64,{img_base64}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
section.main > div {{
    background-color: rgba(0, 0, 0, 0.90);
    padding: 30px;
    border-radius: 20px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}}
div[data-testid="stTabs"] > div {{
    background-color: rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    padding: 10px;
}}
.stMetric {{
    background-color: rgba(255,255,255,0.05);
    padding: 15px;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.1);
}}
h1, h2, h3 {{
    color: #ffffff !important;
}}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. AUTENTIFIKÁCIA A STAV
# ==========================================
if "auth_pass" not in st.session_state: st.session_state["auth_pass"] = False
if "user_data" not in st.session_state: st.session_state["user_data"] = None
if "debt_confirmed" not in st.session_state: st.session_state["debt_confirmed"] = False

# KROK 1: Vstup s hlavným heslom
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

# KROK 2: Identifikácia majiteľa (VS + PIN)
if st.session_state["auth_pass"] and st.session_state["user_data"] is None:
    st.markdown("<h2 style='text-align: center;'>🔑 Identifikácia majiteľa</h2>", unsafe_allow_html=True)
    col_log1, col_log2 = st.columns(2)
    with col_log1:
        vs_vstup = st.text_input("Variabilný symbol (VS):", placeholder="Napr. 1007")
    with col_log2:
        pin_vstup = st.text_input("Váš osobný PIN:", type="password", placeholder="****")

    if st.button("Prihlásiť sa", use_container_width=True):
        df_a = get_df("Adresar", SID)
        if not df_a.empty:
            vs_col = next((c for c in df_a.columns if "VS" in c.upper()), "VS")
            pin_col = next((c for c in df_a.columns if "PIN" in c.upper()), "PIN")
            rola_col = next((c for c in df_a.columns if "ROLA" in c.upper()), "ROLA")
            spravca_col = next((c for c in df_a.columns if "SPRAVCA" in c.upper()), "SPRAVCA")
            
            df_a[vs_col] = df_a[vs_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(4)
            df_a[pin_col] = df_a[pin_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            target_vs = vs_vstup.strip().zfill(4)
            user_row = df_a[(df_a[vs_col] == target_vs) & (df_a[pin_col] == pin_vstup.strip())]
            
            if not user_row.empty:
                st.session_state["user_data"] = {
                    "vs": target_vs,
                    "meno": str(user_row.iloc[0].get("Meno a priezvisko", "Neznámy")),
                    "email": str(user_row.iloc[0].get("Email", "Neuvedený")),
                    "rola": str(user_row.iloc[0].get(rola_col, "")).upper(),
                    "je_spravca": str(user_row.iloc[0].get(spravca_col, "")).upper() == "ANO"
                }
                st.rerun()
            else:
                st.error("Kombinácia VS a PIN kódu je nesprávna.")
    st.stop()

# Krok 3: Kontrola nedoplatku (Interstitial)
if not st.session_state["debt_confirmed"]:
    u = st.session_state["user_data"]
    df_p, df_k = get_df("Platby", SID), get_df("Konfiguracia", SID)
    if not df_p.empty and not df_k.empty:
        _, _, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)
        if bilancia < -0.01:
            st.markdown(f"""
            <div style="background-color:#fff5f5; padding:30px; border-radius:15px; border:3px solid #e53e3e; text-align:center;">
                <h2 style="color:#c53030;">⚠️ Upozornenie na nedoplatok</h2>
                <h3 style="color:#2d3748;">Suma: {abs(bilancia):.2f} €</h3>
                <p style="color:#4a5568;">Pred vstupom na portál prosíme o kontrolu vašich platieb.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Rozumiem a pokračujem", use_container_width=True):
                st.session_state["debt_confirmed"] = True
                st.rerun()
            st.stop()
    st.session_state["debt_confirmed"] = True
    st.rerun()

# ==========================================
# 3. HLAVNÝ PORTÁL
# ==========================================
try:
    u = st.session_state["user_data"]
    df_p = get_df("Platby", SID)
    df_v = get_df("Vydavky", SID)
    df_h = get_df("Hlasovanie", SID)
    df_n = get_df("Nastenka", SID)
    df_o = get_df("Odkazy", SID)
    df_k = get_df("Konfiguracia", SID)
    df_a = get_df("Adresar", SID)

    st.markdown(f"<h1 style='text-align: center;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    
    col_logout1, col_logout2, col_logout3 = st.columns([1, 2, 1])
    with col_logout2:
        if st.button("Odhlásiť sa", use_container_width=True):
            st.session_state.update({"auth_pass": False, "user_data": None, "debt_confirmed": False})
            st.rerun()

    st.divider()
    
    # Definícia tabov na základe oprávnení
    tabs_labels = ["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa", "💬 Miestny pokec"]
    if u["je_spravca"] or u["rola"] == "ZASTUPCA":
        tabs_labels.append("⚙️ Správa")
    
    tabs = st.tabs(tabs_labels)

    # --- T1: NÁSTENKA ---
    with tabs[0]:
        st.subheader("📢 Aktuálne oznamy")
        if not df_n.empty:
            st.table(df_n.iloc[::-1])
        else:
            st.info("Žiadne nové oznamy.")
        
        st.divider()
        st.subheader("🛠️ Súkromný podnet pre správcu")
        podnet_text = st.text_area("Váš podnet bude doručený e-mailom priamo správcovi:", key="p_area")
        p_subj = urllib.parse.quote(f"Podnet Victory Port - VS {u['vs']}")
        p_body = urllib.parse.quote(f"Meno: {u['meno']}\nVS: {u['vs']}\n\nPodnet:\n{podnet_text}")
        st.link_button("🚀 Odoslať podnet", f"mailto:{MAIL_SPRAVCA}?subject={p_subj}&body={p_body}", use_container_width=True)

    # --- T2: FINANCIE (KOMPLETNÁ GRAFIKA) ---
    with tabs[1]:
        if not df_p.empty:
            vsetky_m = [c for c in df_p.columns if "/" in c]
            teraz = datetime.now()
            stlpce_m = sorted([c for c in vsetky_m if datetime.strptime(c, "%m/%y") <= teraz], key=lambda x: datetime.strptime(x, "%m/%y"))
            
            if stlpce_m:
                suma_p = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
                suma_v = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Fond celkom", f"{suma_p:.2f} €")
                c2.metric("Výdavky celkom", f"{suma_v:.2f} €")
                c3.metric("Zostatok", f"{(suma_p - suma_v):.2f} €")

                # Simulácia grafu
                if not df_v.empty:
                    df_v_graph = df_v.copy()
                    df_v_graph["temp_dt"] = pd.to_datetime(df_v_graph["Dátum"], dayfirst=True, errors='coerce')
                    v_mes = df_v_graph.groupby(df_v_graph["temp_dt"].dt.strftime('%m/%y'))["Suma"].sum().reindex(stlpce_m, fill_value=0)
                    p_mes = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                    
                    df_g = pd.DataFrame({
                        "Mesiac": stlpce_m,
                        "Príjmy": p_mes.values,
                        "Zostatok": (p_mes.values - v_mes.values).cumsum()
                    })
                    fig = px.area(df_g, x="Mesiac", y="Zostatok", title="Trend stavu fondu", template="plotly_dark")
                    fig.update_traces(line_color='#28a745', fillcolor='rgba(40, 167, 69, 0.3)')
                    st.plotly_chart(fig, use_container_width=True)

        st.subheader("📜 Zoznam výdavkov")
        if not df_v.empty:
            st.dataframe(df_v, hide_index=True, use_container_width=True,
                         column_config={"Doklad": st.column_config.LinkColumn("Odkaz", display_text="Zobraziť 🔗")})

    # --- T3: MOJE PLATBY ---
    with tabs[2]:
        st.subheader(f"💰 Prehľad pre VS: {u['vs']}")
        vs_p_col = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
        df_p[vs_p_col] = df_p[vs_p_col].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4)
        moje_data = df_p[df_p[vs_p_col] == u['vs']]
        
        if not moje_data.empty:
            st.dataframe(moje_data, hide_index=True, use_container_width=True)
            real, predpis, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)
            
            st.divider()
            if bilancia < 0:
                st.error(f"⚠️ Evidujeme nedoplatok vo výške {abs(bilancia):.2f} €")
            else:
                st.success(f"✅ Platby sú v poriadku. Aktuálny preplatok: {bilancia:.2f} €")
            
            st.info(f"Suma predpisov k dnešnému dňu: {predpis:.2f} € | Vaše celkové úhrady: {real:.2f} €")

    # --- T4: ANKETA ---
    with tabs[3]:
        if OTAZKA.strip().upper() == "ŽIADNA":
            st.info("Momentálne neprebieha žiadne hlasovanie.")
        else:
            st.subheader(f"🗳️ Aktuálna otázka: {OTAZKA}")
            # Tu by bola logika na zobrazenie aktuálnych výsledkov z df_h
            st.write("Váš hlas odošlete kliknutím na tlačidlo nižšie (otvorí e-mail):")
            s_za = urllib.parse.quote(f"HLAS: ZA | VS: {u['vs']} | {OTAZKA}")
            s_proti = urllib.parse.quote(f"HLAS: PROTI | VS: {u['vs']} | {OTAZKA}")
            col_h1, col_h2 = st.columns(2)
            col_h1.link_button("👍 HLASUJEM ZA", f"mailto:{MAIL_SPRAVCA}?subject={s_za}", use_container_width=True)
            col_h2.link_button("👎 HLASUJEM PROTI", f"mailto:{MAIL_SPRAVCA}?subject={s_proti}", use_container_width=True)

    # --- T5: MIESTNY POKEC ---
    with tabs[4]:
        st.subheader("💬 Verejná nástenka")
        msg_text = st.text_area("Napíšte správu, ktorú uvidia ostatní susedia (po schválení správcom):", key="msg_area")
        if msg_text:
            m_subj = urllib.parse.quote(f"ODKAZ NA NASTENKU - {u['meno']}")
            m_body = urllib.parse.quote(f"Text správy:\n{msg_text}")
            st.link_button("✉️ Poslať správu na zverejnenie", f"mailto:{MAIL_SPRAVCA}?subject={m_subj}&body={m_body}", use_container_width=True)
        st.divider()
        if not df_o.empty:
            for _, row in df_o.iloc[::-1].iterrows():
                with st.chat_message("user"):
                    st.write(f"**{row.get('Meno', 'Sused')}** ({row.get('Dátum', '')})")
                    st.info(row.get('Odkaz', ''))

    # --- T6: SPRÁVA (KOMUNIKAČNÉ CENTRUM) ---
    if u["je_spravca"] or u["rola"] == "ZASTUPCA":
        with tabs[-1]:
            st.subheader("⚙️ Správa a komunikácia")
            
            vs_col_a = next((c for c in df_a.columns if "VS" in c.upper()), "VS")
            df_a[vs_col_a] = df_a[vs_col_a].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4)
            
            # Určenie cieľovej skupiny
            if u["je_spravca"]:
                st.warning("🔓 Mod: **HLAVNÝ SPRÁVCA** (Prístup k všetkým 109 subjektom)")
                df_target = df_a.copy()
                default_subject = "Oznam pre obyvateľov Victory Port"
            else:
                prefix = u["vs"][:2]
                st.info(f"🏘️ Mod: **ZÁSTUPCA BLOKU {prefix}xx** (Správa prislúchajúcich bytov)")
                df_target = df_a[df_a[vs_col_a].str.startswith(prefix)]
                default_subject = f"Oznam pre obyvateľov bloku {prefix}xx"

            # KOMUNIKÁTOR
            st.write("### ✍️ Napísať hromadný oznam")
            custom_subject = st.text_input("Predmet e-mailu:", value=default_subject)
            custom_message = st.text_area("Text správy (napr. o odstávke vody, schôdzi...):", placeholder="Sem napíšte váš oznam...")
            
            email_col = next((c for c in df_target.columns if "EMAIL" in c.upper()), "Email")
            list_emails = [str(m) for m in df_target[email_col].dropna().unique().tolist() if "@" in str(m)]
            
            if list_emails:
                bcc_str = "; ".join(list_emails)
                q_subj = urllib.parse.quote(custom_subject)
                q_body = urllib.parse.quote(custom_message)
                
                st.link_button(f"✉️ Odoslať e-mail ({len(list_emails)} adresátom)", 
                              f"mailto:?bcc={bcc_str}&subject={q_subj}&body={q_body}", 
                              use_container_width=True)
                
                with st.expander("Zobraziť zoznam e-mailov (BCC)"):
                    st.code(bcc_str)
            
            st.divider()
            st.write("### 📉 Kontrola nedoplatkov")
            dlznici = []
            for t_vs in sorted(df_target[vs_col_a].tolist()):
                _, _, bil = vypocitaj_bilanciu(t_vs, df_p, df_k)
                if bil < -0.01:
                    dlznici.append({"VS": t_vs, "Suma (€)": abs(bil)})
            
            if dlznici:
                df_dlhy = pd.DataFrame(dlznici)
                st.table(df_dlhy)
                # Tlačidlo pre rýchlu upomienku dlžníkom
                u_emails = df_target[df_target[vs_col_a].isin(df_dlhy["VS"])][email_col].dropna().tolist()
                if u_emails:
                    u_bcc = "; ".join(u_emails)
                    u_s = urllib.parse.quote("Upozornenie na nedoplatok - Victory Port")
                    u_b = urllib.parse.quote("Dobrý deň,\n\ndovoľujeme si Vás upozorniť na evidovaný nedoplatok. Prosíme o kontrolu platieb v portáli.")
                    st.link_button("📧 Poslať rýchlu upomienku len dlžníkom", f"mailto:?bcc={u_bcc}&subject={u_s}&body={u_b}", use_container_width=True)
            else:
                st.success("Všetky subjekty v správe majú vyrovnané záväzky. ✅")

except Exception as e:
    if st.session_state["user_data"] is not None:
        st.error(f"Vyskytla sa neočakávaná chyba: {e}")

st.markdown("<p style='text-align: center; font-size: 0.8em; color: gray; margin-top:50px;'>© 2026 Správa areálu Victory Port</p>", unsafe_allow_html=True)
