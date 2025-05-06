"""
Script para añadir las nuevas columnas al modelo SyncLog en la base de datos.

Este script añade las siguientes columnas:
- start_date (VARCHAR)
- end_date (VARCHAR)
- records_processed (INTEGER)
"""

import os
import sys
from sqlalchemy import create_engine, text

# Obtener la URL de la base de datos del entorno o usar la configurada en app.py
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require")

# Imprimir mensaje de inicio
print("Iniciando actualización de la tabla sync_logs...")

try:
    # Crear conexión a la base de datos
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    # Añadir columna start_date si no existe
    print("Añadiendo columna start_date...")
    try:
        conn.execute(text("ALTER TABLE sync_logs ADD COLUMN IF NOT EXISTS start_date VARCHAR(20)"))
        print("- Columna start_date añadida correctamente o ya existía")
    except Exception as e:
        print(f"- Error al añadir columna start_date: {str(e)}")
    
    # Añadir columna end_date si no existe
    print("Añadiendo columna end_date...")
    try:
        conn.execute(text("ALTER TABLE sync_logs ADD COLUMN IF NOT EXISTS end_date VARCHAR(20)"))
        print("- Columna end_date añadida correctamente o ya existía")
    except Exception as e:
        print(f"- Error al añadir columna end_date: {str(e)}")
    
    # Añadir columna records_processed si no existe
    print("Añadiendo columna records_processed...")
    try:
        conn.execute(text("ALTER TABLE sync_logs ADD COLUMN IF NOT EXISTS records_processed INTEGER DEFAULT 0"))
        print("- Columna records_processed añadida correctamente o ya existía")
    except Exception as e:
        print(f"- Error al añadir columna records_processed: {str(e)}")
    
    # Confirmar los cambios
    conn.commit()
    print("Todos los cambios han sido confirmados.")
    
    # Cerrar la conexión
    conn.close()
    print("Actualización completada con éxito.")
    
except Exception as e:
    print(f"Error durante la actualización: {str(e)}")
    sys.exit(1)