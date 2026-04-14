# Auditoría móvil de edificio · MVP Streamlit

Este prototipo está pensado para usar desde el celular durante recorridos de auditoría.

## Qué incluye
- Inicio de auditoría con edificio, auditor y tipo
- Checklist por espacios
- Score automático sobre 100
- Captura de foto para hallazgos
- Resumen final y guardado en CSV/JSON
- Enfoque móvil-first y visual simple
- Selector de estado con lista desplegable para cada pregunta

## Ejecutar localmente
```bash
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

## Subir a GitHub
1. Crea un repositorio nuevo en GitHub.
2. Sube estos archivos a la raíz del repositorio:
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. Haz commit y push.

## Publicar en Streamlit Community Cloud
1. Entra a Streamlit Community Cloud.
2. Pulsa **Create app**.
3. Conecta tu cuenta de GitHub si aún no lo has hecho.
4. Elige el repositorio donde subiste este proyecto.
5. En **Main file path** selecciona `app.py`.
6. Pulsa **Deploy**.

## Estructura de datos
- `data/auditorias_detalle.csv`: detalle histórico por pregunta
- `data/auditoria_YYYYMMDD_HHMMSS.json`: resumen por auditoría

## Próximos pasos sugeridos
1. Ajustar preguntas, pesos y espacios según tu edificio.
2. Hacer obligatoria la foto en hallazgos críticos.
3. Conectar a base de datos o dashboard.
4. Crear vista histórica por edificio y evolución del score.
5. Convertir hallazgos a tickets internos.
