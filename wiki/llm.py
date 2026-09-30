"""Minimal Ollama client: chat generation (thinking off) and embeddings, with timing and memory numbers."""
import time

import psutil
import requests

from .config import EMBED_MODEL, GEN_MODEL, NUM_CTX, OLLAMA_URL


class OllamaError(RuntimeError):
    pass


class OllamaUnavailable(OllamaError):
    pass


class ModelMissing(OllamaError):
    pass


def _post(path, payload, timeout):
    try:
        r = requests.post(f"{OLLAMA_URL}{path}", json=payload, timeout=timeout)
    except requests.ConnectionError:
        raise OllamaUnavailable(
            f"Ollama is not reachable at {OLLAMA_URL}. Start it (open the Ollama app or run `ollama serve`) and retry."
        ) from None
    except requests.Timeout:
        raise OllamaError(f"Ollama did not answer {path} within {timeout}s.") from None
    if r.status_code == 404 and "not found" in r.text.lower():
        model = payload.get("model")
        raise ModelMissing(f"Model '{model}' is not installed. Run `ollama pull {model}` while online.")
    if r.status_code >= 400:
        raise OllamaError(f"Ollama error {r.status_code} on {path}: {r.text[:300]}")
    return r.json()


def is_up(timeout=2):
    try:
        requests.get(f"{OLLAMA_URL}/api/version", timeout=timeout)
        return True
    except requests.RequestException:
        return False


def loaded_models():
    """Models currently in memory according to Ollama (`ollama ps`): name -> size in bytes."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/ps", timeout=3).json()
        return {m["name"]: m.get("size", 0) for m in r.get("models", [])}
    except requests.RequestException:
        return {}


def system_memory():
    vm = psutil.virtual_memory()
    return {"ram_total_gb": round(vm.total / 1e9, 1), "ram_available_gb": round(vm.available / 1e9, 1)}


def chat(messages, model=GEN_MODEL, temperature=0.2, max_tokens=512, timeout=600, fmt=None):
    """Send chat messages to Gemma. Returns (text, stats)."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"num_ctx": NUM_CTX, "temperature": temperature, "num_predict": max_tokens},
    }
    if fmt:
        payload["format"] = fmt
    t0 = time.perf_counter()
    data = _post("/api/chat", payload, timeout)
    wall = time.perf_counter() - t0
    eval_n = data.get("eval_count", 0)
    eval_s = data.get("eval_duration", 0) / 1e9
    stats = {
        "model": model,
        "wall_s": round(wall, 2),
        "load_s": round(data.get("load_duration", 0) / 1e9, 2),
        "prompt_tokens": data.get("prompt_eval_count", 0),
        "output_tokens": eval_n,
        "tok_per_s": round(eval_n / eval_s, 1) if eval_s else None,
        "model_loaded_gb": round(loaded_models().get(model, 0) / 1e9, 2),
        **system_memory(),
    }
    return data["message"]["content"].strip(), stats


def embed(texts, model=EMBED_MODEL, timeout=600, batch=16):
    """Embed a list of strings. Returns a list of float lists."""
    out = []
    for i in range(0, len(texts), batch):
        data = _post("/api/embed", {"model": model, "input": texts[i:i + batch]}, timeout)
        out.extend(data["embeddings"])
    return out
