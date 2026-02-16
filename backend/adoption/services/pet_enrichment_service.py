import re
from typing import Optional

# Keep it deterministic: no randomness, no external calls.

DEFAULT_FUN_TAGLINES = [
    "Ready to meet a new sidekick.",
    "Looking for a cozy home base.",
    "Here for good vibes and belly rubs (if offered).",
]

# Stable choice based on content hash-ish without randomness
def _stable_tagline(seed: str) -> str:
    if not seed:
        return DEFAULT_FUN_TAGLINES[0]
    idx = sum(ord(c) for c in seed) % len(DEFAULT_FUN_TAGLINES)
    return DEFAULT_FUN_TAGLINES[idx]


class PetEnrichmentService:
    """
    Deterministic, provider agnostic enrichment.

    Produces:
      short, warm, neutral summary (1 to 2 sentences)
      ONLY uses info present in raw_description
      never blocks ingestion
    """

    MAX_LEN = 220

    @staticmethod
    def generate_fun_neutral_summary(raw_description: Optional[str]) -> Optional[str]:
        if not raw_description:
            return None

        text = raw_description.strip()
        if not text:
            return None

        # 1) Normalize whitespace / strip boilerplate-y formatting
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"(?:\*+|_+|~+)", "", text).strip()

        # 2) Pull simple “facts” only if clearly present
        lowered = text.lower()

        # Temperament-ish keywords (only if present)
        traits = []
        for kw, label in [
            ("gentle", "gentle"),
            ("sweet", "sweet"),
            ("friendly", "friendly"),
            ("playful", "playful"),
            ("calm", "calm"),
            ("snuggle", "snuggly"),
            ("cuddle", "snuggly"),
            ("goofy", "goofy"),
            ("curious", "curious"),
            ("shy", "a little shy"),
            ("quiet", "quiet"),
            ("energetic", "energetic"),
            ("active", "active"),
        ]:
            if kw in lowered and label not in traits:
                traits.append(label)

        # Compatibility hints (only if explicitly mentioned)
        compat = []
        if "kids" in lowered or "children" in lowered:
            if "good with" in lowered or "great with" in lowered:
                compat.append("may do well with kids")
        if "dog" in lowered and ("good with" in lowered or "gets along" in lowered):
            compat.append("may enjoy dog friends")
        if "cat" in lowered and ("good with" in lowered or "gets along" in lowered):
            compat.append("may do well with cats")

        # 3) Build a 1–2 sentence summary that stays neutral
        # Sentence 1: warm neutral opening with 1–3 traits if present
        if traits:
            top = traits[:3]
            trait_phrase = ", ".join(top[:-1]) + (f", and {top[-1]}" if len(top) > 1 else top[0])
            s1 = f"A {trait_phrase} pup."
        else:
            s1 = "A pup with their own vibe."

        # Sentence 2: add compatibility if present; otherwise add deterministic tagline
        if compat:
            # keep short
            c = compat[0] if len(compat) == 1 else compat[0]
            s2 = f"They {c}."
        else:
            s2 = _stable_tagline(text)

        out = f"{s1} {s2}".strip()

        # 4) Hard cap length (deterministic)
        if len(out) > PetEnrichmentService.MAX_LEN:
            out = out[: PetEnrichmentService.MAX_LEN - 3].rstrip() + "..."

        return out
