import sys
import os
import pytest
from datetime import datetime
from flask import template_rendered
from contextlib import contextmanager


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app3 import app as application

@pytest.fixture
def app():
    application.config['TESTING'] = True
    application.config['WTF_CSRF_ENABLED'] = False
    return application

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
@contextmanager
def captured_templates(app):
    recorded = []
    def record(template, context):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

@pytest.fixture
def posts_list():
    return [
        {
            'title': 'Заголовок поста',
            'text': 'Текст поста',
            'author': 'Иванов Иван Иванович',
            'date': datetime(2025, 3, 10),
            'image_id': '123.jpg',
            'comments': []
        }
    ]