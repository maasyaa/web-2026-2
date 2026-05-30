import os
import re
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from faker import Faker
import random
from functools import lru_cache

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'lab5-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

from models import db, User, Role, VisitLog

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к этой странице необходимо войти.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ──────────────────────────────────────────
#  ДЕКОРАТОР ПРОВЕРКИ ПРАВ
# ──────────────────────────────────────────
def check_rights(action):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Администратор может всё
            if current_user.is_authenticated and current_user.role_obj and current_user.role_obj.name == 'Администратор':
                return f(*args, **kwargs)

            # Обычный пользователь
            if current_user.is_authenticated and current_user.role_obj and current_user.role_obj.name == 'Пользователь':
                if action == 'edit' and str(kwargs.get('user_id')) == str(current_user.id):
                    return f(*args, **kwargs)
                if action == 'show' and str(kwargs.get('user_id')) == str(current_user.id):
                    return f(*args, **kwargs)
                if action == 'view_logs':
                    return f(*args, **kwargs)

            flash('У вас недостаточно прав для доступа к данной странице.', 'danger')
            return redirect(url_for('index'))

        return decorated_function

    return decorator


# ──────────────────────────────────────────
#  АВТОМАТИЧЕСКОЕ ЛОГИРОВАНИЕ ПОСЕЩЕНИЙ
# ──────────────────────────────────────────
@app.before_request
def log_visit():
    if request.path.startswith('/static') or request.path.endswith('.ico'):
        return
    try:
        log = VisitLog(
            path=request.path,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


# ──────────────────────────────────────────
#  БЛОГ (из ЛР3)
# ──────────────────────────────────────────
fake = Faker()
images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
            '2d2ab7df-cdbc-48a8-a936-35bba702def5',
            '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
            'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
            'cab5b7f2-774e-4884-a200-0c0180fa777f']


def generate_comments(replies=True):
    comments = []
    for _ in range(random.randint(1, 3)):
        comment = {'author': fake.name(), 'text': fake.text()}
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments


def generate_post(i):
    return {
        'title': fake.sentence(nb_words=6)[:-1],
        'text': fake.paragraph(nb_sentences=20),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-2y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': generate_comments()
    }


@lru_cache
def posts_list():
    return sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)


# ──────────────────────────────────────────
#  ВАЛИДАЦИЯ (из ЛР4)
# ──────────────────────────────────────────
def validate_user_data(data, is_new=True):
    errors = {}
    if is_new:
        login = data.get('login', '').strip()
        if not login:
            errors['login'] = 'Поле не может быть пустым'
        elif len(login) < 5:
            errors['login'] = 'Логин должен быть не менее 5 символов'
        elif not re.match(r'^[a-zA-Z0-9]+$', login):
            errors['login'] = 'Только латинские буквы и цифры'
        elif User.query.filter_by(login=login).first():
            errors['login'] = 'Такой логин уже занят'

        password = data.get('password', '')
        if not password:
            errors['password'] = 'Поле не может быть пустым'
        else:
            if not (8 <= len(password) <= 128):
                errors['password'] = 'Пароль должен быть от 8 до 128 символов'
            if not any(c.isupper() for c in password):
                errors['password'] = 'Нужна хотя бы одна заглавная буква'
            if not any(c.islower() for c in password):
                errors['password'] = 'Нужна хотя бы одна строчная буква'
            if not any(c.isdigit() for c in password):
                errors['password'] = 'Нужна хотя бы одна цифра'
            if ' ' in password:
                errors['password'] = 'Пароль не должен содержать пробелы'
            allowed = set(r"~! ?@#$%^&*_-+()[]{}><\/|\"'. ,:;")
            if any(not (c.isalnum() or c in allowed) for c in password):
                errors['password'] = 'Пароль содержит недопустимые символы'

    if not data.get('first_name', '').strip():
        errors['first_name'] = 'Поле не может быть пустым'
    if not data.get('last_name', '').strip():
        errors['last_name'] = 'Поле не может быть пустым'
    return errors


