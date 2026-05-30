from flask import Blueprint, render_template, request, Response, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, VisitLog, User

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    query = VisitLog.query.order_by(VisitLog.created_at.desc())
    if current_user.role_obj.name == 'Пользователь':
        query = query.filter_by(user_id=current_user.id)
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    return render_template('logs/index.html', logs=pagination.items, pagination=pagination)


@reports_bp.route('/pages')
@login_required
def pages_stat():
    if current_user.role_obj.name != 'Администратор':
        flash('У вас недостаточно прав.', 'danger')
        return redirect(url_for('reports.index'))
    stats = db.session.query(VisitLog.path, func.count(VisitLog.id)).group_by(VisitLog.path).order_by(func.count(VisitLog.id).desc()).all()
    return render_template('logs/pages.html', stats=stats)


@reports_bp.route('/users')
@login_required
def users_stat():
    if current_user.role_obj.name != 'Администратор':
        flash('У вас недостаточно прав.', 'danger')
        return redirect(url_for('reports.index'))
    stats = db.session.query(User.id, User.last_name, User.first_name, User.middle_name, func.count(VisitLog.id)) \
        .outerjoin(VisitLog).group_by(User.id).order_by(func.count(VisitLog.id).desc()).all()
    return render_template('logs/users.html', stats=stats)


@reports_bp.route('/export/<type>')
@login_required
def export_csv(type):
    if current_user.role_obj.name != 'Администратор':
        flash('У вас недостаточно прав.', 'danger')
        return redirect(url_for('reports.index'))
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    if type == 'pages':
        writer.writerow(['№', 'Страница', 'Количество посещений'])
        stats = db.session.query(VisitLog.path, func.count(VisitLog.id)).group_by(VisitLog.path).order_by(func.count(VisitLog.id).desc()).all()
        for i, (path, cnt) in enumerate(stats, 1):
            writer.writerow([i, path, cnt])
        filename = "pages_report.csv"
    else:
        writer.writerow(['№', 'Пользователь', 'Количество посещений'])
        stats = db.session.query(User, func.count(VisitLog.id)).outerjoin(VisitLog).group_by(User.id).order_by(func.count(VisitLog.id).desc()).all()
        for i, (user, cnt) in enumerate(stats, 1):
            name = user.fio if user else "Неаутентифицированный пользователь"
            writer.writerow([i, name, cnt])
        filename = "users_report.csv"
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})