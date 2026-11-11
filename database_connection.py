import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

URL: str = os.getenv("SUPABASE_URL")
KEY: str = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(URL, KEY)


def test_connection():
    """Función simple para verificar que la conexión al esquema 3NF está activa."""
    try:
        response = supabase.table("personas").select("id_persona").limit(1).execute()
        print("Conexión a Supabase (Esquema 3NF) establecida con éxito.")
        return True
    except Exception as e:
        print(f"Error al conectar con Supabase: {e}")
        return False


if __name__ == "__main__":
    test_connection()