# ──────────────────────────────────────────
#  ОСНОВНЫЕ МАРШРУТЫ (CRUD + права)
# ──────────────────────────────────────────
@app.route('/')
def index():
    users = User.query.all()
    return render_template('index.html', title='Пользователи', users=users)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        user = User.query.filter_by(login=login).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash('Вы успешно вошли!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Неверный логин или пароль', 'danger')
    return render_template('login.html', title='Вход')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/users/<int:user_id>')
@login_required
@check_rights('show')
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user_view.html', title='Просмотр пользователя', u=user)


@app.route('/users/create', methods=['GET', 'POST'])
@login_required
@check_rights('create')
def create_user():
    from forms import RegistrationForm
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            new_user = User(
                login=form.login.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                middle_name=form.middle_name.data,
                role_id=form.role_id.data if form.role_id.data != 0 else None
            )
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash('Пользователь успешно создан', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка БД: {str(e)}', 'danger')
    return render_template('user_form.html', title='Создание пользователя', form=form, is_edit=False)


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@check_rights('edit')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    from forms import EditUserForm
    form = EditUserForm(obj=user)
    if form.role_id.choices:
        form.role_id.data = user.role_id or 0
    if form.validate_on_submit():
        try:
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.middle_name = form.middle_name.data
            user.role_id = form.role_id.data if form.role_id.data != 0 else None
            db.session.commit()
            flash('Данные обновлены', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка БД: {str(e)}', 'danger')
    return render_template('user_form.html', title='Редактирование пользователя', form=form, is_edit=True, user=user)

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@check_rights('delete')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Нельзя удалить самого себя', 'danger')
        return redirect(url_for('index'))
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'Пользователь {user.fio} удалён.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
    return redirect(url_for('index'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pass = request.form.get('old_password')
        new_pass = request.form.get('new_password')
        confirm_pass = request.form.get('confirm_password')
        if not check_password_hash(current_user.password_hash, old_pass):
            flash('Неверный старый пароль.', 'danger')
        elif new_pass != confirm_pass:
            flash('Пароли не совпадают.', 'danger')
        else:
            errors = validate_user_data({'password': new_pass, 'first_name': 'x', 'last_name': 'x'})
            if 'password' in errors:
                flash(errors['password'], 'danger')
            else:
                current_user.password_hash = generate_password_hash(new_pass)
                db.session.commit()
                flash('Пароль успешно изменён!', 'success')
                return redirect(url_for('index'))
    return render_template('change_password.html', title='Смена пароля')


# ──────────────────────────────────────────
#  БЛОГ (маршруты)
# ──────────────────────────────────────────
@app.route('/posts')
def posts():
    return render_template('posts.html', title='Блог', posts=posts_list())


@app.route('/posts/<int:index>')
def post(index):
    try:
        p = posts_list()[index]
    except IndexError:
        abort(404)
    return render_template('post.html', title=p['title'], post=p)


# ──────────────────────────────────────────
#  ИНИЦИАЛИЗАЦИЯ БД И РЕГИСТРАЦИЯ BLUEPRINT
# ──────────────────────────────────────────
with app.app_context():
    db.create_all()
    if Role.query.count() == 0:
        admin_role = Role(name='Администратор', description='Полный доступ')
        user_role = Role(name='Пользователь', description='Обычный пользователь')
        db.session.add_all([admin_role, user_role])
        db.session.commit()
    if not User.query.filter_by(login='admin').first():
        admin = User(login='admin', first_name='Администратор', role_id=1)
        admin.set_password('Admin123!')
        user = User(login='user', first_name='Обычный', last_name='Пользователь', role_id=2)
        user.set_password('User123!')
        db.session.add_all([admin, user])
        db.session.commit()

    from reports import reports_bp
    if 'reports' not in app.blueprints:
        app.register_blueprint(reports_bp, url_prefix='/logs')


if __name__ == '__main__':
    app.run(debug=True)