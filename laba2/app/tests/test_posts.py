import pytest


# -------------------------------------------------------------------
# Тесты для страницы "Параметры URL" (URL Parameters)
# -------------------------------------------------------------------

def test_url_params_no_params(client):
    """На странице URL-параметров без параметров отображается сообщение об их отсутствии."""
    response = client.get('/url-params')
    assert response.status_code == 200
    assert 'Нет переданных параметров URL.' in response.text


def test_url_params_with_params(client):
    """На странице URL-параметров отображаются все переданные параметры."""
    response = client.get('/url-params?key1=value1&key2=value2')
    assert response.status_code == 200
    assert 'value1' in response.text
    assert 'value2' in response.text


# -------------------------------------------------------------------
# Тесты для страницы "Заголовки запроса" (Headers)
# -------------------------------------------------------------------

def test_headers_page_status(client):
    """Страница заголовков доступна."""
    response = client.get('/headers')
    assert response.status_code == 200


def test_headers_contain_host(client):
    """На странице отображается заголовок Host."""
    response = client.get('/headers')
    assert 'Host' in response.text


def test_headers_contain_user_agent(client):
    """На странице отображается заголовок User-Agent."""
    response = client.get('/headers')
    assert 'User-Agent' in response.text


# -------------------------------------------------------------------
# Тесты для страницы "Cookie"
# -------------------------------------------------------------------

def test_cookie_set_if_not_present(client):
    """Если куки нет, она устанавливается."""
    # Удаляем куку перед тестом
    client.set_cookie('my_cookie', '', expires=0)
    response = client.get('/cookie')
    assert response.status_code == 200
    # Проверяем, что в заголовках ответа есть Set-Cookie с нашим значением
    set_cookie = response.headers.get('Set-Cookie', '')
    assert 'my_cookie=some_value' in set_cookie


def test_cookie_deleted_if_present(client):
    """Если кука есть, она удаляется."""
    # Устанавливаем куку перед тестом
    client.set_cookie('my_cookie', 'test_value')
    response = client.get('/cookie')
    assert response.status_code == 200
    # Проверяем, что кука удаляется (пустое значение или истекший срок)
    set_cookie = response.headers.get('Set-Cookie', '')
    assert 'my_cookie=;' in set_cookie


# -------------------------------------------------------------------
# Тесты для страницы "Параметры формы" (Form Parameters)
# -------------------------------------------------------------------

def test_form_params_get_request(client):
    """При GET-запросе форма пуста."""
    response = client.get('/form-params')
    assert response.status_code == 200
    assert 'Данные еще не отправлены.' in response.text


def test_form_params_post_request(client):
    """При POST-запросе отображаются введенные данные."""
    response = client.post('/form-params', data={
        'name': 'Иван',
        'email': 'ivan@example.com'
    })
    assert response.status_code == 200
    assert 'Иван' in response.text
    assert 'ivan@example.com' in response.text


# -------------------------------------------------------------------
# Тесты для страницы "Валидация номера телефона"
# -------------------------------------------------------------------

def check_phone_error(response, expected_message):
    """Вспомогательная функция для проверки ошибки валидации."""
    assert response.status_code == 200
    assert 'is-invalid' in response.text
    assert expected_message in response.text


def test_phone_validator_page_get(client):
    """Страница валидатора отображается без ошибок при GET-запросе."""
    response = client.get('/phone-validator')
    assert response.status_code == 200
    assert 'is-invalid' not in response.text


def test_phone_invalid_symbols(client):
    """Ошибка при вводе недопустимых символов (буквы)."""
    response = client.post('/phone-validator', data={'phone': '123abc4567890'})
    check_phone_error(response, 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.')


def test_phone_invalid_symbols_special(client):
    """Ошибка при вводе недопустимых символов (@)."""
    response = client.post('/phone-validator', data={'phone': '123@456.7890'})
    check_phone_error(response, 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.')


def test_phone_wrong_length_9_digits(client):
    """Ошибка, если цифр меньше 10 (9 цифр)."""
    response = client.post('/phone-validator', data={'phone': '123-45-67-89'})
    check_phone_error(response, 'Недопустимый ввод. Неверное количество цифр.')


def test_phone_wrong_length_12_digits(client):
    """Ошибка, если цифр больше 11 (12 цифр)."""
    response = client.post('/phone-validator', data={'phone': '1-2-3-4-5-6-7-8-9-0-1-2'})
    check_phone_error(response, 'Недопустимый ввод. Неверное количество цифр.')


def test_phone_11_digits_bad_start(client):
    """Ошибка, если 11 цифр, но не начинается на +7 или 8."""
    response = client.post('/phone-validator', data={'phone': '9 (123) 456-78-90'})
    check_phone_error(response, 'Недопустимый ввод. Неверное количество цифр.')


# --- Тесты успешной валидации ---

def check_phone_success(response, expected_format):
    """Вспомогательная функция для проверки успешной валидации."""
    assert response.status_code == 200
    assert 'is-valid' in response.text
    assert 'is-invalid' not in response.text
    assert expected_format in response.text


def test_phone_valid_10_digits(client):
    """Корректный 10-значный номер."""
    response = client.post('/phone-validator', data={'phone': '123.456.75.90'})
    check_phone_success(response, '8-123-456-75-90')


def test_phone_valid_11_digits_with_8(client):
    """Корректный 11-значный номер, начинающийся с 8."""
    response = client.post('/phone-validator', data={'phone': '8 (123) 4567590'})
    check_phone_success(response, '8-123-456-75-90')


def test_phone_valid_11_digits_with_plus7(client):
    """Корректный 11-значный номер, начинающийся с +7."""
    response = client.post('/phone-validator', data={'phone': '+7 (123) 456-75-90'})
    check_phone_success(response, '8-123-456-75-90')


def test_phone_valid_with_spaces_and_dashes(client):
    """Корректный номер со сложным форматированием."""
    response = client.post('/phone-validator', data={'phone': '+7 123-456-75-90'})
    check_phone_success(response, '8-123-456-75-90')