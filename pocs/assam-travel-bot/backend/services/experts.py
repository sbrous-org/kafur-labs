import json
from pathlib import Path
from typing import List, Dict, Any, Optional

_AVAILABILITY_RANK = {
    "available_now": 0,
    "available_in_2h": 1,
    "available_today": 2,
    "by_appointment": 3,
}

_AVAILABILITY_LABEL = {
    "available_now": "Available now",
    "available_in_2h": "Available in ~2 hours",
    "available_today": "Available later today",
    "by_appointment": "By appointment",
}


class ExpertDirectory:
    """
    Static local-expert directory — the POC stand-in for the target "Local
    Expert Service" (see ARCHITECTURE.md §3).

    Production owns guide profiles, KYC/verification, real calendars and live
    availability. Here the profiles are hand-written and `availability` is a
    fixed string in the JSONL. What the POC actually tests: does the router
    correctly identify "connect me to a human who lives there" and hand back a
    guide, instead of trying to answer as the bot.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.experts: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        if not self.path.exists():
            print(f"Warning: local-experts file {self.path} not found")
            return

        with open(self.path, "r") as f:
            for line in f:
                if line.strip():
                    self.experts.append(json.loads(line))

        print(f"Loaded {len(self.experts)} local experts")

    def match(self, region: str = None, interests: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Return the single best-matching available expert, or None.

        Scoring: region match first, then specialty overlap with `interests`,
        then soonest availability, then most experience.
        """
        if not self.experts:
            return None

        region_l = (region or "").lower()
        interests_l = [i.lower() for i in (interests or [])]

        def score(e: Dict[str, Any]):
            primary_hit = district_hit = 0
            if region_l:
                if region_l in e.get("region", "").lower():
                    primary_hit = 1
                elif any(region_l in d.lower() for d in e.get("districts", [])):
                    district_hit = 1
            specialty_hits = sum(
                1 for s in e.get("specialties", [])
                if any(term in s.lower() or s.lower() in term for term in interests_l)
            )
            avail = _AVAILABILITY_RANK.get(e.get("availability", "by_appointment"), 9)
            # higher is better: primary-region match, then district, then specialty
            # overlap, then sooner availability, then experience
            return (primary_hit, district_hit, specialty_hits, -avail, e.get("years_experience", 0))

        best = max(self.experts, key=score)
        return self._decorate(best)

    def _decorate(self, expert: Dict[str, Any]) -> Dict[str, Any]:
        out = expert.copy()
        out["availability_label"] = _AVAILABILITY_LABEL.get(
            expert.get("availability", "by_appointment"), "By appointment"
        )
        return out

    def get_all(self) -> List[Dict[str, Any]]:
        return [self._decorate(e) for e in self.experts]
