from dataclasses import dataclass
from typing import List, Dict, Optional, Protocol


@dataclass
class ExtractedEntity:
    """
    Normalized entity shape used across all extractors (LangExtract, LLM, spaCy, etc.)
    """
    text: str
    start: int
    end: int
    label: str  # e.g., "medication", "dosage", "route", "frequency", "duration", "condition", etc.
    attributes: Optional[Dict] = None
    confidence: Optional[float] = None


class MedicalExtractor(Protocol):
    """
    Protocol for pluggable extractors. Implementations must return grounded entities with offsets.
    """
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        ...


def map_label_to_category(label: str) -> str:
    """
    Map extractor-specific labels to our frontend categories (kept simple for now).
    Frontend currently just uses 'category' for styling, so we keep it close to the label.
    """
    if not label:
        return "medical"
    l = label.lower()
    # Basic normalization
    if l in {"drug", "med", "medication", "medicine"}:
        return "medication"
    if l in {"dose", "dosage", "strength"}:
        return "dosage"
    if l in {"freq", "frequency"}:
        return "frequency"
    if l in {"route"}:
        return "route"
    if l in {"duration"}:
        return "duration"
    if l in {"condition", "diagnosis", "disease"}:
        return "condition"
    if l in {"symptom"}:
        return "symptom"
    return l
