
import streamlit as st
import pandas as pd
import io
import plotly.express as px

from gmail_helper import find_latest_xlsx


# ==================================================
# CONFIGURACION
# ==================================================

st.set_page_config(
    page_title="Gotta Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================================================
# ESTILOS VISUALES Y RESPONSIVE
# ==================================================

st.markdown("""
<style>

    .stApp {
        background-color: #F3F6FA;
    }

    [data-testid="stSidebar"] {
        background-color: #102B46;
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    .main-title {
        background: linear-gradient(110deg, #102B46, #1E5277);
        padding: 25px;
        border-radius: 14px;
        margin-bottom: 22px;
        color: white;
    }

    .main-title h1 {
        color: white;
        margin: 0;
        font-size: 30px;
    }

    .main-title p {
        color: #D4E6F3;
        margin: 5px 0 0 0;
    }

    .section-title {
        color: #173D5B;
        font-size: 21px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 12px;
    }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #DFE7EF;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 7px rgba(16,43,70,0.05);
    }

    [data-testid="stMetricLabel"] {
        color: #52677B;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: #163B59;
        font-weight: 700;
    }

    .stButton > button {
        background-color: #174F78;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 15px;
        width: 100%;
    }

    .stButton > button:hover {
        background-color: #236B9D;
        color: white;
        border: none;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #DFE7EF;
        border-radius: 10px;
        overflow: hidden;
    }

    hr {
        border-color: #DCE5ED;
    }

    .nav-link {
        display: block;
        text-decoration: none !important;
        color: #EAF3FA !important;
        background-color: transparent;
        padding: 12px 14px;
        margin: 5px 0;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        transition: background-color 0.2s ease;
    }

    .nav-link:hover {
        background-color: #1E5277;
        color: white !important;
    }

    html {
        scroll-behavior: smooth;
        scroll-padding-top: 20px;
    }

    .section-anchor {
        scroll-margin-top: 20px;
    }

    /* ADAPTACION PARA CELULARES */

    @media (max-width: 768px) {

        .main-title {
            padding: 18px;
            border-radius: 10px;
        }

        .main-title h1 {
            font-size: 23px;
        }

        .main-title p {
            font-size: 13px;
        }

        .section-title {
            font-size: 18px;
        }

        [data-testid="stMetric"] {
            padding: 10px;
        }

        [data-testid="stMetricLabel"] {
            font-size: 11px;
        }

        [data-testid="stMetricValue"] {
            font-size: 23px;
        }

        .stButton > button {
            font-size: 13px;
            padding: 9px;
        }

        [data-testid="stDataFrame"] {
            width: 100%;
        }

    }

</style>
""", unsafe_allow_html=True)


# ==================================================
# FUNCIONES AUXILIARES
# ==================================================

def normalize_text(value):

    if value is None:
        return ""

    value = str(value).strip().lower()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n"
    }

    for original, replacement in replacements.items():
        value = value.replace(original, replacement)

    return value


def fix_encoding(value):

    if not isinstance(value, str):
        return value

    suspicious = [
        "Ã¡", "Ã©", "Ã­", "Ã³", "Ãº",
        "Ã±", "Ã‘", "Ã‰", "Ã“", "Ãš",
        "Â"
    ]

    if not any(item in value for item in suspicious):
        return value

    try:
        return value.encode("latin1").decode("utf-8")

    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def fix_column_names(df):

    df = df.copy()

    df.columns = [
        fix_encoding(str(col).strip())
        for col in df.columns
    ]

    return df


def find_column(columns, possible_names, exact_only=False):

    normalized_columns = {
        normalize_text(col): col for col in columns
    }

    # Coincidencias exactas
    for name in possible_names:

        normalized_name = normalize_text(name)

        if normalized_name in normalized_columns:
            return normalized_columns[normalized_name]

    if exact_only:
        return None

    # Coincidencias parciales
    for col in columns:

        normalized_col = normalize_text(col)

        for name in possible_names:

            if normalize_text(name) in normalized_col:
                return col

    return None


