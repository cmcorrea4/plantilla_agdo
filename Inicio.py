import streamlit as st
import requests
import json
import time
import base64
from gtts import gTTS
import io
from fpdf import FPDF
import tempfile

# Configuración de la página sin el parámetro theme (compatible con versiones anteriores)
st.set_page_config(
    page_title="Asistente Digital",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# Establecer tema claro mediante CSS personalizado
st.markdown("""
<style>
    /* Tema claro con colores Construinmuniza */
    body {
        color: #2C3E50;
        background-color: #FAFAFA;
    }
    .stApp {
        background-color: #FAFAFA;
    }
    
    /* Inputs y controles */
    .stTextInput>div>div>input {
        background-color: #FFFFFF;
        color: #2C3E50;
        border: 1px solid #E0E6E8;
        border-radius: 8px;
    }
    .stTextInput>div>div>input:focus {
        border-color: #1B5E20;
        box-shadow: 0 0 0 2px rgba(27, 94, 32, 0.2);
    }
    
    .stSlider>div>div>div {
        color: #2C3E50;
    }
    
    .stSelectbox>div>div>div {
        background-color: #FFFFFF;
        color: #2C3E50;
        border: 1px solid #E0E6E8;
        border-radius: 8px;
    }
    
    /* Botones con colores Construinmuniza */
    .stButton > button {
        background-color: #1B5E20;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #2E7D32;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(27, 94, 32, 0.3);
    }
    
    /* Sidebar con colores Construinmuniza */
    .css-1d391kg, .css-12oz5g7, section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E0E6E8;
    }
    
    /* Estilos personalizados para el asistente con branding Construinmuniza */
    .main-header {
        font-size: 2.8rem;
        color: #2C3E50;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1B5E20, #FFC107);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: none;
    }
    
    .subheader {
        font-size: 1.3rem;
        color: #2E7D32;
        margin-bottom: 1rem;
        font-weight: 500;
    }
    
    .audio-controls {
        display: flex;
        align-items: center;
        margin-top: 10px;
        padding: 8px;
        background-color: #F1F8E9;
        border-radius: 8px;
        border: 1px solid #C8E6C9;
    }
    
    .footer {
        position: fixed;
        bottom: 0;
        width: 100%;
        background-color: #FFFFFF;
        border-top: 1px solid #E0E6E8;
        text-align: center;
        padding: 10px;
        font-size: 0.8rem;
        color: #2E7D32;
    }
    
    /* Títulos en la barra lateral con colores Construinmuniza */
    .sidebar .sidebar-content h1, 
    .sidebar .sidebar-content h2, 
    .sidebar .sidebar-content h3,
    .css-1outpf7,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #1B5E20 !important;
        font-weight: 600;
    }
    
    /* Ejemplos de preguntas con tema Construinmuniza */
    .example-questions {
        background: linear-gradient(135deg, #FAFAFA 0%, #F1F8E9 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 2rem;
        border: 1px solid #C8E6C9;
    }
    
    .example-questions p {
        color: #2E7D32 !important;
        font-weight: 500;
    }
    
    .example-questions li {
        background: linear-gradient(135deg, #FFFFFF 0%, #F9FBE7 100%) !important;
        border: 1px solid #C8E6C9 !important;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .example-questions li:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(27, 94, 32, 0.15);
        border-color: #1B5E20 !important;
    }
    
    .example-questions span {
        color: #2C3E50 !important;
    }
    
    /* Chat messages con tema Construinmuniza */
    .stChatMessage {
        background-color: #FFFFFF;
        border: 1px solid #E0E6E8;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(27, 94, 32, 0.05);
    }
    
    /* Expanders con colores Construinmuniza */
    .streamlit-expanderHeader {
        background-color: #F1F8E9;
        color: #1B5E20;
        border: 1px solid #C8E6C9;
        border-radius: 8px;
    }
    
    /* Success/Error/Info messages con branding */
    .stSuccess {
        background-color: #E8F5E8;
        color: #2E7D32;
        border: 1px solid #A5D6A7;
    }
    
    .stError {
        background-color: #FFEBEE;
        color: #C62828;
        border: 1px solid #EF9A9A;
    }
    
    .stInfo {
        background-color: #FFF3C4;
        color: #E65100;
        border: 1px solid #FFE082;
    }
    
    /* Code blocks */
    .stCode {
        background-color: #F9F9F9;
        border: 1px solid #E0E6E8;
        color: #2C3E50;
    }
    
    /* Spinner con color Construinmuniza */
    .stSpinner {
        color: #1B5E20;
    }
    
    /* Tabs con tema Construinmuniza */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #F1F8E9;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #2C3E50;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1B5E20;
        color: white;
    }
    
    /* Custom scrollbar con colores Construinmuniza */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #F1F8E9;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #A5D6A7;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #81C784;
    }
</style>
""", unsafe_allow_html=True)

# Función para inicializar variables de sesión
def initialize_session_vars():
    if "is_configured" not in st.session_state:
        st.session_state.is_configured = False
    if "agent_endpoint" not in st.session_state:
        # Endpoint fijo como solicitado
        st.session_state.agent_endpoint = "https://vs3sawqsrcx6yzud3roifshn.agents.do-ai.run"
    if "agent_access_key" not in st.session_state:
        st.session_state.agent_access_key = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []

# Inicializar variables
initialize_session_vars()

# Función para generar audio a partir de texto
def text_to_speech(text):
    try:
        # Crear objeto gTTS (siempre en español y rápido)
        tts = gTTS(text=text, lang='es', slow=False)
        
        # Guardar audio en un buffer en memoria
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        # Convertir a base64 para reproducir en HTML (sin autoplay)
        audio_base64 = base64.b64encode(audio_buffer.read()).decode()
        audio_html = f'''
        <div class="audio-controls">
            <audio controls style="width: 100%; height: 35px;">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                Tu navegador no soporta el elemento de audio.
            </audio>
        </div>
        '''
        return audio_html
    except Exception as e:
        return f"<div class='error' style='color: #C62828; padding: 8px; background-color: #FFEBEE; border-radius: 4px; border: 1px solid #EF9A9A;'>Error al generar audio: {str(e)}</div>"

# Título y descripción de la aplicación
st.markdown("<h1 class='main-header'>🌲 Asistente Construinmuniza</h1>", unsafe_allow_html=True)

# Pantalla de configuración inicial si aún no se ha configurado
if not st.session_state.is_configured:
    st.markdown("<h2 class='subheader'>🔐 Acceso al Asistente</h2>", unsafe_allow_html=True)
    
    # Container con mejor estilo para el login
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #FFFFFF 0%, #F8F9FA 100%); 
                        padding: 2rem; border-radius: 12px; border: 1px solid #E3E8EF; 
                        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;">
                <h3 style="color: #2C3E50; margin-bottom: 1rem;">Bienvenido</h3>
                <p style="color: #7F8C8D; margin-bottom: 1.5rem;">
                    Por favor ingresa tu clave de acceso para comenzar a interactuar con el asistente digital
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Solo solicitar la clave de acceso
            agent_access_key = st.text_input(
                "🔑 Clave de Acceso", 
                type="password",
                placeholder="Ingresa tu clave de acceso al asistente",
                help="Tu clave de acceso para autenticar las solicitudes"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
            with col_btn2:
                if st.button("🚀 Iniciar sesión", use_container_width=True):
                    if not agent_access_key:
                        st.error("❌ Por favor, ingresa la clave de acceso")
                    else:
                        # Guardar configuración en session_state
                        st.session_state.agent_access_key = agent_access_key
                        st.session_state.is_configured = True
                        st.success("✅ Clave configurada correctamente")
                        time.sleep(1)  # Breve pausa para mostrar el mensaje de éxito
                        st.rerun()
    
    # Parar ejecución hasta que se configure
    st.stop()

# Una vez configurado, mostrar la interfaz normal
st.markdown("<p class='subheader'>💬 Interactúa con tu asistente inteligente</p>", unsafe_allow_html=True)

# Agregar ejemplos de preguntas con estilo profesional
st.markdown("""
<div class="example-questions">
    <p style="font-size: 1rem; margin-bottom: 1.5rem; font-style: italic; font-family: 'Segoe UI', Arial, sans-serif;">
        💡 Ejemplos de preguntas que puedes hacerle:
    </p>
    <ul style="list-style-type: none; padding-left: 0; margin-bottom: 0; font-family: 'Segoe UI', Arial, sans-serif;">
        <li style="margin-bottom: 0.8rem; padding: 1rem; border-radius: 8px; border-left: 4px solid #3498DB;">
            <span style="font-weight: 500;">🏢 ¿Qué servicios presta Construinmuniza?</span>
        </li>
        <li style="margin-bottom: 0.8rem; padding: 1rem; border-radius: 8px; border-left: 4px solid #3498DB;">
            <span style="font-weight: 500;">🛡️ ¿Por qué se debe aplicar inmunizante a la madera?</span>
        </li>
        <li style="margin-bottom: 0.8rem; padding: 1rem; border-radius: 8px; border-left: 4px solid #3498DB;">
            <span style="font-weight: 500;">📦 ¿Puedes darme la disponibilidad de inventario de la referencia RE40009250?</span>
        </li>
        <li style="margin-bottom: 0.8rem; padding: 1rem; border-radius: 8px; border-left: 4px solid #3498DB;">
            <span style="font-weight: 500;">💰 ¿Puedes darme el precio de PISO PARED 10X1.7X100M2 CEP en El Chagualo?</span>
        </li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Sidebar para configuración
st.sidebar.title("⚙️ Configuración")

# Mostrar información de conexión actual
st.sidebar.success("✅ Configuración cargada")
with st.sidebar.expander("📋 Ver configuración actual"):
    st.code(f"Endpoint: {st.session_state.agent_endpoint}\nClave de acceso: {'*'*10}")

# Ajustes avanzados
with st.sidebar.expander("🔧 Ajustes avanzados"):
    temperature = st.slider("🌡️ Temperatura", min_value=0.0, max_value=1.0, value=0.2, step=0.1,
                          help="Valores más altos generan respuestas más creativas, valores más bajos generan respuestas más deterministas.")
    
    max_tokens = st.slider("📏 Longitud máxima", min_value=100, max_value=2000, value=1000, step=100,
                          help="Número máximo de tokens en la respuesta.")

# Sección para probar conexión con el agente
with st.sidebar.expander("🔍 Probar conexión"):
    if st.button("🔗 Verificar endpoint"):
        with st.spinner("Verificando conexión..."):
            try:
                agent_endpoint = st.session_state.agent_endpoint
                agent_access_key = st.session_state.agent_access_key
                
                if not agent_endpoint or not agent_access_key:
                    st.error("❌ Falta configuración del endpoint o clave de acceso")
                else:
                    # Asegurarse de que el endpoint termine correctamente
                    if not agent_endpoint.endswith("/"):
                        agent_endpoint += "/"
                    
                    # Verificar si la documentación está disponible (común en estos endpoints)
                    docs_url = f"{agent_endpoint}docs"
                    
                    # Preparar headers
                    headers = {
                        "Authorization": f"Bearer {agent_access_key}",
                        "Content-Type": "application/json"
                    }
                    
                    try:
                        # Primero intentar verificar si hay documentación disponible
                        response = requests.get(docs_url, timeout=10)
                        
                        if response.status_code < 400:
                            st.success(f"✅ Documentación del agente accesible en: {docs_url}")
                        
                        # Luego intentar hacer una solicitud simple para verificar la conexión
                        completions_url = f"{agent_endpoint}api/v1/chat/completions"
                        test_payload = {
                            "model": "n/a",
                            "messages": [{"role": "user", "content": "Hello"}],
                            "max_tokens": 5,
                            "stream": False
                        }
                        
                        response = requests.post(completions_url, headers=headers, json=test_payload, timeout=10)
                        
                        if response.status_code < 400:
                            st.success(f"✅ Conexión exitosa con el endpoint del agente")
                            with st.expander("📄 Ver detalles de la respuesta"):
                                try:
                                    st.json(response.json())
                                except:
                                    st.code(response.text)
                            st.info("🔍 La API está configurada correctamente y responde a las solicitudes.")
                        else:
                            st.error(f"❌ Error al conectar con el agente. Código: {response.status_code}")
                            with st.expander("📄 Ver detalles del error"):
                                st.code(response.text)
                    except Exception as e:
                        st.error(f"❌ Error de conexión: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error al verificar endpoint: {str(e)}")

# Opciones de gestión de conversación
st.sidebar.markdown("### 💬 Gestión de conversación")

# Botón para limpiar conversación
if st.sidebar.button("🗑️ Limpiar conversación"):
    st.session_state.messages = []
    st.rerun()

# Botón para guardar conversación en PDF
if st.sidebar.button("💾 Guardar conversación en PDF"):
    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Añadir título
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Conversación con el Asistente", ln=True, align='C')
    pdf.ln(10)
    
    # Añadir fecha
    from datetime import datetime
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=True)
    pdf.ln(10)
    
    # Recuperar mensajes
    pdf.set_font("Arial", size=12)
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            pdf.set_text_color(27, 94, 32)  # Verde Construinmuniza para usuario
            pdf.cell(200, 10, "Usuario:", ln=True)
        else:
            pdf.set_text_color(46, 125, 50)  # Verde más claro para asistente
            pdf.cell(200, 10, "Asistente:", ln=True)
        
        pdf.set_text_color(44, 62, 80)  # Color oscuro para el contenido
        
        # Partir el texto en múltiples líneas si es necesario
        text = msg["content"]
        pdf.multi_cell(190, 10, text)
        pdf.ln(5)
    
    # Guardar el PDF en un archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf_path = tmp_file.name
        pdf.output(pdf_path)
    
    # Abrir y leer el archivo para la descarga
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()
    
    # Botón de descarga
    st.sidebar.download_button(
        label="📥 Descargar PDF",
        data=pdf_data,
        file_name="conversacion.pdf",
        mime="application/pdf",
    )

# Botón para cerrar sesión
if st.sidebar.button("🔓 Cerrar sesión"):
    st.session_state.is_configured = False
    st.session_state.agent_access_key = ""
    st.rerun()

# Función para enviar consulta al agente
def query_agent(prompt, history=None):
    try:
        # Obtener configuración del agente
        agent_endpoint = st.session_state.agent_endpoint
        agent_access_key = st.session_state.agent_access_key
        
        if not agent_endpoint or not agent_access_key:
            return {"error": "Las credenciales de API no están configuradas correctamente."}
        
        # Asegurarse de que el endpoint termine correctamente
        if not agent_endpoint.endswith("/"):
            agent_endpoint += "/"
        
        # Construir URL para chat completions
        completions_url = f"{agent_endpoint}api/v1/chat/completions"
        
        # Preparar headers con autenticación
        headers = {
            "Authorization": f"Bearer {agent_access_key}",
            "Content-Type": "application/json"
        }
        
        # Preparar los mensajes en formato OpenAI
        messages = []
        if history:
            messages.extend([{"role": msg["role"], "content": msg["content"]} for msg in history])
        messages.append({"role": "user", "content": prompt})
        
        # Construir el payload
        payload = {
            "model": "n/a",  # El modelo no es relevante para el agente
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # Enviar solicitud POST
        try:
            response = requests.post(completions_url, headers=headers, json=payload, timeout=60)
            
            # Verificar respuesta
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    
                    # Procesar la respuesta en formato OpenAI
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        choice = response_data["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            result = {
                                "response": choice["message"]["content"]
                            }
                            return result
                    
                    # Si no se encuentra la estructura esperada
                    return {"error": "Formato de respuesta inesperado", "details": str(response_data)}
                except ValueError:
                    # Si no es JSON, devolver el texto plano
                    return {"response": response.text}
            else:
                # Error en la respuesta
                error_message = f"Error en la solicitud. Código: {response.status_code}"
                try:
                    error_details = response.json()
                    return {"error": error_message, "details": str(error_details)}
                except:
                    return {"error": error_message, "details": response.text}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Error en la solicitud HTTP: {str(e)}"}
        
    except Exception as e:
        return {"error": f"Error al comunicarse con el asistente: {str(e)}"}

# Mostrar historial de conversación
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Si es un mensaje del asistente y tiene audio asociado, mostrarlo
        if message["role"] == "assistant" and "audio_html" in message:
            st.markdown(message["audio_html"], unsafe_allow_html=True)

# Campo de entrada para el mensaje
prompt = st.chat_input("💭 Escribe tu pregunta aquí...")

# Procesar la entrada del usuario
if prompt:
    # Añadir mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Preparar historial para la API
    api_history = st.session_state.messages[:-1]  # Excluir el mensaje actual
    
    # Mostrar indicador de carga mientras se procesa
    with st.chat_message("assistant"):
        with st.spinner("🔍 Buscando información..."):
            # Enviar consulta al agente
            response = query_agent(prompt, api_history)
            
            if "error" in response:
                st.error(f"❌ Error: {response['error']}")
                if "details" in response:
                    with st.expander("📋 Detalles del error"):
                        st.code(response["details"])
                
                # Añadir mensaje de error al historial
                error_msg = f"Lo siento, ocurrió un error al procesar tu solicitud: {response['error']}"
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                # Mostrar respuesta del asistente
                response_text = response.get("response", "No se recibió respuesta del agente.")
                st.markdown(response_text)
                
                # Generar audio (siempre)
                audio_html = None
                with st.spinner("🎵 Generando audio..."):
                    audio_html = text_to_speech(response_text)
                    st.markdown(audio_html, unsafe_allow_html=True)
                
                # Añadir respuesta al historial con el audio
                message_data = {"role": "assistant", "content": response_text}
                if audio_html:
                    message_data["audio_html"] = audio_html
                st.session_state.messages.append(message_data)

# Pie de página
st.markdown("<div class='footer'>🌲 Asistente Digital Construinmuniza © 2025</div>", unsafe_allow_html=True)
