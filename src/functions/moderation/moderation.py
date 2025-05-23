from flask import Blueprint, g, jsonify, request, abort, render_template
from sqlalchemy.orm import joinedload

from src.functions.database.models import Report, Post, Comment, db

moderation_bp = Blueprint('moderation', __name__)

@moderation_bp.route('/moderation')
def moderation_panel():
    return render_template('moderation/moderation_panel.html')

@moderation_bp.route('/reports/pending')
def moderation_reports_pending():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = Report.query.filter_by(status='pending') \
        .options(joinedload(Report.user)) \
        .options(joinedload(Report.post).joinedload(Post.author)) \
        .options(joinedload(Report.comment).joinedload(Comment.author)) \
        .paginate(page=page, per_page=per_page, error_out=False)
    reports = pagination.items
    return render_template(
        'moderation/moderation_reports_pending.html',
        pending_reports=reports,
        pagination=pagination
    )

@moderation_bp.route('/reports/processed')
def moderation_reports_processed():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = Report.query.filter(Report.status != 'pending') \
        .options(joinedload(Report.user)) \
        .options(joinedload(Report.post).joinedload(Post.author)) \
        .options(joinedload(Report.comment).joinedload(Comment.author)) \
        .paginate(page=page, per_page=per_page, error_out=False)
    reports = pagination.items
    return render_template(
        'moderation/moderation_reports_processed.html',
        processed_reports=reports,
        pagination=pagination
    )

@moderation_bp.route('/handle_report/<int:report_id>', methods=['POST'])
def handle_report(report_id):
    if g.role not in ['admin', 'moderator']:
        abort(403)
    report = Report.query.get(report_id)
    if not report:
        abort(404)
    status = request.json.get('status')
    if status not in ['valid', 'invalid']:
        return jsonify({'success': False, 'message': '无效的状态值'})
    if status == 'invalid':
        if report.post:
            # 删除帖子及其所有评论
            for comment in report.post.comments:
                db.session.delete(comment)
            db.session.delete(report.post)
        elif report.comment:
            # 删除评论
            db.session.delete(report.comment)
        report.status = 'invalid'
        report.resolved_by = g.user.id if g.user else None
        db.session.commit()
        return jsonify({'success': True, 'message': '已违规，内容已删除'})
    elif status == 'valid':
        report.status = 'valid'
        report.resolved_by = g.user.id if g.user else None
        db.session.commit()
        return jsonify({'success': True, 'message': '未违规，举报已关闭'})