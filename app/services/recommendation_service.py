from sqlalchemy.orm import Session

from app.models.user import User
from app.patterns.factories.recommendation_factory import RecommendationStrategyFactory
from app.repository import recommendation_repository
from app.schemas.recommendation import RecommendationParams


def recommend(db: Session, user: User, params: RecommendationParams) -> list[dict]:
    exclude = recommendation_repository.excluded_course_ids(db, user.id)
    strategy = RecommendationStrategyFactory.create(params.strategy)
    return [
        {"course": item.course, "reason": item.reason} for item in strategy.recommend(db, user, params.limit, exclude)
    ]
