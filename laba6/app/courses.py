from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app.models import db
from app.repositories import CourseRepository, UserRepository, CategoryRepository, ImageRepository, ReviewRepository

user_repository = UserRepository(db)
course_repository = CourseRepository(db)
category_repository = CategoryRepository(db)
image_repository = ImageRepository(db)
review_repository = ReviewRepository(db)

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]


def params():
    return {p: request.form.get(p) or None for p in COURSE_PARAMS}


def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }


@bp.route('/')
def index():
    pagination = course_repository.get_pagination_info(**search_params())
    courses = course_repository.get_all_courses(pagination=pagination)
    categories = category_repository.get_all_categories()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())


@bp.route('/new')
@login_required
def new():
    course = course_repository.new_course()
    categories = category_repository.get_all_categories()
    users = user_repository.get_all_users()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users,
                           course=course)


@bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.files.get('background_img')
    img = None
    course = None

    try:
        if f and f.filename:
            img = image_repository.add_image(f)

        image_id = img.id if img else None
        course = course_repository.add_course(**params(), background_image_id=image_id)
    except IntegrityError as err:
        flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
        categories = category_repository.get_all_categories()
        users = user_repository.get_all_users()
        return render_template('courses/new.html',
                               categories=categories,
                               users=users,
                               course=course)

    flash(f'Курс {course.name} был успешно добавлен!', 'success')
    return redirect(url_for('courses.index'))


@bp.route('/<int:course_id>')
def show(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    # Получаем последние 5 отзывов
    recent_reviews = review_repository.get_by_course_id(course_id, limit=5, sort_by='newest')

    # Проверяем, оставлял ли текущий пользователь отзыв
    user_review = None
    if current_user.is_authenticated:
        user_review = review_repository.get_user_review_for_course(course_id, current_user.id)

    return render_template('courses/show.html',
                           course=course,
                           reviews=recent_reviews,
                           user_review=user_review)


@bp.route('/<int:course_id>/reviews')
def reviews(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'newest')
    per_page = 10

    pagination = review_repository.get_pagination(course_id, page, per_page, sort_by)
    all_reviews = pagination.items

    user_review = None
    if current_user.is_authenticated:
        user_review = review_repository.get_user_review_for_course(course_id, current_user.id)

    return render_template('courses/reviews.html',
                           course=course,
                           reviews=all_reviews,
                           pagination=pagination,
                           sort_by=sort_by,
                           user_review=user_review)


@bp.route('/<int:course_id>/review/create', methods=['POST'])
@login_required
def create_review(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    # Проверяем, не оставлял ли пользователь уже отзыв
    existing_review = review_repository.get_user_review_for_course(course_id, current_user.id)
    if existing_review:
        flash('Вы уже оставили отзыв на этот курс.', 'danger')
        return redirect(url_for('courses.show', course_id=course_id))

    rating = request.form.get('rating', type=int)
    text = request.form.get('text', '').strip()

    if rating is None or rating < 0 or rating > 5:
        flash('Некорректная оценка. Оценка должна быть от 0 до 5.', 'danger')
        return redirect(url_for('courses.show', course_id=course_id))

    if not text:
        flash('Текст отзыва не может быть пустым.', 'danger')
        return redirect(url_for('courses.show', course_id=course_id))

    # Добавляем отзыв
    review_repository.add_review(course_id, current_user.id, rating, text)

    # Обновляем рейтинг курса
    all_reviews = review_repository.get_by_course_id(course_id)
    total_rating = sum(r.rating for r in all_reviews)
    total_count = len(all_reviews)

    course.rating_sum = total_rating
    course.rating_num = total_count
    db.session.commit()

    flash('Ваш отзыв успешно добавлен!', 'success')
    return redirect(url_for('courses.show', course_id=course_id))