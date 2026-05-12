from pydantic import BaseModel, Field, model_validator


class RetrievalSettings(BaseModel):
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.6, ge=0, le=1)
    strict_refusal: bool = True
    enable_hybrid_search: bool = False
    enable_rerank: bool = False


class ChunkingSettings(BaseModel):
    chunk_size: int = Field(default=800, ge=100, le=3000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)
    min_chunk_size: int = Field(default=100, ge=20, le=1000)
    enable_section_path: bool = True

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingSettings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        return self


class GenerationSettings(BaseModel):
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1200, ge=100, le=8000)


class AppSettingsSchema(BaseModel):
    retrieval: RetrievalSettings = RetrievalSettings()
    chunking: ChunkingSettings = ChunkingSettings()
    generation: GenerationSettings = GenerationSettings()
