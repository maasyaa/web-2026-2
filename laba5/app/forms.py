from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, EqualTo, ValidationError
import re

class RegistrationForm(FlaskForm):
    login = StringField('Логин', validators=[
        DataRequired(message='Логин не может быть пустым'),
        Length(min=5, message='Логин должен быть не менее 5 символов'),
        Regexp(r'^[a-zA-Z0-9]+$', message='Только латинские буквы и цифры')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль не может быть пустым'),
        Length(min=8, max=128)
    ])
    confirm = PasswordField('Подтверждение пароля', validators=[
        DataRequired(), EqualTo('password', message='Пароли не совпадают')
    ])
    last_name = StringField('Фамилия', validators=[DataRequired('Фамилия обязательна')])
    first_name = StringField('Имя', validators=[DataRequired('Имя обязательно')])
    middle_name = StringField('Отчество')
    role_id = SelectField('Роль', coerce=int, choices=[], validate_choice=False)
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from models import Role
        self.role_id.choices = [(0, '— без роли —')] + [(r.id, r.name) for r in Role.query.all()]

    def validate_password(self, field):
        pwd = field.data
        if not re.search(r'[A-Z]', pwd):
            raise ValidationError('Нужна хотя бы одна заглавная латинская буква')
        if not re.search(r'[a-z]', pwd):
            raise ValidationError('Нужна хотя бы одна строчная латинская буква')
        if not re.search(r'\d', pwd):
            raise ValidationError('Нужна хотя бы одна цифра')
        if ' ' in pwd:
            raise ValidationError('Пароль не должен содержать пробелы')
        allowed = r"~!?@#$%^&*_\-+()\[\]{}><\/\\|'\".,:;"
        if any(not (c.isalnum() or c in allowed) for c in pwd):
            raise ValidationError('Пароль содержит недопустимые символы')

    def validate_login(self, field):
        from models import User
        if User.query.filter_by(login=field.data).first():
            raise ValidationError('Пользователь с таким логином уже существует')

class EditUserForm(FlaskForm):
    last_name = StringField('Фамилия', validators=[DataRequired('Фамилия обязательна')])
    first_name = StringField('Имя', validators=[DataRequired('Имя обязательно')])
    middle_name = StringField('Отчество')
    role_id = SelectField('Роль', coerce=int, choices=[], validate_choice=False)
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from models import Role
        self.role_id.choices = [(0, '— без роли —')] + [(r.id, r.name) for r in Role.query.all()]

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Старый пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[
        DataRequired(),
        Length(min=8, max=128)
    ])
    confirm_password = PasswordField('Повторите пароль', validators=[
        DataRequired(), EqualTo('new_password', message='Пароли не совпадают')
    ])
    submit = SubmitField('Сменить пароль')

    def validate_new_password(self, field):
        pwd = field.data
        if not re.search(r'[A-Z]', pwd):
            raise ValidationError('Нужна хотя бы одна заглавная буква')
        if not re.search(r'[a-z]', pwd):
            raise ValidationError('Нужна хотя бы одна строчная буква')
        if not re.search(r'\d', pwd):
            raise ValidationError('Нужна хотя бы одна цифра')
        if ' ' in pwd:
            raise ValidationError('Пароль не должен содержать пробелы')
        allowed = r"~!?@#$%^&*_\-+()\[\]{}><\/\\|'\".,:;"
        if any(not (c.isalnum() or c in allowed) for c in pwd):
            raise ValidationError('Пароль содержит недопустимые символы')