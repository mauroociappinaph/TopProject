import os
from typing import Dict, Any, List, TypedDict, Annotated
import json
from app.ai.ollama_client import generate_embedding, generate_completion
from app.ai.pinecone_client import query_pinecone
from app.db.mongo import get_mongo_db
import redis
from datetime import datetime

# Definición del Estado de LangGraph
class AgentState(TypedDict):
    query: str
    simulation_id: str
    rag_context: List[str]
    current_agent: str
    draft_response: str
    final_response: str
    validation_approved: bool
    iterations: int

# Cliente Redis para actualizaciones en tiempo real
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

async def notify_realtime(simulation_id: str, agent_name: str, action: str, x: int, y: int, extra: Dict[str, Any]):
    """Publica actualizaciones en tiempo real a Redis Pub/Sub y las guarda en MongoDB."""
    payload = {
        "simulation_id": simulation_id,
        "agent_name": agent_name,
        "action": action,
        "coordinates": {"x": x, "y": y},
        "extra": extra,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # 1. Redis Broadcast
    redis_client.publish("simulation:updates", json.dumps(payload))
    
    # 2. MongoDB Persistence
    try:
        db = get_mongo_db()
        await db["agent_logs"].insert_one(payload.copy())
    except Exception as e:
        print(f"[Mongo Error] No se pudo guardar log del agente: {e}")

# Definición de los Nodos del Grafo
async def researcher_node(state: AgentState) -> AgentState:
    """Nodo 1: Investigador. Genera embeddings y consulta RAG en Pinecone."""
    simulation_id = state["simulation_id"]
    query = state["query"]
    
    await notify_realtime(
        simulation_id=simulation_id,
        agent_name="Investigador",
        action="Generando embedding de consulta semántica con Ollama...",
        x=100, y=150,
        extra={"query": query}
    )
    
    # 1. Generar embedding con Ollama
    vector = generate_embedding(query)
    
    await notify_realtime(
        simulation_id=simulation_id,
        agent_name="Investigador",
        action="Consultando documentos de contexto en Pinecone DB...",
        x=100, y=150,
        extra={"vector_dimension": len(vector)}
    )
    
    # 2. Buscar en Pinecone
    results = query_pinecone(vector, top_k=2)
    context_chunks = [res["metadata"]["content"] for res in results]
    
    state["rag_context"] = context_chunks
    state["current_agent"] = "Redactor"
    
    return state

async def writer_node(state: AgentState) -> AgentState:
    """Nodo 2: Redactor. Utiliza LLM local en Ollama con contexto RAG inyectado."""
    simulation_id = state["simulation_id"]
    query = state["query"]
    context = "\n".join(state["rag_context"])
    
    await notify_realtime(
        simulation_id=simulation_id,
        agent_name="Redactor",
        action="Generando respuesta estructurada usando LLM local en Ollama...",
        x=300, y=200,
        extra={"context_length": len(context)}
    )
    
    # Prompt Engineering avanzado para inyección de RAG
    system_prompt = (
        "Sos un Arquitecto de Software Senior experto en sistemas distribuidos. "
        "Responde de forma concisa y técnica basándote ÚNICAMENTE en el siguiente contexto:\n"
        f"--- CONTEXTO RAG ---\n{context}\n--------------------"
    )
    prompt = f"Consulta del desarrollador: {query}"
    
    # Generación con Ollama
    response = generate_completion(prompt, system_prompt, model="llama3")
    
    state["draft_response"] = response
    state["current_agent"] = "Supervisor"
    state["iterations"] += 1
    
    return state

async def supervisor_node(state: AgentState) -> AgentState:
    """Nodo 3: Supervisor. Valida la calidad y consistencia técnica de la respuesta."""
    simulation_id = state["simulation_id"]
    draft = state["draft_response"]
    
    await notify_realtime(
        simulation_id=simulation_id,
        agent_name="Supervisor",
        action="Evaluando respuesta generada para control de calidad...",
        x=500, y=150,
        extra={"draft_preview": draft[:50] + "..."}
    )
    
    # Simulación de evaluación técnica
    # En producción real, se puede usar un LLM clasificador (Ollama/Structured Output)
    approved = len(draft) > 20 and "Simulación" not in draft
    
    state["validation_approved"] = approved
    if approved:
        state["final_response"] = draft
        await notify_realtime(
            simulation_id=simulation_id,
            agent_name="Supervisor",
            action="Respuesta aprobada con éxito. Finalizando simulación.",
            x=500, y=150,
            extra={"status": "APPROVED"}
        )
    else:
        state["current_agent"] = "Redactor"
        await notify_realtime(
            simulation_id=simulation_id,
            agent_name="Supervisor",
            action="Respuesta rechazada por falta de detalles. Solicitando corrección...",
            x=500, y=150,
            extra={"status": "REJECTED"}
        )
        
    return state

# Orquestador del Ciclo de Ejecución
async def execute_multi_agent_simulation(query: str, user_id: str, simulation_id: str) -> Dict[str, Any]:
    """Orquesta la ejecución secuencial interactiva del grafo de agentes (LangGraph)."""
    # Inicialización del estado
    state: AgentState = {
        "query": query,
        "simulation_id": simulation_id,
        "rag_context": [],
        "current_agent": "Investigador",
        "draft_response": "",
        "final_response": "",
        "validation_approved": False,
        "iterations": 0
    }
    
    # 1. Ejecutar Investigador
    state = await researcher_node(state)
    
    # 2. Ejecutar Redactor y Supervisor en bucle si es necesario (Máximo 3 iteraciones)
    while not state["validation_approved"] and state["iterations"] < 3:
        state = await writer_node(state)
        state = await supervisor_node(state)
        
    return {
        "simulation_id": simulation_id,
        "user_id": user_id,
        "query": query,
        "final_response": state["final_response"] or state["draft_response"],
        "iterations": state["iterations"],
        "status": "success" if state["validation_approved"] else "completed_with_warnings"
    }
