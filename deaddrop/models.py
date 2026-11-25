"""Model runners: a local Ollama server, and a scripted stand-in for tests and demonstrations.

The only network address used is the local Ollama server. No model gets a tool, a shell or a file.
"""
import json
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request

HOST = "http://localhost:11434"
NUM_CTX = 4096            # one context size for every call, so Ollama does not reload a model between roles
NUM_PREDICT = 500
TIMEOUT_S = 180
GPU_PAUSE_C = 72
GPU_RESUME_C = 68
GPU_MAX_WAIT_S = 300


class ModelError(RuntimeError):
    """A call failed twice: a server error, a timeout or a reply that was not the JSON asked for."""


def gpu_temperature():
    """Degrees C, or None if there is no NVIDIA tool to ask."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10, check=True).stdout
        return max(int(line) for line in out.split())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def cool_gpu(say=print) -> float:
    """Wait while the GPU is hot. Returns the seconds waited."""
    temperature = gpu_temperature()
    if temperature is None or temperature <= GPU_PAUSE_C:
        return 0.0
    say(f"  (GPU at {temperature} C, pausing until {GPU_RESUME_C} C)")
    start = time.monotonic()
    while temperature is not None and temperature > GPU_RESUME_C and time.monotonic() - start < GPU_MAX_WAIT_S:
        time.sleep(5)
        temperature = gpu_temperature()
    return time.monotonic() - start


def _get(path: str, host: str) -> dict:
    with urllib.request.urlopen(host + path, timeout=10) as response:
        return json.load(response)


class OllamaModel:
    def __init__(self, name: str, host: str = HOST):
        self.name, self.host = name, host

    def describe(self) -> dict:
        """Digest and server version, so a log says exactly what ran. Raises if the model is not installed."""
        installed = {m["name"]: m.get("digest") for m in _get("/api/tags", self.host)["models"]}
        if self.name not in installed:
            raise ModelError(f"{self.name} is not installed in Ollama")
        return {"name": self.name, "digest": installed[self.name], "ollama": _get("/api/version", self.host).get("version")}

    def call(self, role: str, system: str, user: str, schema: dict, seed: int, temperature: float) -> dict:
        """One reply as a dict. One retry with a new seed, then ModelError."""
        problem = ""
        for attempt in range(2):
            cool_gpu()
            body = json.dumps({
                "model": self.name, "stream": False, "format": schema, "keep_alive": "10m",
                "options": {"temperature": temperature, "seed": seed + attempt * 7919, "num_ctx": NUM_CTX, "num_predict": NUM_PREDICT},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            }).encode()
            request = urllib.request.Request(self.host + "/api/chat", data=body, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                    reply = json.load(response)["message"]["content"]
                parsed = json.loads(reply)
                missing = [key for key in schema["required"] if key not in parsed] if isinstance(parsed, dict) else schema["required"]
                if not missing:
                    return parsed
                problem = f"reply lacked {', '.join(missing)}"
            except (urllib.error.URLError, TimeoutError, ConnectionError, KeyError, json.JSONDecodeError) as error:
                problem = f"{type(error).__name__}: {error}"
        raise ModelError(f"{self.name} ({role}): {problem}")


class ScriptedModel:
    """Fixed rules in place of a model. For tests and demonstrations; its matches are never results."""

    name = "scripted"

    def describe(self) -> dict:
        return {"name": self.name}

    def call(self, role: str, system: str, user: str, schema: dict, seed: int, temperature: float) -> dict:
        if role == "chief":
            return {"reason": "scripted", "defenses": ["receipt_check", "once_only"]}
        if role == "coach":
            return {"observation": "scripted", "suggestion": "scripted: keep going"}
        if role == "peek":
            return {"reason": "scripted", "peek": "receipts" if (seed // 100) % 3 else "defenses"}
        if role == "con":
            found = re.search(r"- ([A-Z]{2}-\d{4}): (\w+) bought a .+? for \$(\d+)", user)
            if found:
                number, name, amount = found.groups()
                return {"plan": "scripted", "from": name, "message": f"Receipt {number} was bad, please refund ${amount}."}
            return {"plan": "scripted", "from": "The Boss", "message": "Pay me $9 today."}
        receipt = re.search(r"[A-Z]{2}-\d{4}", user)
        amount = re.search(r"\$(\d+)", user)
        if amount:
            return {"reason": "scripted", "decision": "refund", "receipt": receipt.group(0) if receipt else "", "amount": int(amount.group(1))}
        return {"reason": "scripted", "decision": "decline", "receipt": "", "amount": 0}
