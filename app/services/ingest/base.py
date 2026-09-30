from abc import ABC, abstractmethod
from app.core.ir import DocIR

class DocumentExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> DocIR:
        """Extract raw content blocks from document into DocIR format."""
        pass
