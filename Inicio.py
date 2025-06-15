import streamlit as st
import requests
import json
import time
import tempfile
import re
from datetime import datetime
from fpdf import FPDF

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

# Función mejorada para extraer datos de cotización de la respuesta del LLM
def extract_cotization_data(response_text):
    """Extrae datos de productos de la respuesta del LLM - Versión mejorada"""
    cotization_data = {
        'items': [],
        'subtotal': 0,
        'impuestos': 0,
        'total': 0,
        'cliente': 'CONSUMIDOR FINAL',
        'fecha': datetime.now().strftime('%d/%m/%Y'),
        'numero_cotizacion': f"CCV-{int(time.time())}"[-8:]
    }
    
    # Normalizar texto
    text_lower = response_text.lower()
    
    # Patrones más amplios para encontrar precios
    price_patterns = [
        r'(\d{1,3}(?:[.,]\d{3})+)\s*cop',  # 51,792 COP
        r'\$\s*(\d{1,3}(?:[.,]\d{3})+)',   # $51,792
        r'precio.*?(\d{1,3}(?:[.,]\d{3})+)',  # precio ... 51,792
        r'cuesta.*?(\d{1,3}(?:[.,]\d{3})+)',  # cuesta ... 51,792
        r'(\d{1,3}(?:[.,]\d{3})+)\s*pesos',   # 51,792 pesos
        r'es\s+de\s+(\d{1,3}(?:[.,]\d{3})+)', # es de 51,792
        r'total.*?(\d{1,3}(?:[.,]\d{3})+)',   # total ... 155,376
        r'subtotal.*?(\d{1,3}(?:[.,]\d{3})+)', # subtotal ... 155,376
        r'vale.*?(\d{1,3}(?:[.,]\d{3})+)',    # vale ... 51,792
        r'por\s+(\d{1,3}(?:[.,]\d{3})+)',     # por 51,792
        # Patrones para números sin separadores pero grandes
        r'\b(\d{5,7})\b',  # 51792, 155376
    ]
    
    # Patrones para cantidades
    quantity_patterns = [
        r'para\s+(\d+)\s+(?:alfardas|unidades|productos|items)',
        r'(\d+)\s+(?:alfardas|unidades|uds?)\b',
        r'cantidad.*?(\d+)',
        r'(\d+)\s*x\s*',  # 3 x
        r'x\s*(\d+)',     # x 3
        r'(\d+)\s+(?:alfardas|pisos|paredes|tablas)',
    ]
    
    # Buscar precios
    precios_encontrados = []
    for pattern in price_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            # Limpiar el número
            precio_str = match.replace(',', '').replace('.', '')
            try:
                precio = int(precio_str)
                # Validar que sea un precio razonable
                if 1000 <= precio <= 50000000:
                    precios_encontrados.append(precio)
            except ValueError:
                continue
    
    # Buscar cantidades
    cantidades_encontradas = []
    for pattern in quantity_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            try:
                cantidad = int(match)
                if 1 <= cantidad <= 1000:
                    cantidades_encontradas.append(cantidad)
            except ValueError:
                continue
    
    # Determinar producto basándose en el texto
    descripcion = "PRODUCTO"
    referencia = "REF001"
    
    if 'alfarda' in text_lower:
        if '12x300' in text_lower or ('12' in text_lower and '300' in text_lower):
            descripcion = "ALFARDA TRATADA 12X300"
            referencia = "RA40012300"
        else:
            descripcion = "ALFARDA TRATADA"
            referencia = "RA001"
    elif 'piso' in text_lower and 'pared' in text_lower:
        if '10x1.7x100' in text_lower:
            descripcion = "PISO PARED 10X1.7X100M2 CEP"
            referencia = "PP10017100"
        else:
            descripcion = "PISO PARED"
            referencia = "PP001"
    elif any(word in text_lower for word in ['madera', 'tabla', 'listón', 'tablón']):
        descripcion = "MADERA TRATADA"
        referencia = "MT001"
    elif any(word in text_lower for word in ['viga', 'vigas']):
        descripcion = "VIGA TRATADA"
        referencia = "VT001"
    
    # Si encontramos al menos un precio, crear el item
    if precios_encontrados:
        # Usar el precio más relevante
        precios_ordenados = sorted(set(precios_encontrados))
        precio_unitario = precios_ordenados[0]  # El menor suele ser el unitario
        
        # Usar cantidad si se encontró, sino usar 1
        cantidad = cantidades_encontradas[0] if cantidades_encontradas else 1
        
        # Calcular total
        total_calculado = precio_unitario * cantidad
        
        # Si hay múltiples precios, verificar si alguno corresponde al total
        if len(precios_ordenados) > 1:
            for precio in precios_ordenados[1:]:
                # Si encontramos un precio que podría ser el total
                if abs(precio - total_calculado) <= total_calculado * 0.1:  # 10% tolerancia
                    total_calculado = precio
                    break
                elif precio > precio_unitario * cantidad:
                    # Podría ser el total, recalcular precio unitario
                    total_calculado = precio
                    if cantidad > 1:
                        precio_unitario = precio // cantidad
        
        item = {
            'referencia': referencia,
            'descripcion': descripcion,
            'cantidad': cantidad,
            'precio_unitario': precio_unitario,
            'impuestos': 0,
            'valor_total': total_calculado,
            'peso': 186
        }
        
        cotization_data['items'].append(item)
        cotization_data['subtotal'] = total_calculado
        cotization_data['impuestos'] = 0
        cotization_data['total'] = total_calculado
    
    return cotization_data