def find_header_row(excel_file, sheet_name):

    preview = pd.read_excel(
        excel_file,
        sheet_name=sheet_name,
        header=None,
        nrows=30
    )

    for index, row in preview.iterrows():

        values = [
            normalize_text(fix_encoding(str(value)))
            for value in row.tolist()
        ]

        if any(
            value in ["estacion", "nombre estacion", "station"]
            for value in values
        ):
            return index

    return 0


def load_excel_file(file_bytes):

    excel_file = pd.ExcelFile(io.BytesIO(file_bytes))

    sheet_name = None

    for sheet in excel_file.sheet_names:

        if normalize_text(fix_encoding(sheet)) == "resumen":
            sheet_name = sheet
            break

    if sheet_name is None:

        st.error("No se encontró la hoja 'Resumen' en el archivo.")

        return None, None

    header_row = find_header_row(
        io.BytesIO(file_bytes),
        sheet_name
    )

    df = pd.read_excel(
        io.BytesIO(file_bytes),
        sheet_name=sheet_name,
        header=header_row
    )

    df = df.dropna(how="all")

    df = fix_column_names(df)

    # Corregir textos de las celdas
    for column in df.select_dtypes(include=["object"]).columns:
        df[column] = df[column].apply(fix_encoding)

    station_col = find_column(
        df.columns,
        ["Estación", "Estacion", "Nombre estación", "Station"]
    )

    if station_col is None:

        st.error("No se encontró la columna de estaciones.")

        return None, None

    df = df[df[station_col].notna()].copy()

    return df, excel_file.sheet_names


# ==================================================
# CLASIFICACION DE ESTADOS
# ==================================================

def to_number(value):

    try:

        if pd.isna(value):
            return 0

        return float(
            str(value).replace(",", ".").strip()
        )

    except (ValueError, TypeError):
        return 0


def classify_status(status_value, error_value=None, warning_value=None):

    status = normalize_text(status_value).upper()

    errors = to_number(error_value)
    warnings = to_number(warning_value)

    # PRIORIDAD 1: CUALQUIER ERROR REGISTRADO
    if errors > 0:
        return "ERROR"

    # PRIORIDAD 2: ESTADO DE ERROR
    if any(word in status for word in ["ERROR", "FALLA", "FAIL"]):
        return "ERROR"

    # PRIORIDAD 3: ESTADO REVISAR
    if status in ["REVISAR", "WARNING", "ADVERTENCIA"]:
        return "REVISAR"

    if warnings > 0:
        return "REVISAR"

    # PRIORIDAD 4: ESTADO CORRECTO
    if status in ["OK", "NORMAL", "CORRECTO"]:
        return "OK"

    return "SIN CLASIFICAR"


# ==================================================
# ENCABEZADO
# ==================================================

st.markdown("""
<div class="main-title">
    <h1>📡 GOTTA MONITOR</h1>
    <p>Sistema de monitoreo de estaciones hidrológicas</p>
</div>
""", unsafe_allow_html=True)


# ==================================================
# PANEL LATERAL
# ==================================================

