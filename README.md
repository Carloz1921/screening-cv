# 🔬 Screening Automático de CV
### Powered by Google Gemini AI

App web para analizar CVs contra perfiles de puestos automáticamente.

## 🚀 Cómo ejecutar localmente

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar la app
streamlit run app.py
```

## ☁️ Publicar gratis en Streamlit Cloud

1. Sube esta carpeta a **GitHub** (repositorio público o privado)
2. Ve a 👉 https://share.streamlit.io
3. Conecta tu repositorio
4. Selecciona `app.py` como archivo principal
5. En **Secrets**, agrega: `GOOGLE_API_KEY = "AIza..."`
6. ¡Clic en Deploy!

## 📁 Estructura
```
screening_app/
├── app.py              ← App principal
├── requirements.txt    ← Dependencias
├── .streamlit/
│   └── config.toml     ← Tema oscuro
└── README.md
```

## 🔑 API Key
Obtén tu clave gratuita en: https://aistudio.google.com/apikey
