import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar las variables de entorno
load_dotenv()

URL: str = os.getenv("SUPABASE_URL")
KEY: str = os.getenv("SUPABASE_KEY")

# Inicializar el cliente de Supabase
supabase: Client = create_client(URL, KEY)

def test_connection():
    """Función simple para verificar que la conexión está activa."""
    try:
        # Intentamos hacer un select a la tabla parlamentarios
        response = supabase.table('parlamentarios').select("*").limit(1).execute()
        print("Conexión a Supabase establecida con éxito.")
        return True
    except Exception as e:
        print(f"Error al conectar con Supabase: {e}")
        return False

if __name__ == "__main__":
    test_connection()