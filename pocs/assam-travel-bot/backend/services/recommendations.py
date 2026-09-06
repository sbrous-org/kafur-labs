import json
from pathlib import Path
from typing import List, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class HiddenGems:
    """
    Curated hidden-gems directory with TF-IDF similarity matching.

    This is the POC stand-in for the target "Hidden Gems / Recommendation
    Service" (see ARCHITECTURE.md §3): production uses real embeddings + a
    vector DB and a feedback signal. Here it's a small hand-curated JSONL plus
    the same TF-IDF trick the knowledge base uses — enough to test whether the
    router correctly *asks* for hidden gems rather than repeating guidebook
    stops.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.gems: List[Dict[str, Any]] = []
        self.vectorizer = None
        self.vectors = None
        self.load()

    def load(self):
        if not self.path.exists():
            print(f"Warning: hidden-gems file {self.path} not found")
            return

        with open(self.path, "r") as f:
            for line in f:
                if line.strip():
                    self.gems.append(json.loads(line))

        print(f"Loaded {len(self.gems)} hidden gems")

        if self.gems:
            texts = [g.get("embedding_text", g["name"]) for g in self.gems]
            self.vectorizer = TfidfVectorizer(max_features=200, lowercase=True, stop_words="english")
            self.vectors = self.vectorizer.fit_transform(texts)

    def retrieve(self, query: str, region: str = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Return up to top_k hidden gems ranked by similarity to the query.

        If `region` is given and any gem is anchored near that region, results
        are restricted to that region; otherwise similarity alone decides.
        """
        if not self.gems or self.vectorizer is None:
            return []

        candidates = list(range(len(self.gems)))
        if region:
            region_l = region.lower()
            regional = [
                i for i in candidates
                if region_l in self.gems[i].get("near", "").lower()
                or region_l in self.gems[i].get("district", "").lower()
            ]
            if regional:
                candidates = regional

        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.vectors)[0]

        scored = sorted(candidates, key=lambda i: sims[i], reverse=True)

        results = []
        for idx in scored[:top_k]:
            gem = self.gems[idx].copy()
            gem["match_score"] = float(sims[idx])
            results.append(gem)
        return results

    def get_all(self) -> List[Dict[str, Any]]:
        return self.gems
