import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
import time
from datetime import datetime
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

# ==========================================
# KONFIGURÁCIA A NASTAVENIA
# ==========================================
try:
    MAIL_SPRAVCA = st.secrets["MAIL_SPRAVCA"]
    SID = st.secrets["SID"]
    HLAVNE_HESLO = st.secrets["HLAVNE_HESLO"]
    IBAN = st.secrets.get("IBAN", "SK00 0000 0000 0000 0000 0000")
except:
    st.error("⚠️ CHYBA: Chýbajú nastavenia v Secrets.")
    st.stop()

OTAZKA = "ŽIADNA" 
KONIEC_ANKETY = "2026-03-05"
VERZIA = "v1.2"

st.set_page_config(page_title="Správa areálu Victory Port", layout="centered", page_icon="🏡")

# ==========================================
# POMOCNÉ FUNKCIE A LOGIKA
# ==========================================
def generuj_pdf_potvrdenie(meno, vs, uhrady, predpis):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "Potvrdenie o stave platieb - Victory Port")
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Majiteľ: {meno}")
    c.drawString(50, 755, f"Variabilný symbol: {vs}")
    c.line(50, 740, 550, 740)
    c.drawString(50, 710, f"Celková suma predpisov: {predpis:.2f} €")
    c.drawString(50, 695, f"Celkom uhradené: {uhrady:.2f} €")
    c.drawString(50, 680, f"Bilancia: {(uhrady - predpis):.2f} €")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 640, "Platobné údaje:")
    c.setFont("Helvetica", 12)
    c.drawString(50, 625, f"IBAN: {IBAN}")
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 560, "Ďakujeme za vašu príkladnú platobnú disciplínu.")
    c.save()
    buffer.seek(0)
    return buffer

def get_df(sheet, spreadsheet_id):
    cache_bust = int(time.time() * 1000)
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}&cb={cache_bust}"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

def vypocitaj_bilanciu(vs_uzivatela, df_platby, df_konfig):
    if df_konfig.empty: return 0.0, 0.0, 0.0
    df_k = df_konfig.copy()
    df_k['Predpis'] = pd.to_numeric(df_k['Predpis'], errors='coerce').fillna(0)
    suma_predpisov = df_k['Predpis'].sum()
    vs_p = next((c for c in df_platby.columns if "VS" in c.upper()), "VS")
    df_platby[vs_p] = df_platby[vs_p].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(4)
    u_riadok = df_platby[df_platby[vs_p] == vs_uzivatela]
    if u_riadok.empty: return 0.0, round(suma_predpisov, 2), round(-suma_predpisov, 2)
    stlpce_historie = [c for c in df_platby.columns if "/" in c]
    suma_uhrad = pd.to_numeric(u_riadok.iloc[0][stlpce_historie], errors='coerce').fillna(0).sum()
    return round(suma_uhrad, 2), round(suma_predpisov, 2), round(suma_uhrad - suma_predpisov, 2)

# ==========================================
# ŠTÝLOVANIE
# ==========================================
img_base64 = base64.b64encode(open("image_5.png", "rb").read()).decode() if "image_5.png" in locals() else ""
st.markdown(f"<style>.stApp {{background-image: url('data:image/png;base64,{img_base64}'); background-size: cover;}} section.main > div {{background-color: rgba(0, 0, 0, 0.92); padding: 30px; border-radius: 20px;}}</style>", unsafe_allow_html=True)

# ==========================================
# AUTENTIFIKÁCIA
# ==========================================
if "auth_pass" not in st.session_state: st.session_state["auth_pass"] = False
if "user_data" not in st.session_state: st.session_state["user_data"] = None

if not st.session_state["auth_pass"]:
    st.markdown("## 🔐 Vstup do portálu")
    if st.text_input("Heslo:", type="password") == HLAVNE_HESLO:
        if st.button("Prihlásiť"):
            st.session_state["auth_pass"] = True
            st.rerun()
    st.stop()
    # ==========================================