with st.sidebar:

    st.markdown("## 📡 GOTTA MONITOR")

    st.markdown("---")

    st.markdown("### 📍 Navegación")

    st.markdown("""
        <a class="nav-link" href="#resumen">
            📊 Resumen general
        </a>

        <a class="nav-link" href="#estaciones">
            📋 Estaciones
        </a>

        <a class="nav-link" href="#consulta">
            📈 Consulta de datos
        </a>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.caption(
        "Sistema de consulta de reportes diarios"
    )


# ==================================================
# CARGA DEL REPORTE
# ==================================================

st.markdown(
    '<div class="section-title">📥 Gestión del reporte</div>',
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)


# BUSQUEDA EN GMAIL

with col1:

    if st.button(
        "📧 Obtener reporte",
        use_container_width=True
    ):

        with st.spinner("Buscando el reporte en Gmail..."):

            try:

                result = find_latest_xlsx(
                    query="has:attachment filename:xlsx"
                )

                if result:

                    if isinstance(result, tuple):

                        file_name = result[0]
                        file_bytes = result[1]

                    else:

                        file_name = "Reporte_DADDS.xlsx"
                        file_bytes = result

                    if hasattr(file_bytes, "getvalue"):
                        file_bytes = file_bytes.getvalue()

                    st.session_state["report_bytes"] = file_bytes
                    st.session_state["report_name"] = file_name

                    st.success(
                        f"Reporte cargado: {file_name}"
                    )

                    st.rerun()

                else:

                    st.warning(
                        "No se encontró ningún reporte."
                    )

            except Exception as error:

                st.error(
                    f"No fue posible conectar o buscar: {error}"
                )


# CARGA MANUAL

with col2:

    uploaded_file = st.file_uploader(
        "Cargar reporte Excel manualmente",
        type=["xlsx"]
    )

    if uploaded_file is not None:

        new_bytes = uploaded_file.getvalue()

        if (
            st.session_state.get("report_name") != uploaded_file.name
            or st.session_state.get("report_bytes") != new_bytes
        ):

            st.session_state["report_bytes"] = new_bytes
            st.session_state["report_name"] = uploaded_file.name

            st.rerun()


# LIMPIAR REPORTE

if st.button("🗑️ Limpiar reporte"):

    st.session_state.pop("report_bytes", None)
    st.session_state.pop("report_name", None)

    st.rerun()


# ==================================================
# PROCESAMIENTO DEL REPORTE
# ==================================================

if "report_bytes" in st.session_state:

    st.divider()

    st.success(
        f"Reporte disponible: "
        f"{st.session_state.get('report_name', 'Archivo Excel')}"
    )

    try:

        df, sheet_names = load_excel_file(
            st.session_state["report_bytes"]
        )

    except Exception as error:

        st.error(
            f"Error al leer el archivo Excel: {error}"
        )

        st.stop()

    if df is not None and not df.empty:

        # ==========================================
        # IDENTIFICACION DE COLUMNAS
        # ==========================================

        station_col = find_column(
            df.columns,
            ["Estación", "Estacion", "Nombre estación", "Station"]
        )

        status_col = find_column(
            df.columns,
            ["Estado"],
            exact_only=True
        )

        received_col = find_column(
            df.columns,
            ["Recibidos", "Datos recibidos", "Received"]
        )

        error_col = find_column(
            df.columns,
            ["Errores", "Errors", "Error"]
        )

        warning_col = find_column(
            df.columns,
            ["Advertencias", "Warnings", "Warning"]
        )

        last_col = find_column(
            df.columns,
            [
                "Última transmisión",
                "Ultima transmision",
                "Último dato",
                "Last transmission"
            ]
        )

        detail_col = find_column(
            df.columns,
            [
                "Detalle",
                "Observación",
                "Observacion",
                "Descripción"
            ]
        )

        # ==========================================
        # CLASIFICACION UNIFICADA
        # ==========================================

        df["Clasificacion_DADDS"] = df.apply(
            lambda row: classify_status(
                row[status_col] if status_col is not None else None,
                row[error_col] if error_col is not None else None,
                row[warning_col] if warning_col is not None else None
            ),
            axis=1
        )

        # ==========================================
        # RESUMEN GENERAL
        # ==========================================

        st.markdown(
            '<div id="resumen" class="section-anchor"></div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="section-title">📊 Resumen general</div>',
            unsafe_allow_html=True
        )

        total_stations = len(df)

        ok_count = int(
            (df["Clasificacion_DADDS"] == "OK").sum()
        )

        review_count = int(
            (df["Clasificacion_DADDS"] == "REVISAR").sum()
        )

        error_count = int(
            (df["Clasificacion_DADDS"] == "ERROR").sum()
        )

        unknown_count = int(
            (df["Clasificacion_DADDS"] == "SIN CLASIFICAR").sum()
        )

        # Indicadores
        metric1, metric2, metric3, metric4 = st.columns(4)

        metric1.metric(
            "TOTAL ESTACIONES",
            total_stations
        )

        metric2.metric(
            "ESTADO OK",
            ok_count
        )

        metric3.metric(
            "ESTADO REVISAR",
            review_count
        )

        metric4.metric(
            "ESTADO ERROR",
            error_count
        )

        # Mostrar pendientes solamente si existen
        if unknown_count > 0:

            st.info(
                f"Hay {unknown_count} estaciones sin información "
                "suficiente para clasificarlas."
            )

        # ==========================================
        # TABLA GENERAL Y FILTROS
        # ==========================================

        st.divider()

        st.markdown(
            '<div id="estaciones" class="section-anchor"></div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="section-title">📋 Reporte general de estaciones</div>',
            unsafe_allow_html=True
        )

        filtro1, filtro2 = st.columns([2, 1])

        with filtro1:

            buscar_estacion = st.text_input(
                "🔎 Buscar estación",
                placeholder="Escribe el nombre de la estación...",
                key="buscar_estacion"
            )

        with filtro2:

            opciones_estado = [
                "Todos",
                "OK",
                "REVISAR",
                "ERROR",
                "SIN CLASIFICAR"
            ]

            estado_seleccionado = st.selectbox(
                "Filtrar por estado",
                opciones_estado,
                key="filtro_estado"
            )

        # Aplicar filtros
        df_filtrado = df.copy()

        # FILTRO POR NOMBRE

        if buscar_estacion.strip():

            df_filtrado = df_filtrado[
                df_filtrado[station_col]
                .astype(str)
                .str.contains(
                    buscar_estacion.strip(),
                    case=False,
                    na=False,
                    regex=False
                )
            ]

        # FILTRO POR CLASIFICACION

        if estado_seleccionado != "Todos":

            df_filtrado = df_filtrado[
                df_filtrado["Clasificacion_DADDS"]
                == estado_seleccionado
            ]

        st.caption(
            f"Estaciones encontradas: {len(df_filtrado)} de {len(df)}"
        )

        if not df_filtrado.empty:

            st.dataframe(
                df_filtrado.drop(
                    columns=["Clasificacion_DADDS"]
                ),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.warning(
                "No se encontraron estaciones con los filtros seleccionados."
            )

        # ==========================================
        # CONSULTA INDIVIDUAL
        # ==========================================

        st.divider()

        st.markdown(
            '<div id="consulta" class="section-anchor"></div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="section-title">🔎 Consulta individual de estaciones</div>',
            unsafe_allow_html=True
        )

        estaciones_consulta = (
            df_filtrado
            if not df_filtrado.empty
            else df
        )

        station_names = sorted(
            estaciones_consulta[station_col]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        if station_names:

            if (
                st.session_state.get("estacion_individual")
                not in station_names
            ):

                st.session_state.pop(
                    "estacion_individual",
                    None
                )

            selected_station = st.selectbox(
                "Selecciona una estación para consultar sus datos",
                station_names,
                key="estacion_individual"
            )

            station_row = df[
                df[station_col].astype(str) == selected_station
            ].iloc[0]

            st.markdown(
                f"### 📍 {selected_station}"
            )

            # ======================================
            # INDICADORES INDIVIDUALES
            # ======================================

            fields = [
                ("Estado", status_col),
                ("Datos recibidos", received_col),
                ("Errores registrados", error_col),
                ("Advertencias registradas", warning_col),
                ("Última transmisión", last_col)
            ]

            visible_fields = [
                (label, column)
                for label, column in fields
                if column is not None
            ]

            info_columns = st.columns(3)

            for index, (label, column) in enumerate(visible_fields):

                with info_columns[index % 3]:

                    value = station_row[column]

                    if pd.isna(value):
                        value = "Sin información"

                    st.metric(
                        label,
                        str(value)
                    )

            if detail_col is not None:

                detail_value = station_row[detail_col]

                if pd.notna(detail_value):

                    st.info(
                        f"Observación registrada en el reporte: "
                        f"{detail_value}"
                    )

            # ======================================
            # HOJA INDIVIDUAL
            # ======================================

            matching_sheet = None

            for sheet in sheet_names:

                if (
                    normalize_text(fix_encoding(sheet))
                    == normalize_text(selected_station)
                ):

                    matching_sheet = sheet
                    break

            if matching_sheet is not None:

                station_data = pd.read_excel(
                    io.BytesIO(st.session_state["report_bytes"]),
                    sheet_name=matching_sheet
                )

                station_data = station_data.dropna(how="all")

                station_data = fix_column_names(station_data)

                # Corregir textos
                for column in station_data.select_dtypes(include=["object"]).columns:

                    station_data[column] = station_data[column].apply(
                        fix_encoding
                    )

                st.divider()

                st.markdown(
                    '<div class="section-title">📈 Datos registrados</div>',
                    unsafe_allow_html=True
                )

                st.dataframe(
                    station_data,
                    use_container_width=True,
                    hide_index=True
                )

                # ==================================
                # GRAFICAS
                # ==================================

                time_col = find_column(
                    station_data.columns,
                    [
                        "Data Time",
                        "Fecha",
                        "Fecha Hora",
                        "Datetime",
                        "Timestamp",
                        "Time"
                    ]
                )

                if time_col is not None:

                    station_data[time_col] = pd.to_datetime(
                        station_data[time_col],
                        errors="coerce"
                    )

                    numeric_columns = []

                    for column in station_data.columns:

                        if column == time_col:
                            continue

                        converted = pd.to_numeric(
                            station_data[column],
                            errors="coerce"
                        )

                        if converted.notna().any():

                            station_data[column] = converted
                            numeric_columns.append(column)

                    if numeric_columns:

                        st.markdown(
                            '<div class="section-title">📉 Visualización de variables</div>',
                            unsafe_allow_html=True
                        )

                        selected_variables = st.multiselect(
                            "Selecciona las variables que deseas visualizar",
                            numeric_columns,
                            default=numeric_columns[:1],
                            key=f"variables_{normalize_text(selected_station)}"
                        )

                        for variable in selected_variables:

                            chart_data = station_data[
                                [time_col, variable]
                            ].dropna()

                            if not chart_data.empty:

                                chart_data = chart_data.sort_values(
                                    time_col
                                )

                                fig = px.line(
                                    chart_data,
                                    x=time_col,
                                    y=variable,
                                    markers=True,
                                    title=f"Comportamiento de {variable}"
                                )

                                fig.update_layout(
                                    template="plotly_white",
                                    xaxis_title="Fecha y hora",
                                    yaxis_title=variable,
                                    hovermode="x unified",
                                    title_font_color="#173D5B",
                                    title_font_size=18,
                                    margin=dict(
                                        l=20,
                                        r=20,
                                        t=55,
                                        b=20
                                    )
                                )

                                fig.update_traces(
                                    line=dict(width=2.5),
                                    marker=dict(size=6)
                                )

                                st.plotly_chart(
                                    fig,
                                    use_container_width=True
                                )

                    else:

                        st.info(
                            "No se encontraron variables numéricas para graficar."
                        )

                else:

                    st.info(
                        "No se identificó una columna de fecha u hora "
                        "para generar las gráficas."
                    )

            else:

                st.warning(
                    "No se encontró una hoja individual para esta estación."
                )

        else:

            st.warning(
                "No hay estaciones disponibles para consultar."
            )

    else:

        st.warning(
            "El reporte no contiene estaciones para mostrar."
        )

else:

    # ==========================================
    # PANTALLA DE BIENVENIDA
    # ==========================================

    st.info(
        "Obtén el último reporte desde Gmail o carga un archivo Excel "
        "para comenzar."
    )

    st.markdown("""
    ### Bienvenido a Gotta Monitor

    Desde esta aplicación podrás:

    - Consultar reportes diarios recibidos por Gmail.
    - Visualizar el estado registrado de las estaciones.
    - Buscar y filtrar estaciones por nombre y estado.
    - Consultar información individual.
    - Visualizar gráficas de las variables disponibles.
    """)


# ==================================================
# PIE DE PAGINA
# ==================================================

st.divider()

st.caption(
    "Gotta Monitor | Sistema de monitoreo de estaciones hidrológicas"
)
