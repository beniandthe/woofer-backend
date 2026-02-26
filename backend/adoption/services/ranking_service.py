from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from adoption.models import Pet, RiskClassification, AdopterProfile
 

# Deterministic weights (tunable later)
BOOST_LONG_STAY = 0.30
BOOST_SENIOR = 0.20
BOOST_MEDICAL = 0.20
BOOST_OVERLOOKED = 0.15
BOOST_RETURNED = 0.25
BOOST_PROFILE_ACTIVITY_MATCH = 0.10
BOOST_PROFILE_HOME_MATCH = 0.08
BOOST_PROFILE_EXPERIENCE_MATCH = 0.07

# cap total boost influence so boosted pets don't permanently dominate
MAX_TOTAL_BOOST = 0.40

# Feed diversity (deterministic) used by PetFeedService 
DIVERSITY_TARGET_BOOSTED_RATIO = 0.40  
DIVERSITY_RATIO_MIN = 0.20
DIVERSITY_RATIO_MAX = 0.60

# Diversity targets (tunable, deterministic)
DIVERSITY_TARGET_BOOSTED_RATIO = 0.60  
DIVERSITY_MIN_NORMAL_PER_PAGE = 1      


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
        # Normalize to "days since epoch" so weights are comparable
        return listed_at.timestamp() / 86400.0

    @staticmethod
    def _profile_boost(pet: Pet, profile: AdopterProfile) -> Tuple[float, List[str]]:
        """
        Soft compatibility boosts (v1).
        Deterministic and explainable. Never excludes pets.
        """
        boost = 0.0
        reasons: List[str] = []

        # Prefer ai_description if present, fallback to raw_description
        description = (pet.ai_description or pet.raw_description or "")
        lowered = description.lower()

        # Activity matching
        if profile.activity_level == AdopterProfile.ActivityLevel.HIGH:
            if "active" in lowered or "energetic" in lowered:
                boost += BOOST_PROFILE_ACTIVITY_MATCH
                reasons.append("PROFILE_ACTIVITY_MATCH")

        # Home matching - apartments often do better with smaller/medium 
        if profile.home_type == AdopterProfile.HomeType.APARTMENT:
            if pet.size in ("S", "M"):
                boost += BOOST_PROFILE_HOME_MATCH
                reasons.append("PROFILE_HOME_MATCH")

        # New adopters - soft boost for gentle/easy language if present
        if profile.experience_level == AdopterProfile.ExperienceLevel.NEW:
            if "gentle" in lowered or "easy" in lowered:
                boost += BOOST_PROFILE_EXPERIENCE_MATCH
                reasons.append("PROFILE_EXPERIENCE_MATCH")

        return boost, reasons



    @staticmethod
    def score_pet(pet: Pet, profile: Optional[AdopterProfile] = None) -> Tuple[float, List[str]]:

        score = RankingService._recency_score(pet.listed_at)
        reasons: List[str] = []

        try:
            risk = pet.risk
        except RiskClassification.DoesNotExist:
            risk = None

        total_boost = 0.0

        if risk:
            if risk.is_long_stay:
                total_boost += BOOST_LONG_STAY
                reasons.append("LONG_STAY_BOOST")
            if risk.is_senior:
                total_boost += BOOST_SENIOR
                reasons.append("SENIOR_BOOST")
            if risk.is_medical:
                total_boost += BOOST_MEDICAL
                reasons.append("MEDICAL_BOOST")
            if risk.is_overlooked_breed_group:
                total_boost += BOOST_OVERLOOKED
                reasons.append("OVERLOOKED_GROUP_BOOST")
            if risk.recently_returned:
                total_boost += BOOST_RETURNED
                reasons.append("RECENTLY_RETURNED_BOOST")

        if profile is not None:
            p_boost, p_reasons = RankingService._profile_boost(pet, profile)
            score += p_boost
            reasons.extend(p_reasons)

        # cap total boost
        if total_boost > MAX_TOTAL_BOOST:
            total_boost = MAX_TOTAL_BOOST
        
        score += total_boost
        return score, reasons

    @staticmethod
    def rank(pets: List[Pet], profile: Optional[AdopterProfile] = None) -> List[RankedPet]:

        ranked: List[RankedPet] = []
        for p in pets:
            score, reasons = RankingService.score_pet(p, profile=profile)
            ranked.append(RankedPet(pet=p, score=score, reasons=reasons))

        # Deterministic ordering score DESC, then pet_id DESC
        ranked.sort(key=lambda rp: (rp.score, str(rp.pet.pet_id)), reverse=True)
        return ranked

    @staticmethod
    def reasons_for_pet(pet: Pet) -> List[str]:
        _, reasons = RankingService.score_pet(pet)
        return reasons

    @staticmethod
    def is_boosted(reasons: List[str]) -> bool:
        """
        A ranked pet is considered "boosted" if it has any bias-correction reasons.
        Deterministic, server-only. Used for feed diversity slotting.
        """
        return bool(reasons)


