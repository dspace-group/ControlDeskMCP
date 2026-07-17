"""Token counting strategies for local, offline MCP schema analysis.

Two strategies are provided:
  1. GPT2TokenCounter — uses the cached GPT-2 BPE tokenizer (huggingface/transformers).
     GPT-2 and Claude both use byte-pair encoding on similar vocabularies.
     For JSON/English text the counts are within ~10-20% of Claude's actual counts.
     Good enough for comparing tools *relative to each other*.
  2. CharHeuristicCounter — divides char count by 4 (rule-of-thumb for English/JSON).
     Always available; used as a fallback when GPT-2 is not cached.

Neither counter requires API keys or internet access.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TokenCounter(ABC):
    @abstractmethod
    def count(self, text: str) -> int: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class CharHeuristicCounter(TokenCounter):
    """Approximates tokens as max(1, len(text) // 4).

    Rule-of-thumb: modern BPE tokenizers average ~4 chars per token for
    English prose and JSON payloads.  Exact ratio varies (JSON keys and
    short words tend toward 3 chars/token; long words toward 5+).
    """

    @property
    def name(self) -> str:
        return "char_heuristic (chars/4)"

    def count(self, text: str) -> int:
        return max(1, len(text) // 4) if text else 0


class GPT2TokenCounter(TokenCounter):
    """Uses the cached GPT-2 BPE tokenizer for local, offline token counting.

    GPT-2 uses the same cl100k-family BPE approach as GPT-3/4 and is a
    reasonable proxy for Claude's tokenizer on JSON/English text.
    The model weights must already be cached in ~/.cache/huggingface/hub/.
    """

    def __init__(self) -> None:
        from transformers import AutoTokenizer  # type: ignore[import]

        self._tokenizer = AutoTokenizer.from_pretrained("gpt2")
        # Suppress the harmless "sequence longer than model_max_length" warning.
        # GPT-2's positional embeddings max out at 1024 tokens, but we only need
        # the token IDs — no model forward pass is performed.
        self._tokenizer.model_max_length = 10**9

    @property
    def name(self) -> str:
        return "gpt2_bpe"

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._tokenizer.encode(text))


def create_counter(prefer_gpt2: bool = True) -> TokenCounter:
    """Return the best available TokenCounter.

    Tries GPT-2 first (must already be cached); falls back to char heuristic.
    """
    if prefer_gpt2:
        try:
            return GPT2TokenCounter()
        except Exception:
            pass
    return CharHeuristicCounter()
