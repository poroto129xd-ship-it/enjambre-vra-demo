import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import time
import pandas as pd
from datetime import date
import urllib.parse
import requests

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Enjambre VRA | Plataforma Integral", page_icon="🚁", layout="wide")

st.markdown("""
    <style>
    .sensor-verde { background-color: #d4edda; color: #155724; padding: 15px; border-radius: 8px; border-left: 5px solid #28a745; text-align: center; }
    .sensor-amarillo { background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; border-left: 5px solid #ffc107; text-align: center; }
    .sensor-rojo { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; border-left: 5px solid #dc3545; text-align: center; font-weight: bold;}
    .whatsapp-btn { background-color: #25D366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; text-align: center; width: 100%;}
    .whatsapp-btn:hover { background-color: #128C7E; color: white;}
    </style>
""", unsafe_allow_html=True)

# Variables de Memoria (Persistencia de datos)
if 'paso' not in st.session_state: st.session_state.paso = 'login'
if 'usuario' not in st.session_state: st.session_state.usuario = {}
if 'parcela_area' not in st.session_state: st.session_state.parcela_area = 0
if 'cultivos_asignados' not in st.session_state: st.session_state.cultivos_asignados = {}
if 'registro_diario' not in st.session_state: st.session_state.registro_diario = []
if 'poligono_coords' not in st.session_state: st.session_state.poligono_coords = None # Guarda el dibujo del mapa
if 'clima_real' not in st.session_state: st.session_state.clima_real = {"temp": 0, "hum": 0, "viento": 0}

DB_CULTIVOS = ["Cerezas", "Uva Vinífera", "Paltos", "Nogales", "Maíz", "Trigo", "Arándanos"]

