from typing import List, Optional, Dict, Any
import numpy as np
from functools import lru_cache

from ..core.config import settings


class EmbeddingService:
    """Service for generating text embeddings for semantic search."""
    
    _model = None
    
    @classmethod
    def get_model(cls):
        """Lazy load the embedding model."""
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                cls._model = None
        return cls._model
    
    def prepare_food_text(
        self,
        name: str,
        description: Optional[str] = None,
        ingredients: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> str:
        """Prepare text for food item embedding."""
        parts = [name]
        
        if description:
            parts.append(description)
        
        if category:
            parts.append(f"Category: {category}")
        
        if ingredients:
            parts.append(f"Ingredients: {', '.join(ingredients)}")
        
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")
        
        return " ".join(parts)
    
    def prepare_asset_text(
        self,
        name: str,
        description: Optional[str] = None,
        specifications: Optional[Dict[str, Any]] = None,
        vendor: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Prepare text for IT asset embedding."""
        parts = [name]
        
        if description:
            parts.append(description)
        
        if vendor:
            parts.append(f"Vendor: {vendor}")
        
        if specifications:
            spec_parts = []
            for key, value in specifications.items():
                spec_parts.append(f"{key}: {value}")
            parts.append(f"Specifications: {', '.join(spec_parts)}")
        
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")
        
        return " ".join(parts)
    
    async def generate_embedding(
        self,
        text: str
    ) -> Optional[List[float]]:
        """Generate embedding for text."""
        model = self.get_model()
        if model is None:
            # Return None if model not available
            return None
        
        try:
            embedding = model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts."""
        model = self.get_model()
        if model is None:
            return [None] * len(texts)
        
        try:
            embeddings = model.encode(texts, normalize_embeddings=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            print(f"Error generating embeddings batch: {e}")
            return [None] * len(texts)