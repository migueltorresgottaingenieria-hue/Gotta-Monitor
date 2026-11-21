
# Gotta Monitor

## Descripcion
Gotta Monitor es una aplicacion desarrollada en Python con Streamlit para consultar, visualizar y monitorear informacion de estaciones DADDS mediante archivos Excel obtenidos desde Gmail.

## Funcionalidades
- Conexion con Gmail mediante autorizacion de Google.
- Busqueda de archivos Excel recibidos por correo electronico.
- Lectura y procesamiento de datos de estaciones.
- Visualizacion de informacion mediante tablas y graficas.
- Seguimiento de estaciones de nivel.
- Monitoreo del estado de las baterias.
- Generacion de alertas cuando la bateria presenta valores inferiores a 11 V.

## Tecnologias utilizadas
- Python
- Streamlit
- Pandas
- Plotly
- OpenPyXL
- Google API

## Requisitos
- Python 3.10 o superior.
- Conexion a internet.
- Acceso autorizado a Gmail.

## Instalacion

1. Clonar el repositorio:

   git clone https://github.com/migueltorresgottaingenieria-hue/Gotta-Monitor.git

2. Entrar a la carpeta:

   cd Gotta-Monitor

3. Instalar las dependencias:

   pip install -r requirements.txt

4. Configurar las credenciales de Google Gmail.

5. Ejecutar la aplicacion:

   streamlit run app.py

## Seguridad
Los archivos credentials.json y token.json contienen informacion de autorizacion de Gmail y no deben publicarse en el repositorio.

## Autor
Proyecto Gotta Monitor.
