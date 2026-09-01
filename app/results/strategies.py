"""
Ranking Strategy Protocol Abstraction.
Strictly defines the RankingStrategy Protocol without inventing or executing arbitrary ranking rules.
"""
from typing import Any, Dict, List, Protocol, runtime_checkable
from app.database.models import QuizResult


@runtime_checkable
class RankingStrategy(Protocol):
    """
    Protocol for calculating participant rankings from quiz results.
    Strictly an interface/abstraction that can be implemented once an approved ranking formula is defined.
    """

    def calculate_rankings(self, results: List[QuizResult]) -> List[Dict[str, Any]]:
        """Calculates ranks and returns list of ranked items."""
        ...
