import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
from datetime import datetime
import base64
import unicodedata
from fpdf import FPDF

# ==============================================================================
# 1. ZÁKLADNÁ KONFIGURÁCIA A NAČÍTANIE SECRETS
# ==============================================================================
# Táto časť zabezpečuje prepojenie na Google Sheets a overovacie údaje.
try:
    MAIL_SPRAVCA = st.secrets["MAIL_SPRAVCA"]
    SID = st.secrets["SID"]
    HLAVNE_HESLO = st.secrets["HLAVNE_HESLO"]
except Exception as e:
    st.error("⚠️ KRITICKÁ CHYBA: Chýbajú konfiguračné údaje v Streamlit Secrets (MAIL_SPRAVCA, SID, HLAVNE_HESLO).")
    st.stop()

# --- GLOBÁLNE KONŠTANTY SYSTÉMU ---
AKTUALNY_IBAN = "SK00 0000 0000 0000 0000 0000"
OTAZKA = "ŽIADNA"  # Ak tu nie je "ŽIADNA", aktivuje sa hlasovací modul
KONIEC_ANKETY = "2026-03-15"

st.set_page_config(
    page_title="Správa areálu Victory Port",
    layout="centered",
    page_icon="🏡",
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# 2. POMOCNÉ FUNKCIE (LOGIKA A GENERÁTORY)
# ==============================================================================

def odstran_diakritiku(text):
    """
    Normalizuje text a odstráni slovenské znaky. 
    Nevyhnutné pre knižnicu FPDF, ktorá nepodporuje plné UTF-8 v základnom nastavení.
    """
    if not isinstance(text, str):
        return str(text)
    return "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def get_df(sheet, spreadsheet_id):
    """
    Načítava dáta z Google Sheets cez CSV export.
    Používa cache_bust (time.time), aby sa vyhlo starým dátam v medzipamäti.
    """
    try:
        cache_bust = int(time.time() * 1000)
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
        df = pd.read_csv(url)
        # Vyčistenie názvov stĺpcov od bielych znakov
        df.columns = [str(c).strip() for c in df.columns]
        # Odstránenie prázdnych stĺpcov, ktoré Google Sheets niekedy generuje
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Chyba pri načítaní hárka {sheet}: {e}")
        return pd.DataFrame()

def get_base64_image(image_path):
    """Kóduje lokálny obrázok do Base64 pre vloženie do CSS."""
    try:
        with open(image_path, "rb") as img:
            return base64.b64encode(img.read()).decode()
    except:
        return ""

def vytvor_pdf(meno, vs, realne, ocakavane, bilancia):
    """
    Vygeneruje profesionálne PDF potvrdenie o stave konta.
    Obsahuje rekapituláciu platieb a platobné údaje.
    """
    pdf = FPDF()
    pdf.add_page()
    
    # Hlavička
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 15, txt=odstran_diakritiku("POTVRDENIE O STAVE ÚČTU - VICTORY PORT"), ln=True, align='C')
    pdf.line(10, 25, 200, 25)
    
    # Informácie o majiteľovi
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(100, 8, txt=f"Majitel: {odstran_diakritiku(meno)}", ln=False)
    pdf.cell(100, 8, txt=f"Variabilny symbol: {vs}", ln=True, align='R')
    pdf.cell(200, 8, txt=f"Datum vystavenia: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True)
    
    # Finančná sekcia
    pdf.ln(10)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="REKAPITULACIA PLATIEB", ln=True, fill=True)
    
    pdf.set_font("Arial", size=11)
    pdf.cell(130, 8, txt=f"Celkova suma predpisov (ocakavana):", ln=False)
    pdf.cell(70, 8, txt=f"{ocakavane:.2f} EUR", ln=True, align='R')
    
    pdf.cell(130, 8, txt=f"Celkova suma vasich uhrad:", ln=False)
    pdf.cell(70, 8, txt=f"{realne:.2f} EUR", ln=True, align='R')
    
    pdf.line(140, 65, 200, 65)
    
    # Zostatok
    pdf.set_font("Arial", 'B', 12)
    stav_label = "AKTUALNY PREPLATOK:" if bilancia >= 0 else "AKTUALNY NEDOPLATOK:"
    pdf.cell(130, 12, txt=stav_label, ln=False)
    pdf.cell(70, 12, txt=f"{abs(bilancia):.2f} EUR", ln=True, align='R')
    
    # Platobné inštrukcie
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, txt="V pripade nedoplatku prosim pouzite tieto udaje:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 7, txt=f"Cislo uctu (IBAN): {AKTUALNY_IBAN}", ln=True)
    pdf.cell(200, 7, txt=f"Variabilny symbol: {vs}", ln=True)
    
    # Pätička
    pdf.set_y(-30)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(200, 10, txt="Doklad bol generovany automaticky systemom Victory Port. Ma informativny charakter.", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

def vypocitaj_bilanciu(vs_uzivatela, df_platby, df_konfig):
    """
    Kľúčová funkcia pre výpočet dlhu alebo preplatku.
    Sčíta predpisy z Konfigurácie po aktuálny mesiac a porovná ich s platbami.
    """
    teraz = datetime.now()
    akt_m, akt_r = teraz.month, teraz.year
    
    if df_konfig.empty:
        return 0.0, 0.0, 0.0
    
    # 1. Výpočet očakávaných predpisov
    df_k = df_konfig.copy()
    df_k['Mesiac'] = pd.to_numeric(df_k['Mesiac'], errors='coerce')
    df_k['Rok'] = pd.to_numeric(df_k['Rok'], errors='coerce')
    df_k['Predpis'] = pd.to_numeric(df_k['Predpis'], errors='coerce').fillna(0)
    
    # Filter na predpisy, ktoré už mali nastať (minulosť + aktuálny mesiac)
    mask = (df_k['Rok'] < akt_r) | ((df_k['Rok'] == akt_r) & (df_k['Mesiac'] <= akt_m))
    suma_predpisov = df_k[mask]['Predpis'].sum()
    
    # 2. Výpočet reálnych úhrad
    vs_col = next((c for c in df_platby.columns if "VS" in c.upper()), "VS")
    df_platby[vs_col] = df_platby[vs_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(4)
    u_riadok = df_platby[df_platby[vs_col] == vs_uzivatela]
    
    if u_riadok.empty:
        return 0.0, round(suma_predpisov, 2), round(-suma_predpisov, 2)
    
    # Vyberieme len stĺpce, ktoré reprezentujú mesiace (obsahujú lomku, napr. 01/24)
    stlpce_historie = [c for c in df_platby.columns if "/" in c]
    suma_uhrad = pd.to_numeric(u_riadok.iloc[0][stlpce_historie], errors='coerce').fillna(0).sum()
    
    return round(suma_uhrad, 2), round(suma_predpisov, 2), round(suma_uhrad - suma_predpisov, 2)

# ==============================================================================
# 3. VIZUÁLNY ŠTÝL (CSS)
# ==============================================================================
img_b64 = get_base64_image("image_5.png")
st.markdown(f"""
<style>
    /* Pozadie celej aplikácie */
    .stApp {{
        background-image: url("data:image/png;base64,{img_b64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    /* Hlavný kontajner s obsahom */
    section.main > div {{
        background-color: rgba(0, 0, 0, 0.94);
        padding: 40px;
        border-radius: 25px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.6);
        color: #e0e0e0;
    }}
    /* Štýlovanie tabov */
    div[data-testid="stTabs"] > div {{
        background-color: rgba(30, 30, 30, 0.9);
        border-radius: 15px;
        padding: 15px;
        border: 1px solid #444;
    }}
    /* Tlačidlá a interaktívne prvky */
    .stButton > button {{
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s;
    }}
    /* Nadpisy */
    h1, h2, h3 {{
        color: #ffffff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }}
    /* Metriky */
    div[data-testid="stMetricValue"] {{
        font-size: 1.8rem;
    }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. SYSTÉM AUTENTIFIKÁCIE (LOGIN)
# ==============================================================================
if "auth_pass" not in st.session_state: st.session_state["auth_pass"] = False
if "user_data" not in st.session_state: st.session_state["user_data"] = None
if "debt_confirmed" not in st.session_state: st.session_state["debt_confirmed"] = False

# KROK A: Hlavné prístupové heslo (Gatekeeper)
if not st.session_state["auth_pass"]:
    st.markdown("<h1 style='text-align: center;'>🏡 Victory Port</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Vstúpte do súkromného portálu majiteľov</p>", unsafe_allow_html=True)
    
    with st.container():
        heslo_vstup = st.text_input("Vstupné heslo:", type="password", help="Heslo nájdete v uvítacom maily.")
        if st.button("Overiť a vstúpiť", use_container_width=True):
            if heslo_vstup == HLAVNE_HESLO:
                st.session_state["auth_pass"] = True
                st.rerun()
            else:
                st.error("Nesprávne prístupové heslo.")
    st.stop()

# KROK B: Identifikácia konkrétneho majiteľa (VS + PIN)
if st.session_state["auth_pass"] and st.session_state["user_data"] is None:
    st.markdown("<h2 style='text-align: center;'>🔑 Prihlásenie majiteľa</h2>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns(2)
    with col_l:
        vs_log = st.text_input("Váš VS (4 číslice):", placeholder="napr. 1001")
    with col_r:
        pin_log = st.text_input("Váš PIN kód:", type="password", placeholder="****")
        
    if st.button("Prihlásiť sa do môjho konta", use_container_width=True):
        df_adresar = get_df("Adresar", SID)
        if not df_adresar.empty:
            v_col = next((c for c in df_adresar.columns if "VS" in c.upper()), "VS")
            p_col = next((c for c in df_adresar.columns if "PIN" in c.upper()), "PIN")
            
            # Normalizácia dát pre porovnanie
            df_adresar[v_col] = df_adresar[v_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(4)
            df_adresar[p_col] = df_adresar[p_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            target_vs = vs_log.strip().zfill(4)
            target_pin = pin_log.strip()
            
            user_match = df_adresar[(df_adresar[v_col] == target_vs) & (df_adresar[p_col] == target_pin)]
            
            if not user_match.empty:
                st.session_state["user_data"] = {
                    "vs": target_vs,
                    "meno": str(user_match.iloc[0].get("Meno a priezvisko", "Neznámy majiteľ")),
                    "email": str(user_match.iloc[0].get("Email", "")),
                    "rola": str(user_match.iloc[0].get("ROLA", "MAJITEL")).upper(),
                    "je_spravca": str(user_match.iloc[0].get("SPRAVCA", "NIE")).upper() == "ANO"
                }
                st.rerun()
            else:
                st.error("Nesprávna kombinácia VS a PIN kódu. Skontrolujte údaje.")
    st.stop()

# ==============================================================================
# 5. KONTROLA NEDOPLATKU (INTERSTITIÁLNA OBRAZOVKA)
# ==============================================================================
# Táto časť sa aktivuje hneď po prihlásení, ak má užívateľ dlh.
if not st.session_state["debt_confirmed"]:
    u = st.session_state["user_data"]
    df_p, df_k = get_df("Platby", SID), get_df("Konfiguracia", SID)
    
    if not df_p.empty and not df_k.empty:
        _, _, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)
        if bilancia < -0.01:
            st.markdown(f"""
            <div style="background-color:#fff5f5; padding:40px; border-radius:20px; border:4px solid #e53e3e; text-align:center; margin-top: 40px; box-shadow: 0 0 20px rgba(229, 62, 62, 0.4);">
                <h1 style="color:#c53030 !important; margin-top:0;">⚠️ Dôležité upozornenie</h1>
                <h2 style="color:#2d3748 !important;">Evidujeme nedoplatok: {abs(bilancia):.2f} €</h2>
                <p style="color:#4a5568; font-size: 1.1em; margin-bottom: 30px;">
                    Prosíme o vyrovnanie tohto záväzku v čo najkratšom čase, aby sme zabezpečili plynulý chod areálu.<br>
                    <b>IBAN:</b> {AKTUALNY_IBAN}<br><b>VS:</b> {u['vs']}
                </p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Rozumiem a chcem pokračovať do portálu", use_container_width=True):
                st.session_state["debt_confirmed"] = True
                st.rerun()
            st.stop()
    
    # Ak nemá dlh, automaticky ho pustíme ďalej
    st.session_state["debt_confirmed"] = True
    st.rerun()

# ==============================================================================
# 6. HLAVNÝ OBSAH A MENU PORTÁLU
# ==============================================================================
try:
    u = st.session_state["user_data"]
    # Hromadné načítanie všetkých potrebných dát z Google Sheets
    df_p = get_df("Platby", SID)
    df_v = get_df("Vydavky", SID)
    df_h = get_df("Hlasovanie", SID)
    df_n = get_df("Nastenka", SID)
    df_o = get_df("Odkazy", SID)
    df_k = get_df("Konfiguracia", SID)
    df_a = get_df("Adresar", SID)

    # Hlavička s privítaním a tlačidlom odhlásenia
    st.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'>Vitaj, {u['meno']} 👋</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #aaa;'>Rola: {u['rola']} | VS: {u['vs']}</p>", unsafe_allow_html=True)
    
    col_logout_1, col_logout_2, col_logout_3 = st.columns([1, 1.5, 1])
    with col_logout_2:
        if st.button("Odhlásiť sa zo systému", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.divider()
    
    # Definícia dynamického zoznamu tabov (Administrácia sa zobrazí len vyvoleným)
    tabs_labels = ["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa", "💬 Miestny pokec"]
    if u["je_spravca"] or u["rola"] == "ZASTUPCA":
        tabs_labels.append("⚙️ Správa")
    
    tabs = st.tabs(tabs_labels)

    # --- TAB 1: NÁSTENKA A OZNAMY ---
    with tabs[0]:
        # Ak prebieha anketa, zobrazíme veľký žltý box ako pripomienku
        if OTAZKA.strip().upper() != "ŽIADNA":
            try:
                koniec_dt = datetime.strptime(KONIEC_ANKETY, "%Y-%m-%d")
                dni_zostava = (koniec_dt - datetime.now()).days + 1
                if dni_zostava >= 0:
                    st.markdown(f"""
                    <div style="background-color:#fff3cd; padding:20px; border-radius:15px; border-left:8px solid #ffc107; margin-bottom:25px; color: #856404;">
                        <h3 style="margin-top:0; color: #856404 !important;">🗳️ AKTÍVNE HLASOVANIE</h3>
                        <p style="font-size: 1.1em;"><b>Téma:</b> {OTAZKA}</p>
                        <p style="font-weight:bold; color: #bd2130;">⌛ Do konca zostáva: {dni_zostava} dní</p>
                    </div>""", unsafe_allow_html=True)
            except: pass

        st.subheader("📢 Oficiálne oznamy správy")
        if not df_n.empty:
            st.table(df_n.iloc[::-1])
        else:
            st.info("Žiadne nové oznamy.")

        st.divider()
        st.subheader("🛠️ Súkromný podnet pre správcu")
        podnet = st.text_area("Váš podnet alebo otázka (uvidí len správca):", placeholder="Napr. nahlásenie poruchy, otázka k vyúčtovaniu...")
        
        if podnet:
            p_subj = urllib.parse.quote(f"Podnet VP - VS {u['vs']}")
            p_body = urllib.parse.quote(f"Majiteľ: {u['meno']}\nVS: {u['vs']}\n\nPodnet:\n{podnet}")
            st.link_button("🚀 Odoslať podnet oficiálne", f"mailto:{MAIL_SPRAVCA}?subject={p_subj}&body={p_body}", use_container_width=True)
            
        st.markdown(f"""
        <div style="background-color:rgba(229, 62, 62, 0.1); padding:15px; border-radius:10px; border:1px solid #e53e3e; margin-top:20px; font-size: 0.85em;">
            <b>📩 Manuálne odoslanie:</b> Ak tlačidlo nefunguje, pošlite e-mail na <b>{MAIL_SPRAVCA}</b> s predmetom <b>Podnet VP {u['vs']}</b>.
        </div>""", unsafe_allow_html=True)

    # --- TAB 2: FINANČNÝ PREHĽAD AREÁLU ---
    with tabs[1]:
        if not df_p.empty:
            # Príprava časovej osi z názvov stĺpcov (01/24, 02/24...)
            stlpce_m = sorted([c for c in df_p.columns if "/" in c], key=lambda x: datetime.strptime(x, "%m/%y"))
            
            p_celkom = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum()
            v_celkom = pd.to_numeric(df_v["Suma"], errors="coerce").fillna(0).sum() if not df_v.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Vybraté do fondu", f"{p_celkom:.2f} €")
            c2.metric("Spoločné výdavky", f"{v_celkom:.2f} €")
            c3.metric("Zostatok na účte", f"{(p_celkom - v_celkom):.2f} €", delta_color="normal")

            # Vizualizácia vývoja financií
            if not df_v.empty:
                df_v_copy = df_v.copy()
                df_v_copy["dt"] = pd.to_datetime(df_v_copy["Dátum"], dayfirst=True, errors='coerce')
                # Agregácia výdavkov podľa mesiacov, aby sedeli so stĺpcami platieb
                v_po_mesiacoch = df_v_copy.groupby(df_v_copy["dt"].dt.strftime('%m/%y'))["Suma"].sum().reindex(stlpce_m, fill_value=0)
                p_po_mesiacoch = df_p[stlpce_m].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                
                df_graf = pd.DataFrame({
                    "Mesiac": stlpce_m, 
                    "Kumulatívny zostatok": (p_po_mesiacoch.values - v_po_mesiacoch.values).cumsum()
                })
                fig = px.area(df_graf, x="Mesiac", y="Kumulatívny zostatok", title="Trend spoločných financií", template="plotly_dark")
                fig.update_traces(line_color='#00d1b2', fillcolor='rgba(0, 209, 178, 0.2)')
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("📜 Detailný zoznam výdavkov")
        if not df_v.empty:
            st.dataframe(
                df_v, 
                hide_index=True, 
                use_container_width=True, 
                column_config={"Doklad": st.column_config.LinkColumn("Doklad 🔗", display_text="Zobraziť PDF/Foto")}
            )

    # --- TAB 3: OSOBNÉ PLATBY A PDF ---
    with tabs[2]:
        st.subheader(f"💰 Moja história platieb")
        vs_platby = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
        df_p[vs_platby] = df_p[vs_platby].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4)
        moj_vypis = df_p[df_p[vs_platby] == u['vs']]
        
        if not moj_vypis.empty:
            st.dataframe(moj_vypis, hide_index=True, use_container_width=True)
            realne, ocakavane, bilancia = vypocitaj_bilanciu(u['vs'], df_p, df_k)
            st.divider()
            
            # Farebné karty so stavom
            if bilancia < 0:
                st.markdown(f"""<div style="background-color:#fff5f5; padding:25px; border-radius:15px; border:2px solid #e53e3e; text-align:center;">
                    <h2 style="color:#c53030 !important; margin:0;">STAV: NEDOPLATOK {abs(bilancia):.2f} €</h2>
                    <p style="color:#4a5568;">Predpis: {ocakavane:.2f} € | Uhradené: {realne:.2f} €</p></div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div style="background-color:#f0fff4; padding:25px; border-radius:15px; border:2px solid #38a169; text-align:center;">
                    <h2 style="color:#2f855a !important; margin:0;">STAV: VYROVNANÉ (Preplatok {bilancia:.2f} €)</h2>
                    <p style="color:#4a5568;">Predpis: {ocakavane:.2f} € | Uhradené: {realne:.2f} €</p></div>""", unsafe_allow_html=True)
            
            st.ln(1)
            if st.button("📋 Vygenerovať PDF potvrdenie pre banku/úrad", use_container_width=True):
                pdf_data = vytvor_pdf(u['meno'], u['vs'], realne, ocakavane, bilancia)
                st.download_button("📥 Stiahnuť vygenerované PDF", data=pdf_data, file_name=f"Potvrdenie_VictoryPort_{u['vs']}.pdf", mime="application/pdf", use_container_width=True)

        # Špeciálna sekcia pre ZÁSTUPCU (vidí susedov vo svojom bloku)
        if u["rola"] == "ZASTUPCA":
            st.divider()
            prefix_bloku = u['vs'][:2]
            st.subheader(f"📊 Stav platieb v bloku {prefix_bloku}xx")
            susedia = [v for v in df_p[vs_platby].unique() if str(v).startswith(prefix_bloku)]
            zoznam_susedov = []
            for s_vs in sorted(susedia):
                _, _, b_sused = vypocitaj_bilanciu(s_vs, df_p, df_k)
                zoznam_susedov.append({"VS": s_vs, "Status": "V poriadku" if b_sused >= 0 else "DLŽNÍK", "Suma (€)": f"{abs(b_sused):.2f}"})
            
            def color_debts(val):
                color = 'rgba(229, 62, 62, 0.3)' if val == 'DLŽNÍK' else 'rgba(56, 161, 105, 0.3)'
                return f'background-color: {color}'
            
            st.dataframe(pd.DataFrame(zoznam_susedov).style.applymap(color_debts, subset=['Status']), hide_index=True, use_container_width=True)

    # --- TAB 4: HLASOVACÍ MODUL ---
    with tabs[3]:
        if OTAZKA.strip().upper() == "ŽIADNA":
            st.info("Aktuálne neprebieha žiadne hlasovanie. O novom hlasovaní budete informovaní e-mailom.")
        else:
            st.subheader(f"🗳️ HLASOVANIE: {OTAZKA}")
            c_vs_h = next((c for c in df_h.columns if "VS" in c.upper()), "VS")
            c_ot_h = next((c for c in df_h.columns if "OTAZKA" in str(c).upper().replace("Á","A")), "Otázka")
            clean_vs = u['vs'].lstrip('0')
            
            hlasoval_uz = False
            if not df_h.empty:
                hlasoval_uz = any((df_h[c_vs_h].astype(str).str.lstrip('0') == clean_vs) & (df_h[c_ot_h].astype(str).str.strip() == OTAZKA.strip()))
            
            if hlasoval_uz:
                st.success("Vaša voľba už bola zaevidovaná v systéme. Ďakujeme za účasť.")
            else:
                st.write("Vyjadrite svoj súhlas alebo nesúhlas s navrhovanou otázkou:")
                mail_za = urllib.parse.quote(f"HLAS:ANO | VS:{u['vs']} | Téma:{OTAZKA}")
                mail_proti = urllib.parse.quote(f"HLAS:NIE | VS:{u['vs']} | Téma:{OTAZKA}")
                
                b_col1, b_col2 = st.columns(2)
                b_col1.link_button("✅ SÚHLASÍM (ZA)", f"mailto:{MAIL_SPRAVCA}?subject={mail_za}", use_container_width=True)
                b_col2.link_button("❌ NESÚHLASÍM (PROTI)", f"mailto:{MAIL_SPRAVCA}?subject={mail_proti}", use_container_width=True)
            
            st.markdown(f"""
            <div style="background-color:rgba(56, 161, 105, 0.1); padding:15px; border-radius:10px; border:1px solid #38a169; margin-top:20px; font-size: 0.85em;">
                <b>📝 Manuálny návod:</b> Ak tlačidlá nereagujú, pošlite e-mail na <b>{MAIL_SPRAVCA}</b> s predmetom <b>HLAS:ANO | VS:{u['vs']}</b>.
            </div>""", unsafe_allow_html=True)

    # --- TAB 5: VEREJNÁ NÁSTENKA (POKEC) ---
    with tabs[4]:
        st.subheader("💬 Miestna diskusia a odkazy")
        nova_sprava = st.text_area("Chcete niečo odkázať susedom? (Napíšte sem a odošlite na schválenie):")
        if nova_sprava:
            o_sub = urllib.parse.quote(f"ODKAZ NA NASTENKU | VS:{u['vs']}")
            st.link_button("✉️ Odoslať správu na moderovanie", f"mailto:{MAIL_SPRAVCA}?subject={o_sub}&body={urllib.parse.quote(nova_sprava)}", use_container_width=True)
        
        st.divider()
        if not df_o.empty:
            for _, row in df_o.iloc[::-1].iterrows():
                with st.chat_message("user", avatar="🏡"):
                    st.write(f"**{row.get('Meno', 'Sused')}**")
                    st.info(row.get('Odkaz', 'Bez textu'))
        else:
            st.write("Zatiaľ tu nie sú žiadne správy.")

    # --- TAB 6: ADMINISTRÁCIA (LEN PRE ROLE) ---
    if len(tabs_labels) == 6:
        with tabs[5]:
            st.subheader("⚙️ Správa areálu a adresár")
            prefix_adm = u["vs"][:2] if not u["je_spravca"] else ""
            
            # Filtrovanie kontaktov podľa kompetencie (blok vs. celý areál)
            df_filtrovane = df_a[df_a["VS"].astype(str).str.startswith(prefix_adm)] if prefix_adm else df_a
            vsetky_maily = [str(m) for m in df_filtrovane["Email"].dropna().unique() if "@" in str(m)]
            
            st.write(f"### 📧 Hromadná komunikácia ({'Váš blok' if prefix_adm else 'Celý areál'})")
            e_predmet = st.text_input("Predmet hromadnej správy:")
            e_text = st.text_area("Text správy:")
            
            if vsetky_maily:
                st.link_button(f"✉️ Otvoriť e-mail pre {len(vsetky_maily)} susedov", f"mailto:?bcc={'; '.join(vsetky_maily)}&subject={urllib.parse.quote(e_predmet)}&body={urllib.parse.quote(e_text)}", use_container_width=True)
            
            st.divider()
            st.write("### 👥 Zoznam priradených majiteľov")
            st.dataframe(df_filtrovane[["VS", "Meno a priezvisko", "Email", "ROLA"]], hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Došlo k neočakávanej systémovej chybe: {e}")

# Pätička portálu
st.markdown(f"""
<div style="text-align: center; color: #666; margin-top: 60px; padding-bottom: 20px; font-size: 0.8em; border-top: 1px solid #333; padding-top: 20px;">
    © 2026 Správa areálu Victory Port | Vyvinuté pre efektívnu susedskú komunikáciu | Verzia systému 3.1.2
</div>
""", unsafe_allow_html=True)