# Función para generar PDF de cotización
def generate_cotization_pdf(cotization_data):
    """Genera un PDF de cotización similar al formato de la imagen"""
    try:
        # Crear PDF con orientación vertical y márgenes ajustados
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=10)
        
        # Encabezado de la empresa - más compacto
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 6, "Construcciones Inmunizadas De Colombia", ln=True, align='C')
        pdf.set_font("Arial", size=8)
        pdf.cell(0, 4, "Nit: 900297110", ln=True, align='C')
        pdf.cell(0, 4, "Cra 58 64 10", ln=True, align='C')
        pdf.cell(0, 4, "Tel: 4075014 Fax:", ln=True, align='C')
        pdf.ln(3)
        
        # Título COTIZACIONES
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 6, "COTIZACIONES", ln=True, align='C')
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 5, f"No. {cotization_data['numero_cotizacion']}", ln=True, align='C')
        pdf.ln(2)
        
        # COTIZACIÓN DE VENTAS
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, "COTIZACION DE VENTAS", ln=True, align='C')
        pdf.ln(3)
        
        # Información del cliente y fecha en dos columnas
        y_start = pdf.get_y()
        
        # Cliente (lado izquierdo) - más compacto
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(35, 5, "Cliente", ln=True)
        pdf.set_font("Arial", size=7)
        pdf.cell(15, 4, "Nombre:", ln=False)
        pdf.cell(55, 4, cotization_data['cliente'], ln=True)
        pdf.cell(15, 4, "Dirección:", ln=False)
        pdf.cell(55, 4, "CR 58 64 10", ln=True)
        pdf.cell(15, 4, "Ciudad:", ln=False)
        pdf.cell(55, 4, "Medellín", ln=True)
        pdf.cell(15, 4, "Teléfono:", ln=False)
        pdf.cell(55, 4, "4075014", ln=True)
        
        # Información de fecha (lado derecho)
        pdf.set_xy(110, y_start)
        pdf.set_font("Arial", size=7)
        pdf.cell(15, 4, "Fecha:", ln=False)
        pdf.cell(25, 4, cotization_data['fecha'], ln=True)
        pdf.set_x(110)
        pdf.cell(15, 4, "No. pedido:", ln=False)
        pdf.cell(25, 4, "C01", ln=True)
        pdf.set_x(110)
        pdf.cell(15, 4, "Forma pago:", ln=False)
        pdf.cell(25, 4, "CONSTRUCCIONES", ln=True)
        pdf.set_x(110)
        pdf.cell(15, 4, "Vendedor:", ln=False)
        pdf.cell(25, 4, "CONSTRUCCIONES", ln=True)
        
        pdf.ln(6)
        
        # Tabla de productos - anchos optimizados para caber en la página
        pdf.set_font("Arial", 'B', 7)
        headers = ["Referencia", "Descripción", "U.M.", "Cant.", "Peso", "Precio unit.", "Impuestos", "Valor total"]
        widths = [22, 45, 12, 12, 12, 22, 18, 22]  # Total: 165 (cabe en 190)
        
        # Dibujar encabezados
        x_start = 15
        pdf.set_x(x_start)
        for i, header in enumerate(headers):
            pdf.cell(widths[i], 6, header, 1, 0, 'C')
        pdf.ln()
        
        # Datos de productos
        pdf.set_font("Arial", size=6)
        for item in cotization_data['items']:
            pdf.set_x(x_start)
            pdf.cell(widths[0], 6, item.get('referencia', ''), 1, 0, 'C')
            
            # Truncar descripción si es muy larga
            desc = item.get('descripcion', '')
            if len(desc) > 25:
                desc = desc[:22] + "..."
            pdf.cell(widths[1], 6, desc, 1, 0, 'L')
            
            pdf.cell(widths[2], 6, "UND", 1, 0, 'C')
            pdf.cell(widths[3], 6, str(item.get('cantidad', 0)), 1, 0, 'C')
            pdf.cell(widths[4], 6, str(item.get('peso', 0)), 1, 0, 'C')
            pdf.cell(widths[5], 6, f"${item.get('precio_unitario', 0):,}", 1, 0, 'R')
            pdf.cell(widths[6], 6, f"${item.get('impuestos', 0):,}", 1, 0, 'R')
            pdf.cell(widths[7], 6, f"${item.get('valor_total', 0):,}", 1, 0, 'R')
            pdf.ln()
        
        # Llenar filas vacías - menos filas para ahorrar espacio
        empty_rows = max(0, 8 - len(cotization_data['items']))
        for _ in range(empty_rows):
            pdf.set_x(x_start)
            for width in widths:
                pdf.cell(width, 6, "", 1, 0, 'C')
            pdf.ln()
        
        # Sección de notas y totales
        pdf.ln(3)
        y_notas = pdf.get_y()
        
        # Notas (lado izquierdo) - más pequeño
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(30, 6, "Notas", 1, 0, 'C')
        pdf.set_font("Arial", size=7)
        pdf.cell(60, 6, "", 1, 0, 'L')  # Celda vacía para notas
        
        # Totales (lado derecho) - compacto
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(25, 6, "Totales", 1, 0, 'C')
        pdf.cell(35, 6, "", 1, 1, 'L')
        
        # Fila de subtotal
        pdf.set_x(x_start)
        pdf.cell(90, 5, "", 0, 0)  # Espacio para notas
        pdf.set_font("Arial", size=7)
        pdf.cell(25, 5, "Valor Subtotal:", 1, 0, 'L')
        pdf.cell(35, 5, f"${cotization_data['subtotal']:,}", 1, 1, 'R')
        
        # Fila de impuestos
        pdf.set_x(x_start)
        pdf.cell(90, 5, "", 0, 0)  # Espacio para notas
        pdf.cell(25, 5, "Valor impuestos:", 1, 0, 'L')
        pdf.cell(35, 5, f"${cotization_data['impuestos']:,}", 1, 1, 'R')
        
        # Fila de total
        pdf.set_x(x_start)
        pdf.cell(90, 5, "", 0, 0)  # Espacio para notas
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(25, 6, "Total:", 1, 0, 'L')
        pdf.cell(35, 6, f"${cotization_data['total']:,}", 1, 1, 'R')
        
        # Firmas - más compacto
        pdf.ln(4)
        pdf.set_font("Arial", size=7)
        
        # Líneas para firmas
        y_firma = pdf.get_y()
        pdf.line(25, y_firma, 65, y_firma)  # Elaborado
        pdf.line(75, y_firma, 115, y_firma)  # Aprobado  
        pdf.line(125, y_firma, 165, y_firma)  # Recibido
        
        pdf.ln(2)
        pdf.cell(50, 4, "Elaborado", ln=False, align='C')
        pdf.cell(50, 4, "Aprobado", ln=False, align='C')
        pdf.cell(50, 4, "Recibido", ln=False, align='C')
        
        pdf.ln(6)
        pdf.set_font("Arial", size=6)
        pdf.cell(95, 3, "ORIGINAL REIMPRESO", ln=False, align='L')
        pdf.cell(95, 3, "Página 1 de 1", ln=True, align='R')
        
        return pdf
        
    except Exception as e:
        st.error(f"Error al generar PDF: {str(e)}")
        return None

