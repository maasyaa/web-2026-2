import pytest
from app import app, db
from models import User, Role
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    """Тестовый клиент с временной БД в памяти"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # отключаем CSRF для тестов
    app.config['LOGIN_DISABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Создаём роли
            role_admin = Role(name='Администратор', description='Полный доступ')
            role_user = Role(name='Пользователь', description='Обычный')
            db.session.add_all([role_admin, role_user])
            db.session.commit()
            # Создаём тестового пользователя
            test_user = User(
                login='testuser',
                first_name='Тест',
                last_name='Тестов',
                role_id=role_user.id
            )
            test_user.set_password('Test123!')
            db.session.add(test_user)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def login(client, username, password):
    """Вспомогательная функция для входа"""
    return client.post('/login', data={
        'login': username,
        'password': password,
        'remember': False
    }, follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

# ---------- Тесты доступности страниц ----------
def test_index_page_accessible(client):
    """Главная страница доступна всем"""
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Пользователи системы' in rv.data or b'Список пользователей' in rv.data

def test_login_page_accessible(client):
    rv = client.get('/login')
    assert rv.status_code == 200

def test_create_user_page_requires_login(client):
    """Создание пользователя требует аутентификации"""
    rv = client.get('/users/create', follow_redirects=True)
    assert b'login' in rv.data  # перенаправляет на логин

def test_secret_change_password_page_requires_login(client):
    rv = client.get('/change-password', follow_redirects=True)
    assert b'login' in rv.data

# ---------- Тесты аутентификации ----------
def test_login_valid_user(client):
    rv = login(client, 'testuser', 'Test123!')
    assert b'Вы успешно вошли' in rv.data

def test_login_invalid_password(client):
    rv = login(client, 'testuser', 'wrong')
    assert b'Неверный логин или пароль' in rv.data

def test_logout(client):
    login(client, 'testuser', 'Test123!')
    rv = logout(client)
    assert b'Вы вышли из системы' in rv.data

# ---------- Тесты создания пользователя (только авторизованный) ----------
def test_create_user_success(client):
    login(client, 'testuser', 'Test123!')
    rv = client.post('/users/create', data={
        'login': 'newuser',
        'password': 'Valid123!',
        'confirm': 'Valid123!',
        'last_name': 'Иванов',
        'first_name': 'Иван',
        'middle_name': 'Иванович',
        'role_id': '2'   # роль "Пользователь"
    }, follow_redirects=True)
    assert b'Пользователь успешно создан' in rv.data
    # Проверяем, что пользователь появился в БД
    with app.app_context():
        user = User.query.filter_by(login='newuser').first()
        assert user is not None
        assert user.first_name == 'Иван'

def test_create_user_validation_login_short(client):
    login(client, 'testuser', 'Test123!')
    rv = client.post('/users/create', data={
        'login': 'ab',   # слишком короткий
        'password': 'Valid123!',
        'confirm': 'Valid123!',
        'last_name': 'Петров',
        'first_name': 'Петр',
        'role_id': ''
    })
    assert b'Логин должен быть не менее 5 символов' in rv.data

def test_create_user_validation_password_no_uppercase(client):
    login(client, 'testuser', 'Test123!')
    rv = client.post('/users/create', data={
        'login': 'validuser',
        'password': 'valid123!',   # нет заглавной
        'confirm': 'valid123!',
        'last_name': 'Сидоров',
        'first_name': 'Сидор'
    })
    assert b'Нужна хотя бы одна заглавная буква' in rv.data

def test_create_user_validation_empty_fields(client):
    login(client, 'testuser', 'Test123!')
    rv = client.post('/users/create', data={
        'login': '',
        'password': '',
        'confirm': '',
        'last_name': '',
        'first_name': '',
    })
    assert b'Логин не может быть пустым' in rv.data
    assert b'Пароль не может быть пустым' in rv.data
    assert b'Фамилия обязательна' in rv.data or b'Поле не может быть пустым' in rv.data

# ---------- Тесты редактирования пользователя ----------
def test_edit_user_success(client):
    login(client, 'testuser', 'Test123!')
    with app.app_context():
        user = User.query.filter_by(login='testuser').first()
        user_id = user.id
    rv = client.post(f'/users/{user_id}/edit', data={
        'last_name': 'НоваяФамилия',
        'first_name': 'НовоеИмя',
        'middle_name': 'НовоеОтчество',
        'role_id': '1'
    }, follow_redirects=True)
    assert b'Данные обновлены' in rv.data
    with app.app_context():
        updated = User.query.get(user_id)
        assert updated.last_name == 'НоваяФамилия'
        assert updated.first_name == 'НовоеИмя'

def test_edit_user_validation_missing_firstname(client):
    login(client, 'testuser', 'Test123!')
    with app.app_context():
        user = User.query.filter_by(login='testuser').first()
        user_id = user.id
    rv = client.post(f'/users/{user_id}/edit', data={
        'last_name': 'Иванов',
        'first_name': '',
        'role_id': ''
    })
    assert b'Имя обязательно' in rv.data

# ---------- Тесты удаления пользователя ----------
def test_delete_user_success(client):
    login(client, 'testuser', 'Test123!')
    # Создаём второго пользователя, которого будем удалять
    with app.app_context():
        user2 = User(login='todelete', first_name='НаУдаление')
        user2.set_password('Test123!')
        db.session.add(user2)
        db.session.commit()
        user2_id = user2.id
    rv = client.post(f'/users/{user2_id}/delete', follow_redirects=True)
    assert b'Пользователь НаУдаление удалён' in rv.data
    with app.app_context():
        assert User.query.get(user2_id) is None

def test_delete_self_forbidden(client):
    login(client, 'testuser', 'Test123!')
    with app.app_context():
        user = User.query.filter_by(login='testuser').first()
        user_id = user.id
    rv = client.post(f'/users/{user_id}/delete', follow_redirects=True)
    assert b'Нельзя удалить самого себя' in rv.data
    with app.app_context():
        assert User.query.get(user_id) is not None

# ---------- Тесты смены пароля ----------
def test_change_password_success(client):
    login(client, 'testuser', 'Test123!')
    rv = client.post('/change-password', data={
        'old_password': 'Test123!',
        'new_password': 'NewPass456!',
        'confirm_password': 'NewPass456!'
    }, follow_redirects=True)
    assert b'Пароль успешно изменён' in rv.data
    # Проверяем, что старый пароль больше не работает
    logout(client)
    rv2 = login(client, 'testuser', 'Test123!')
    assert b'Неверный логин или пароль' in rv2.data
    rv3 = login(client, 'testuser', 'NewPass456!')
    assert b'Вы успешно вошли' in rv3.data

def test_change_password_wrong_old(client):
    login(client, 'testuser', 'Test123!')
    rv = client.post('/change-password', data={
        'old_password': 'WrongOld',
        'new_password': 'NewPass456!',
        'confirm_password': 'NewPass456!'
    })
    assert b'Неверный старый пароль' in rv.data

def test_change_password_mismatch(client):
    login(client, 'testuser', 'Test123!')
    rv = client.post('/change-password', data={
        'old_password': 'Test123!',
        'new_password': 'NewPass456!',
        'confirm_password': 'Different'
    })
    assert b'Пароли не совпадают' in rv.data

def test_change_password_weak_new(client):
    login(client, 'testuser', 'Test123!')
    rv = client.post('/change-password', data={
        'old_password': 'Test123!',
        'new_password': 'weak',
        'confirm_password': 'weak'
    })
    assert b'длина' in rv.data or b'8' in rv.data

# ---------- Тест просмотра пользователя (доступен всем) ----------
def test_view_user_accessible_without_login(client):
    with app.app_context():
        user = User.query.filter_by(login='testuser').first()
        user_id = user.id
    rv = client.get(f'/users/{user_id}')
    assert rv.status_code == 200
    assert b'Тест' in rv.data or b'testuser' in rv.data

# ---------- Тест, что кнопки редактирования/удаления видны только авторизованным ----------
def test_edit_delete_buttons_visibility(client):
    # Не авторизован
    rv = client.get('/')
    # В таблице не должно быть ссылок на редактирование/удаление
    assert b'Ред.' not in rv.data
    assert b'Удалить' not in rv.data
    # Авторизуемся
    login(client, 'testuser', 'Test123!')
    rv = client.get('/')
    # Теперь кнопки должны быть видны
    assert b'Ред.' in rv.data
    assert b'Удалить' in rv.data

# ---------- Тест создания пользователя неавторизованным ----------
def test_create_user_unauthorized_redirect(client):
    rv = client.get('/users/create', follow_redirects=True)
    # Должен быть редирект на страницу логина
    assert b'login' in rv.data