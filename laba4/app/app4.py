import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from faker import Faker
import random
from functools import lru_cache

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

from models import db, User, Role
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к этой странице необходимо войти.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- Блог (из ЛР3) -----------------
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

# ---------------- Маршруты -----------------
@app.route('/')
def index():
    users = User.query.all()
    return render_template('index.html', title='Пользователи', users=users)

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
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user_view.html', title='Просмотр пользователя', u=user)

@app.route('/users/create', methods=['GET', 'POST'])
@login_required
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
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Нельзя удалить самого себя', 'danger')
        return redirect(url_for('index'))
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'Пользователь {user.fio} удалён', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления: {str(e)}', 'danger')
    return redirect(url_for('index'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    from forms import ChangePasswordForm
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash('Неверный старый пароль', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Пароль успешно изменён', 'success')
            return redirect(url_for('index'))
    return render_template('change_password.html', title='Смена пароля', form=form)

# ---------------- Инициализация БД -----------------
if __name__ == '__main__':
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
            demo = User(login='user', first_name='Обычный', last_name='Пользователь', role_id=2)
            demo.set_password('User123!')
            db.session.add_all([admin, demo])
            db.session.commit()
    app.run(debug=True)