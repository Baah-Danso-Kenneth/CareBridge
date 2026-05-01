import logging
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

import cohere

from app.memory.base import MemoryBase
from app.config import config

logger = logging.getLogger(__name__)


class SemanticMemory(MemoryBase):
    """
    Semantic Memory for medical knowledge retrieval.
    uses Cohere embeddings + FAISS for similarity search.
    Stores: Clinical guidelines, drug information, symptom-disease mappings
    """

    def __init__(self, knowledge_path: Optional[str] = None):
        """
        Initialize semantic memory.

        Args:
          Knowledge path: Path to JSON file with medical documents
        """

        self.co = cohere.Client(config.COHERE_API_KEY)
        self.index = None
        self.documents = []
        self.metadata = []

        if knowledge_path:
            self._load_and_index(knowledge_path)

        logger.info("SemanticMemory initialized")


    def _load_and_index(self, knowledge_path:str):
        """Load medical knowledge and build FAISS index"""
        try:
            with open(knowledge_path, 'r') as f:
                data = json.load(f)
                documents = data.get("documents",[])
            logger.info(f"Loading {len(documents)} medical into semantic memory")

            for doc in documents:
                text = doc.get("text", "")
                self.documents.append(text)
                self.metadata.append(doc.get("metadata", {}))  

            if not self.documents:
                logger.warning("Nod documents loaded Semantic Memory willbe empty")

                return
            
            response = self.co.embed(
                texts=self.documents,
                model="embed-english-v3.0",
                input_type="search_document"
            )

            embeddings = np.array(response.embeddings).astype("float32")

            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)

            logger.info(f"FAISS index built with {len.self.documents} vector")


        except Exception as e:
            logger.error(f"Failed to load semantic memory: {e}")

    

    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant medical knowledge.

        Args:
            query: Search query (e.g, "chest pain causes")
            k: Number of results to return

        Returns:
            List of relevant document with content and metadata
        """
        if not self.index or not self.documents:
            logger.warning("Semantic memory index is empty. Returning empty results")
            return []
        
        try:
            response = self.co.embed(
                texts=[query],
                model="embed-english-v3.0",
                input_type="search_query"
            )

            query_embedding = np.array(response.embeddings).astype("float32")

            # Search FAISS
            k = min(k, len(self.documents))
            distances, indices = self.index.search(query_embedding, k)

            results = []

            for i, idx in enumerate(indices[0]):
                similarity = 1/ (1 + distances[0][i])
                results.append({
                    "content": self.documents[idx],
                    "metadata": self.metadata[idx],
                    "similarity": float(similarity)
                })

            logger.debug(f"Semantic search returnd {len(results)} results for query")

            return results
        

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
        

    def add_document(self, text: str, metadata: Dict[str, Any]) -> bool:
        """
        Add a new document to semantic memory.
        Args:
            text: Document text content
            metadata: Associated metadata (source, category, etc.)
        """

        try:
            # Add to localStorage
            self.documents.append(text)
            self.metadata.append(metadata)

            response = self.co.embed(
                texts=[text],
                model="embed-english-v3.0",
                input_type="search_document"
            )

            embedding = np.array(response.embeddings).astype("float32")

            # Add to FAISS index
            if self.index is None:
                dimension = embedding.shape[1]
                self.index = faiss.IndexFlatL2(dimension)

            self.index.add(embedding)
            logger.info(f"Added document to semantic memory")

            return True
        
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False
        


    def store(self, key: str, value: Any) -> bool:
        """
        Store a document by key.
        Value should be dict with 'text' and 'metadata'
        """

        if isinstance(value, dict) and 'text' in value:
            metadata = value.get("metadata", {})
            return self.add_document(value["text"],metadata)
        
        return False

        
    def retrieve(self, key: str) -> bool:
        """Retrieve by key - not directly supported."""
        logger.warning("SemanticMemory. retrieve not implemented")
        return None
    
    def update(self, key: str, value: Any) -> bool:
        """Update not supported for semantic memory"""
        logger.warning("SemanticMemory. update not implemented")
        return False
    
    def delete(self, key: str) -> bool:
        """Delete not supported for semantic memory"""
        logger.warning("SemanticMemory.delete is not implemented")
        return False