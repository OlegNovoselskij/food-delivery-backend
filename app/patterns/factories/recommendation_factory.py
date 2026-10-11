from app.patterns.strategies.recommendation import (
    CategoryAffinityStrategy,
    CollaborativeStrategy,
    FallbackChain,
    PopularStrategy,
    RecommendationStrategy,
)

_collaborative = CollaborativeStrategy()
_category = CategoryAffinityStrategy()
_popular = PopularStrategy()


class RecommendationStrategyFactory:
    _strategies: dict[str, RecommendationStrategy] = {
        "collaborative": _collaborative,
        "category": _category,
        "popular": _popular,
        "auto": FallbackChain(_collaborative, _category, _popular),
    }

    @classmethod
    def create(cls, name: str) -> RecommendationStrategy:
        return cls._strategies[name]
