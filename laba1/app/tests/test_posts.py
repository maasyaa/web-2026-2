import pytest
from flask import template_rendered
from contextlib import contextmanager

# 1. Test Index Page Status
def test_index_status(client):
    response = client.get('/')
    assert response.status_code == 200

# 2. Test Index Page Content
def test_index_content(client):
    response = client.get('/')
    assert "Лабораторная работа № 1" in response.text

# 3. Test Posts Page Status
def test_posts_status(client):
    response = client.get('/posts')
    assert response.status_code == 200

# 4. Test Posts Page Template Used
def test_posts_template_used(client, captured_templates, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    client.get('/posts')
    assert len(captured_templates) > 0
    template, _ = captured_templates[0]
    assert template.name == 'posts.html'

# 5. Test Posts Page Context Title
def test_posts_context_title(client, captured_templates, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    client.get('/posts')
    _, context = captured_templates[0]
    assert context['title'] == 'Все посты'

# 6. Test Posts Page Context Posts List
def test_posts_context_list(client, captured_templates, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    client.get('/posts')
    _, context = captured_templates[0]
    assert len(context['posts']) == 1

# 7. Test Single Post Page Status (Valid)
def test_post_status_valid(client, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    response = client.get('/posts/0')
    assert response.status_code == 200

# 8. Test Single Post Page Template Used
def test_post_template_used(client, captured_templates, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    client.get('/posts/0')
    assert len(captured_templates) > 0
    template, _ = captured_templates[0]
    assert template.name == 'post.html'

# 9. Test Single Post Page Context Title
def test_post_context_title(client, captured_templates, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    client.get('/posts/0')
    _, context = captured_templates[0]
    assert context['title'] == posts_list[0]['title']

# 10. Test Single Post Page Context Post Object
def test_post_context_object(client, captured_templates, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    client.get('/posts/0')
    _, context = captured_templates[0]
    assert context['post'] == posts_list[0]

# 11. Test Single Post Page Content: Title
def test_post_content_title(client, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    response = client.get('/posts/0')
    assert posts_list[0]['title'] in response.text

# 12. Test Single Post Page Content: Author
def test_post_content_author(client, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    response = client.get('/posts/0')
    assert posts_list[0]['author'] in response.text

# 13. Test Single Post Page Content: Date Format
def test_post_content_date(client, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    response = client.get('/posts/0')
    # Date is 2025-03-10 in fixture, template uses %Y-%m-%d
    assert "2025-03-10" in response.text

# 14. Test Single Post Page Content: Text
def test_post_content_text(client, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    response = client.get('/posts/0')
    assert posts_list[0]['text'] in response.text

# 15. Test Single Post Page Content: Image
def test_post_content_image(client, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    response = client.get('/posts/0')
    # Image ID is 123.jpg in fixture
    assert "123.jpg" in response.text

# 16. Test Single Post Page Content: Comment Form
def test_post_content_form(client, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    response = client.get('/posts/0')
    assert "Оставьте комментарий" in response.text
    assert "<form" in response.text

# 17. Test Single Post Page Content: Footer (Name and Group)
def test_post_content_footer(client, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    response = client.get('/posts/0')
    assert "Казарян Мария Арсеновна" in response.text
    assert "Группа: 241-372" in response.text

# 18. Test Invalid Post ID (404)
def test_post_404(client, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    response = client.get('/posts/1') # Valid is 0 only
    assert response.status_code == 404

# 19. Test Post Template Data Parsing (Check author specifically in template data)
def test_post_template_data(client, captured_templates, mocker, posts_list):
    mocker.patch("app1.posts_list", return_value=posts_list)
    client.get('/posts/0')
    _, context = captured_templates[0]
    assert context['post']['author'] == 'Иванов Иван Иванович'