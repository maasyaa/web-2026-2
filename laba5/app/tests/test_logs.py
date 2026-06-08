import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app5 import app as flask_app, db, User


@pytest.fixture
def app():
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.secret_key = 'test-secret-key'

    with flask_app.app_context():
        db.create_all()

        from werkzeug.security import generate_password_hash
        from app5 import Role

        if not Role.query.first():
            admin_role = Role(name='Администратор', description='Полный доступ')
            user_role = Role(name='Пользователь', description='Ограниченный доступ')
            db.session.add_all([admin_role, user_role])
            db.session.commit()

        if not User.query.filter_by(login='admin').first():
            admin_user = User(
                login='admin',
                password_hash=generate_password_hash('admin-Qwerty1234'),
                first_name='Админ',
                last_name='Тестовый',
                role_id=1
            )
            db.session.add(admin_user)

        if not User.query.filter_by(login='testuser').first():
            regular_user = User(
                login='testuser',
                password_hash=generate_password_hash('qwerty-Qwerty1234'),
                first_name='Тест',
                last_name='Пользователь',
                role_id=2
            )
            db.session.add(regular_user)

        db.session.commit()

    yield flask_app

    with flask_app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login_admin(client):
    return client.post('/login', data={
        'login': 'admin',
        'password': 'admin-Qwerty1234',
        'remember': False
    }, follow_redirects=True)


def login_user(client):
    return client.post('/login', data={
        'login': 'testuser',
        'password': 'qwerty-Qwerty1234',
        'remember': False
    }, follow_redirects=True)


def test_admin_can_view_users(client):
    login_admin(client)
    response = client.get('/')
    assert response.status_code == 200
    assert 'Список пользователей' in response.text



def test_user_cannot_edit_other_profile(client):
    login_user(client)
    response = client.get('/users/1/edit', follow_redirects=False)
    assert response.status_code in [302, 403]



def test_login_success(client):
    response = login_admin(client)
    assert response.status_code == 200
    assert 'успешно' in response.text.lower()



def test_login_failure(client):
    response = client.post('/login', data={
        'login': 'wronguser',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Неверный логин или пароль' in response.text



def test_logs_page_accessible_for_auth_users(client):
    login_admin(client)
    response = client.get('/logs/')
    assert response.status_code == 200
    assert 'Журнал посещений' in response.text



def test_logs_page_redirects_unauthenticated(client):
    response = client.get('/logs/', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']



