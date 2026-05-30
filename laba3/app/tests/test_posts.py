"""
Тесты для Flask-приложения (Лабораторная работа №3)
Запуск: python -m pytest app/tests/ -v  (из директории "Лабораторная 3")
"""

import pytest
from app.py import app as flask_app


# ──────────────────────────────────────────
#  ФИКСТУРЫ
# ──────────────────────────────────────────

@pytest.fixture
def app():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    # Хранить сессии на стороне клиента (по умолчанию Flask так и делает)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username='user', password='qwerty', remember=False):
    """Хелпер: выполнить вход."""
    data = {'username': username, 'password': password}
    if remember:
        data['remember'] = 'on'
    return client.post('/login', data=data, follow_redirects=True)


# ──────────────────────────────────────────
#  1. СЧЁТЧИК ПОСЕЩЕНИЙ
# ──────────────────────────────────────────

# 1. Первый визит на /counter → счётчик = 1
def test_counter_first_visit(client):
    response = client.get('/counter')
    assert response.status_code == 200
    assert '1' in response.text

# 2. Повторный визит → счётчик увеличивается
def test_counter_increments(client):
    client.get('/counter')
    client.get('/counter')
    response = client.get('/counter')
    assert response.status_code == 200
    assert '3' in response.text

# 3. Счётчики разных клиентов независимы
def test_counter_independent_per_session(app):
    client_a = app.test_client()
    client_b = app.test_client()
    # client_a открывает 3 раза
    client_a.get('/counter')
    client_a.get('/counter')
    resp_a = client_a.get('/counter')
    # client_b открывает 1 раз
    resp_b = client_b.get('/counter')
    assert '3' in resp_a.text
    assert '1' in resp_b.text

# 4. Страница содержит слово «посещений» или «визит»
def test_counter_page_text(client):
    response = client.get('/counter')
    text = response.text.lower()
    assert 'посещ' in text or 'визит' in text


# ──────────────────────────────────────────
#  2. АУТЕНТИФИКАЦИЯ
# ──────────────────────────────────────────

# 5. Успешный вход → редирект на главную + flash-сообщение
def test_login_success_redirect(client):
    response = login(client)
    assert response.status_code == 200
    # Попали на главную (/ → index)
    assert 'DevAuth' in response.text or 'Главная' in response.text
    # Сообщение об успехе
    assert 'успешно' in response.text.lower()

# 6. Успешный вход → flash-сообщение категории 'success'
def test_login_success_flash_category(client):
    response = login(client)
    assert 'flash-alert--success' in response.text

# 7. Неверный пароль → остаёмся на /login + сообщение об ошибке
def test_login_wrong_password(client):
    response = client.post('/login', data={'username': 'user', 'password': 'wrong'},
                           follow_redirects=True)
    assert response.status_code == 200
    assert 'login-form' in response.text          # всё ещё страница входа
    assert 'Неверный логин или пароль' in response.text

# 8. Неверный логин → остаёмся на /login + сообщение об ошибке
def test_login_wrong_username(client):
    response = client.post('/login', data={'username': 'hacker', 'password': 'qwerty'},
                           follow_redirects=True)
    assert response.status_code == 200
    assert 'login-form' in response.text
    assert 'Неверный логин или пароль' in response.text

# 9. После неудачной попытки — flash категории 'danger'
def test_login_failure_flash_category(client):
    response = client.post('/login', data={'username': 'x', 'password': 'x'},
                           follow_redirects=True)
    assert 'flash-alert--danger' in response.text


# ──────────────────────────────────────────
#  3. СЕКРЕТНАЯ СТРАНИЦА
# ──────────────────────────────────────────

# 10. Авторизованный пользователь видит секретную страницу
def test_secret_accessible_when_authenticated(client):
    login(client)
    response = client.get('/secret')
    assert response.status_code == 200
    assert 'secret-content' in response.text

# 11. Неавторизованный → редирект на /login
def test_secret_redirects_unauthenticated(client):
    response = client.get('/secret', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

# 12. После редиректа на /login — flash-сообщение об аутентификации
def test_secret_redirect_shows_auth_message(client):
    response = client.get('/secret', follow_redirects=True)
    assert response.status_code == 200
    assert 'аутентификации' in response.text.lower()
    assert 'flash-alert--warning' in response.text

# 13. Вход после редиректа → возврат на /secret
def test_secret_redirect_then_login_returns_to_secret(client):
    # Пытаемся зайти на /secret без авторизации → сохраняется next=/secret
    client.get('/secret')
    # Логинимся через форму с параметром next
    response = client.post('/login?next=%2Fsecret',
                           data={'username': 'user', 'password': 'qwerty'},
                           follow_redirects=True)
    assert response.status_code == 200
    # Оказались на секретной странице
    assert 'secret-content' in response.text


# ──────────────────────────────────────────
#  4. "ЗАПОМНИТЬ МЕНЯ"
# ──────────────────────────────────────────

# 14. Без «Запомнить меня» — remember_token НЕ установлен
def test_login_without_remember_no_token(client):
    response = client.post('/login', data={'username': 'user', 'password': 'qwerty'})
    set_cookies = str(response.headers.getlist('Set-Cookie'))
    assert 'remember_token' not in set_cookies

# 15. С «Запомнить меня» — remember_token установлен
def test_login_with_remember_sets_token(client):
    response = client.post('/login', data={'username': 'user', 'password': 'qwerty', 'remember': 'on'})
    set_cookies = str(response.headers.getlist('Set-Cookie'))
    assert 'remember_token' in set_cookies


# ──────────────────────────────────────────
#  5. НАВБАР
# ──────────────────────────────────────────

# 16. Неавторизованный → в навбаре есть «Войти», нет «Секретная»/«Выйти»
def test_navbar_unauthenticated(client):
    response = client.get('/')
    assert 'nav-login' in response.text
    assert 'nav-secret' not in response.text
    assert 'nav-logout' not in response.text

# 17. Авторизованный → в навбаре есть «Секретная» и «Выйти», нет «Войти»
def test_navbar_authenticated(client):
    login(client)
    response = client.get('/')
    assert 'nav-secret' in response.text
    assert 'nav-logout' in response.text
    assert 'nav-login' not in response.text