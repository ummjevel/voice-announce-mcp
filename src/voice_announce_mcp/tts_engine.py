"""Loads a FreyaTTS checkpoint once and keeps it warm in memory.

Model loading takes ~10s (see FreyaTTS/eval/results/speed_final.json,
load_s: 11.3) -- too slow to pay on every tool call, which is why this is an
MCP server (long-lived process) rather than a per-invocation script.
"""

from .config import Config

_ENGINE: "TTSEngine | None" = None


class TTSEngine:
    def __init__(self, model_id_or_path: str, device: str, steps: int, seed: int):
        from freyatts import FreyaTTS

        self.tts = FreyaTTS.from_pretrained(model_id_or_path, device=device)
        self.steps = steps
        self.seed = seed
        self.model_id_or_path = model_id_or_path
        self.device = device

    def synthesize_to_file(self, text: str, out_path: str) -> str:
        wav = self.tts.synthesize(text, steps=self.steps, seed=self.seed)
        self.tts.save_wav(wav, out_path)
        return out_path


def get_engine() -> TTSEngine:
    global _ENGINE
    if _ENGINE is None:
        cfg = Config.from_env()
        _ENGINE = TTSEngine(cfg.model, cfg.device, cfg.steps, cfg.seed)
    return _ENGINE
