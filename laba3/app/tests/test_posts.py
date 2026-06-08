import pytest


def login(client, username='user', password='qwerty', remember=False):
    """Хелпер: выполнить вход."""
    data = {'username': username, 'password': password}
    if remember:
        data['remember'] = 'on'
    return client.post('/login', data=data, follow_redirects=True)


# ──────────────────────────────────────────
#  1. СЧЁТЧИК ПОСЕЩЕНИЙ
# ──────────────────────────────────────────

def test_counter_first_visit(client):
    response = client.get('/counter')
    assert response.status_code == 200
    assert '1' in response.text


def test_counter_increments(client):
    client.get('/counter')
    client.get('/counter')
    response = client.get('/counter')
    assert response.status_code == 200
    assert '3' in response.text


def test_counter_independent_per_session(app):
    client_a = app.test_client()
    client_b = app.test_client()
    client_a.get('/counter')
    client_a.get('/counter')
    resp_a = client_a.get('/counter')
    resp_b = client_b.get('/counter')
    assert '3' in resp_a.text
    assert '1' in resp_b.text


def test_counter_page_text(client):
    response = client.get('/counter')
    text = response.text.lower()
    assert 'посещ' in text or 'визит' in text


# ──────────────────────────────────────────
#  2. АУТЕНТИФИКАЦИЯ
# ──────────────────────────────────────────

def test_login_success_redirect(client):
    response = login(client)
    assert response.status_code == 200
    assert 'DevAuth' in response.text or 'Главная' in response.text
    assert 'успешно' in response.text.lower()


def test_login_success_flash_category(client):
    response = login(client)
    assert 'flash-alert--success' in response.text


def test_login_wrong_password(client):
    response = client.post('/login', data={'username': 'user', 'password': 'wrong'}, follow_redirects=True)
    assert response.status_code == 200
    assert 'login-form' in response.text
    assert 'Неверный логин или пароль' in response.text


def test_login_wrong_username(client):
    response = client.post('/login', data={'username': 'hacker', 'password': 'qwerty'}, follow_redirects=True)
    assert response.status_code == 200
    assert 'login-form' in response.text
    assert 'Неверный логин или пароль' in response.text


def test_login_failure_flash_category(client):
    response = client.post('/login', data={'username': 'x', 'password': 'x'}, follow_redirects=True)
    assert 'flash-alert--danger' in response.text


# ──────────────────────────────────────────
#  3. СЕКРЕТНАЯ СТРАНИЦА
# ──────────────────────────────────────────

def test_secret_redirects_unauthenticated(client):
    response = client.get('/secret', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_secret_redirect_shows_auth_message(client):
    response = client.get('/secret', follow_redirects=True)
    assert response.status_code == 200
    assert 'аутентификации' in response.text.lower()
    assert 'flash-alert--warning' in response.text



# ──────────────────────────────────────────
#  4. "ЗАПОМНИТЬ МЕНЯ"
# ──────────────────────────────────────────

def test_login_without_remember_no_token(client):
    response = client.post('/login', data={'username': 'user', 'password': 'qwerty'})
    set_cookies = str(response.headers.getlist('Set-Cookie'))
    assert 'remember_token' not in set_cookies


def test_login_with_remember_sets_token(client):
    response = client.post('/login', data={'username': 'user', 'password': 'qwerty', 'remember': 'on'})
    set_cookies = str(response.headers.getlist('Set-Cookie'))
    assert 'remember_token' in set_cookies


# ──────────────────────────────────────────
#  5. НАВБАР
# ──────────────────────────────────────────

def test_navbar_unauthenticated(client):
    response = client.get('/')
    assert 'nav-login' in response.text
    assert 'nav-secret' not in response.text
    assert 'nav-logout' not in response.text


def test_navbar_authenticated(client):
    login(client)
    response = client.get('/')
    assert 'nav-secret' in response.text
    assert 'nav-logout' in response.text
    assert 'nav-login' not in response.text