from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from adoption.models import Pet, RiskClassification

# Deterministic weights (tunable later)
BOOST_LONG_STAY = 0.30
BOOST_SENIOR = 0.20
BOOST_MEDICAL = 0.20
BOOST_OVERLOOKED = 0.15
BOOST_RETURNED = 0.25


@dataclass(frozen=True)
class RankedPet:
    pet: Pet
    score: float
    reasons: List[str]


class RankingService:
    """
    v0 deterministic ranker.
    Base signal = recency (listed_at), plus bias-correction boosts from RiskClassification.
    """

    @staticmethod
    def _recency_score(listed_at: Optional[datetime]) -> float:
        if not listed_at:
            return 0.0
        if listed_at.tzinfo is None:
            listed_at = listed_at.replace(tzinfo=timezone.utc)
        # Normalize to "days since epoch" so weights are comparable-ish.
        return listed_at.timestamp() / 86400.0

    @staticmethod
    def score_pet(pet: Pet) -> Tuple[float, List[str]]:
        score = RankingService._recency_score(pet.listed_at)
        reasons: List[str] = []

        try:
            risk = pet.risk
        except RiskClassification.DoesNotExist:
            risk = None

        if risk:
            if risk.is_long_stay:
                score += BOOST_LONG_STAY
                reasons.append("LONG_STAY_BOOST")
            if risk.is_senior:
                score += BOOST_SENIOR
                reasons.append("SENIOR_BOOST")
            if risk.is_medical:
                score += BOOST_MEDICAL
                reasons.append("MEDICAL_BOOST")
            if risk.is_overlooked_breed_group:
                score += BOOST_OVERLOOKED
                reasons.append("OVERLOOKED_GROUP_BOOST")
            if risk.recently_returned:
                score += BOOST_RETURNED
                reasons.append("RECENTLY_RETURNED_BOOST")

        return score, reasons

    @staticmethod
    def rank(pets: List[Pet]) -> List[RankedPet]:
        ranked: List[RankedPet] = []
        for p in pets:
            score, reasons = RankingService.score_pet(p)
            ranked.append(RankedPet(pet=p, score=score, reasons=reasons))

        # Deterministic ordering: score DESC, then pet_id DESC
        ranked.sort(key=lambda rp: (rp.score, str(rp.pet.pet_id)), reverse=True)
        return ranked

    @staticmethod
    def reasons_for_pet(pet: Pet) -> List[str]:
        _, reasons = RankingService.score_pet(pet)
        return reasons

