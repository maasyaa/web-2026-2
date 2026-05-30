import pytest
from app import app, db
from models import User, Role, VisitLog

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Создаём роли
            admin_role = Role(name='Администратор', description='')
            user_role = Role(name='Пользователь', description='')
            db.session.add_all([admin_role, user_role])
            db.session.commit()
            # Создаём тестового админа и пользователя
            admin = User(login='admin', first_name='Admin', role_id=1)
            admin.set_password('Admin123!')
            user = User(login='user', first_name='User', role_id=2)
            user.set_password('User123!')
            db.session.add_all([admin, user])
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def login(client, login, password):
    return client.post('/login', data={'login': login, 'password': password, 'remember': False}, follow_redirects=True)

def test_logging_works(client):
    """Проверка, что посещения логируются"""
    client.get('/')
    with app.app_context():
        assert VisitLog.query.count() >= 1

def test_admin_can_see_all_logs(client):
    login(client, 'admin', 'Admin123!')
    # Создаём несколько логов от разных пользователей
    with app.app_context():
        user = User.query.filter_by(login='user').first()
        log1 = VisitLog(path='/test1', user_id=1)
        log2 = VisitLog(path='/test2', user_id=user.id)
        db.session.add_all([log1, log2])
        db.session.commit()
    rv = client.get('/logs/')
    assert b'/test1' in rv.data
    assert b'/test2' in rv.data

def test_user_sees_only_own_logs(client):
    login(client, 'user', 'User123!')
    with app.app_context():
        user = User.query.filter_by(login='user').first()
        admin = User.query.filter_by(login='admin').first()
        log1 = VisitLog(path='/user_page', user_id=user.id)
        log2 = VisitLog(path='/admin_page', user_id=admin.id)
        db.session.add_all([log1, log2])
        db.session.commit()
    rv = client.get('/logs/')
    assert b'/user_page' in rv.data
    assert b'/admin_page' not in rv.data

def test_pages_stat_only_for_admin(client):
    login(client, 'user', 'User123!')
    rv = client.get('/logs/pages', follow_redirects=True)
    assert b'У вас недостаточно прав' in rv.data
    login(client, 'admin', 'Admin123!')
    rv = client.get('/logs/pages')
    assert rv.status_code == 200

def test_export_csv(client):
    login(client, 'admin', 'Admin123!')
    rv = client.get('/logs/export/pages')
    assert rv.status_code == 200
    assert rv.mimetype == 'text/csv'