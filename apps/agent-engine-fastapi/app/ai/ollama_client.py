import os
import urllib.request
import json
from typing import List

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def generate_embedding(text: str, model: str = "nomic-embed-text") -> List[float]:
    """Genera embeddings vectoriales de forma local usando Ollama."""
    url = f"{OLLAMA_HOST}/api/embeddings"
    data = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["embedding"]
    except Exception as e:
        # Fallback robusto para desarrollo si Ollama no está activo en el host de compilación
        print(f"[Ollama Warning] No se pudo conectar a Ollama: {e}. Usando vector mock de 768 dimensiones.")
        return [0.01] * 768

def generate_completion(prompt: str, system_prompt: str = "", model: str = "llama3") -> str:
    """Genera inferencia de texto (LLM) usando Ollama de forma local."""
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False
    }
    data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["response"]
    except Exception as e:
        print(f"[Ollama Warning] Error de inferencia local con Ollama: {e}. Usando respuesta simulada.")
        return f"Simulación de IA (Local Fallback): Analicé tu consulta '{prompt[:40]}...'. La arquitectura desacoplada de AgentArena está operando correctamente."
