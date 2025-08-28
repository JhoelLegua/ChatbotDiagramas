from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
from uuid import uuid4
import os
import shutil
import re

from script import ejecutar_plantuml

# LLM: Google Gemini
try:
    import google.generativeai as genai
except Exception:
    genai = None

# Cargar variables de entorno desde .env si está disponible
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    pass

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)
TEMP_IMGS_DIR = BASE_DIR / "temp_imgs"
TEMP_IMGS_DIR.mkdir(exist_ok=True)

# API Key y modelo
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

if genai and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    except Exception:
        _gemini_model = None
else:
    _gemini_model = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"ok": False, "error": "Mensaje vacío."}), 400

    # Identificador de esta interacción
    file_id = f"chat_{uuid4().hex}"

    # 1) Generar código PlantUML con el LLM si está disponible; si no, usar el texto tal cual
    plantuml_code = None
    if _gemini_model is not None:
        try:
            prompt = (
                "Eres un asistente que genera código PlantUML válido para la versión 1.2025.4. "
                "Devuelve únicamente el código PlantUML completo y funcional. "
                "Incluye @startuml y @enduml. No agregues explicaciones adicionales. "
                "Usa sintaxis moderna de PlantUML: "
                "- Para diagramas de estado, usa 'state \"Texto\" as Alias <<choice>>' en lugar de 'choice'. "
                "- Para describir un estado, usa 'state \"Nombre\" : Descripción en una línea'. NO uses llaves {} para los estados. "
                "- Usa únicamente elementos estándar como class, package, note, state, etc. "
                "- Evita elementos no estándar como concept o frame. "
                "- Para diagramas de secuencia usa participant, actor, ->, -->. "
                "- Para diagramas de clase usa class, interface, +method(), -attribute. "
                "\n\n"
                f"Solicitud del usuario: {message}"
            )
            result = _gemini_model.generate_content(prompt)
            text = getattr(result, "text", None) or (result.candidates[0].content.parts[0].text if getattr(result, "candidates", None) else None)
            # Log de la respuesta del LLM
            try:
                print("[Gemini] Respuesta bruta:\n", (text or "").strip())
                # Guardar respuesta bruta para auditoría
                raw_path = TEMP_DIR / f"{file_id}_llm.txt"
                raw_path.write_text((text or "").strip(), encoding="utf-8")
                print(f"[Gemini] Respuesta bruta guardada en: {raw_path}")
            except Exception:
                pass
            plantuml_code = (text or "").strip()
        except Exception as e:
            plantuml_code = None

    if not plantuml_code:
        # Si no hay LLM disponible y el mensaje no parece PlantUML, informar al usuario
        if not _is_probable_plantuml(message):
            return jsonify({
                "ok": False,
                "error": (
                    "El texto no parece código PlantUML. Configura el LLM o pega un bloque PlantUML. "
                    "Pasos: instala dependencias (pip install -r requirements.txt), define GEMINI_API_KEY en .env y reinicia el servidor."
                )
            }), 400

        # Fallback: usar el mensaje del usuario como si fuera PlantUML
        plantuml_code = message

    # Extraer bloque entre @startuml y @enduml si el modelo incluyó formato extra
    plantuml_code = _extract_plantuml_block(plantuml_code)
    # Limpiar el código PlantUML para asegurar compatibilidad
    plantuml_code = _clean_plantuml(plantuml_code)
    
    # Validar que el código PlantUML sea básico válido
    validation_error = _validate_plantuml_code(plantuml_code)
    if validation_error:
        return jsonify({"ok": False, "error": f"Código PlantUML inválido: {validation_error}"}), 400
    
    try:
        print("[Gemini] PlantUML extraído y limpiado:\n", plantuml_code)
    except Exception:
        pass

    # Asegurar que contiene @startuml y @enduml
    if "@startuml" not in plantuml_code or "@enduml" not in plantuml_code:
        plantuml_code = f"@startuml\n{plantuml_code}\n@enduml"

    # 2) Guardar el contenido PlantUML en ./temp como .txt
    uml_txt_name = f"{file_id}.txt"
    uml_txt_path = TEMP_DIR / uml_txt_name

    try:
        uml_txt_path.write_text(plantuml_code, encoding="utf-8")
    except Exception as e:
        return jsonify({"ok": False, "error": f"No se pudo guardar el archivo: {e}"}), 500

    # 3) Ejecutar PlantUML con nuestro script (generará PNG en ./temp)
    ok = ejecutar_plantuml(str(uml_txt_path.relative_to(BASE_DIR)))

    if not ok:
        # Limpiar archivo temporal de entrada si hubo error
        try:
            if uml_txt_path.exists():
                uml_txt_path.unlink()
        except Exception:
            pass
        return jsonify({"ok": False, "error": "Fallo al ejecutar PlantUML. Revisa que Java esté instalado y el JAR exista."}), 500

    # 4) Determinar imagen generada (PlantUML suele generar .png en ./temp)
    png_name = f"{file_id}.png"
    png_path = TEMP_DIR / png_name

    # En algunos casos PlantUML usa nombre del archivo base + .png en carpeta temp
    if not png_path.exists():
        # Buscar primer .png generado recientemente dentro de temp como fallback
        try:
            candidates = sorted(TEMP_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                png_path = candidates[0]
                png_name = png_path.name
        except Exception:
            pass

    if not png_path.exists():
        # Limpieza del archivo de entrada
        try:
            if uml_txt_path.exists():
                uml_txt_path.unlink()
        except Exception:
            pass
        return jsonify({"ok": False, "error": "No se encontró la imagen generada."}), 500

    # 5) Copiar la imagen a ./temp_imgs con nombre basado en file_id y eliminar el original
    try:
        final_png_name = f"{file_id}.png"
        dest_path = TEMP_IMGS_DIR / final_png_name
        # Copiar (sobreescribir si existe)
        shutil.copyfile(str(png_path), str(dest_path))
        # Eliminar original en temp para que solo quede en temp_imgs
        try:
            png_path.unlink(missing_ok=True)
        except TypeError:
            # Compatibilidad con Python <3.8
            if png_path.exists():
                png_path.unlink()
        png_path = dest_path
        png_name = dest_path.name
    except Exception as e:
        return jsonify({"ok": False, "error": f"No se pudo mover la imagen a temp_imgs: {e}"}), 500

    # Limpiar el archivo de texto de entrada luego de generar la imagen
    try:
        if uml_txt_path.exists():
            uml_txt_path.unlink()
    except Exception:
        pass

    # URL final siempre desde temp_imgs
    img_url = f"/temp_imgs/{png_name}"

    return jsonify({
        "ok": True,
        "reply": "Diagrama generado",
        "image_url": img_url
    })


@app.route('/temp/<path:filename>')
def serve_temp(filename: str):
    # Servir archivos generados en temp (p. ej. PNG)
    return send_from_directory(TEMP_DIR, filename, as_attachment=False)


@app.route('/temp_imgs/<path:filename>')
def serve_temp_imgs(filename: str):
    # Servir archivos movidos a temp_imgs
    return send_from_directory(TEMP_IMGS_DIR, filename, as_attachment=False)


def _extract_plantuml_block(text: str) -> str:
    """Extrae el bloque PlantUML entre @startuml y @enduml o dentro de fences ``` si existen."""
    if not text:
        return text

    # Prioridad: buscar @startuml ... @enduml directo
    m = re.search(r"@startuml[\s\S]*?@enduml", text, re.IGNORECASE)
    if m:
        return m.group(0)

    # Buscar dentro de fences de código ```
    fence = re.search(r"```(?:plantuml|puml|uml)?\n([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()

    return text


def _clean_plantuml(code: str) -> str:
    """Limpia el código PlantUML reemplazando elementos no estándar."""
    if not code:
        return code
    
    # Reemplazar 'concept' con 'class' (PlantUML estándar)
    code = re.sub(r'\bconcept\b', 'class', code, flags=re.IGNORECASE)
    
    # Reemplazar 'frame' con 'package' (PlantUML estándar)
    code = re.sub(r'\bframe\b', 'package', code, flags=re.IGNORECASE)
    
    # Eliminar llaves {} de la definición de estados y convertir a descripción
    # state "Nombre" { ... } -> state "Nombre" : ...
    def replace_state_body(match):
        state_name = match.group(1)
        body = match.group(2)
        # Convertir el cuerpo en una sola línea de descripción
        description = ' '.join(line.strip() for line in body.strip().split('\n'))
        return f'state "{state_name}" : {description}'
    
    code = re.sub(r'state\s+"([^"]+)"\s*\{([\s\S]*?)\}', replace_state_body, code)
    
    # Convertir sintaxis antigua de choice a sintaxis moderna
    # choice "Texto" as Alias -> state "Texto" as Alias <<choice>>
    code = re.sub(r'\bchoice\s+"([^"]+)"\s+as\s+(\w+)', r'state "\1" as \2 <<choice>>', code, flags=re.IGNORECASE)
    
    # Manejar choice sin comillas
    code = re.sub(r'\bchoice\s+([^\s]+)\s+as\s+(\w+)', r'state \1 as \2 <<choice>>', code, flags=re.IGNORECASE)
    
    # Pero preservar sintaxis ya correcta <<choice>>
    # No hacer nada adicional si ya está en formato correcto
    
    # Convertir sintaxis antigua de state con choice
    # state "Texto" as Alias <<choice>> (ya está bien)
    # Pero asegurar que no haya problemas con espacios
    code = re.sub(r'<<\s*choice\s*>>', '<<choice>>', code)
    
    # Limpiar caracteres de escape innecesarios en nombres de estado
    code = re.sub(r'state\s+"([^"\\]+)\\([^"]+)"\s+as\s+(\w+)', r'state "\1" as \2', code)
    
    # Eliminar líneas que comiencen con ``` si quedan
    code = re.sub(r'^```.*$', '', code, flags=re.MULTILINE)
    
    # Limpiar líneas vacías excesivas
    code = re.sub(r'\n\s*\n\s*\n+', '\n\n', code)
    
    # Asegurar que termine con @enduml si falta
    if not code.strip().endswith('@enduml'):
        code = code.rstrip() + '\n@enduml'
    
    # Asegurar que comience con @startuml si falta
    if not code.strip().startswith('@startuml'):
        code = '@startuml\n' + code.lstrip()
    
    return code.strip()


def _validate_plantuml_code(code: str) -> str:
    """Valida que el código PlantUML sea básicamente correcto."""
    if not code or not code.strip():
        return "Código vacío"
    
    code_lower = code.lower()
    
    # Verificar que tenga las etiquetas básicas
    if "@startuml" not in code_lower:
        return "Falta @startuml"
    
    if "@enduml" not in code_lower:
        return "Falta @enduml"
    
    # Verificar que @startuml venga antes que @enduml
    start_pos = code_lower.find("@startuml")
    end_pos = code_lower.find("@enduml")
    if start_pos > end_pos:
        return "@startuml debe venir antes que @enduml"
    
    # Verificar que no haya choice sin convertir (sintaxis antigua)
    # Buscar 'choice' que NO esté dentro de <<choice>>
    if re.search(r'\bchoice\b(?![^<]*>>)', code, re.IGNORECASE):
        return "Sintaxis 'choice' obsoleta detectada. Use 'state ... <<choice>>' en su lugar"
    
    return ""  # Sin errores


def _is_probable_plantuml(text: str) -> bool:
    """Heurística básica para detectar si el texto parece PlantUML."""
    if not text:
        return False
    t = text.strip().lower()
    if "@startuml" in t and "@enduml" in t:
        return True
    # Detectar arte de secuencia o clase común
    probable_tokens = ["->", "-->", "participant", "actor", "class ", "interface ", "entity "]
    return any(tok in t for tok in probable_tokens)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
