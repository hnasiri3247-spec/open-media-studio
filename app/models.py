from typing import Literal
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    script: str = Field(min_length=1)
    format: Literal["9:16", "16:9", "1:1"] = "9:16"
    duration: int = Field(default=15, ge=1, le=300)
    style: str = "cartoon"

class SceneCreate(BaseModel):
    prompt: str = Field(min_length=1)
    duration: int = Field(default=5, ge=1, le=60)

class VoiceCreate(BaseModel):
    text: str = Field(min_length=1)
    voice: str = "default"

class MediaRequest(BaseModel):
    prompt: str = Field(min_length=1)
    duration: int = Field(default=5, ge=1, le=60)

class RenderRequest(BaseModel):
    project_id: str
