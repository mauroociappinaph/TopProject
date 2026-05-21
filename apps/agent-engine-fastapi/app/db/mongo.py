import os
from motor.motor_asyncio import AsyncIOMotorClient

# Configuración del cliente Async de MongoDB usando motor
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "agentarena")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

def get_mongo_db():
    """Retorna la base de datos de MongoDB activa."""
    return db

async def ping_mongo():
    """Realiza un ping a la base de datos para verificar conectividad."""
    try:
        await client.admin.command('ping')
        return True
    except Exception:
        return False
