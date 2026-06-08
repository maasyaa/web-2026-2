from app.models import Review
from sqlalchemy import desc, asc


class ReviewRepository:
    def __init__(self, db):
        self.db = db

    def get_by_course_id(self, course_id, limit=None, sort_by='newest'):
        """Получить отзывы для курса"""
        query = self.db.select(Review).filter(Review.course_id == course_id)

        if sort_by == 'newest':
            query = query.order_by(desc(Review.created_at))
        elif sort_by == 'positive_first':
            query = query.order_by(desc(Review.rating), desc(Review.created_at))
        elif sort_by == 'negative_first':
            query = query.order_by(asc(Review.rating), desc(Review.created_at))

        if limit:
            query = query.limit(limit)

        return self.db.session.execute(query).scalars().all()

    def get_pagination(self, course_id, page, per_page=10, sort_by='newest'):
        """Получить отзывы с пагинацией"""
        query = self.db.select(Review).filter(Review.course_id == course_id)

        if sort_by == 'newest':
            query = query.order_by(desc(Review.created_at))
        elif sort_by == 'positive_first':
            query = query.order_by(desc(Review.rating), desc(Review.created_at))
        elif sort_by == 'negative_first':
            query = query.order_by(asc(Review.rating), desc(Review.created_at))

        return self.db.paginate(query, page=page, per_page=per_page)

    def get_user_review_for_course(self, course_id, user_id):
        """Получить отзыв пользователя на курс"""
        query = self.db.select(Review).filter(
            Review.course_id == course_id,
            Review.user_id == user_id
        )
        return self.db.session.execute(query).scalar()

    def add_review(self, course_id, user_id, rating, text):
        """Добавить новый отзыв"""
        review = Review(
            course_id=course_id,
            user_id=user_id,
            rating=rating,
            text=text
        )
        self.db.session.add(review)
        self.db.session.commit()
        return review

    def get_course_reviews_count(self, course_id):
        """Получить количество отзывов на курс"""
        query = self.db.select(Review).filter(Review.course_id == course_id)
        return self.db.session.execute(query).scalars().count()