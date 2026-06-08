import pytest
from app import create_app
from app.models import db, User, Course, Category, Image, Review
from werkzeug.security import generate_password_hash
import os

@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })

    with app.app_context():
        db.create_all()
        
        # Setup data
        cat = Category(name='Test Category')
        img = Image(id='test_img', file_name='test.jpg', mime_type='image/jpeg', md5_hash='hash')
        user = User(first_name='Admin', last_name='User', login='admin')
        user.set_password('pass')
        
        db.session.add_all([cat, img, user])
        db.session.commit()
        
        course = Course(
            name='Test Course',
            short_desc='Short',
            full_desc='Full',
            category_id=cat.id,
            author_id=user.id,
            background_image_id=img.id
        )
        db.session.add(course)
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth(client):
    class AuthActions:
        def login(self, login='admin', password='pass'):
            return client.post('/auth/login', data={'login': login, 'password': password}, follow_redirects=True)
        def logout(self):
            return client.get('/auth/logout')
    return AuthActions()

def test_show_course_page(client):
    response = client.get('/courses/1')
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert 'Test Course' in text
    assert 'Последние отзывы' in text

def test_add_review(client, auth, app):
    auth.login()
    response = client.post('/courses/1/reviews/add', data={
        'rating': 5,
        'text': 'Great course!'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'Ваш отзыв успешно добавлен!' in response.get_data(as_text=True)
    
    with app.app_context():
        review = db.session.get(Review, 1)
        assert review is not None
        assert review.rating == 5
        assert review.text == 'Great course!'
        
        course = db.session.get(Course, 1)
        assert course.rating_num == 1
        assert course.rating_sum == 5

def test_prevent_duplicate_review(client, auth):
    auth.login()
    # Add first review
    client.post('/courses/1/reviews/add', data={'rating': 5, 'text': 'First'})
    
    # Try second review
    response = client.post('/courses/1/reviews/add', data={'rating': 4, 'text': 'Second'}, follow_redirects=True)
    assert 'Вы уже оставили отзыв к этому курсу.' in response.get_data(as_text=True)

def test_reviews_pagination_and_sorting(client, app, auth):
    with app.app_context():
        # Add another user
        user2 = User(first_name='User2', last_name='Two', login='user2')
        user2.set_password('pass')
        db.session.add(user2)
        db.session.commit()
        
        # Add reviews
        r1 = Review(course_id=1, user_id=1, rating=2, text='Bad')
        r2 = Review(course_id=1, user_id=2, rating=5, text='Good')
        db.session.add_all([r1, r2])
        db.session.commit()
        
    # Test sorting - positive first
    response = client.get('/courses/1/reviews?sort_by=positive')
    assert response.status_code == 200
    # 'Good' should appear before 'Bad'
    assert response.data.find(b'Good') < response.data.find(b'Bad')
    
    # Test sorting - negative first
    response = client.get('/courses/1/reviews?sort_by=negative')
    assert response.data.find(b'Bad') < response.data.find(b'Good')
