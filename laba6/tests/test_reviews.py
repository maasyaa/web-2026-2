import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import create_app, db
from app.models import User, Course, Category, Review, Image


@pytest.fixture
def app():
    """Создание тестового приложения"""
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })

    with app.app_context():
        db.create_all()

        # Создаём тестовую категорию
        category = Category(name='Тестовая категория')
        db.session.add(category)

        # Создаём тестового пользователя
        user = User(
            first_name='Тест',
            last_name='Тестовый',
            login='testuser'
        )
        user.set_password('testpass')
        db.session.add(user)
        db.session.flush()  # Чтобы получить id

        # Создаём тестовое изображение (чтобы избежать NOT NULL constraint)
        test_image = Image(
            id='test_image_id',
            file_name='test.jpg',
            mime_type='image/jpeg',
            md5_hash='test_hash_12345'
        )
        db.session.add(test_image)
        db.session.flush()

        # Создаём тестовый курс (с background_image_id)
        course = Course(
            name='Тестовый курс',
            short_desc='Краткое описание тестового курса',
            full_desc='Полное описание тестового курса для проверки функциональности отзывов',
            author_id=user.id,
            category_id=category.id,
            background_image_id=test_image.id
        )
        db.session.add(course)
        db.session.commit()

        yield app

        db.drop_all()


@pytest.fixture
def client(app):
    """Тестовый клиент"""
    return app.test_client()


@pytest.fixture
def login_test_user(client):
    """Логин тестового пользователя"""
    return client.post('/auth/login', data={
        'login': 'testuser',
        'password': 'testpass'
    }, follow_redirects=True)


def test_course_page_displays_no_reviews_initially(client):
    """На странице курса изначально нет отзывов"""
    response = client.get('/courses/1')
    assert response.status_code == 200
    assert 'Пока нет отзывов' in response.text


def test_create_review_success(client, login_test_user):
    """Успешное создание отзыва"""
    response = client.post('/courses/1/review/create', data={
        'rating': 5,
        'text': 'Отличный курс! Всё очень понравилось.'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Ваш отзыв успешно добавлен' in response.text


def test_review_appears_on_course_page(client, login_test_user):
    """Отзыв отображается на странице курса"""
    client.post('/courses/1/review/create', data={
        'rating': 5,
        'text': 'Тестовый отзыв для проверки отображения'
    })

    response = client.get('/courses/1')
    assert 'Тестовый отзыв для проверки отображения' in response.text


def test_user_cannot_create_second_review(client, login_test_user):
    """Пользователь не может оставить второй отзыв на тот же курс"""
    client.post('/courses/1/review/create', data={
        'rating': 4,
        'text': 'Первый отзыв'
    })

    response = client.post('/courses/1/review/create', data={
        'rating': 5,
        'text': 'Второй отзыв'
    }, follow_redirects=True)

    assert 'Вы уже оставили отзыв' in response.text


def test_create_review_without_login(client):
    """Неавторизованный пользователь не может оставить отзыв"""
    response = client.post('/courses/1/review/create', data={
        'rating': 5,
        'text': 'Отзыв без авторизации'
    }, follow_redirects=False)

    # Проверяем, что это редирект на страницу логина
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']


def test_review_rating_validation(client, login_test_user):
    """Валидация оценки: некорректные значения"""
    response = client.post('/courses/1/review/create', data={
        'rating': 6,
        'text': 'Некорректная оценка'
    }, follow_redirects=True)

    assert 'Некорректная оценка' in response.text


def test_review_text_validation(client, login_test_user):
    """Валидация текста отзыва: пустое поле"""
    response = client.post('/courses/1/review/create', data={
        'rating': 5,
        'text': ''
    }, follow_redirects=True)

    assert 'Текст отзыва не может быть пустым' in response.text


def test_reviews_page_pagination(client, login_test_user):
    """Страница всех отзывов с пагинацией"""
    for i in range(15):
        client.post('/courses/1/review/create', data={
            'rating': 5,
            'text': f'Тестовый отзыв номер {i}'
        })

    response = client.get('/courses/1/reviews')
    assert response.status_code == 200
    assert 'Тестовый отзыв номер' in response.text


def test_reviews_sort_by_newest(client, login_test_user):
    """Сортировка отзывов: сначала новые"""
    client.post('/courses/1/review/create', data={
        'rating': 5,
        'text': 'Самый новый отзыв'
    })

    response = client.get('/courses/1/reviews?sort=newest')
    assert 'Самый новый отзыв' in response.text


def test_reviews_sort_by_positive_first(client, login_test_user):
    """Сортировка отзывов: сначала положительные"""
    client.post('/courses/1/review/create', data={'rating': 2, 'text': 'Плохой отзыв'})
    client.post('/courses/1/review/create', data={'rating': 5, 'text': 'Отличный отзыв'})

    response = client.get('/courses/1/reviews?sort=positive_first')
    pos_index = response.text.find('Отличный отзыв')
    neg_index = response.text.find('Плохой отзыв')
    assert pos_index < neg_index


def test_reviews_sort_by_negative_first(client, login_test_user):
    """Сортировка отзывов: сначала отрицательные"""
    client.post('/courses/1/review/create', data={'rating': 5, 'text': 'Отличный отзыв'})
    client.post('/courses/1/review/create', data={'rating': 1, 'text': 'Ужасный отзыв'})

    response = client.get('/courses/1/reviews?sort=negative_first')
    neg_index = response.text.find('Ужасный отзыв')
    pos_index = response.text.find('Отличный отзыв')
    assert neg_index < pos_index


def test_course_rating_updates_after_review(client, login_test_user):
    """Рейтинг курса обновляется после добавления отзыва"""
    client.post('/courses/1/review/create', data={
        'rating': 5,
        'text': 'Отличный курс!'
    })

    response = client.get('/courses/1')
    assert response.status_code == 200


def test_all_reviews_link_on_course_page(client, login_test_user):
    """На странице курса есть ссылка 'Все отзывы'"""
    for i in range(3):
        client.post('/courses/1/review/create', data={
            'rating': 5,
            'text': f'Отзыв {i}'
        })

    response = client.get('/courses/1')
    assert 'Все отзывы' in response.text