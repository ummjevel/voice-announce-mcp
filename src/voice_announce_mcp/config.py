import os
from dataclasses import dataclass

# Not published to Hugging Face yet -- see project_voicechat_tts_distillation
# memory. Until it is, set VOICE_MCP_MODEL to a local checkpoint directory
# (e.g. .../FreyaTTS/checkpoints/distill_voiceA/final).
DEFAULT_MODEL = "ummjevel/freyatts-ko-voiceA"
DEFAULT_STEPS = 32
DEFAULT_SEED = 9  # voiceA's locked seed, per FreyaTTS/confirmed_voices/best_seeds.json


@dataclass
class Config:
    model: str
    device: str
    steps: int
    seed: int

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            model=os.environ.get("VOICE_MCP_MODEL", DEFAULT_MODEL),
            device=os.environ.get("VOICE_MCP_DEVICE") or _autodetect_device(),
            steps=int(os.environ.get("VOICE_MCP_STEPS", str(DEFAULT_STEPS))),
            seed=int(os.environ.get("VOICE_MCP_SEED", str(DEFAULT_SEED))),
        )


def _autodetect_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"
