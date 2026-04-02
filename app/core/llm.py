from __future__ import annotations

import json
from typing import Optional
from urllib.request import Request, urlopen


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    def generate_markdown_only(
        self,
        model: str,
        system: str,
        prompt: str,
        temperature: float = 0.2,
        num_predict: int = 1200,
        retry_once_on_fluff: bool = True,
    ) -> str:
        out = self._generate(model, system, prompt, temperature, num_predict)
        if retry_once_on_fluff and self._looks_like_fluff(out):
            stricter_system = system + "\n\nCRITICAL: Output ONLY the Markdown content. No preamble, no explanations, no greetings."
            out = self._generate(model, stricter_system, prompt, temperature, num_predict)
        return (out or "").strip()

    def _generate(self, model: str, system: str, prompt: str, temperature: float, num_predict: int) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        req = Request(
            url=f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")

    def _looks_like_fluff(self, text: Optional[str]) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return True
        banned_starts = (
            "sure",
            "here's",
            "here is",
            "of course",
            "certainly",
            "i can",
            "below is",
        )
        return any(t.startswith(b) for b in banned_starts)