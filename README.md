# 🤖 ChatBot PlantUML - Guía de Configuración

## 📋 Prerrequisitos

### 1. Instalar Java
- Descarga Java desde: https://www.oracle.com/java/technologies/downloads/
- O instala OpenJDK desde: https://adoptium.net/
- Verifica la instalación ejecutando: `java -version`

### 2. Configurar API de Google Gemini
1. Ve a: https://ai.google.dev/
2. Crea una cuenta y obtén tu API Key
3. Copia el archivo `.env.example` a `.env`
4. Reemplaza `tu_clave_de_gemini_aqui` con tu API Key real

## 🚀 Instalación

1. **Instalar dependencias de Python**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar variables de entorno**:
   - Copia `.env.example` a `.env`
   - Edita `.env` con tu API Key de Gemini

3. **Ejecutar la aplicación**:
   ```bash
   python app.py
   ```

4. **Abrir en el navegador**:
   - Ve a: http://localhost:5000

## 📁 Estructura del Proyecto

```
ia/
├── app.py                     # Servidor Flask principal
├── script.py                  # Script para ejecutar PlantUML
├── plantuml-1.2025.4.jar      # Ejecutable de PlantUML
├── requirements.txt            # Dependencias de Python
├── .env                       # Variables de entorno (crear desde .env.example)
├── templates/
│   └── index.html             # Interfaz del chatbot
├── temp/                      # Archivos temporales .txt y .png
└── temp_imgs/                 # Imágenes finales para mostrar
```

## 🔄 Flujo de Funcionamiento

1. **Usuario envía prompt** → Frontend envía mensaje a `/chat`
2. **LLM genera PlantUML** → Gemini convierte prompt a código PlantUML
3. **Guardar archivo .txt** → Código se guarda en `temp/` con ID único
4. **Ejecutar PlantUML** → `script.py` ejecuta JAR y genera PNG en `temp/`
5. **Mover imagen** → PNG se copia a `temp_imgs/` 
6. **Mostrar resultado** → Frontend recibe URL y muestra imagen

## 🛠️ Troubleshooting

### Error: "Java no encontrado"
- Instala Java y asegúrate de que esté en el PATH del sistema
- Reinicia la terminal después de instalar Java

### Error: "API Key no válida"
- Verifica que tu API Key de Gemini sea correcta
- Asegúrate de que el archivo `.env` esté en el directorio raíz

### Error: "PlantUML no genera imagen"
- Verifica que el archivo `plantuml-1.2025.4.jar` exista
- Comprueba que Java esté funcionando correctamente
- Revisa los logs en la terminal para más detalles

## 📝 Ejemplo de Uso

Prueba enviando este código PlantUML:

```plantuml
@startuml
left to right direction
actor Cliente
participant "Aplicación" as app
participant "Servidor" as server

Cliente -> app: Realiza solicitud
app -> server: Procesa datos
server --> app: Devuelve respuesta
app --> Cliente: Muestra resultado
@enduml
```

O simplemente describe lo que quieres en lenguaje natural:
"Crea un diagrama de secuencia para un proceso de login"

## 🎯 Características

- ✅ Interfaz web moderna y responsiva
- ✅ Generación automática de código PlantUML con IA
- ✅ Soporte para código PlantUML directo
- ✅ Visualización en tiempo real de diagramas
- ✅ Gestión automática de archivos temporales
- ✅ Indicadores de estado y errores claros