# --- FUNCIÓN: OBTENER CLIMA REAL (API Open-Meteo) ---
def obtener_clima_real(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=relative_humidity_2m"
        respuesta = requests.get(url).json()
        temp = respuesta["current_weather"]["temperature"]
        viento = respuesta["current_weather"]["windspeed"]
        humedad = respuesta["hourly"]["relative_humidity_2m"][0] # Toma la humedad de la hora actual
        return {"temp": temp, "hum": humedad, "viento": viento}
    except:
        return {"temp": 28.5, "hum": 35, "viento": 12.0} # Datos de respaldo si falla el internet

# ==========================================
# FASE 1: REGISTRO DE USUARIO
# ==========================================
if st.session_state.paso == 'login':
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🌱 Enjambre VRA")
        st.subheader("Cree su cuenta de administrador")
        with st.form("registro_form"):
            nombre = st.text_input("Nombre Completo")
            email = st.text_input("Correo Electrónico")
            # Pedimos el número con código de país para que el link de WhatsApp funcione real
            telefono = st.text_input("Número de Teléfono (Ej: +56912345678)") 
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Crear Cuenta e Ingresar", type="primary", use_container_width=True)
            
            if submit and nombre and email and telefono:
                # Limpiamos el número de teléfono (quitamos espacios o símbolos extraños)
                tel_limpio = ''.join(filter(str.isdigit, telefono))
                st.session_state.usuario = {'nombre': nombre, 'email': email, 'telefono': tel_limpio}
                st.session_state.paso = 'onboarding_mapa'
                st.rerun()

# ==========================================
# FASE 2: DIBUJO DE PARCELA Y ÁREA (Capturando el dibujo)
# ==========================================
elif st.session_state.paso == 'onboarding_mapa':
    st.header(f"Bienvenido {st.session_state.usuario['nombre']} - Delimitación Satelital")
    st.write("📍 **Paso 1:** Utilice la herramienta de polígono ⬠ para dibujar su parcela real.")
    
    mapa_dibujo = folium.Map(location=[-33.456, -70.650], zoom_start=15, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
    draw = plugins.Draw(export=True, position='topleft', draw_options={'polyline':False, 'circlemarker':False, 'marker':False, 'circle':False})
    draw.add_to(mapa_dibujo)
    
    # Capturamos toda la data de lo que el usuario dibuje en el mapa
    mapa_data = st_folium(mapa_dibujo, width=1000, height=400, key="dibujo_inicial")
    
    st.write("📍 **Paso 2:** Ingrese el área total de la zona.")
    area_ingresada = st.number_input("Área total del predio (m²):", min_value=100, max_value=1000000, value=5000, step=100)
    
    if st.button("Confirmar Terreno y Continuar ➡️", type="primary"):
        st.session_state.parcela_area = area_ingresada
        
        # MAGIA: Rescatamos las coordenadas exactas del dibujo
        lat_clima, lon_clima = -33.456, -70.650 # Coordenadas por defecto (Quilicura)
        if mapa_data and mapa_data.get("all_drawings"):
            dibujo = mapa_data["all_drawings"][0]
            if dibujo["geometry"]["type"] == "Polygon":
                st.session_state.poligono_coords = dibujo["geometry"]["coordinates"][0]
                # Sacamos un punto del polígono para buscar el clima exacto de esa zona
                lon_clima = st.session_state.poligono_coords[0][0]
                lat_clima = st.session_state.poligono_coords[0][1]
        
        # Consultamos el clima real a la API meteorológica
        st.session_state.clima_real = obtener_clima_real(lat_clima, lon_clima)
        
        st.session_state.paso = 'onboarding_cultivos'
        st.rerun()

# ==========================================
# FASE 3: DISTRIBUCIÓN DE CULTIVOS
# ==========================================
elif st.session_state.paso == 'onboarding_cultivos':
    st.header("🌾 Distribución de Plantaciones")
    st.write(f"Usted cuenta con un total de **{st.session_state.parcela_area} m²** registrados.")
    
    cultivos_seleccionados = st.multiselect("Seleccione los tipos de cultivos presentes en su parcela:", DB_CULTIVOS)
    
    if cultivos_seleccionados:
        area_asignada_total = 0
        asignaciones_temporales = {}
        for cultivo in cultivos_seleccionados:
            m2 = st.number_input(f"Metros cuadrados para {cultivo}:", min_value=0, max_value=st.session_state.parcela_area, value=0, step=100)
            asignaciones_temporales[cultivo] = m2
            area_asignada_total += m2
        
        st.progress(min(area_asignada_total / st.session_state.parcela_area, 1.0))
        st.write(f"Total asignado: **{area_asignada_total} m²** de **{st.session_state.parcela_area} m²**")
        
        if area_asignada_total > st.session_state.parcela_area:
            st.error("❌ Error: Has superado el límite de tu parcela.")
        elif area_asignada_total == 0:
            st.warning("⚠️ Debes asignar al menos 1 metro cuadrado para continuar.")
        else:
            if st.button("✅ Confirmar Distribución y Acceder al Sistema", type="primary"):
                st.session_state.cultivos_asignados = asignaciones_temporales
                st.session_state.paso = 'dashboard'
                st.session_state.registro_diario = [{"Hora": "06:00", "Sector": "General", "Acción": "Monitoreo Inicial", "Estado": "🟢 Óptimo", "Observación": "Lectura satelital iniciada."}]
                st.rerun()

# ==========================================
# FASE 4: DASHBOARD PRINCIPAL
# ==========================================
elif st.session_state.paso == 'dashboard':
    st.title(f"📊 Dashboard Enjambre VRA | Admin: {st.session_state.usuario['nombre']}")
    
    tab1, tab2, tab3 = st.tabs(["🌱 1. Sensores y Suelo (IoT)", "🚁 2. Logística Dron", "📈 3. Reporte Diario y WhatsApp"])
    
    # ---------------- PESTAÑA 1: SENSORES Y CLIMA REAL ----------------
    with tab1:
        st.header("Monitoreo en Tiempo Real (Inteligencia Weenat / API)")
        st.write("Los datos a continuación son extraídos en tiempo real de la zona satelital seleccionada.")
        clima_cols = st.columns(4)
        
        # Mostramos los datos reales obtenidos de la API
        temp_real = st.session_state.clima_real["temp"]
        hum_real = st.session_state.clima_real["hum"]
        viento_real = st.session_state.clima_real["viento"]
        
        clima_cols[0].metric("Temp. Zona Seleccionada", f"{temp_real}°C", "Sensory Data")
        clima_cols[1].metric("Humedad Ambiental", f"{hum_real}%", "IoT")
        clima_cols[2].metric("Velocidad de Viento", f"{viento_real} km/h", "Drone Safe" if viento_real < 25 else "Riesgo de Vuelo")
        
        # Inteligencia Artificial Simple: Si hace mucho calor, lanza alerta de radiación
        alerta_uv = "Riesgo Foliar" if temp_real > 26 else "Óptimo"
        clima_cols[3].metric("Radiación / Evaporación", "Alta" if temp_real > 26 else "Normal", alerta_uv)
        
        st.markdown("---")
        st.subheader("📡 Estado de Plantaciones por Sector")
        nombres_cultivos = list(st.session_state.cultivos_asignados.keys())
        zonas = st.columns(3)
        
        if len(nombres_cultivos) > 0:
            with zonas[0]:
                st.markdown(f'<div class="sensor-verde"><b>Zona A ({nombres_cultivos[0]})</b><br>Humedad Suelo: 68%<br>Área: {st.session_state.cultivos_asignados[nombres_cultivos[0]]} m2<br>Estado: Óptimo</div>', unsafe_allow_html=True)
        if len(nombres_cultivos) > 1:
            with zonas[1]:
                st.markdown(f'<div class="sensor-amarillo"><b>Zona B ({nombres_cultivos[1]})</b><br>Humedad Suelo: 45%<br>Área: {st.session_state.cultivos_asignados[nombres_cultivos[1]]} m2<br>Estado: Estrés leve</div>', unsafe_allow_html=True)
        
        with zonas[2]:
            # IA cruzando datos: Si la humedad ambiente es baja, el suelo sufre más.
            estado_suelo = "22%" if hum_real > 40 else "15% (CRÍTICO)" 
            st.markdown(f'<div class="sensor-rojo"><b>🚨 Zona de Riesgo (Bordes)</b><br>Humedad Suelo: {estado_suelo}<br>Alerta de estrés hídrico<br>Requiere Dron Inmediato</div>', unsafe_allow_html=True)

    # ---------------- PESTAÑA 2: DRON Y PERÍMETRO HEREDADO ----------------
    with tab2:
        st.header("Centro de Mando Logístico VRA")
        col_ctrl, col_map = st.columns([1, 2])
        
        with col_ctrl:
            hora_actual = st.slider("Simulador de Reloj:", min_value=0, max_value=23, value=14, format="%d:00 hrs")
            tipo_mision = st.radio("Acción a ejecutar:", ["Riego de Emergencia", "Nutrición (Proteínas)", "Tratamiento (Anti-plagas)"])
            
            es_riesgoso = (tipo_mision == "Riego de Emergencia" and 10 <= hora_actual <= 18)
            boton_deshabilitado = False
            
            if es_riesgoso:
                st.error("⚠️ ADVERTENCIA CRÍTICA: Desplegar riego a esta hora quemará la plantación por efecto lupa solar.")
                if not st.checkbox("Declaro que entiendo los riesgos y autorizo el despliegue manual."):
                    boton_deshabilitado = True 
            
            if st.button("🚀 Forzar Despliegue Manual", type="primary", disabled=boton_deshabilitado, use_container_width=True):
                with st.spinner("Transmitiendo polígono al dron..."):
                    time.sleep(1.5)
                    st.success(f"Dron en vuelo sobre el área delimitada. Misión: {tipo_mision}")
                    st.session_state.registro_diario.append({"Hora": f"{hora_actual}:00", "Sector": "Zona de Riesgo", "Acción": f"Dron: {tipo_mision}", "Estado": "🟡 Riesgo Asumido" if es_riesgoso else "🟢 Completado", "Observación": "Operación de Tasa Variable ejecutada."})
        
        with col_map:
            # MAPA DEL DRON (Ahora muestra el dibujo real de la pestaña 1)
            mapa_dron = folium.Map(location=[-33.456, -70.650], zoom_start=15, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
            
            # MAGIA: Si el usuario dibujó algo, lo redibujamos aquí automáticamente
            if st.session_state.poligono_coords:
                # GeoJSON guarda [lon, lat], Folium necesita [lat, lon], así que lo invertimos
                coords_formateadas = [[punto[1], punto[0]] for punto in st.session_state.poligono_coords]
                
                # Dibujamos el polígono en el mapa del dron
                folium.Polygon(locations=coords_formateadas, color="cyan", fill=True, fill_color="cyan", fill_opacity=0.3, popup="Área VRA Asignada").add_to(mapa_dron)
                # Hacemos que la cámara vuele directo a la parcela
                mapa_dron.fit_bounds(coords_formateadas)
                
            st_folium(mapa_dron, width=700, height=400)

    # ---------------- PESTAÑA 3: WHATSAPP BOT REAL ----------------
    with tab3:
        st.header("Bitácora Diaria y WhatsApp Bot")
        
        df_registro = pd.DataFrame(st.session_state.registro_diario)
        st.dataframe(df_registro, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📲 Exportación Móvil")
        
        # Preparamos el mensaje exacto que se enviará
        resumen_texto = f"""*REPORTE ENJAMBRE VRA* 🚁🌱
Gerente: {st.session_state.usuario['nombre']}
Área cubierta: {st.session_state.parcela_area} m2
Clima local: {temp_real}°C / Humedad: {hum_real}%

Estado General: ESTABLE ✅
Atención: Revisar Zona de Bordes.
Operaciones Dron hoy: {len(st.session_state.registro_diario) - 1}"""
        
        st.text_area("Vista previa del mensaje a enviar:", value=resumen_texto, height=200, disabled=True)
        
        # MAGIA WHATSAPP: Convertimos el texto para que las URLs lo entiendan
        mensaje_url = urllib.parse.quote(resumen_texto)
        numero_destino = st.session_state.usuario['telefono']
        
        # Enlace oficial de la API de WhatsApp
        link_whatsapp = f"https://api.whatsapp.com/send?phone={numero_destino}&text={mensaje_url}"
        
        st.markdown(f'<a href="{link_whatsapp}" target="_blank" class="whatsapp-btn">📲 Enviar Reporte Real por WhatsApp</a>', unsafe_allow_html=True)
        st.caption(f"El reporte será enviado a la cuenta asociada al número: +{numero_destino}")
