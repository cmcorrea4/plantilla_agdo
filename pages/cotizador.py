import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

class GeneradorCotizacionesMadera:
    def __init__(self):
        self.productos = None
        self.ubicaciones = {
            'caldas': {
                'sin_iva': 'PRECIO CALDAS',
                'con_iva': 'PRECIO CALDAS CON IVA'
            },
            'chagualo': {
                'sin_iva': 'PRECIO CHAGUALO, GIRARDOTA, SAN CRISTOBAL',
                'con_iva': 'PRECIO CHAGUALO, GIRARDOTA, SAN CRISTOBAL IVA INCLUIDO'
            }
        }
        
    def cargar_excel(self, archivo_excel):
        """Cargar productos desde archivo Excel"""
        try:
            # Leer el archivo Excel
            df = pd.read_excel(archivo_excel, engine='openpyxl')
            
            # Limpiar nombres de columnas
            df.columns = df.columns.str.strip()
            
            # Filtrar filas con referencia y descripción válidas
            df = df.dropna(subset=['Referencia', 'DESCRIPCION'])
            df = df[df['Referencia'].str.strip() != '']
            df = df[df['DESCRIPCION'].str.strip() != '']
            
            # Limpiar precios (convertir a numérico)
            columnas_precio = [
                'PRECIO CALDAS',
                'PRECIO CALDAS CON IVA',
                'PRECIO CHAGUALO, GIRARDOTA, SAN CRISTOBAL',
                'PRECIO CHAGUALO, GIRARDOTA, SAN CRISTOBAL IVA INCLUIDO'
            ]
            
            for col in columnas_precio:
                if col in df.columns:
                    df[col] = df[col].apply(self.limpiar_precio)
            
            self.productos = df
            
            return {
                'exito': True,
                'total_productos': len(df),
                'mensaje': f'Excel cargado exitosamente con {len(df)} productos',
                'columnas': list(df.columns)
            }
        except Exception as e:
            return {
                'exito': False,
                'error': str(e),
                'mensaje': 'Error al cargar el archivo Excel'
            }
    
    def limpiar_precio(self, precio):
        """Limpiar y convertir precio a número"""
        if pd.isna(precio):
            return 0
        
        # Convertir a string y limpiar
        precio_str = str(precio)
        # Remover caracteres no numéricos excepto punto y coma
        precio_limpio = re.sub(r'[^\d.,]', '', precio_str)
        # Remover comas (separadores de miles)
        precio_limpio = precio_limpio.replace(',', '')
        
        try:
            return float(precio_limpio)
        except:
            return 0
    
    def formatear_precio(self, precio):
        """Formatear precio como moneda colombiana"""
        if pd.isna(precio) or precio == 0:
            return "$ 0"
        return f"$ {precio:,.0f}".replace(',', '.')
    
    def buscar_productos(self, termino_busqueda, ubicacion='caldas', incluir_iva=True, limite=10):
        """Buscar productos por descripción"""
        if self.productos is None or self.productos.empty:
            return {
                'exito': False,
                'mensaje': 'No hay productos cargados'
            }
        
        # Filtrar productos que contengan el término de búsqueda
        mask = self.productos['DESCRIPCION'].str.contains(
            termino_busqueda, 
            case=False, 
            na=False
        )
        resultados = self.productos[mask].head(limite)
        
        if resultados.empty:
            return {
                'exito': False,
                'mensaje': f'No se encontraron productos para: {termino_busqueda}'
            }
        
        # Formatear resultados
        productos_formateados = []
        for _, producto in resultados.iterrows():
            producto_formateado = self.formatear_producto(producto, ubicacion, incluir_iva)
            productos_formateados.append(producto_formateado)
        
        return {
            'exito': True,
            'resultados': productos_formateados,
            'total': len(productos_formateados)
        }
    
    def formatear_producto(self, producto, ubicacion='caldas', incluir_iva=True):
        """Formatear un producto con toda la información"""
        ubicacion_config = self.ubicaciones[ubicacion]
        columna_precio = ubicacion_config['con_iva'] if incluir_iva else ubicacion_config['sin_iva']
        
        precio = producto.get(columna_precio, 0)
        
        return {
            'referencia': producto.get('Referencia', ''),
            'descripcion': producto.get('DESCRIPCION', ''),
            'acabado': producto.get('ACABADO DE LA MADERA', ''),
            'uso': producto.get('USO', ''),
            'garantia': producto.get('GARANTIA', ''),
            'ubicacion': ubicacion,
            'incluir_iva': incluir_iva,
            'precio': self.formatear_precio(precio),
            'precio_numerico': precio,
            'precios': {
                'caldas_sin_iva': producto.get('PRECIO CALDAS', 0),
                'caldas_con_iva': producto.get('PRECIO CALDAS CON IVA', 0),
                'chagualo_sin_iva': producto.get('PRECIO CHAGUALO, GIRARDOTA, SAN CRISTOBAL', 0),
                'chagualo_con_iva': producto.get('PRECIO CHAGUALO, GIRARDOTA, SAN CRISTOBAL IVA INCLUIDO', 0)
            }
        }
    
    def generar_cotizacion(self, productos_seleccionados, datos_cliente, opciones=None):
        """Generar cotización completa"""
        if opciones is None:
            opciones = {}
            
        ubicacion = opciones.get('ubicacion', 'caldas')
        incluir_iva = opciones.get('incluir_iva', True)
        descuento_porcentaje = opciones.get('descuento', 0)
        validez_dias = opciones.get('validez_dias', 30)
        
        subtotal = 0
        items_cotizacion = []
        
        for item in productos_seleccionados:
            cantidad = item.get('cantidad', 1)
            precio_unitario = item['precio_numerico']
            total_item = cantidad * precio_unitario
            subtotal += total_item
            
            items_cotizacion.append({
                'referencia': item['referencia'],
                'descripcion': item['descripcion'],
                'acabado': item['acabado'],
                'uso': item['uso'],
                'garantia': item['garantia'],
                'cantidad': cantidad,
                'precio_unitario': self.formatear_precio(precio_unitario),
                'total': self.formatear_precio(total_item),
                'precio_unitario_numerico': precio_unitario,
                'total_numerico': total_item
            })
        
        # Calcular totales
        valor_descuento = subtotal * (descuento_porcentaje / 100)
        total = subtotal - valor_descuento
        
        fecha_actual = datetime.now()
        fecha_vencimiento = fecha_actual + timedelta(days=validez_dias)
        
        ubicacion_texto = 'Caldas' if ubicacion == 'caldas' else 'Chagualo, Girardota, San Cristóbal'
        
        return {
            'numero_cotizacion': self.generar_numero_cotizacion(),
            'fecha': fecha_actual.strftime('%d/%m/%Y'),
            'fecha_vencimiento': fecha_vencimiento.strftime('%d/%m/%Y'),
            'cliente': datos_cliente,
            'ubicacion': ubicacion_texto,
            'incluye_iva': incluir_iva,
            'items': items_cotizacion,
            'resumen': {
                'subtotal': self.formatear_precio(subtotal),
                'descuento': f'{descuento_porcentaje}% - {self.formatear_precio(valor_descuento)}' if descuento_porcentaje > 0 else None,
                'total': self.formatear_precio(total),
                'subtotal_numerico': subtotal,
                'descuento_numerico': valor_descuento,
                'total_numerico': total
            },
            'condiciones': self.obtener_condiciones_generales()
        }
    
    def generar_numero_cotizacion(self):
        """Generar número único de cotización"""
        fecha = datetime.now()
        timestamp = str(int(fecha.timestamp()))[-6:]
        return f"COT-MAD-{fecha.strftime('%Y%m')}-{timestamp}"
    
    def generar_pdf_cotizacion(self, cotizacion, datos_empresa=None):
        """Generar PDF de la cotización con formato profesional"""
        buffer = BytesIO()
        
        # Configuración de la página con márgenes equilibrados
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.black,
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )
        
        # Datos de empresa por defecto
        if datos_empresa is None:
            datos_empresa = {
                'nombre': 'Tu Empresa de Productos de Madera',
                'nit': '900.XXX.XXX-X',
                'direccion': 'Calle XX # XX - XX',
                'telefono': 'XXX-XXXX',
                'ciudad': 'Medellín',
                'email': 'ventas@tuempresa.com'
            }
        
        # Contenido del PDF
        story = []
        
        # HEADER DE LA EMPRESA
        header_data = [
            [
                Paragraph(f"""
                <b>{datos_empresa['nombre']}</b><br/>
                NIT: {datos_empresa['nit']}<br/>
                {datos_empresa['direccion']}<br/>
                Tel: {datos_empresa['telefono']}<br/>
                {datos_empresa['ciudad']}
                """, header_style),
                Paragraph(f"""
                <b>COTIZACIÓN</b><br/>
                No. {cotizacion['numero_cotizacion']}
                """, ParagraphStyle(
                    'HeaderRight',
                    parent=styles['Normal'],
                    fontSize=12,
                    textColor=colors.black,
                    alignment=TA_CENTER,
                    fontName='Helvetica-Bold'
                ))
            ]
        ]
        
        header_table = Table(header_data, colWidths=[4.2*inch, 2.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (1, 0), (1, 0), 1.5, colors.black),
            ('INNERGRID', (1, 0), (1, 0), 1.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 20))
        
        # TÍTULO
        story.append(Paragraph("COTIZACIÓN DE VENTAS", title_style))
        story.append(Spacer(1, 15))
        
        # INFORMACIÓN DEL CLIENTE Y COTIZACIÓN
        cliente_data = [
            [
                Paragraph(f"""
                <b>Cliente</b><br/>
                <b>Nombre:</b> {cotizacion['cliente']['nombre']}<br/>
                <b>Empresa:</b> {cotizacion['cliente'].get('empresa', 'N/A')}<br/>
                <b>Teléfono:</b> {cotizacion['cliente'].get('telefono', 'N/A')}<br/>
                <b>Email:</b> {cotizacion['cliente'].get('email', 'N/A')}
                """, header_style),
                Paragraph(f"""
                <b>Fecha:</b> {cotizacion['fecha']}<br/>
                <b>Vencimiento:</b> {cotizacion['fecha_vencimiento']}<br/>
                <b>Ubicación:</b> {cotizacion['ubicacion']}<br/>
                <b>IVA incluido:</b> {'Sí' if cotizacion['incluye_iva'] else 'No'}
                """, header_style)
            ]
        ]
        
        cliente_table = Table(cliente_data, colWidths=[3.3*inch, 3.3*inch])
        cliente_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(cliente_table)
        story.append(Spacer(1, 20))
        
        # TABLA DE PRODUCTOS
        # Headers - mantenemos los 5 campos pero con mejor distribución
        productos_headers = [
            'Referencia', 'Descripción', 'Acabado', 'Cantidad', 'Precio Unitario', 'Total'
        ]
        
        # Datos de productos
        productos_data = [productos_headers]
        
        for item in cotizacion['items']:
            productos_data.append([
                item['referencia'],
                # Reducir caracteres para que quepa mejor
                item['descripcion'][:30] if len(item['descripcion']) > 30 else item['descripcion'],
                # Acabado más corto
                item['acabado'][:15] if len(item['acabado']) > 15 else item['acabado'],
                str(item['cantidad']),
                item['precio_unitario'],
                item['total']
            ])
        
        # Crear tabla de productos con anchos más conservadores
        productos_table = Table(
            productos_data, 
            colWidths=[1.1*inch, 2.5*inch, 1.1*inch, 0.6*inch, 1*inch, 1*inch]
        )
        
        productos_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),  # Fuente más pequeña
            
            # Datos - fuente más pequeña
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),  # Fuente más pequeña
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Referencia centrada
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Descripción a la izquierda
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Acabado a la izquierda
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Cantidad centrada
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),  # Precios a la derecha
            
            # Bordes
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            
            # Padding reducido para ahorrar espacio
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            
            # Ajuste vertical para mejor distribución del texto
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(productos_table)
        story.append(Spacer(1, 20))
        
        # TOTALES - usar más ancho de página
        totales_data = [
            ['', 'Valor Subtotal:', cotizacion['resumen']['subtotal']],
        ]
        
        if cotizacion['resumen']['descuento']:
            totales_data.append(['', 'Descuento:', cotizacion['resumen']['descuento']])
        
        totales_data.append(['', 'Total:', cotizacion['resumen']['total']])
        
        totales_table = Table(totales_data, colWidths=[3.5*inch, 1.5*inch, 1.5*inch])
        totales_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (1, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (-1, -1), 9),  # Fuente más pequeña
            ('BOX', (1, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (1, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (1, -1), (-1, -1), colors.lightgrey),  # Destacar total
            ('LEFTPADDING', (1, 0), (-1, -1), 6),  # Padding reducido
            ('RIGHTPADDING', (1, 0), (-1, -1), 6),
            ('TOPPADDING', (1, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (1, 0), (-1, -1), 6),
        ]))
        
        story.append(totales_table)
        story.append(Spacer(1, 30))
        
        # CONDICIONES GENERALES
        if cotizacion.get('condiciones'):
            story.append(Paragraph("<b>Condiciones Generales:</b>", 
                                 ParagraphStyle('ConditionsTitle', parent=styles['Normal'], 
                                              fontSize=10, fontName='Helvetica-Bold')))
            story.append(Spacer(1, 8))
            
            for condicion in cotizacion['condiciones']:
                story.append(Paragraph(f"• {condicion}", 
                                     ParagraphStyle('Condition', parent=styles['Normal'], 
                                                  fontSize=9, leftIndent=10)))
            
            story.append(Spacer(1, 20))
        
        # FIRMAS
        firmas_data = [
            ['Elaborado', 'Aprobado', 'Recibido'],
            ['', '', ''],
            ['', '', ''],
            ['_________________', '_________________', '_________________']
        ]
        
        firmas_table = Table(firmas_data, colWidths=[2.2*inch, 2.2*inch, 2.2*inch])
        firmas_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),  # Fuente más pequeña
            ('TOPPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        story.append(firmas_table)
        
        # Generar PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def obtener_condiciones_generales(self):
        """Condiciones generales de la cotización"""
        return [
            'Los precios están sujetos a cambios sin previo aviso',
            'La garantía aplica según las especificaciones del producto',
            'Tiempos de entrega sujetos a disponibilidad',
            'Se requiere 50% de anticipo para procesar el pedido'
        ]
    
    def obtener_estadisticas(self):
        """Obtener estadísticas del catálogo"""
        if self.productos is None or self.productos.empty:
            return None
        
        stats = {
            'total_productos': len(self.productos),
            'acabados_disponibles': self.productos['ACABADO DE LA MADERA'].dropna().unique().tolist(),
            'usos_disponibles': self.productos['USO'].dropna().unique().tolist()
        }
        
        # Estadísticas de precios por ubicación
        for ubicacion, config in self.ubicaciones.items():
            precios_sin_iva = self.productos[config['sin_iva']].dropna()
            precios_con_iva = self.productos[config['con_iva']].dropna()
            
            if not precios_sin_iva.empty:
                stats[f'precios_{ubicacion}'] = {
                    'min_sin_iva': precios_sin_iva.min(),
                    'max_sin_iva': precios_sin_iva.max(),
                    'promedio_sin_iva': precios_sin_iva.mean(),
                    'min_con_iva': precios_con_iva.min(),
                    'max_con_iva': precios_con_iva.max(),
                    'promedio_con_iva': precios_con_iva.mean()
                }
        
        return stats

def main():
    # Configuración de la página
    st.set_page_config(
        page_title="Cotizador de Productos de Madera",
        page_icon="🪵",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Título principal
    st.title("🪵 Cotizador de Productos de Madera")
    st.markdown("---")
    
    # Inicializar el generador
    if 'generador' not in st.session_state:
        st.session_state.generador = GeneradorCotizacionesMadera()
    
    # Sidebar para configuración
    st.sidebar.header("⚙️ Configuración")
    
    # Cargar archivo
    st.sidebar.subheader("📁 Cargar Catálogo")
    archivo_excel = st.sidebar.file_uploader(
        "Selecciona tu archivo Excel:",
        type=['xlsx', 'xls'],
        help="Sube tu archivo 'GUION PARA IA LISTADO.xlsx'"
    )
    
    if archivo_excel is not None:
        with st.sidebar:
            with st.spinner('Cargando catálogo...'):
                resultado = st.session_state.generador.cargar_excel(archivo_excel)
                
                if resultado['exito']:
                    st.success(f"✅ {resultado['mensaje']}")
                    st.session_state.catalogo_cargado = True
                else:
                    st.error(f"❌ {resultado['mensaje']}")
                    st.session_state.catalogo_cargado = False
    else:
        st.session_state.catalogo_cargado = False
    
    # Verificar si el catálogo está cargado
    if not st.session_state.get('catalogo_cargado', False):
        st.warning("📋 Por favor, carga tu archivo Excel en la barra lateral para comenzar.")
        st.stop()
    
    # Configuración de búsqueda
    st.sidebar.subheader("🔍 Configuración de Búsqueda")
    ubicacion = st.sidebar.selectbox(
        "Ubicación:",
        options=['caldas', 'chagualo'],
        format_func=lambda x: 'Caldas' if x == 'caldas' else 'Chagualo, Girardota, San Cristóbal'
    )
    
    incluir_iva = st.sidebar.checkbox("Incluir IVA", value=True)
    
    # Área principal - Búsqueda
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🔍 Buscar Productos")
        termino_busqueda = st.text_input(
            "Describe el producto que buscas:",
            placeholder="Ej: mesa comedor, silla oficina, escritorio..."
        )
    
    with col2:
        st.subheader("📊 Estadísticas")
        if st.button("Ver Estadísticas del Catálogo"):
            stats = st.session_state.generador.obtener_estadisticas()
            if stats:
                st.metric("Total Productos", stats['total_productos'])
                with st.expander("Ver más detalles"):
                    st.write("**Acabados disponibles:**")
                    st.write(", ".join(stats['acabados_disponibles'][:10]))
                    st.write("**Usos disponibles:**")
                    st.write(", ".join(stats['usos_disponibles'][:10]))
    
    # Realizar búsqueda
    if termino_busqueda:
        with st.spinner('Buscando productos...'):
            resultados = st.session_state.generador.buscar_productos(
                termino_busqueda, 
                ubicacion=ubicacion, 
                incluir_iva=incluir_iva,
                limite=20
            )
        
        if resultados['exito']:
            st.subheader(f"📦 Productos encontrados ({resultados['total']})")
            
            # Mostrar productos en tarjetas
            for i, producto in enumerate(resultados['resultados']):
                with st.expander(f"🪵 {producto['descripcion']} - {producto['precio']}", expanded=i<3):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Referencia:** {producto['referencia']}")
                        st.write(f"**Acabado:** {producto['acabado']}")
                        st.write(f"**Uso:** {producto['uso']}")
                    
                    with col2:
                        st.write(f"**Garantía:** {producto['garantia']}")
                        st.write(f"**Ubicación:** {producto['ubicacion'].title()}")
                        st.write(f"**Precio:** {producto['precio']}")
                    
                    with col3:
                        # Comparación de precios
                        st.write("**Comparación de precios:**")
                        st.write(f"Caldas s/IVA: {st.session_state.generador.formatear_precio(producto['precios']['caldas_sin_iva'])}")
                        st.write(f"Caldas c/IVA: {st.session_state.generador.formatear_precio(producto['precios']['caldas_con_iva'])}")
                        st.write(f"Chagualo s/IVA: {st.session_state.generador.formatear_precio(producto['precios']['chagualo_sin_iva'])}")
                        st.write(f"Chagualo c/IVA: {st.session_state.generador.formatear_precio(producto['precios']['chagualo_con_iva'])}")
                    
                    # Botón para agregar a cotización
                    cantidad = st.number_input(
                        f"Cantidad para {producto['referencia']}:",
                        min_value=1,
                        value=1,
                        key=f"cantidad_{i}"
                    )
                    
                    if st.button(f"➕ Agregar a Cotización", key=f"agregar_{i}"):
                        if 'productos_cotizacion' not in st.session_state:
                            st.session_state.productos_cotizacion = []
                        
                        producto_con_cantidad = producto.copy()
                        producto_con_cantidad['cantidad'] = cantidad
                        st.session_state.productos_cotizacion.append(producto_con_cantidad)
                        st.success(f"✅ {producto['descripcion']} agregado a la cotización")
        else:
            st.warning(f"⚠️ {resultados['mensaje']}")
    
    # Sección de cotización
    if 'productos_cotizacion' in st.session_state and st.session_state.productos_cotizacion:
        st.markdown("---")
        st.subheader("📋 Cotización en Progreso")
        
        # Mostrar productos seleccionados
        total_items = 0
        for i, producto in enumerate(st.session_state.productos_cotizacion):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.write(f"**{producto['descripcion']}**")
                st.write(f"Ref: {producto['referencia']}")
            
            with col2:
                st.write(f"Cantidad: {producto['cantidad']}")
            
            with col3:
                st.write(f"Precio: {producto['precio']}")
            
            with col4:
                if st.button("🗑️", key=f"eliminar_{i}"):
                    st.session_state.productos_cotizacion.pop(i)
                    st.experimental_rerun()
            
            total_items += producto['cantidad']
        
        st.write(f"**Total items:** {total_items}")
        
        # Formulario de cliente y opciones
        st.subheader("👤 Datos del Cliente")
        
        col1, col2 = st.columns(2)
        
        with col1:
            nombre_cliente = st.text_input("Nombre completo:")
            empresa_cliente = st.text_input("Empresa:")
            email_cliente = st.text_input("Email:")
        
        with col2:
            telefono_cliente = st.text_input("Teléfono:")
            descuento = st.number_input("Descuento (%):", min_value=0, max_value=50, value=0)
            validez_dias = st.number_input("Validez (días):", min_value=1, value=30)
        
        # Generar cotización
        if st.button("📄 Generar Cotización", type="primary"):
            if nombre_cliente:
                datos_cliente = {
                    'nombre': nombre_cliente,
                    'empresa': empresa_cliente,
                    'email': email_cliente,
                    'telefono': telefono_cliente
                }
                
                opciones = {
                    'ubicacion': ubicacion,
                    'incluir_iva': incluir_iva,
                    'descuento': descuento,
                    'validez_dias': validez_dias
                }
                
                cotizacion = st.session_state.generador.generar_cotizacion(
                    st.session_state.productos_cotizacion,
                    datos_cliente,
                    opciones
                )
                
                # Mostrar cotización
                st.success("✅ Cotización generada exitosamente!")
                
                # Guardar cotización en session_state para descargar PDF
                st.session_state.ultima_cotizacion = cotizacion
                
                # Generar PDF automáticamente al crear cotización
                try:
                    datos_empresa_pdf = None
                    if any(key.startswith('empresa_') for key in st.session_state.keys()):
                        datos_empresa_pdf = {
                            'nombre': st.session_state.get('empresa_nombre', 'Tu Empresa de Productos de Madera'),
                            'nit': st.session_state.get('empresa_nit', '900.XXX.XXX-X'),
                            'direccion': st.session_state.get('empresa_direccion', 'Calle XX # XX - XX'),
                            'telefono': st.session_state.get('empresa_telefono', 'XXX-XXXX'),
                            'ciudad': st.session_state.get('empresa_ciudad', 'Medellín'),
                            'email': st.session_state.get('empresa_email', 'ventas@tuempresa.com')
                        }
                    
                    pdf_buffer = st.session_state.generador.generar_pdf_cotizacion(cotizacion, datos_empresa_pdf)
                    st.session_state.pdf_generado = pdf_buffer.getvalue()
                    st.session_state.nombre_archivo_pdf = f"Cotizacion_{cotizacion['numero_cotizacion']}.pdf"
                except Exception as e:
                    st.error(f"Error al generar PDF: {str(e)}")
                    st.session_state.pdf_generado = None
                
                # Botones de acción
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Botón de descarga directo
                    if st.session_state.get('pdf_generado') is not None:
                        st.download_button(
                            label="📄 Descargar PDF",
                            data=st.session_state.pdf_generado,
                            file_name=st.session_state.nombre_archivo_pdf,
                            mime="application/pdf",
                            type="primary"
                        )
                    else:
                        st.error("No se pudo generar el PDF")
                
                with col2:
                    if st.button("🗑️ Nueva Cotización"):
                        st.session_state.productos_cotizacion = []
                        if 'pdf_generado' in st.session_state:
                            del st.session_state.pdf_generado
                        if 'ultima_cotizacion' in st.session_state:
                            del st.session_state.ultima_cotizacion
                        st.experimental_rerun()
                
                with col3:
                    # Configurar datos de empresa para PDF
                    if st.button("⚙️ Configurar Empresa"):
                        st.session_state.mostrar_config_empresa = True
                
                # Configuración de empresa (modal)
                if st.session_state.get('mostrar_config_empresa', False):
                    st.markdown("---")
                    st.subheader("🏢 Configuración de Empresa para PDF")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nombre_empresa = st.text_input("Nombre de la empresa:", 
                                                     value=st.session_state.get('empresa_nombre', 'Tu Empresa de Productos de Madera'))
                        nit_empresa = st.text_input("NIT:", 
                                                   value=st.session_state.get('empresa_nit', '900.XXX.XXX-X'))
                        direccion_empresa = st.text_input("Dirección:", 
                                                         value=st.session_state.get('empresa_direccion', 'Calle XX # XX - XX'))
                    
                    with col2:
                        telefono_empresa = st.text_input("Teléfono:", 
                                                       value=st.session_state.get('empresa_telefono', 'XXX-XXXX'))
                        ciudad_empresa = st.text_input("Ciudad:", 
                                                     value=st.session_state.get('empresa_ciudad', 'Medellín'))
                        email_empresa = st.text_input("Email:", 
                                                    value=st.session_state.get('empresa_email', 'ventas@tuempresa.com'))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("💾 Guardar Configuración"):
                            st.session_state.empresa_nombre = nombre_empresa
                            st.session_state.empresa_nit = nit_empresa
                            st.session_state.empresa_direccion = direccion_empresa
                            st.session_state.empresa_telefono = telefono_empresa
                            st.session_state.empresa_ciudad = ciudad_empresa
                            st.session_state.empresa_email = email_empresa
                            st.session_state.mostrar_config_empresa = False
                            
                            # Regenerar PDF con nuevos datos de empresa
                            if 'ultima_cotizacion' in st.session_state:
                                try:
                                    datos_empresa_pdf = {
                                        'nombre': nombre_empresa,
                                        'nit': nit_empresa,
                                        'direccion': direccion_empresa,
                                        'telefono': telefono_empresa,
                                        'ciudad': ciudad_empresa,
                                        'email': email_empresa
                                    }
                                    pdf_buffer = st.session_state.generador.generar_pdf_cotizacion(
                                        st.session_state.ultima_cotizacion, 
                                        datos_empresa_pdf
                                    )
                                    st.session_state.pdf_generado = pdf_buffer.getvalue()
                                except:
                                    pass
                            
                            st.success("✅ Configuración guardada")
                            st.experimental_rerun()
                    
                    with col2:
                        if st.button("❌ Cancelar"):
                            st.session_state.mostrar_config_empresa = False
                            st.experimental_rerun()
                    
                    st.markdown("---")
                
                # Información de la cotización
                st.subheader(f"📄 Cotización {cotizacion['numero_cotizacion']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Fecha:** {cotizacion['fecha']}")
                    st.write(f"**Vencimiento:** {cotizacion['fecha_vencimiento']}")
                
                with col2:
                    st.write(f"**Cliente:** {cotizacion['cliente']['nombre']}")
                    st.write(f"**Empresa:** {cotizacion['cliente']['empresa']}")
                
                with col3:
                    st.write(f"**Ubicación:** {cotizacion['ubicacion']}")
                    st.write(f"**IVA incluido:** {'Sí' if cotizacion['incluye_iva'] else 'No'}")
                
                # Detalles de productos
                st.subheader("📦 Productos")
                df_cotizacion = pd.DataFrame(cotizacion['items'])
                st.dataframe(df_cotizacion[['referencia', 'descripcion', 'cantidad', 'precio_unitario', 'total']], use_container_width=True)
                
                # Resumen financiero
                st.subheader("💰 Resumen")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Subtotal", cotizacion['resumen']['subtotal'])
                
                with col2:
                    if cotizacion['resumen']['descuento']:
                        st.metric("Descuento", cotizacion['resumen']['descuento'])
                
                with col3:
                    st.metric("TOTAL", cotizacion['resumen']['total'])
                
                # Condiciones
                with st.expander("📋 Condiciones Generales"):
                    for condicion in cotizacion['condiciones']:
                        st.write(f"• {condicion}")
                
                # Botón para limpiar cotización
                if st.button("🗑️ Limpiar Cotización", key="limpiar_final"):
                    st.session_state.productos_cotizacion = []
                    if 'pdf_generado' in st.session_state:
                        del st.session_state.pdf_generado
                    if 'ultima_cotizacion' in st.session_state:
                        del st.session_state.ultima_cotizacion
                    st.experimental_rerun()
            else:
                st.error("❌ Por favor, ingresa al menos el nombre del cliente.")

if __name__ == "__main__":
    main()
