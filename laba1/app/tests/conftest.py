import sys
import os
import pytest
from flask import template_rendered
from datetime import datetime

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем приложение
from app1 import app as application

@pytest.fixture
def client():
    application.config['TESTING'] = True
    with application.test_client() as client:
        with application.app_context():
            yield client

@pytest.fixture
def captured_templates():
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, application)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, application)

@pytest.fixture
def posts_list():
    return [
        {
            'title': 'Тестовый пост',
            'text': 'Текст тестового поста для проверки',
            'author': 'Иванов Иван Иванович',
            'date': datetime(2025, 3, 10),
            'image_id': '123.jpg',
            'comments': []
        }
    ]