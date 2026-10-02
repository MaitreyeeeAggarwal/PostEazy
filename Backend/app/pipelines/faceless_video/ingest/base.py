from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol
from app.core.ir import DocIR

class DocumentExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> DocIR:
        """Extract raw content blocks from document into DocIR format."""
        pass
