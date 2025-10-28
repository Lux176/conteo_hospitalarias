import streamlit as st
import pandas as pd
import numpy as np
from docx import Document
from docx.shared import Inches
import matplotlib.pyplot as plt
import plotly.express as px
import tempfile
import os
from datetime import datetime
from io import BytesIO
import unicodedata
import base64

# Configuración de la página
st.set_page_config(
    page_title="Analizador de Incidentes",
    page_icon="📊",
    layout="wide"
)

# --- FUNCIONES ADAPTADAS ---

def limpiar_texto(texto):
    """Limpia texto: minúsculas, sin acentos"""
    if not isinstance(texto, str):
        return texto
    texto_limpio = unicodedata.normalize('NFD', texto)\
                              .encode('ascii', 'ignore')\
                              .decode('utf-8')\
                              .lower()\
                              .strip()
    return texto_limpio

def parsear_fecha(fecha):
    """Parsea fechas en diferentes formatos"""
    if pd.isna(fecha): 
        return None
    if isinstance(fecha, (datetime, pd.Timestamp)): 
        return fecha
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y'):
        try: 
            return datetime.strptime(str(fecha).strip(), fmt)
        except: 
            continue
    return None

def generar_grafica_bar(conteo, titulo, filename):
    """Genera gráficas usando matplotlib"""
    df_plot = conteo.reset_index()
    df_plot.columns = ['Tipo de Incidente', 'Cantidad']
    
    # Crear gráfica con matplotlib
    plt.figure(figsize=(12, 6))
    colors = plt.cm.viridis(np.linspace(0, 1, len(df_plot)))
    bars = plt.bar(df_plot['Tipo de Incidente'], df_plot['Cantidad'], color=colors)
    
    plt.title(titulo, fontsize=14, fontweight='bold')
    plt.xlabel('Tipo de Incidente', fontweight='bold')
    plt.ylabel('Cantidad', fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    
    # Añadir valores en las barras
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    # Guardar imagen
    path = os.path.join(tempfile.gettempdir(), filename)
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return path

def generar_grafica_plotly(conteo, titulo):
    """Genera gráfica plotly para mostrar en Streamlit"""
    df_plot = conteo.reset_index()
    df_plot.columns = ['Tipo de Incidente', 'Cantidad']
    fig = px.bar(df_plot, x='Tipo de Incidente', y='Cantidad', title=titulo,
                 color='Cantidad', color_continuous_scale='Viridis')
    fig.update_layout(
        xaxis_tickangle=-45,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12)
    )
    fig.update_xaxes(title_text="Tipo de Incidente")
    fig.update_yaxes(title_text="Cantidad")
    return fig

def generar_reporte_word(conteos, traslados_info, imagenes):
    """Genera reporte en formato Word"""
    doc = Document()
    
    # Título principal
    title = doc.add_heading('Análisis de Incidentes', 0)
    title.alignment = 1  # Centrado
    
    # Fecha de generación
    doc.add_paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    doc.add_paragraph()
    
    doc.add_heading('Resumen de Conteos', level=1)
    for nombre, conteo in conteos.items():
        doc.add_heading(nombre, level=2)
        doc.add_paragraph(f"Total de incidentes: {conteo.sum()}")
        tabla = doc.add_table(rows=1, cols=2)
        tabla.style = 'Table Grid'
        hdr_cells = tabla.rows[0].cells
        hdr_cells[0].text = "Tipo de Incidente"
        hdr_cells[1].text = "Cantidad"
        for tipo, cantidad in conteo.items():
            row_cells = tabla.add_row().cells
            row_cells[0].text = str(tipo)
            row_cells[1].text = str(cantidad)

    if traslados_info:
        doc.add_heading('Resumen de Traslados', level=1)
        for k, v in traslados_info.items():
            doc.add_paragraph(f"{k}: {v}", style='List Bullet')

    doc.add_page_break()
    doc.add_heading('Gráficas', level=1)
    for titulo, path in imagenes.items():
        if os.path.exists(path):
            doc.add_heading(titulo, level=2)
            doc.add_picture(path, width=Inches(5.5))
            doc.add_paragraph()

    output_path = os.path.join(tempfile.gettempdir(), 'reporte_incidentes.docx')
    doc.save(output_path)
    return output_path