# Función para detectar si se solicita generar cotización
def is_cotization_request(user_prompt):
    """Detecta si el usuario solicita generar una cotización"""
    text_lower = user_prompt.lower()
    
    # Detectar solicitudes de cotización con múltiples variantes
    cotization_requests = [
        'genera una cotización',
        'generar cotización',
        'hacer una cotización',
        'crear cotización',
        'cotización para',
        'genera cotización',
        'realiza una cotización',
        'realizar cotización',
        'elabora una cotización',
        'elaborar cotización',
        'prepara una cotización',
        'preparar cotización',
        'dame una cotización',
        'necesito una cotización',
        'quiero una cotización',
        'haz una cotización',
        'haga una cotización',
        'cotizar',
        'cotizame',
        'cotízame',
        'precio',
        'cuanto cuesta',
        'cuánto cuesta',
        'valor',
        'presupuesto'
    ]
    
    return any(request in text_lower for request in cotization_requests)

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

# Sección para generar PDF de cotización - SIEMPRE VISIBLE si hay datos
if st.session_state.last_cotization_data and st.session_state.last_cotization_data.get('items'):
    st.sidebar.markdown("### 📄 Última Cotización")
    
    # Mostrar información básica de la cotización
    cotization_info = st.session_state.last_cotization_data
    if cotization_info['items']:
        item = cotization_info['items'][0]  # Mostrar el primer item
        st.sidebar.write(f"**Producto:** {item['descripcion']}")
        st.sidebar.write(f"**Cantidad:** {item['cantidad']} UND")
        st.sidebar.write(f"**Total:** ${cotization_info['total']:,} COP")
        st.sidebar.write(f"**Número:** {cotization_info['numero_cotizacion']}")
    
    # Usar columnas para el botón
    col_pdf1, col_pdf2 = st.sidebar.columns([1, 1])
    
    with col_pdf1:
        if st.button("📄 Generar PDF", key="generate_pdf"):
            with st.spinner("Generando PDF..."):
                pdf = generate_cotization_pdf(st.session_state.last_cotization_data)
                if pdf:
                    # Guardar el PDF en un archivo temporal
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        pdf_path = tmp_file.name
                        pdf.output(pdf_path)
                    
                    # Abrir y leer el archivo para la descarga
                    with open(pdf_path, "rb") as f:
                        pdf_data = f.read()
                    
                    # Guardar PDF en session state para descarga
                    st.session_state.pdf_data = pdf_data
                    st.session_state.pdf_filename = f"cotizacion_{st.session_state.last_cotization_data['numero_cotizacion']}.pdf"
                    st.sidebar.success("PDF generado!")
                    st.rerun()
    
    # Mostrar botón de descarga si hay PDF generado
    if hasattr(st.session_state, 'pdf_data') and st.session_state.pdf_data:
        with col_pdf2:
            st.download_button(
                label="⬇️ Descargar",
                data=st.session_state.pdf_data,
                file_name=st.session_state.pdf_filename,
                mime="application/pdf",
                key="download_pdf"
            )

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

