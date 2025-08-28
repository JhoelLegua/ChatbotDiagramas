import subprocess
import os
import sys
from pathlib import Path

def ejecutar_plantuml(archivo_entrada):
    """
    Ejecuta PlantUML con el archivo especificado y guarda el resultado en la carpeta temp
    
    Args:
        archivo_entrada (str): Nombre del archivo de entrada (ej: 'ano.txt')
    """
    # Rutas del proyecto
    directorio_proyecto = Path(__file__).parent
    jar_plantuml = directorio_proyecto / "plantuml-1.2025.4.jar"
    carpeta_temp = directorio_proyecto / "temp"
    archivo_completo = directorio_proyecto / archivo_entrada
    
    # Verificar que el archivo JAR existe
    if not jar_plantuml.exists():
        print(f"Error: No se encontró el archivo {jar_plantuml}")
        return False
    
    # Verificar que el archivo de entrada existe
    if not archivo_completo.exists():
        print(f"Error: No se encontró el archivo de entrada {archivo_completo}")
        return False
    
    # Crear carpeta temp si no existe
    carpeta_temp.mkdir(exist_ok=True)
    
    # Construir el comando
    comando = [
        "java", 
        "-jar", 
        str(jar_plantuml),
        "-o", 
        str(carpeta_temp),  # Directorio de salida
        str(archivo_completo)
    ]
    
    try:
        print(f"Ejecutando: {' '.join(comando)}")
        
        # Ejecutar el comando
        resultado = subprocess.run(
            comando,
            cwd=directorio_proyecto,
            capture_output=True,
            text=True,
            check=True
        )
        
        print("✓ PlantUML ejecutado exitosamente")
        print(f"Resultado guardado en: {carpeta_temp}")
        
        if resultado.stdout:
            print(f"Salida: {resultado.stdout}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar PlantUML: {e}")
        print(f"Código de error: {e.returncode}")
        if e.stdout:
            print(f"Salida estándar: {e.stdout}")
        if e.stderr:
            print(f"Error estándar: {e.stderr}")
        return False
    
    except FileNotFoundError:
        print("Error: Java no está instalado o no está en el PATH del sistema")
        return False

def main():
    """Función principal del script"""
    if len(sys.argv) != 2:
        print("Uso: python script.py <archivo_entrada>")
        print("Ejemplo: python script.py ano.txt")
        sys.exit(1)
    
    archivo_entrada = sys.argv[1]
    exito = ejecutar_plantuml(archivo_entrada)
    
    if not exito:
        sys.exit(1)

if __name__ == "__main__":
    main()