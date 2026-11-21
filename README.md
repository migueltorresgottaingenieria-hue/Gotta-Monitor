
# Gotta Monitor Web corregido

## Archivos
- `app.py`: aplicación Streamlit con el panel y procesamiento de Excel.
- `gmail_helper.py`: OAuth web y búsqueda/descarga de Excel en Gmail.
- `requirements.txt`: dependencias.
- `secrets.toml.example`: ejemplo de configuración (sin credenciales reales).

## Configuración en Streamlit Community Cloud

1. Sube `app.py`, `gmail_helper.py` y `requirements.txt` al repositorio de la aplicación.
2. En Google Cloud Console configura un OAuth Client ID de tipo **Web application**.
3. En Google Cloud configura como URI de redirección autorizada exactamente la URL pública de tu app, por ejemplo:
   `https://TU-APP.streamlit.app`
   Debe coincidir exactamente con `redirect_uri` en Secrets.
4. Habilita Gmail API en el proyecto de Google Cloud.
5. Configura la pantalla de consentimiento OAuth. Si la app está en modo Testing, agrega las cuentas corporativas de los usuarios como usuarios de prueba. Para uso organizacional amplio, consulta con el administrador de Google Workspace y publica/configura la app según sus políticas.
6. En Streamlit Community Cloud abre App -> Settings -> Secrets y pega:

```toml
[google]
client_id = "CLIENT_ID"
client_secret = "CLIENT_SECRET"
redirect_uri = "https://TU-APP.streamlit.app"
```

7. Reinicia/redeploy la aplicación.
8. Abre Gotta Monitor, pulsa **Autorizar Gmail**, continúa con Google y concede el permiso de lectura.

## Seguridad y alcance

- Este ejemplo guarda el token OAuth en `st.session_state`, no en un archivo compartido. Así cada sesión del navegador usa su propia cuenta.
- Al cerrar/perder la sesión, puede ser necesario volver a autorizar. Para persistencia duradera entre sesiones y dispositivos, se requiere una base de datos segura por usuario y un mecanismo de identidad/sesiones.
- Usa HTTPS y no publiques `client_secret`, tokens ni `secrets.toml` en GitHub.
- Cada trabajador debe autorizar su propia cuenta. El archivo se busca en el Gmail del usuario que autorizó esa sesión.
- El código conserva el procesamiento de Excel, clasificación, filtros, tablas y gráficas de la versión compartida.
- No se ha podido validar contra tu Excel corporativo ni contra la configuración real de Google Cloud; prueba primero con una copia del reporte.

## Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Crea `.streamlit/secrets.toml` usando el formato del ejemplo y registra una URL de redirección que coincida exactamente con la dirección local que utilices. La URL local puede requerir configuración específica de Google OAuth; para la publicación web es preferible usar el dominio HTTPS de Streamlit Cloud.

