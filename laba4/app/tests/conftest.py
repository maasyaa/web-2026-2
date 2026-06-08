import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app4 import app
from models import db, User, Role


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['LOGIN_DISABLED'] = False

    with app.app_context():
        # Сброс старого движка (на всякий случай)
        db.engine.dispose()
        db.create_all()

        # --- Создание ролей ---
        if Role.query.count() == 0:
            admin_role = Role(name='Администратор', description='Полный доступ')
            user_role = Role(name='Пользователь', description='Обычный пользователь')
            db.session.add_all([admin_role, user_role])
            db.session.commit()

        # --- Создание тестового пользователя ---
        if not User.query.filter_by(login='testuser').first():
            testuser = User(
                login='testuser',
                first_name='Тест',
                last_name='Пользователь',
                role_id=2
            )
            testuser.set_password('Test123!')
            db.session.add(testuser)
            db.session.commit()

    with app.test_client() as client:
        yield client

    # Cleanup
    with app.app_context():
        db.drop_all()
        db.engine.dispose()