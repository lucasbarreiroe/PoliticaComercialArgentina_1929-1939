"""
Conexión central a la base de datos de Supabase.

Carga las variables de entorno desde el archivo .env y arma el cliente 
para que lo usen todos los extractores y scripts de análisis del proyecto.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Levantamos las credenciales locales (.env en la raíz del proyecto)
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

URL: str = os.getenv("SUPABASE_URL")
KEY: str = os.getenv("SUPABASE_KEY")

if not URL or not KEY:
    raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env")

# Cliente único reutilizable en todo el proyecto
supabase: Client = create_client(URL, KEY)


def test_connection():
    """Prueba rápida para confirmar que llegamos bien a las tablas de Supabase."""
    try:
        response = supabase.table("personas").select("id_persona").limit(1).execute()
        print("Conexión a Supabase exitosa.")
        return True
    except Exception as e:
        print(f"Error al conectar con Supabase: {e}")
        return False


if __name__ == "__main__":
    test_connection()

