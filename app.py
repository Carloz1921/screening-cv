import streamlit as st
import google.generativeai as genai
import json, re, tempfile, os
from pathlib import Path

st.set_page_config(page_title="Screening Automático de CV", page_icon="🔬", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
  .header-box { background: linear-gradient(135deg,#0f3460,#1a4d8f); padding:32px 36px;
    border-radius:16px; margin-bottom:28px; color:white; }
  .header-box h1 { margin:0; font-size:2em; }
  .header-box p  { margin:6px 0 0; color:#badcf7; }
  .card { background:#1e2330; border-radius:14px; padding:24px; margin-bottom:18px;
    border:1px solid #2d3561; color:#dfe6e9; }
  .card h3 { color:#74b9ff; font-size:.75em; text-transform:uppercase; letter-spacing:2px;
    border-bottom:1px solid #2d3561; padding-bottom:8px; margin-top:0; }
  .chip { display:inline-block; padding:3px 12px; border-radius:20px;
    font-size:.78em; font-weight:600; margin:2px; }
  .stButton > button { background:linear-gradient(135deg,#1a4d8f,#0f3460); color:white;
    border:none; border-radius:10px; padding:12px 28px; font-size:1em;
    font-weight:600; width:100%; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        st.error("❌ API Key no configurada. Contacta al administrador.")
        st.stop()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash")

def extract_pdf(path):
    import fitz
    doc = fitz.open(path)
    text = "\n".join(p.get_text() for p in doc)
    doc.close()
    return text.strip()

def extract_docx(path):
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def extract_image(path, model):
    import PIL.Image
    img = PIL.Image.open(path)
    resp = model.generate_content(["Extrae todo el texto de este documento. Solo el texto.", img])
    return resp.text.strip()

def extract_text(uploaded_file, model):
    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    try:
        if   suffix == ".pdf":                               text = extract_pdf(tmp_path)
        elif suffix in (".docx", ".doc"):                    text = extract_docx(tmp_path)
        elif suffix in (".jpg",".jpeg",".png",".webp"):      text = extract_image(tmp_path, model)
        elif suffix == ".txt":                               text = Path(tmp_path).read_text(encoding="utf-8", errors="ignore")
        else: raise ValueError(f"Formato '{suffix}' no soportado.")
    finally:
        os.unlink(tmp_path)
    return text

def screening_cv(perfil, cv_text, model):
    prompt = f"""
Eres un experto en reclutamiento con 15 años de experiencia en selección de talento industrial.
Respondes SIEMPRE en español.

══ PERFIL REQUERIDO ══
{perfil}

══ CV DEL CANDIDATO ══
{cv_text}

Devuelve ÚNICAMENTE un JSON válido (sin markdown):
{{
  "fit_percentage": <0-100>,
  "nivel_recomendacion": "<ALTAMENTE RECOMENDADO|RECOMENDADO|RECOMENDADO CON RESERVAS|NO RECOMENDADO>",
  "resumen_ejecutivo": "<2-3 oraciones>",
  "fortalezas": [{{"punto":"<aspecto>","relevancia":"<por qué encaja>"}}],
  "brechas": [{{"punto":"<brecha>","impacto":"<ALTO|MEDIO|BAJO>"}}],
  "competencias_detectadas": {{"tecnicas":["..."],"blandas":["..."]}},
  "experiencia_relevante": "<resumen>",
  "recomendaciones_mejora": ["..."],
  "preguntas_entrevista": ["..."]
}}
"""
    response = model.generate_content(prompt)
    raw = re.sub(r"^```(?:json)?\s*","", response.text.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\s*```$","", raw, flags=re.MULTILINE)
    return json.loads(raw.strip())

def render_results(r):
    fit   = r.get("fit_percentage", 0)
    nivel = r.get("nivel_recomendacion","—")
    color, bg = ("#00b894","#00b89422") if fit>=80 else ("#fdcb6e","#fdcb6e22") if fit>=60 else ("#d63031","#d6303122")

    c1,c2,c3 = st.columns([1,2,1])
    with c1:
        st.markdown(f"""<div style='background:{bg};border:3px solid {color};border-radius:50%;
            width:130px;height:130px;display:flex;flex-direction:column;align-items:center;
            justify-content:center;margin:auto'>
          <span style='font-size:2.2em;font-weight:700;color:{color}'>{fit}%</span>
          <span style='font-size:.7em;color:#b2bec3'>FIT</span></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style='padding:12px 0'>
          <span style='background:{bg};border:1.5px solid {color};color:{color};
            padding:5px 16px;border-radius:30px;font-size:.85em;font-weight:700'>{nivel}</span>
          <div style='background:#2d3561;border-radius:8px;height:10px;margin:14px 0;overflow:hidden'>
            <div style='width:{fit}%;background:linear-gradient(90deg,{color},{color}99);height:100%;border-radius:8px'></div>
          </div>
          <p style='color:#b2bec3;font-size:.9em;line-height:1.6;margin:0'>{r.get("resumen_ejecutivo","—")}</p>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.metric("Fit Score", f"{fit}%")

    st.divider()
    ca, cb = st.columns(2)
    with ca:
        st.markdown("<div class='card'><h3>✅ Fortalezas</h3>", unsafe_allow_html=True)
        for f in r.get("fortalezas",[]):
            st.markdown(f"**{f['punto']}**"); st.caption(f['relevancia'])
        st.markdown("</div>", unsafe_allow_html=True)
    with cb:
        imp = {"ALTO":"#d63031","MEDIO":"#fdcb6e","BAJO":"#74b9ff"}
        st.markdown("<div class='card'><h3>⚠️ Brechas detectadas</h3>", unsafe_allow_html=True)
        for b in r.get("brechas",[]):
            c2c = imp.get(b["impacto"],"#636e72")
            st.markdown(f'<span class="chip" style="background:{c2c}22;border:1px solid {c2c};color:{c2c}">● {b["impacto"]}</span> {b["punto"]}', unsafe_allow_html=True)
            st.write("")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='card'><h3>🏭 Experiencia relevante</h3><div style='background:#232a42;border-left:3px solid #74b9ff;padding:12px 16px;border-radius:8px;line-height:1.7'>{r.get('experiencia_relevante','—')}</div></div>", unsafe_allow_html=True)

    cc, cd = st.columns(2)
    with cc:
        chips = " ".join(f'<span class="chip" style="background:#0984e322;border:1px solid #0984e3;color:#0984e3">{c}</span>' for c in r.get("competencias_detectadas",{}).get("tecnicas",[]))
        st.markdown(f"<div class='card'><h3>🔧 Competencias técnicas</h3>{chips or 'No identificadas'}</div>", unsafe_allow_html=True)
    with cd:
        chips = " ".join(f'<span class="chip" style="background:#a29bfe22;border:1px solid #a29bfe;color:#a29bfe">{c}</span>' for c in r.get("competencias_detectadas",{}).get("blandas",[]))
        st.markdown(f"<div class='card'><h3>🤝 Competencias blandas</h3>{chips or 'No identificadas'}</div>", unsafe_allow_html=True)

    ce, cf = st.columns(2)
    with ce:
        st.markdown("<div class='card'><h3>📈 Recomendaciones de mejora</h3>", unsafe_allow_html=True)
        for rec in r.get("recomendaciones_mejora",[]): st.markdown(f"• {rec}")
        st.markdown("</div>", unsafe_allow_html=True)
    with cf:
        st.markdown("<div class='card'><h3>❓ Preguntas para entrevista</h3>", unsafe_allow_html=True)
        for p in r.get("preguntas_entrevista",[]): st.markdown(f"• {p}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.download_button("⬇️ Descargar reporte JSON",
        data=json.dumps(r, ensure_ascii=False, indent=2),
        file_name="screening_resultado.json", mime="application/json")

# ══════════════════════════════════════════════════════════════════════════════
def main():
    model = get_model()

    st.markdown("<div class='header-box'><h1>🔬 Screening Automático de CV</h1><p>Análisis inteligente de candidatos · Powered by Google Gemini AI</p></div>", unsafe_allow_html=True)

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
        st.title("🔬 Screening CV")
        st.divider()
        st.markdown("**¿Cómo usar?**")
        st.markdown("1. 📌 Ingresa el perfil del puesto\n2. 📎 Sube el CV\n3. 🚀 Clic en Analizar\n4. 📊 Revisa el reporte")
        st.divider()
        st.caption("📁 PDF · DOCX · TXT · JPG · PNG")
        st.divider()
        st.caption("🔒 Los archivos se procesan en tiempo real y no se almacenan.")

    tab1, tab2 = st.tabs(["📋 Nuevo Screening", "ℹ️ Acerca de"])

    with tab1:
        col_izq, col_der = st.columns(2)

        with col_izq:
            st.subheader("📌 Paso 1 — Perfil del puesto")
            modo = st.radio("¿Cómo ingresas el perfil?", ["📂 Subir documento","✏️ Escribir manualmente"], horizontal=True)
            perfil_texto = ""
            if modo == "📂 Subir documento":
                f_perfil = st.file_uploader("Sube el documento del perfil", type=["pdf","docx","txt","jpg","png"], key="perfil")
                if f_perfil:
                    with st.spinner("Extrayendo texto..."):
                        try:
                            perfil_texto = extract_text(f_perfil, model)
                            st.success(f"✅ Perfil cargado: {len(perfil_texto):,} caracteres")
                            with st.expander("👁️ Vista previa"):
                                st.text(perfil_texto[:500]+("..." if len(perfil_texto)>500 else ""))
                        except Exception as e: st.error(f"❌ {e}")
            else:
                perfil_texto = st.text_area("Describe el perfil:", height=220,
                    placeholder="Ej: Analista de Laboratorio con 3-5 años en refinería...")

        with col_der:
            st.subheader("📎 Paso 2 — CV del candidato")
            f_cv = st.file_uploader("Sube el CV", type=["pdf","docx","txt","jpg","png"], key="cv")
            cv_texto = ""
            if f_cv:
                with st.spinner("Extrayendo texto..."):
                    try:
                        cv_texto = extract_text(f_cv, model)
                        st.success(f"✅ CV cargado: {len(cv_texto):,} caracteres")
                        with st.expander("👁️ Vista previa"):
                            st.text(cv_texto[:500]+("..." if len(cv_texto)>500 else ""))
                    except Exception as e: st.error(f"❌ {e}")

        st.divider()
        listo = perfil_texto.strip() and cv_texto.strip()
        if not listo:
            st.warning("⚠️ Completa el perfil y sube el CV para continuar.")

        if st.button("🚀 Analizar con Gemini AI", disabled=not listo):
            with st.spinner("🤖 Gemini está analizando... (~20 segundos)"):
                try:
                    resultado = screening_cv(perfil_texto, cv_texto, model)
                    st.success(f"✅ Análisis completado — Fit: {resultado.get('fit_percentage','?')}%")
                    st.divider()
                    st.subheader("📊 Reporte de Screening")
                    render_results(resultado)
                except json.JSONDecodeError:
                    st.error("❌ Error al procesar la respuesta. Intenta nuevamente.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    with tab2:
        st.markdown("""
        ## 🔬 Screening Automático de CV
        App para análisis automático de candidatos con IA (Google Gemini).

        ### 🎯 Cubre los 7 pasos del ejercicio
        1. ✅ Consulta el perfil requerido
        2. ✅ Adjunta el CV en cualquier formato e idioma
        3. ✅ Analiza el CV automáticamente
        4. ✅ Compara con el perfil requerido
        5. ✅ Define un porcentaje de fit (0-100%)
        6. ✅ Estructura los puntos que cumple el perfil
        7. ✅ Define recomendaciones de mejora

        ### 🔒 Privacidad
        Los archivos se procesan en tiempo real y **no se almacenan** en ningún servidor.
        """)

if __name__ == "__main__":
    main()
