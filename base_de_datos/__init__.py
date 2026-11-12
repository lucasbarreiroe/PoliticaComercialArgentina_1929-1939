"""Módulo de conexión y esquemas de la base de datos Supabase en 3NF."""
from .database_connection import supabase, test_connection

__all__ = ["supabase", "test_connection"]
