import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import time
import pandas as pd
from datetime import date
import urllib.parse
import requests
import base64
import math
import sqlite3
import hashlib
import altair as alt
from twilio.rest import Client
from folium.elements import MacroElement
from jinja2 import Template

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Enjambre VRA | Enterprise Edition", page_icon="🚁", layout="wide")

def cargar_imagen_base64(ruta_imagen):
    try:
        with open(ruta_imagen, "rb") as archivo:
            return base64.b64encode(archivo.read()).decode()
    except FileNotFoundError:
        return None

# ==========================================
# 2. MOTOR DE BASE DE DATOS Y SEGURIDAD
# ==========================================
def init_db():
    conn = sqlite3.connect('enjambre_usuarios.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (telefono TEXT PRIMARY KEY, nombre TEXT, password TEXT)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

init_db()

# ==========================================
# 3. ESTILOS CSS Y DISEÑO GLASSMORPHISM
# ==========================================
st.markdown("""
    <style>
    /* Cursor de hormiga */
    body, .stApp, [data-testid="stAppViewContainer"], * {
        cursor: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32'%3E%3Ctext y='24' font-size='24'%3E🐜%3C/text%3E%3C/svg%3E") 16 16, auto !important;
    }
    
    /* Sensores Dinámicos */
    .sensor-verde { background-color: #d4edda; color: #155724; padding: 15px; border-radius: 8px; border-left: 5px solid #28a745; text-align: center; margin-bottom: 10px;}
    .sensor-amarillo { background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; border-left: 5px solid #ffc107; text-align: center; margin-bottom: 10px;}
    
    /* Barra Lateral y Botones */
    .horario-auto { background-color: #e2e3e5; color: #383d41; padding: 10px; border-radius: 5px; border-left: 5px solid #6c757d; margin-bottom: 5px;}
    .whatsapp-btn { background-color: #25D366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; text-align: center; width: 100%;}
    
    /* Chat IA y Tarjetas */
    .ai-card { background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(34, 197, 94, 0.3); backdrop-filter: blur(10px); margin-bottom: 15px;}
    [data-testid="stChatMessage"] { background: rgba(0, 20, 10, 0.85); border-radius: 10px; border: 1px solid rgba(34, 197, 94, 0.4); padding: 15px; margin-bottom: 10px; }

    /* 🚀 SOLUCIÓN ESTÉTICA: ÁREA DE TEXTO TRANSPARENTE E IMPACTANTE */
    [data-testid="stTextArea"] textarea {
        background: rgba(255, 255, 255, 0.03) !important;
        color: #ffffff !important;
        border-radius: 15px !important;
        border: 1px solid rgba(34, 197, 94, 0.4) !important;
        backdrop-filter: blur(15px) !important;
        font-family: 'Monaco', 'Consolas', monospace;
        font-size: 14px !important;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
    }

    /* Recuadros de Herramientas Mejorados */
    .tool-box {
        background: rgba(255, 255, 255, 0.02); 
        border: 1px solid rgba(34, 197, 94, 0.2); 
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        backdrop-filter: blur(10px);
        min-height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 500; 
        color: #f0fdf4; 
        transition: all 0.3s ease;
    }
    .tool-box:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(34, 197, 94, 0.8); 
        background: rgba(34, 197, 94, 0.05);
        box-shadow: 0 8px 25px rgba(34, 197, 94, 0.15); 
    }

    /* Tablas Glassmorphism */
    .glass-table {
        width: 100%;
        border-collapse: collapse;
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        color: #f0fdf4;
        border: 1px solid rgba(187, 247, 208, 0.15);
    }
    .glass-table th { background: rgba(34, 197, 94, 0.15); padding: 12px; font-size: 13px; text-transform: uppercase;}
    .glass-table td { padding: 10px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); font-weight: 300;}
    </style>
""", unsafe_allow_html=True)

# Fondo Dinámico
fondo_base64 = cargar_imagen_base64("assets/fondo_campo.jpg")
if fondo_base64:
    fondo_css = f'background-image: linear-gradient(rgba(0, 25, 10, 0.72), rgba(0, 40, 18, 0.84)), url("data:image/jpg;base64,{fondo_base64}"); background-size: 115%; background-position: center; background-attachment: fixed; animation: moverFondoCampo 28s ease-in-out infinite alternate;'
else:
    fondo_css = 'background: linear-gradient(135deg, #052e16 0%, #064e3b 45%, #022c22 100%);'
st.markdown(f"<style>.stApp {{ {fondo_css} color: white; }}</style>", unsafe_allow_html=True)

# ==========================================
# 4. BASE DE DATOS AGRONÓMICA
# ==========================================
DB_CULTIVOS_PLAS = {
    "Cerezas": {"agua_m2": 4.5, "color": "#d32f2f", "yield_base": 12.0, "price_ton": 2500, "riesgo_clima": "Heladas", "plaga_comun": "Drosophila", "consecuencia_estres": "Partiduras"},
    "Paltos": {"agua_m2": 6.0, "color": "#388e3c", "yield_base": 10.0, "price_ton": 3200, "riesgo_clima": "Frio extremo", "plaga_comun": "Arañita", "consecuencia_estres": "Caída de flor"},
    "Uva": {"agua_m2": 2.5, "color": "#7b1fa2", "yield_base": 15.0, "price_ton": 1800, "riesgo_clima": "Calor", "plaga_comun": "Polilla", "consecuencia_estres": "Bajo azúcar"}
}

# ==========================================
# 5. LÓGICA DE TWILIO (CORREGIDA PARA CHILE)
# ==========================================
def enviar_whatsapp_twilio(mensaje, telefono_usuario):
    try:
        sid = st.secrets["TWILIO_ACCOUNT_SID"]
        token = st.secrets["TWILIO_AUTH_TOKEN"]
        remitente = st.secrets["TWILIO_PHONE"]
        
        # 🚀 SOLUCIÓN AL ERROR DEL "9": FORMATEO INTELIGENTE
        # Quitamos cualquier carácter no numérico
        num_limpio = ''.join(filter(str.isdigit, telefono_usuario))
        
        # Si el número empieza con 9 y tiene 9 dígitos, le falta el 56
        if len(num_limpio) == 9 and num_limpio.startswith('9'):
            num_final = f"56{num_limpio}"
        # Si ya tiene el 569, lo dejamos igual
        elif num_limpio.startswith('569'):
            num_final = num_limpio
        # Fallback genérico
        else:
            num_final = num_limpio

        client = Client(sid, token)
        message = client.messages.create(
            body=mensaje,
            from_=f"whatsapp:{remitente}",
            to=f"whatsapp:+{num_final}"
        )
        return True, message.sid
    except Exception as e:
        return False, str(e)

# ==========================================
# 6. MOTOR MATEMÁTICO
# ==========================================
def punto_en_poligono(x, y, poligono):
    n = len(poligono); inside = False; p1x, p1y = poligono[0]
    for i in range(n + 1):
        p2x, p2y = poligono[i % n]
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y: xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xints: inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def calcular_area_poligono(coords):
    if not coords or len(coords) < 3: return 0
    R = 6378137; lats = [p[1] for p in coords]; mean_lat = math.radians(sum(lats) / len(lats))
    pts_meters = [(R * math.radians(p[0]) * math.cos(mean_lat), R * math.radians(p[1])) for p in coords]
    area = 0; n = len(pts_meters)
    for i in range(n):
        j = (i + 1) % n; area += pts_meters[i][0] * pts_meters[j][1]; area -= pts_meters[j][0] * pts_meters[i][1]
    return abs(area) / 2.0

def calcular_area_interseccion(p_crop, p_main):
    area_bruta = calcular_area_poligono(p_crop)
    min_x, max_x = min(p[0] for p in p_crop), max(p[0] for p in p_crop)
    min_y, max_y = min(p[1] for p in p_crop), max(p[1] for p in p_crop)
    p_c, p_a, grid = 0, 0, 60
    dx, dy = (max_x - min_x) / grid, (max_y - min_y) / grid
    for i in range(grid):
        for j in range(grid):
            x, y = min_x + i * dx, min_y + j * dy
            if punto_en_poligono(x, y, p_crop):
                p_c += 1
                if punto_en_poligono(x, y, p_main): p_a += 1
    return area_bruta * (p_a / p_c) if p_c > 0 else 0

# ==========================================
# 7. FASES DE LA PLATAFORMA
# ==========================================

# --- LOGIN ---
if st.session_state.paso == 'login':
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🌱 Enjambre VRA")
        t_l, t_r = st.tabs(["🔑 Login", "📝 Registro"])
        with t_l:
            with st.form("login"):
                tel = st.text_input("WhatsApp")
                pw = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Ingresar", use_container_width=True):
                    conn = sqlite3.connect('enjambre_usuarios.db'); c = conn.cursor()
                    c.execute("SELECT nombre, password FROM usuarios WHERE telefono=?", (tel,))
                    u = c.fetchone(); conn.close()
                    if u and u[1] == hash_password(pw):
                        st.session_state.usuario = {'nombre': u[0], 'telefono': tel}
                        st.session_state.paso = 'onboarding_mapa'; st.rerun()
                    else: st.error("Error de acceso.")
        
        with t_r:
            with st.form("registro"):
                n = st.text_input("Nombre"); t = st.text_input("WhatsApp"); p = st.text_input("Clave", type="password")
                if st.form_submit_button("Crear Cuenta"):
                    conn = sqlite3.connect('enjambre_usuarios.db'); c = conn.cursor()
                    try: 
                        c.execute("INSERT INTO usuarios VALUES (?,?,?)", (t, n, hash_password(p)))
                        conn.commit(); st.success("Registrado correctamente.")
                    except: st.error("Ya existe este número.")
                    conn.close()

    st.markdown("---")
    st.markdown("<h3 style='text-align:center; margin-bottom: 25px;'>Ecosistema Tecnológico</h3>", unsafe_allow_html=True)
    
    # 🚀 ACTUALIZACIÓN: STACK COMPLETO CON SENSORES Y DRONES
    h = [
        "Drones VRA (Alta Precisión)", "Sensores IoT de Suelo", "Open-Meteo API", 
        "Nominatim (OSM)", "Twilio API", "Leaflet.Draw & AntPath", 
        "Folium & Leaflet.js", "Esri World Imagery", "Pandas & Python"
    ]
    
    for i in range(0, len(h), 3):
        cols = st.columns(3)
        for j in range(3):
            if i+j < len(h): 
                cols[j].markdown(f'<div class="tool-box">{h[i+j]}</div>', unsafe_allow_html=True)

# --- DASHBOARD ---
elif st.session_state.paso == 'dashboard':
    area_t = st.session_state.parcela_area
    area_u = sum(v['area'] for v in st.session_state.cultivos_mapeados.values())
    
    with st.sidebar:
        st.title(f"Hola, {st.session_state.usuario['nombre']}")
        st.metric("Área Total", f"{area_t:,} m²")
        st.metric("Área Usada", f"{area_u:,} m²")
        st.progress(min(area_u/area_t, 1.0) if area_t>0 else 0)

    t1, t2, t3, t4, t5 = st.tabs(["🌱 Sensores", "🚁 Logística Dron", "📈 Reporte", "📉 IA Gemelo", "🤖 Consultor IA"])

    with t3:
        st.header("Reporte Ejecutivo WhatsApp")
        ahorro = st.session_state.total_litros_tradicional - st.session_state.total_litros_hoy
        msg = f"*REPORTE ENJAMBRE VRA*\\nGerente: {st.session_state.usuario['nombre']}\\nAgua Dron VRA: {st.session_state.total_litros_hoy:.1f}L\\nAhorro Logrado: {ahorro:.1f}L"
        
        st.text_area("Pre-visualización del Reporte:", value=msg, height=200)
        
        if st.button("🚀 ENVIAR VÍA TWILIO", type="primary", use_container_width=True):
            exito, info = enviar_whatsapp_twilio(msg, st.session_state.usuario['telefono'])
            if exito: 
                st.success(f"¡Mensaje enviado! ID de rastreo: {info}")
            else: 
                st.error(f"Error al enviar: {info}. Asegúrate de que tus credenciales en 'secrets' sean correctas.")

# (El resto de fases se mantienen con la lógica robusta previa)
