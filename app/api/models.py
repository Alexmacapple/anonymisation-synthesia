"""Modèles Pydantic pour les requêtes et réponses API."""

from pydantic import BaseModel, Field


class NERAnonymizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500000)
    mode: str = Field(default="mask", pattern="^(mask|redact|hash|anon)$")
    detection_mode: str = Field(default="hybrid", pattern="^(regex|ner|hybrid)$")
    fort: bool = False
    tech: bool = False
    whitelist: list[str] = []
    blacklist: list[str] = []


class NERAnonymizeResponse(BaseModel):
    texte_original: str
    texte_pseudonymise: str
    correspondances: list[dict]
    stats: dict
    score: dict


class NERExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500000)
    labels: list[str] = []
    detection_mode: str = Field(default="hybrid", pattern="^(regex|ner|hybrid)$")
    fort: bool = False
    tech: bool = False
    threshold: float = Field(default=0.4, ge=0.0, le=1.0)


class NERExtractResponse(BaseModel):
    entities: list[dict]
    count: int
    detection_mode: str


class NERDeanonymizeRequest(BaseModel):
    text: str
    mapping: dict[str, str]


class NERDeanonymizeResponse(BaseModel):
    texte_original: str
    remplacements: int


class HealthResponse(BaseModel):
    status: str
    version: str
    ner: dict
    dictionnaires: dict
