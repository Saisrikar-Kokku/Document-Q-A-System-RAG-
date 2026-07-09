# Ingestion layer — reads documents of various formats into a unified schema.

from .document import Document, DocumentMetadata
from .registry import load_document

__all__ = ["Document", "DocumentMetadata", "load_document"]

