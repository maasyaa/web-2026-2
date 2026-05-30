import random
from functools import lru_cache
from faker import Faker
from flask import Flask, render_template, abort, request, make_response
import re

fake = Faker()

app = Flask(__name__)
application = app

images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
            '2d2ab7df-cdbc-48a8-a936-35bba702def5',
            '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
            'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
            'cab5b7f2-774e-4884-a200-0c0180fa777f']

def is_valid_start(phone):
    """Проверяет, начинается ли номер с +7 или 8 после очистки от мусора."""
    cleaned = re.sub(r'[^0-9\+]', '', phone)
    return cleaned.startswith('+7') or cleaned.startswith('8')

def generate_comments(replies=True):
    comments = []
    for _ in range(random.randint(1, 3)):
        comment = { 'author': fake.name(), 'text': fake.text() }
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments

def generate_post(i):
    return {
        'title': fake.sentence(nb_words=6)[:-1],
        'text': fake.paragraph(nb_sentences=100),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-2y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': generate_comments()
    }

@lru_cache
def posts_list():
    return sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)

@app.route('/')
def index():
    return render_template('posts.html', title='Блог', posts=posts_list())

@app.route('/posts')
def posts():
    return render_template('posts.html', title='Все посты', posts=posts_list())

@app.route('/posts/<int:post_index>')
def post(post_index):
    try:
        p = posts_list()[post_index]
    except IndexError:
        abort(404)
    return render_template('post.html', title=p['title'], post=p)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')


@app.route('/url-params')
def url_params():
    """Отображает все GET-параметры запроса."""
    return render_template('url_params.html', title='Параметры URL', params=request.args)


@app.route('/headers')
def headers():
    """Отображает все заголовки запроса."""
    return render_template('headers.html', title='Заголовки запроса', headers=request.headers)


@app.route('/cookie')
def cookie():
    """Устанавливает куку 'my_cookie', если ее нет. Удаляет, если установлена."""
    response = make_response(render_template('cookie.html', title='Cookie'))
    if request.cookies.get('my_cookie'):
        response.set_cookie('my_cookie', '', expires=0)
    else:
        response.set_cookie('my_cookie', 'some_value')
    return response


@app.route('/form-params', methods=['GET', 'POST'])
def form_params():
    """Отображает данные, отправленные через форму."""
    form_data = {}
    if request.method == 'POST':
        form_data = request.form
    return render_template('form_params.html', title='Параметры формы', form_data=form_data)


@app.route('/phone-validator', methods=['GET', 'POST'])
def phone_validator():
    error_message = None
    formatted_number = None
    phone_class = ''

    if request.method == 'POST':
        phone = request.form.get('phone', '')


        if not re.fullmatch(r'[0-9\s().\-+]*', phone):
            error_message = 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.'
        else:

            digits_only = re.sub(r'[^0-9]', '', phone)
            digit_count = len(digits_only)


            if digit_count not in (10, 11):
                error_message = 'Недопустимый ввод. Неверное количество цифр.'
            elif digit_count == 11:
                if not is_valid_start(phone):
                    error_message = 'Недопустимый ввод. Неверное количество цифр.'
                else:
                    formatted_number = format_phone_number(digits_only)
            elif digit_count == 10:
                if is_valid_start(phone):
                    error_message = 'Недопустимый ввод. Неверное количество цифр.'
                else:
                    formatted_number = format_phone_number(digits_only)


        if error_message:
            phone_class = 'is-invalid'
        elif formatted_number:
            phone_class = 'is-valid'

    return render_template('phone_validator.html',
                           title='Валидатор номера',
                           error_message=error_message,
                           formatted_number=formatted_number,
                           phone_class=phone_class)


def format_phone_number(digits):
    """
    Форматирует строку из 10 или 11 цифр в формат 8-***-***-***-**.
    По заданию всегда показываем начиная с 8.
    """
    # Берем последние 10 цифр
    if len(digits) == 11:
        digits = digits[-10:]
    return f'8-{digits[0:3]}-{digits[3:6]}-{digits[6:8]}-{digits[8:10]}'


if __name__ == '__main__':
    app.run(debug=True)