from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, abort
)
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)
from faker import Faker
import random
from functools import lru_cache
from werkzeug.middleware.proxy_fix import ProxyFix

fake = Faker()

app = Flask(__name__)
app.secret_key = 'dev-secret-key-lab3-2024'
# Фикс для корректного отображения внутри Хаба
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

# ──────────────────────────────────────────
#  ДАННЫЕ ПОСТОВ (из Лабораторной 1)
# ──────────────────────────────────────────
images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
            '2d2ab7df-cdbc-48a8-a936-35bba702def5',
            '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
            'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
            'cab5b7f2-774e-4884-a200-0c0180fa777f']

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

# ──────────────────────────────────────────
#  FLASK-LOGIN
# ──────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = (
    'Для доступа к запрашиваемой странице '
    'необходимо пройти процедуру аутентификации.'
)
login_manager.login_message_category = 'warning'

# ──────────────────────────────────────────
#  ПОЛЬЗОВАТЕЛИ (in-memory)
# ──────────────────────────────────────────
USERS = {
    'user': {'id': '1', 'password': 'qwerty'},
}


class User(UserMixin):
    def __init__(self, user_id: str, username: str):
        self.id = user_id
        self.username = username


@login_manager.user_loader
def load_user(user_id: str):
    for username, data in USERS.items():
        if data['id'] == user_id:
            return User(user_id, username)
    return None


# ──────────────────────────────────────────
#  МАРШРУТЫ
# ──────────────────────────────────────────

@app.route('/')
def index():
    return render_template('posts.html', title='Главная', posts=posts_list())

@app.route('/auth')
def auth():
    return render_template('auth.html', title='Аутентификация')

@app.route('/posts/<int:index>')
def post(index):
    try:
        p = posts_list()[index]
    except IndexError:
        abort(404)
    return render_template('post.html', title=p['title'], post=p)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')


@app.route('/counter')
def counter():
    session['visits'] = session.get('visits', 0) + 1
    visits = session['visits']
    return render_template('counter.html', title='Счётчик посещений', visits=visits)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user_data = USERS.get(username)
        if user_data and user_data['password'] == password:
            user = User(user_data['id'], username)
            login_user(user, remember=remember)
            flash('Вы успешно вошли в систему!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))

        flash('Неверный логин или пароль.', 'danger')

    return render_template('login.html', title='Вход')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html', title='Секретная страница')


if __name__ == '__main__':
    app.run(debug=True)