def generar_reporte_txt(conteos, traslados_info):
    """Genera reporte en formato de texto"""
    texto = ["Análisis de Incidentes\n"]
    texto.append("=" * 40)
    texto.append(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    texto.append("\nResumen de Conteos\n")
    
    for nombre, conteo in conteos.items():
        texto.append(f"\n{nombre.upper()}")
        texto.append("-" * len(nombre))
        texto.append(f"Total de incidentes: {conteo.sum()}")
        for tipo, cantidad in conteo.items():
            texto.append(f"  {tipo}: {cantidad}")
    
    if traslados_info:
        texto.append("\n\nResumen de Traslados")
        texto.append("-" * 20)
        for k, v in traslados_info.items():
            texto.append(f"{k}: {v}")
    
    contenido = "\n".join(texto)
    path_txt = os.path.join(tempfile.gettempdir(), "reporte_incidentes.txt")
    with open(path_txt, "w", encoding="utf-8") as f:
        f.write(contenido)
    return path_txt

def get_download_link(file_path, file_label):
    """Genera un enlace de descarga para el archivo"""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    file_name = os.path.basename(file_path)
    href = f'<a href="data:file/octet-stream;base64,{b64}" download="{file_name}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px; margin: 5px;">📥 {file_label}</a>'
    return href

# --- INTERFAZ PRINCIPAL ---

def main():
    st.title("📊 Analizador de Incidentes")
    st.markdown("---")
    
    # Carga de archivo
    st.header("1. Carga de Datos")
    uploaded_file = st.file_uploader("Sube tu archivo de datos (CSV o Excel)", type=['csv', 'xlsx'])
    
    if uploaded_file is not None:
        try:
            # Leer archivo
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            
            st.success(f"✅ Archivo cargado correctamente. Dimensiones: {df.shape[0]} filas × {df.shape[1]} columnas")
            
            # Mostrar vista previa
            with st.expander("📋 Vista previa de los datos"):
                st.dataframe(df.head(10))
            
            # Selección de columnas
            st.header("2. Configuración del Análisis")
            
            col1, col2 = st.columns(2)
            with col1:
                col_incidentes = st.selectbox(
                    "Selecciona la columna de INCIDENTES:",
                    options=df.columns,
                    index=None
                )
            
            with col2:
                col_traslado = st.selectbox(
                    "Selecciona la columna de TRASLADO A HOSPITAL:",
                    options=df.columns,
                    index=None
                )
            
            # Filtro por fechas
            st.subheader("🗓️ Filtro por Fechas (Opcional)")
            usar_fechas = st.checkbox("Activar filtro por fechas")
            
            fecha_inicio = None
            fecha_fin = None
            
            if usar_fechas and col_incidentes:
                col_fechas = st.selectbox(
                    "Selecciona la columna de FECHAS:",
                    options=df.columns,
                    index=None
                )
                
                if col_fechas:
                    col3, col4 = st.columns(2)
                    with col3:
                        fecha_inicio_str = st.text_input("Fecha de inicio (d/m/AAAA):", placeholder="01/01/2024")
                    with col4:
                        fecha_fin_str = st.text_input("Fecha de fin (d/m/AAAA):", placeholder="31/12/2024")
                    
                    if fecha_inicio_str and fecha_fin_str:
                        try:
                            fecha_inicio = datetime.strptime(fecha_inicio_str.strip(), '%d/%m/%Y')
                            fecha_fin = datetime.strptime(fecha_fin_str.strip(), '%d/%m/%Y')
                            
                            if fecha_inicio > fecha_fin:
                                st.error("❌ La fecha de inicio no puede ser mayor que la fecha de fin")
                            else:
                                st.info(f"📅 Rango seleccionado: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
                                
                        except ValueError:
                            st.error("❌ Formato de fecha incorrecto. Use el formato d/m/AAAA (ej: 01/01/2024)")
            
            # Análisis por Servicios Médicos
            st.subheader("🏥 Análisis por Servicios Médicos")
            incluir_sm = st.checkbox("Incluir análisis por Servicios Médicos")
            
            col_sm = None
            if incluir_sm:
                col_sm = st.selectbox(
                    "Selecciona la columna de SERVICIOS MÉDICOS:",
                    options=df.columns,
                    index=None
                )
            
            # Botón para generar análisis
            if col_incidentes and col_traslado:
                st.markdown("---")
                if st.button("🚀 Generar Reporte Completo", type="primary", use_container_width=True):
                    
                    with st.spinner("Procesando datos..."):
                        # Crear copia para no modificar el original
                        df_clean = df.copy()
                        
                        # Aplicar filtro de fechas si está activado
                        if usar_fechas and fecha_inicio and fecha_fin and col_fechas:
                            df_clean['fecha_parseada'] = df_clean[col_fechas].apply(parsear_fecha)
                            df_filtrado = df_clean.dropna(subset=['fecha_parseada'])
                            df_filtrado = df_filtrado[
                                (df_filtrado['fecha_parseada'] >= fecha_inicio) & 
                                (df_filtrado['fecha_parseada'] <= fecha_fin)
                            ]
                            st.info(f"📊 Datos filtrados: {len(df_filtrado)} registros de {len(df_clean)} originales")
                            df_clean = df_filtrado
                        
                        # Verificar que hay datos después del filtrado
                        if df_clean.empty:
                            st.error("❌ No hay datos después del filtrado. Ajusta los criterios de filtro.")
                            return
                        
                        # Generar conteos y traslados
                        conteos = {}
                        traslados_info = {}
                        
                        # Conteo general
                        conteos["Total de Incidentes"] = df_clean[col_incidentes].value_counts()
                        
                        # Traslados generales
                        traslados_info["Total de traslados"] = df_clean[col_traslado].apply(
                            lambda x: str(x).strip().lower() in ['sí', 'si', 's', 'yes', 'true', '1']).sum()
                        
                        # Análisis por Servicios Médicos
                        if incluir_sm and col_sm and col_sm in df_clean.columns:
                            # Limpiar columna SM
                            df_clean[col_sm] = df_clean[col_sm].astype(str).str.strip().str.upper()
                            
                            df_sm = df_clean[df_clean[col_sm] == 'SM']
                            df_no_sm = df_clean[df_clean[col_sm] != 'SM']
                            
                            conteos["Incidentes atendidos por Servicios Médicos MAC"] = df_sm[col_incidentes].value_counts()
                            conteos["Incidentes atendidos por Operativa Médica Protección Civil"] = df_no_sm[col_incidentes].value_counts()
                            
                            traslados_info["Traslados por Servicios Médicos MAC"] = df_sm[col_traslado].apply(
                                lambda x: str(x).strip().lower() in ['sí', 'si', 's', 'yes', 'true', '1']).sum()
                            traslados_info["Traslados por Operativa Médica Protección Civil"] = df_no_sm[col_traslado].apply(
                                lambda x: str(x).strip().lower() in ['sí', 'si', 's', 'yes', 'true', '1']).sum()
                        
                        # Mostrar resultados en la interfaz
                        st.header("3. 📈 Resultados del Análisis")
                        
                        # Métricas rápidas
                        col_met1, col_met2, col_met3 = st.columns(3)
                        with col_met1:
                            total_incidentes = len(df_clean)
                            st.metric("Total de Incidentes", total_incidentes)
                        with col_met2:
                            tipos_incidentes = len(conteos["Total de Incidentes"])
                            st.metric("Tipos de Incidentes", tipos_incidentes)
                        with col_met3:
                            total_traslados = traslados_info.get("Total de traslados", 0)
                            st.metric("Total de Traslados", total_traslados)
                        
                        # Mostrar información de traslados
                        st.subheader("🚑 Resumen de Traslados")
                        for k, v in traslados_info.items():
                            col_t1, col_t2 = st.columns([2, 1])
                            with col_t1:
                                st.write(f"**{k}**")
                            with col_t2:
                                st.write(f"**{v}**")
                        
                        # Mostrar tablas y gráficas de conteos
                        for nombre, conteo in conteos.items():
                            st.subheader(nombre)
                            
                            # Mostrar tabla
                            df_display = conteo.reset_index()
                            df_display.columns = ['Tipo de Incidente', 'Cantidad']
                            st.dataframe(df_display, use_container_width=True)
                            
                            # Mostrar gráfica interactiva
                            fig = generar_grafica_plotly(conteo, nombre)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Generar gráficas para el reporte Word
                        st.header("4. 📄 Generando Reportes Descargables")
                        with st.spinner("Generando gráficas para el reporte..."):
                            imagenes = {}
                            for k, v in conteos.items():
                                safe_filename = f"grafica_{k.replace(' ', '_').replace('/', '_').lower()}.png"
                                imagenes[k] = generar_grafica_bar(v, k, safe_filename)
                        
                        # Generar y ofrecer descarga de reportes
                        st.success("✅ Reportes generados correctamente")
                        
                        col_dl1, col_dl2 = st.columns(2)
                        
                        with col_dl1:
                            with st.spinner("Generando reporte Word..."):
                                doc_path = generar_reporte_word(conteos, traslados_info, imagenes)
                                st.markdown(get_download_link(doc_path, "Descargar Reporte Word (.docx)"), unsafe_allow_html=True)
                        
                        with col_dl2:
                            with st.spinner("Generando reporte de texto..."):
                                txt_path = generar_reporte_txt(conteos, traslados_info)
                                st.markdown(get_download_link(txt_path, "Descargar Reporte Texto (.txt)"), unsafe_allow_html=True)
                        
                        # Limpiar archivos temporales
                        for path in imagenes.values():
                            try:
                                if os.path.exists(path):
                                    os.remove(path)
                            except:
                                pass
            
            else:
                st.warning("⚠️ Por favor, selecciona las columnas de INCIDENTES y TRASLADO para continuar.")
                
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")
    
    else:
        st.info("👆 Por favor, sube un archivo CSV o Excel para comenzar el análisis.")
        st.markdown("""
        ### 📝 Instrucciones:
        1. **Sube tu archivo** de datos (CSV o Excel)
        2. **Selecciona las columnas** correspondientes
        3. **Configura los filtros** si es necesario  
        4. **Genera el reporte** y descarga los resultados
        
        ### 🔍 Análisis que se generan:
        - Conteo general de incidentes
        - Análisis de traslados a hospital
        - Segmentación por Servicios Médicos (opcional)
        - Gráficas y reportes descargables
        """)

if __name__ == "__main__":
    main()
