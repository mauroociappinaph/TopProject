import os
import json
import base64
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import redis
from Crypto.Cipher import AES

app = FastAPI(
    title="AgentArena AI Engine",
    description="Motor de orquestación de agentes usando LangGraph, RAG con Pinecone y encriptación AES-256-GCM",
    version="1.0.0"
)

# Configuración de conexiones
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

AES_KEY = os.getenv("AES_SECRET_KEY", "sixteenbytekey123")  # Clave de 16, 24 o 32 bytes

# Modelos Pydantic
class AgentExecutionRequest(BaseModel):
    query: str
    user_id: str
    simulation_id: str

# Helper para Encriptación AES-256-GCM (Capa de Seguridad Zero Trust)
def encrypt_metadata(data: str, key: str) -> Dict[str, str]:
    """Cifra metadatos sensibles de RAG usando AES-256-GCM."""
    cipher = AES.new(key.encode('utf-8'), AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode('utf-8'))
    return {
        "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
        "nonce": base64.b64encode(cipher.nonce).decode('utf-8'),
        "tag": base64.b64encode(tag).decode('utf-8')
    }

def decrypt_metadata(encrypted: Dict[str, str], key: str) -> str:
    """Descifra metadatos sensibles de RAG verificando su integridad."""
    nonce = base64.b64decode(encrypted["nonce"])
    ciphertext = base64.b64decode(encrypted["ciphertext"])
    tag = base64.b64decode(encrypted["tag"])
    cipher = AES.new(key.encode('utf-8'), AES.MODE_GCM, nonce=nonce)
    decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)
    return decrypted_bytes.decode('utf-8')

from app.db.mongo import get_mongo_db
from datetime import datetime

# Simulación de un Grafo de LangGraph
class SimpleLangGraphOrchestrator:
    def __init__(self, simulation_id: str, redis_conn: redis.Redis):
        self.simulation_id = simulation_id
        self.redis = redis_conn
        self.db = get_mongo_db()

    async def notify_step(self, agent_name: str, action: str, x: int, y: int, extra: Dict[str, Any]):
        """Publica el estado actual en Redis y guarda la traza de ejecución en MongoDB."""
        payload = {
            "simulation_id": self.simulation_id,
            "agent_name": agent_name,
            "action": action,
            "coordinates": {"x": x, "y": y},
            "extra": extra,
            "timestamp": datetime.utcnow().isoformat()
        }
        # 1. Publicar a Redis Pub/Sub
        self.redis.publish("simulation:updates", json.dumps(payload))
        
        # 2. Guardar asíncronamente la traza en MongoDB
        try:
            await self.db["agent_logs"].insert_one(payload.copy())
        except Exception as e:
            print(f"Error al guardar traza en MongoDB: {e}")

    async def execute(self, query: str) -> Dict[str, Any]:
        # Nodo 1: Investigador (RAG + Pinecone Vector Search Mocked)
        await self.notify_step("Investigador", "Buscando contexto en Pinecone...", 100, 150, {"query": query})
        
        # Simulación de búsqueda semántica y cifrado
        raw_context = f"Documento confidencial sobre {query}: La clave del éxito es la arquitectura limpia."
        encrypted_context = encrypt_metadata(raw_context, AES_KEY)
        
        # Nodo 2: Redactor (Inferencia con Ollama/LLM Mocked)
        await self.notify_step("Redactor", "Generando respuesta usando Ollama...", 300, 200, {
            "context_cifrado": encrypted_context["ciphertext"]
        })
        
        # Simulación de desencriptación antes de la inferencia
        decrypted_context = decrypt_metadata(encrypted_context, AES_KEY)
        response_text = f"Respuesta basada en: '{decrypted_context}'. El flujo se completó correctamente."
        
        # Nodo 3: Supervisor (Validación)
        await self.notify_step("Supervisor", "Validando respuesta final...", 500, 150, {"aprobado": True})
        
        return {
            "status": "completed",
            "response": response_text,
            "steps": ["Investigador (RAG)", "Redactor (Ollama)", "Supervisor (Aprobado)"]
        }


# Guardia de Seguridad Zero Trust: Firma HMAC interna
def verify_internal_signature(x_internal_signature: str = Header(...)):
    """Verifica que la llamada provenga del NestJS Gateway usando firma secreta."""
    EXPECTED_SIGNATURE = os.getenv("INTERNAL_HMAC_SECRET", "super-secret-signature-key")
    if x_internal_signature != EXPECTED_SIGNATURE:
        raise HTTPException(status_code=403, detail="Firma de microservicio interna no válida. Zero Trust activa.")

@app.post("/api/v1/agent/run", dependencies=[Depends(verify_internal_signature)])
async def run_agent_workflow(request: AgentExecutionRequest):
    try:
        orchestrator = SimpleLangGraphOrchestrator(request.simulation_id, redis_client)
        result = await orchestrator.execute(request.query)
        return {
            "simulation_id": request.simulation_id,
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
