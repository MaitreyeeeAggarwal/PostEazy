import json
import os
from pathlib import Path
from typing import Any, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class ContentCache:
    def __init__(self, cache_dir: str = "work/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_path(self, stage: str, key: str, ext: str = ".json") -> Path:
        stage_dir = self.cache_dir / stage
        stage_dir.mkdir(parents=True, exist_ok=True)
        return stage_dir / f"{key}{ext}"

    def exists(self, stage: str, key: str, ext: str = ".json") -> bool:
        return self.get_path(stage, key, ext).is_file()

    def load_json(self, stage: str, key: str) -> Optional[dict]:
        p = self.get_path(stage, key, ".json")
        if not p.is_file():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_model(self, stage: str, key: str, model_cls: Type[T]) -> Optional[T]:
        data = self.load_json(stage, key)
        if data is None:
            return None
        return model_cls.model_validate(data)

    def save_json(self, stage: str, key: str, data: Any) -> Path:
        p = self.get_path(stage, key, ".json")
        if isinstance(data, BaseModel):
            raw = data.model_dump(mode="json")
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], BaseModel):
            raw = [item.model_dump(mode="json") for item in data]
        else:
            raw = data
        
        with open(p, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)
        return p

    def save_file(self, stage: str, key: str, source_path: str, ext: str) -> Path:
        p = self.get_path(stage, key, ext)
        with open(source_path, "rb") as sf, open(p, "wb") as df:
            df.write(sf.read())
        return p
