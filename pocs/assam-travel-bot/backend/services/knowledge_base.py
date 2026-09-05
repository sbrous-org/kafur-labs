import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KnowledgeBase:
    """Simple in-memory KB with TF-IDF vector search (no external dependencies for POC)."""

    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)
        self.places = []
        self.vectorizer = None
        self.vectors = None
        self.load()

    def load(self):
        """Load places from JSONL file and build vector index."""
        if not self.kb_path.exists():
            print(f"Warning: KB file {self.kb_path} not found")
            return

        with open(self.kb_path, 'r') as f:
            for line in f:
                if line.strip():
                    self.places.append(json.loads(line))

        print(f"Loaded {len(self.places)} places into KB")

        if self.places:
            embedding_texts = [p.get('embedding_text', p['site_name']) for p in self.places]
            self.vectorizer = TfidfVectorizer(max_features=100, lowercase=True, stop_words='english')
            self.vectors = self.vectorizer.fit_transform(embedding_texts)

    def retrieve(self, query: str, top_k: int = 3, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Retrieve top-k places by semantic similarity to query.

        Filters (optional):
            - district: str
            - site_type: str
            - best_seasons: List[str] (match if query season in place's best_seasons)
        """
        if not self.places or self.vectorizer is None:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.vectors)[0]

        # Get top matches, apply filters
        scored = [
            (i, sim) for i, sim in enumerate(similarities)
            if self._passes_filters(self.places[i], filters)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored[:top_k]:
            place = self.places[idx].copy()
            place['retrieval_score'] = float(score)
            results.append(place)

        return results

    def _passes_filters(self, place: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if place matches optional filters."""
        if filters is None:
            return True

        if 'district' in filters and filters['district'].lower() not in place.get('district', '').lower():
            return False

        if 'site_type' in filters and filters['site_type'].lower() != place.get('site_type', '').lower():
            return False

        if 'season' in filters:
            season = filters['season'].lower()
            best = [s.lower() for s in place.get('best_seasons', [])]
            avoid = [s.lower() for s in place.get('avoid_seasons', [])]
            if season in avoid:
                return False
            # Soft penalty if season not in best_seasons (not a hard filter)

        return True

    def get_by_id(self, site_id: str) -> Dict[str, Any]:
        """Get a place by its site_id."""
        for place in self.places:
            if place['site_id'] == site_id:
                return place
        return None

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all places."""
        return self.places