# Mostrar historial de conversación (sin audio)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

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
                
                # Verificar si el USUARIO solicitó una cotización
                if is_cotization_request(prompt):
                    with st.spinner("Procesando datos de cotización..."):
                        cotization_data = extract_cotization_data(response_text)
                        
                        # Verificar si se encontraron datos válidos
                        if cotization_data['items'] and len(cotization_data['items']) > 0:
                            st.session_state.last_cotization_data = cotization_data
                            
                            # Mostrar resumen de la cotización extraída
                            st.success("✅ Cotización generada exitosamente!")
                            
                            item = cotization_data['items'][0]
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Producto", item['descripcion'])
                            with col2:
                                st.metric("Cantidad", f"{item['cantidad']} UND")
                            with col3:
                                st.metric("Total", f"${cotization_data['total']:,} COP")
                            
                            st.info("📄 Puedes generar el PDF desde la barra lateral.")
                            
                            # Forzar actualización de la interfaz para mostrar el botón del PDF
                            time.sleep(0.5)  # Pequeña pausa para asegurar que se vean los mensajes
                            st.rerun()
                            
                        else:
                            # Si no se pudieron extraer datos, ofrecer opción manual
                            st.warning("⚠️ No se pudieron extraer automáticamente todos los datos de la cotización.")
                            
                            with st.expander("📝 Crear cotización manualmente"):
                                st.write("Basándome en la respuesta, puedes completar estos datos:")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    manual_descripcion = st.text_input("Descripción del producto:", value="PRODUCTO")
                                    manual_cantidad = st.number_input("Cantidad:", min_value=1, value=1)
                                    manual_precio = st.number_input("Precio unitario:", min_value=0, value=0)
                                
                                with col2:
                                    manual_referencia = st.text_input("Referencia:", value="REF001")
                                    manual_cliente = st.text_input("Cliente:", value="CONSUMIDOR FINAL")
                                
                                if st.button("Crear cotización manual"):
                                    if manual_precio > 0:
                                        manual_cotization = {
                                            'items': [{
                                                'referencia': manual_referencia,
                                                'descripcion': manual_descripcion,
                                                'cantidad': manual_cantidad,
                                                'precio_unitario': manual_precio,
                                                'impuestos': 0,
                                                'valor_total': manual_precio * manual_cantidad,
                                                'peso': 186
                                            }],
                                            'subtotal': manual_precio * manual_cantidad,
                                            'impuestos': 0,
                                            'total': manual_precio * manual_cantidad,
                                            'cliente': manual_cliente,
                                            'fecha': datetime.now().strftime('%d/%m/%Y'),
                                            'numero_cotizacion': f"CCV-{int(time.time())}"[-8:]
                                        }
                                        st.session_state.last_cotization_data = manual_cotization
                                        st.success("✅ Cotización manual creada!")
                                        st.rerun()
                                    else:
                                        st.error("Por favor ingresa un precio válido")
                
                # Añadir respuesta al historial
                st.session_state.messages.append({"role": "assistant", "content": response_text})

# Pie de página
st.markdown("<div class='footer'>Asistente Digital © 2025</div>", unsafe_allow_html=True)
