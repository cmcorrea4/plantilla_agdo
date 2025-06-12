import streamlit as st
import requests
import json
import time
import base64
from gtts import gTTS
import io
from fpdf import FPDF
import tempfile
import re
from datetime import datetime

# Configuración de la página sin el parámetro theme (compatible con versiones anteriores)
st.set_page_config(
    page_title="Asistente Digital",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# Establecer tema oscuro mediante CSS personalizado para versiones anteriores
st.markdown("""
<style>
    /* Tema oscuro personalizado para versiones anteriores de Streamlit */
    body {
        color: #fafafa;
        background-color: #0e1117;
    }
    .stApp {
        background-color: #0e1117;
    }
    .stTextInput>div>div>input {
        background-color: #262730;
        color: white;
    }
    .stSlider>div>div>div {
        color: white;
    }
    .stSelectbox>div>div>div {
        background-color: #262730;
        color: white;
    }
    #div.stButton > button:first-child {
    #    background-color: #1E88E5;
    #    color: white;
    #}
    .css-1d391kg, .css-12oz5g7 {
        background-color: #262730;
    }
    
    /* Estilos personalizados para el asistente - Todos los títulos en BLANCO */
    .main-header {
        font-size: 2.5rem;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    }
    .subheader {
        font-size: 1.5rem;
        color: #FFFFFF;
        margin-bottom: 1rem;
    }
    .audio-controls {
        display: flex;
        align-items: center;
        margin-top: 10px;
    }
    .footer {
        position: fixed;
        bottom: 0;
        width: 100%;
        background-color: #0e1117;
        text-align: center;
        padding: 10px;
        font-size: 0.8rem;
    }
    /* Asegurar que todos los títulos en la barra lateral también sean blancos */
    .sidebar .sidebar-content h1, 
    .sidebar .sidebar-content h2, 
    .sidebar .sidebar-content h3,
    .css-1outpf7 {
        color: #FFFFFF !important;
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
    if "last_cotization_data" not in st.session_state:
        st.session_state.last_cotization_data = None

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
            <audio controls>
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                Tu navegador no soporta el elemento de audio.
            </audio>
        </div>
        '''
        return audio_html
    except Exception as e:
        return f"<div class='error'>Error al generar audio: {str(e)}</div>"

# Función para extraer datos de cotización de la respuesta del LLM
def extract_cotization_data(response_text):
    """Extrae datos de productos de la respuesta del LLM"""
    cotization_data = {
        'items': [],
        'subtotal': 0,
        'impuestos': 0,
        'total': 0,
        'cliente': 'CONSUMIDOR FINAL',
        'fecha': datetime.now().strftime('%d/%m/%Y'),
        'numero_cotizacion': f"CCV-{int(time.time())}"[-8:]
    }
    
    # Buscar información específica en el texto
    text_lower = response_text.lower()
    lines = response_text.split('\n')
    
    # Extraer información de la respuesta específica
    precio_match = re.search(r'precio.*?(\d+)\s*cop', text_lower)
    cantidad_match = re.search(r'cantidad.*?(\d+)', text_lower)
    subtotal_match = re.search(r'subtotal.*?(\d+)\s*cop', text_lower)
    total_match = re.search(r'total.*?(\d+)\s*cop', text_lower)
    
    # Buscar especificaciones del producto
    especif_match = re.search(r'especificaciones?.*?(\d+x\d+)', text_lower)
    
    # Construir item basado en la información encontrada
    if precio_match and cantidad_match:
        precio_unitario = int(precio_match.group(1))
        cantidad = int(cantidad_match.group(1))
        
        item = {
            'referencia': 'RA40012300',  # Referencia por defecto para alfardas
            'descripcion': 'ALFARDA TRATADA 12X300',
            'cantidad': cantidad,
            'precio_unitario': precio_unitario,
            'impuestos': 0,
            'valor_total': 0,
            'peso': 186  # Peso típico
        }
        
        # Si se encontraron especificaciones, actualizar descripción
        if especif_match:
            specs = especif_match.group(1).upper()
            item['descripcion'] = f'ALFARDA TRATADA {specs}'
        
        # Calcular valores correctamente
        item['valor_total'] = precio_unitario * cantidad
        item['impuestos'] = 0  # Sin impuestos por el momento según tu solicitud
        
        cotization_data['items'].append(item)
        cotization_data['subtotal'] = item['valor_total']
        cotization_data['impuestos'] = 0  # Sin impuestos
        cotization_data['total'] = cotization_data['subtotal']  # Sin sumar impuestos
    
    # Si no se pudo extraer con el método anterior, usar método alternativo
    elif 'alfarda' in text_lower and ('precio' in text_lower or 'cop' in text_lower):
        # Buscar números que puedan ser precios o cantidades
        numbers = re.findall(r'\d+', response_text)
        if len(numbers) >= 2:
            # Asumir que el primer número pequeño es cantidad y buscar el precio más probable
            cantidad = 5  # Valor por defecto basado en la pregunta
            precio = 42378  # Precio mencionado en la respuesta
            
            # Buscar cantidad específica en el texto
            for num in numbers:
                if int(num) <= 20:  # Probablemente cantidad
                    cantidad = int(num)
                    break
            
            # Buscar precio específico (número más grande)
            for num in numbers:
                if int(num) > 1000:  # Probablemente precio
                    precio = int(num)
                    break
            
            item = {
                'referencia': 'RA40012300',
                'descripcion': 'ALFARDA TRATADA 12X300',
                'cantidad': cantidad,
                'precio_unitario': precio,
                'impuestos': 0,
                'valor_total': 0,
                'peso': 186
            }
            
            # Calcular valores correctamente
            item['valor_total'] = precio * cantidad
            item['impuestos'] = 0  # Sin impuestos por el momento
            
            cotization_data['items'].append(item)
            cotization_data['subtotal'] = item['valor_total']
            cotization_data['impuestos'] = 0  # Sin impuestos
            cotization_data['total'] = cotization_data['subtotal']  # Sin sumar impuestos
    
    return cotization_data

ar fuente
        pdf.set_font("Arial", size=8)
        
        # Encabezado de la empresa
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "Construcciones Inmunizadas De Colombia", ln=True, align='C')
        pdf.set_font("Arial", size=8)
        pdf.cell(0, 4, "Nit: 900297110", ln=True, align='C')
        pdf.cell(0, 4, "Cra 58 64 10", ln=True, align='C')
        pdf.cell(0, 4, "Tel: 4075014 Fax:", ln=True, align='C')
        pdf.ln(5)
        
        # Título COTIZACIONES
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 8, "COTIZACIONES", ln=True, align='C')
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, f"No. {cotization_data['numero_cotizacion']}", ln=True, align='C')
        pdf.ln(3)
        
        # COTIZACIÓN DE VENTAS
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "COTIZACION DE VENTAS", ln=True, align='C')
        pdf.ln(5)
        
        # Información del cliente y fecha
        y_start = pdf.get_y()
        
        # Cliente (lado izquierdo)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 6, "Cliente", ln=False)
        pdf.set_font("Arial", size=8)
        pdf.cell(60, 6, "", ln=True)  # Espacio
        
        pdf.set_font("Arial", size=8)
        pdf.cell(20, 5, "Nombre:", ln=False)
        pdf.cell(70, 5, cotization_data['cliente'], ln=True)
        pdf.cell(20, 5, "Dirección:", ln=False)
        pdf.cell(70, 5, "CR 58 64 10", ln=True)
        pdf.cell(20, 5, "Ciudad:", ln=False)
        pdf.cell(70, 5, "Medellín", ln=True)
        pdf.cell(20, 5, "Teléfono:", ln=False)
        pdf.cell(70, 5, "4075014", ln=True)
        
        # Información de fecha (lado derecho)
        pdf.set_xy(120, y_start + 6)
        pdf.cell(20, 5, "Fecha:", ln=False)
        pdf.cell(30, 5, cotization_data['fecha'], ln=True)
        pdf.set_x(120)
        pdf.cell(20, 5, "Número pedido:", ln=False)
        pdf.cell(30, 5, "C01", ln=True)
        pdf.set_x(120)
        pdf.cell(20, 5, "Forma de pago:", ln=False)
        pdf.cell(30, 5, "CONSTRUCCIONES", ln=True)
        pdf.set_x(120)
        pdf.cell(20, 5, "Vendedor:", ln=False)
        pdf.cell(30, 5, "CONSTRUCCIONES", ln=True)
        
        pdf.ln(10)
        
        # Tabla de productos
        # Encabezados de la tabla
        pdf.set_font("Arial", 'B', 8)
        headers = ["Referencia", "Descripción", "U.M.", "Cantidad", "Peso Kg", "Precio unitario", "Impuestos", "Valor total"]
        widths = [25, 60, 15, 20, 20, 25, 20, 25]
        
        # Dibujar encabezados
        x_start = 10
        pdf.set_x(x_start)
        for i, header in enumerate(headers):
            pdf.cell(widths[i], 8, header, 1, 0, 'C')
        pdf.ln()
        
        # Datos de productos
        pdf.set_font("Arial", size=7)
        for item in cotization_data['items']:
            pdf.set_x(x_start)
            pdf.cell(widths[0], 8, item.get('referencia', ''), 1, 0, 'C')
            pdf.cell(widths[1], 8, item.get('descripcion', ''), 1, 0, 'L')
            pdf.cell(widths[2], 8, "UND", 1, 0, 'C')
            pdf.cell(widths[3], 8, str(item.get('cantidad', 0)), 1, 0, 'C')
            pdf.cell(widths[4], 8, str(item.get('peso', 0)), 1, 0, 'C')
            pdf.cell(widths[5], 8, f"${item.get('precio_unitario', 0):,}", 1, 0, 'R')
            pdf.cell(widths[6], 8, f"${item.get('impuestos', 0):,}", 1, 0, 'R')
            pdf.cell(widths[7], 8, f"${item.get('valor_total', 0):,}", 1, 0, 'R')
            pdf.ln()
        
        # Llenar filas vacías si hay pocas items
        empty_rows = max(0, 15 - len(cotization_data['items']))
        for _ in range(empty_rows):
            pdf.set_x(x_start)
            for width in widths:
                pdf.cell(width, 8, "", 1, 0, 'C')
            pdf.ln()
        
        # Totales
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        
        # Notas (lado izquierdo)
        pdf.cell(40, 8, "Notas", 1, 0, 'L')
        pdf.cell(70, 8, "", 1, 1, 'L')  # Celda vacía para notas
        
        # Totales (lado derecho)
        pdf.set_xy(120, pdf.get_y() - 8)
        pdf.cell(30, 8, "Totales", 1, 0, 'C')
        pdf.cell(40, 8, "", 1, 1, 'L')
        
        pdf.set_x(120)
        pdf.set_font("Arial", size=9)
        pdf.cell(30, 6, "Valor Subtotal:", 1, 0, 'L')
        pdf.cell(40, 6, f"${cotization_data['subtotal']:,}", 1, 1, 'R')
        
        pdf.set_x(120)
        pdf.cell(30, 6, "Valor impuestos:", 1, 0, 'L')
        pdf.cell(40, 6, f"${cotization_data['impuestos']:,}", 1, 1, 'R')
        
        pdf.set_x(120)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(30, 8, "Total:", 1, 0, 'L')
        pdf.cell(40, 8, f"${cotization_data['total']:,}", 1, 1, 'R')
        
        # Firmas
        pdf.ln(10)
        pdf.set_font("Arial", size=8)
        
        # Líneas para firmas
        y_firma = pdf.get_y()
        pdf.line(25, y_firma, 75, y_firma)  # Elaborado
        pdf.line(85, y_firma, 135, y_firma)  # Aprobado  
        pdf.line(145, y_firma, 195, y_firma)  # Recibido
        
        pdf.ln(3)
        pdf.cell(50, 5, "Elaborado", ln=False, align='C')
        pdf.cell(50, 5, "Aprobado", ln=False, align='C')
        pdf.cell(50, 5, "Recibido", ln=False, align='C')
        
        pdf.ln(8)
        pdf.set_font("Arial", size=6)
        pdf.cell(0, 4, "ORIGINAL REIMPRESO", ln=True, align='L')
        pdf.cell(0, 4, f"Página 1 de 1", ln=True, align='R')
        
        return pdf
        
    except Exception as e:
        st.error(f"Error al generar PDF: {str(e)}")
        return None

# Función para detectar si una respuesta contiene información de cotización
def is_cotization_response(response_text):
    """Detecta si la respuesta contiene información de cotización"""
    cotization_keywords = [
        'cotización', 'cotizacion', 'precio', 'valor', 'cop', 'total',
        'referencia', 'producto', 'inventario', 'disponibilidad',
        'unidades', 'UND', 'tratada', 'inmunizada', 'alfarda', 'subtotal'
    ]
    
    text_lower = response_text.lower()
    keyword_count = sum(1 for keyword in cotization_keywords if keyword.lower() in text_lower)
    
    # Si tiene al menos 3 palabras clave relacionadas con cotización, es probable que sea una cotización
    return keyword_count >= 3

# Título y descripción de la aplicación
st.markdown("<h1 class='main-header'>Asistente Construinmuniza</h1>", unsafe_allow_html=True)

# Pantalla de configuración inicial si aún no se ha configurado
if not st.session_state.is_configured:
    st.markdown("<h2 class='subheader'>Acceso al Asistente</h2>", unsafe_allow_html=True)
    
    st.info("Por favor ingresa tu clave de acceso al asistente digital")
    
    # Solo solicitar la clave de acceso
    agent_access_key = st.text_input(
        "Clave de Acceso", 
        type="password",
        placeholder="Ingresa tu clave de acceso al asistente",
        help="Tu clave de acceso para autenticar las solicitudes"
    )
    
    if st.button("Iniciar sesión"):
        if not agent_access_key:
            st.error("Por favor, ingresa la clave de acceso")
        else:
            # Guardar configuración en session_state
            st.session_state.agent_access_key = agent_access_key
            st.session_state.is_configured = True
            st.success("Clave configurada")  # Cambio de mensaje aquí
            time.sleep(1)  # Breve pausa para mostrar el mensaje de éxito
            st.rerun()
    
    # Parar ejecución hasta que se configure
    st.stop()

# Una vez configurado, mostrar la interfaz normal
st.markdown("<p class='subheader'>Interactúa con tu asistente.</p>", unsafe_allow_html=True)

# Agregar ejemplos de preguntas con estilo profesional
st.markdown("""
<div class="example-questions">
    <p style="font-size: 0.9rem; color: #8EBBFF; margin-bottom: 1.5rem; font-style: italic; font-family: 'Segoe UI', Arial, sans-serif;">
        Ejemplos de preguntas que puedes hacerle:
    </p>
    <ul style="list-style-type: none; padding-left: 0; margin-bottom: 1.5rem; font-family: 'Segoe UI', Arial, sans-serif;">
        <li style="margin-bottom: 0.8rem; padding: 0.5rem 0.8rem; background-color: rgba(30, 136, 229, 0.1); border-radius: 4px; border-left: 3px solid #1E88E5;">
            <span style="font-weight: 500; color: #BBDEFB;">¿Qué servicios presta Construinmuniza?</span>
        </li>
        <li style="margin-bottom: 0.8rem; padding: 0.5rem 0.8rem; background-color: rgba(30, 136, 229, 0.1); border-radius: 4px; border-left: 3px solid #1E88E5;">
            <span style="font-weight: 500; color: #BBDEFB;">¿Por qué se debe aplicar inmunizante a la madera?</span>
        </li>
        <li style="margin-bottom: 0.8rem; padding: 0.5rem 0.8rem; background-color: rgba(30, 136, 229, 0.1); border-radius: 4px; border-left: 3px solid #1E88E5;">
            <span style="font-weight: 500; color: #BBDEFB;">¿Puedes darme la disponibilidad de inventario de la referencia RE40009250?</span>
        </li>
        <li style="margin-bottom: 0.8rem; padding: 0.5rem 0.8rem; background-color: rgba(30, 136, 229, 0.1); border-radius: 4px; border-left: 3px solid #1E88E5;">
            <span style="font-weight: 500; color: #BBDEFB;">¿Puedes darme el precio de PISO PARED 10X1.7X100M2 CEP en El Chagualo?</span>
        </li>
        <li style="margin-bottom: 0.8rem; padding: 0.5rem 0.8rem; background-color: rgba(255, 152, 0, 0.1); border-radius: 4px; border-left: 3px solid #FF9800;">
            <span style="font-weight: 500; color: #FFE0B2;">Genera una cotización para 5 alfardas tratadas 12X300</span>
        </li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Sidebar para configuración
st.sidebar.title("Configuración")

# Mostrar información de conexión actual
st.sidebar.success("✅ Configuración cargada")
with st.sidebar.expander("Ver configuración actual"):
    st.code(f"Endpoint: {st.session_state.agent_endpoint}\nClave de acceso: {'*'*10}")

# Ajustes avanzados
with st.sidebar.expander("Ajustes avanzados"):
    temperature = st.slider("Temperatura", min_value=0.0, max_value=1.0, value=0.2, step=0.1,
                          help="Valores más altos generan respuestas más creativas, valores más bajos generan respuestas más deterministas.")
    
    max_tokens = st.slider("Longitud máxima", min_value=100, max_value=2000, value=1000, step=100,
                          help="Número máximo de tokens en la respuesta.")

# Sección para probar conexión con el agente
with st.sidebar.expander("Probar conexión"):
    if st.button("Verificar endpoint"):
        with st.spinner("Verificando conexión..."):
            try:
                agent_endpoint = st.session_state.agent_endpoint
                agent_access_key = st.session_state.agent_access_key
                
                if not agent_endpoint or not agent_access_key:
                    st.error("Falta configuración del endpoint o clave de acceso")
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
                            with st.expander("Ver detalles de la respuesta"):
                                try:
                                    st.json(response.json())
                                except:
                                    st.code(response.text)
                            st.info("🔍 La API está configurada correctamente y responde a las solicitudes.")
                        else:
                            st.error(f"❌ Error al conectar con el agente. Código: {response.status_code}")
                            with st.expander("Ver detalles del error"):
                                st.code(response.text)
                    except Exception as e:
                        st.error(f"Error de conexión: {str(e)}")
            except Exception as e:
                st.error(f"Error al verificar endpoint: {str(e)}")

# Opciones de gestión de conversación
st.sidebar.markdown("### Gestión de conversación")

# Botón para limpiar conversación
if st.sidebar.button("🗑️ Limpiar conversación"):
    st.session_state.messages = []
    st.session_state.last_cotization_data = None
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
            pdf.set_text_color(0, 0, 255)  # Azul para usuario
            pdf.cell(200, 10, "Usuario:", ln=True)
        else:
            pdf.set_text_color(0, 128, 0)  # Verde para asistente
            pdf.cell(200, 10, "Asistente:", ln=True)
        
        pdf.set_text_color(0, 0, 0)  # Negro para el contenido
        
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
        label="Descargar PDF",
        data=pdf_data,
        file_name="conversacion.pdf",
        mime="application/pdf",
    )

# Sección para generar PDF de cotización
if st.session_state.last_cotization_data:
    st.sidebar.markdown("### Última Cotización")
    if st.sidebar.button("📄 Generar PDF de Cotización"):
        with st.spinner("Generando PDF de cotización..."):
            pdf = generate_cotization_pdf(st.session_state.last_cotization_data)
            if pdf:
                # Guardar el PDF en un archivo temporal
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    pdf_path = tmp_file.name
                    pdf.output(pdf_path)
                
                # Abrir y leer el archivo para la descarga
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                
                # Botón de descarga
                st.sidebar.download_button(
                    label="Descargar Cotización PDF",
                    data=pdf_data,
                    file_name=f"cotizacion_{st.session_state.last_cotization_data['numero_cotizacion']}.pdf",
                    mime="application/pdf",
                )
                st.sidebar.success("PDF generado exitosamente!")

# Botón para cerrar sesión
if st.sidebar.button("Cerrar sesión"):
    st.session_state.is_configured = False
    st.session_state.agent_access_key = ""
    st.session_state.last_cotization_data = None
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
prompt = st.chat_input("Escribe tu pregunta aquí...")

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
        with st.spinner("Buscando..."):
            # Enviar consulta al agente
            response = query_agent(prompt, api_history)
            
            if "error" in response:
                st.error(f"Error: {response['error']}")
                if "details" in response:
                    with st.expander("Detalles del error"):
                        st.code(response["details"])
                
                # Añadir mensaje de error al historial
                error_msg = f"Lo siento, ocurrió un error al procesar tu solicitud: {response['error']}"
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                # Mostrar respuesta del asistente
                response_text = response.get("response", "No se recibió respuesta del agente.")
                st.markdown(response_text)
                
                # Verificar si la respuesta contiene información de cotización
                if is_cotization_response(response_text):
                    with st.spinner("Procesando datos de cotización..."):
                        cotization_data = extract_cotization_data(response_text)
                        
                        # Debug: Mostrar información extraída
                        st.write("🔍 **Debug - Datos extraídos:**")
                        st.json(cotization_data)
                        
                        # Guardar datos de cotización en session state
                        if cotization_data['items'] and len(cotization_data['items']) > 0:
                            st.session_state.last_cotization_data = cotization_data
                            
                            # Mostrar mensaje de éxito
                            st.success("✅ Se detectó y procesó información de cotización!")
                            
                            # Mostrar botón para generar PDF directamente aquí también
                            if st.button("📄 Generar PDF de Cotización", key="generate_pdf_main"):
                                with st.spinner("Generando PDF de cotización..."):
                                    pdf = generate_cotization_pdf(cotization_data)
                                    if pdf:
                                        # Guardar el PDF en un archivo temporal
                                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                                            pdf_path = tmp_file.name
                                            pdf.output(pdf_path)
                                        
                                        # Abrir y leer el archivo para la descarga
                                        with open(pdf_path, "rb") as f:
                                            pdf_data = f.read()
                                        
                                        # Botón de descarga
                                        st.download_button(
                                            label="⬇️ Descargar Cotización PDF",
                                            data=pdf_data,
                                            file_name=f"cotizacion_{cotization_data['numero_cotizacion']}.pdf",
                                            mime="application/pdf",
                                            key="download_pdf_main"
                                        )
                            
                            # Preview de la cotización
                            with st.expander("📋 Vista previa de la cotización"):
                                st.write(f"**Número de cotización:** {cotization_data['numero_cotizacion']}")
                                st.write(f"**Fecha:** {cotization_data['fecha']}")
                                st.write(f"**Cliente:** {cotization_data['cliente']}")
                                
                                if cotization_data['items']:
                                    st.write("**Productos:**")
                                    for item in cotization_data['items']:
                                        st.write(f"- {item['referencia']}: {item['descripcion']} - {item['cantidad']} UND - ${item['precio_unitario']:,}")
                                    
                                    st.write(f"**Subtotal:** ${cotization_data['subtotal']:,}")
                                    st.write(f"**Impuestos:** ${cotization_data['impuestos']:,}")
                                    st.write(f"**Total:** ${cotization_data['total']:,}")
                        else:
                            st.warning("⚠️ Se detectó información de cotización pero no se pudieron extraer productos válidos.")
                            st.write("Texto analizado:", response_text[:200] + "...")
                else:
                    st.info("ℹ️ No se detectó información de cotización en esta respuesta.")
                
                # Generar audio (siempre)
                audio_html = None
                with st.spinner("Generando audio..."):
                    audio_html = text_to_speech(response_text)
                    st.markdown(audio_html, unsafe_allow_html=True)
                
                # Añadir respuesta al historial con el audio
                message_data = {"role": "assistant", "content": response_text}
                if audio_html:
                    message_data["audio_html"] = audio_html
                st.session_state.messages.append(message_data)

# Pie de página
st.markdown("<div class='footer'>Asistente Digital © 2025</div>", unsafe_allow_html=True)
