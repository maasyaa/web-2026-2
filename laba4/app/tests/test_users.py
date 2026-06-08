import pytest
from app4 import app, db
from models import User, Role


def login(client, username, password):
    return client.post('/login', data={
        'login': username,
        'password': password,
        'remember': False
    }, follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)


def test_index_page_accessible(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert 'Пользователи системы' in rv.text or 'Список пользователей' in rv.text


def test_login_page_accessible(client):
    rv = client.get('/login')
    assert rv.status_code == 200


def test_create_user_page_requires_login(client):
    rv = client.get('/users/create', follow_redirects=True)
    assert 'login' in rv.text


def test_secret_change_password_page_requires_login(client):
    rv = client.get('/change-password', follow_redirects=True)
    assert 'login' in rv.text


def test_login_valid_user(client):
    rv = login(client, 'testuser', 'Test123!')
    assert 'Вы успешно вошли' in rv.text


def test_login_invalid_password(client):
    rv = login(client, 'testuser', 'wrong')
    assert 'Неверный логин или пароль' in rv.text


def test_logout(client):
    login(client, 'testuser', 'Test123!')
    rv = logout(client)
    assert 'Вы вышли из системы' in rv.text


def test_delete_user_success(client):
    login(client, 'testuser', 'Test123!')
    with app.app_context():
        user2 = User(login='todelete', first_name='НаУдаление')
        user2.set_password('Test123!')
        db.session.add(user2)
        db.session.commit()
        user2_id = user2.id
    rv = client.post(f'/users/{user2_id}/delete', follow_redirects=True)
    assert 'Пользователь НаУдаление удалён' in rv.text
    with app.app_context():
        assert User.query.get(user2_id) is None


def test_delete_self_forbidden(client):
    login(client, 'testuser', 'Test123!')
    with app.app_context():
        user = User.query.filter_by(login='testuser').first()
        user_id = user.id
    rv = client.post(f'/users/{user_id}/delete', follow_redirects=True)
    assert 'Нельзя удалить самого себя' in rv.text
    with app.app_context():
        assert User.query.get(user_id) is not None



def test_view_user_accessible_without_login(client):
    with app.app_context():
        user = User.query.filter_by(login='testuser').first()
        user_id = user.id
    rv = client.get(f'/users/{user_id}')
    assert rv.status_code == 200
    assert 'Тест' in rv.text or 'testuser' in rv.text



def test_create_user_unauthorized_redirect(client):
    rv = client.get('/users/create', follow_redirects=True)
    assert 'login' in rv.text