# HLAVNÝ PORTÁL (PO AUTENTIFIKÁCII)
# ==========================================
if st.session_state["user_data"] is None:
    st.markdown("## 🔑 Identifikácia")
    vs_v = st.text_input("VS:")
    pin_v = st.text_input("PIN:", type="password")
    if st.button("Prihlásiť"):
        df_a = get_df("Adresar", SID)
        # Hľadanie užívateľa v adresári
        vs_col = next((c for c in df_a.columns if "VS" in c.upper()), None)
        pin_col = next((c for c in df_a.columns if "PIN" in c.upper()), None)
        df_a[vs_col] = df_a[vs_col].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4)
        row = df_a[(df_a[vs_col] == vs_v.strip().zfill(4)) & (df_a[pin_col].astype(str) == pin_v.strip())]
        if not row.empty:
            st.session_state["user_data"] = {
                "vs": vs_v.strip().zfill(4), 
                "meno": str(row.iloc[0].get("Meno a priezvisko", "Neznámy")),
                "rola": str(row.iloc[0].get("ROLA", "")).upper(),
                "je_spravca": str(row.iloc[0].get("SPRAVCA", "")).upper() == "ANO"
            }
            st.rerun()
    st.stop()

# Hlavný obsah aplikácie
u = st.session_state["user_data"]
st.title(f"Vitaj, {u['meno']} 👋")

if st.button("Odhlásiť"):
    st.session_state.clear()
    st.rerun()

# Načítanie všetkých dát naraz pre optimalizáciu
df_p = get_df("Platby", SID)
df_v = get_df("Vydavky", SID)
df_h = get_df("Hlasovanie", SID)
df_n = get_df("Nastenka", SID)
df_o = get_df("Odkazy", SID)
df_k = get_df("Konfiguracia", SID)

# 

tabs_list = ["📢 Nástenka", "📊 Financie", "💰 Moje platby", "🗳️ Anketa", "💬 Pokec"]
if u["je_spravca"] or u["rola"] == "ZASTUPCA": tabs_list.append("⚙️ Správa")
tabs = st.tabs(tabs_list)

with tabs[0]: # Nástenka
    st.subheader("📢 Aktuálne oznamy")
    if not df_n.empty: st.table(df_n.iloc[::-1])

with tabs[1]: # Financie
    st.subheader("📊 Prehľad")
    if not df_v.empty: st.dataframe(df_v, hide_index=True, use_container_width=True)

with tabs[2]: # Moje platby
    st.subheader(f"💰 Moje platby (VS: {u['vs']})")
    r, p, b = vypocitaj_bilanciu(u['vs'], df_p, df_k)
    vs_p = next((c for c in df_p.columns if "VS" in c.upper()), "VS")
    st.dataframe(df_p[df_p[vs_p] == u['vs']], hide_index=True, use_container_width=True)
    st.download_button("📥 Stiahnuť PDF", data=generuj_pdf_potvrdenie(u['meno'], u['vs'], r, p), file_name=f"Platby_{u['vs']}.pdf", mime="application/pdf", use_container_width=True)

with tabs[3]: # Anketa
    st.subheader("🗳️ Anketa")
    if not df_h.empty: st.dataframe(df_h, hide_index=True, use_container_width=True)

with tabs[4]: # Pokec
    st.subheader("💬 Pokec")
    for _, row in df_o.iloc[::-1].iterrows():
        st.info(f"**{row.get('Meno', 'Neznámy')}**: {row.get('Odkaz', '')}")

# 

if u["je_spravca"] or u["rola"] == "ZASTUPCA":
    with tabs[-1]: # Správa
        st.subheader("⚙️ Administrácia")
        st.write("Možnosti pre správu areálu Victory Port.")

# Patička
st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.8em; margin-top:50px;'>© 2026 Správa areálu Victory Port | {VERZIA}</p>", unsafe_allow_html=True)
