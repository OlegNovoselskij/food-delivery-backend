from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.catalog import Course
from app.models.user import User
from app.repository import recommendation_repository


@dataclass(frozen=True)
class Recommendation:
    course: Course
    reason: str


class RecommendationStrategy(ABC):
    @abstractmethod
    def recommend(self, db: Session, student: User, limit: int, exclude: set[int]) -> list[Recommendation]: ...


class CollaborativeStrategy(RecommendationStrategy):
    def recommend(self, db, student, limit, exclude) -> list[Recommendation]:
        ids = recommendation_repository.co_enrolled_ids(db, student.id, exclude, limit)
        courses = recommendation_repository.load_published(db, ids)
        return [Recommendation(courses[i], "Students of your courses also learn this") for i in ids if i in courses]


class CategoryAffinityStrategy(RecommendationStrategy):
    def recommend(self, db, student, limit, exclude) -> list[Recommendation]:
        weights = recommendation_repository.category_weights(db, student.id)
        courses = recommendation_repository.courses_in_categories(db, weights, exclude, limit)
        return [Recommendation(course, f'Because you are learning "{course.category.name}"') for course in courses]


class PopularStrategy(RecommendationStrategy):
    def recommend(self, db, student, limit, exclude) -> list[Recommendation]:
        courses = recommendation_repository.popular_courses(db, exclude, limit)
        return [Recommendation(course, "Popular right now") for course in courses]


class FallbackChain(RecommendationStrategy):
    def __init__(self, *strategies: RecommendationStrategy) -> None:
        self._strategies = strategies

    def recommend(self, db, student, limit, exclude) -> list[Recommendation]:
        result: list[Recommendation] = []
        seen = set(exclude)
        for strategy in self._strategies:
            if len(result) >= limit:
                break
            for recommendation in strategy.recommend(db, student, limit - len(result), seen):
                result.append(recommendation)
                seen.add(recommendation.course.id)
        return result
