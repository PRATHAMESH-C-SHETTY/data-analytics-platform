from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os, json, uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'datalens-prod-secret-2024-xK9mP2'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///datalens.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['REPORTS_FOLDER'] = os.path.join(os.path.dirname(__file__), 'reports')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# ══════════════════════════════════════════════════════════════
#  MODELS
# ══════════════════════════════════════════════════════════════
class User(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    username    = db.Column(db.String(80), unique=True, nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    avatar_color  = db.Column(db.String(20), default='#6366f1')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    datasets    = db.relationship('Dataset', backref='owner', lazy=True, cascade='all,delete-orphan')

class Dataset(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    uid         = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    name        = db.Column(db.String(255), nullable=False)
    file_type   = db.Column(db.String(20))
    num_rows    = db.Column(db.Integer)
    num_cols    = db.Column(db.Integer)
    file_size   = db.Column(db.Float)          # MB
    file_path   = db.Column(db.String(512))
    description = db.Column(db.Text, default='')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reports     = db.relationship('Report', backref='dataset', lazy=True, cascade='all,delete-orphan')

class Report(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    uid         = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    name        = db.Column(db.String(255))
    dataset_id  = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    file_path   = db.Column(db.String(512))
    report_type = db.Column(db.String(20), default='pdf')
    file_size   = db.Column(db.Float, default=0.0)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user        = db.relationship('User', backref='reports', foreign_keys=[user_id])

# ══════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════════════════════════════
def current_user():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════
@app.route('/')
def index():
    user = current_user()
    if user:
        datasets = Dataset.query.filter_by(user_id=user.id).order_by(Dataset.uploaded_at.desc()).all()
        reports  = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).all()
    else:
        datasets = Dataset.query.filter_by(user_id=None).order_by(Dataset.uploaded_at.desc()).all()
        reports  = Report.query.filter_by(user_id=None).order_by(Report.created_at.desc()).all()

    stats = {
        'total_datasets': len(datasets),
        'total_reports':  len(reports),
        'total_rows':     sum(d.num_rows or 0 for d in datasets),
        'total_cols':     sum(d.num_cols or 0 for d in datasets),
    }
    recent_datasets = datasets[:5]
    recent_reports  = reports[:5]
    return render_template('dashboard.html', stats=stats,
                           recent_datasets=recent_datasets, recent_reports=recent_reports,
                           user=user)

# ══════════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════════
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    user = current_user()
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)

        allowed = {'csv', 'xlsx', 'xls', 'json'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed:
            flash('Unsupported format. Please upload CSV, Excel, or JSON.', 'error')
            return redirect(request.url)

        original_name = secure_filename(file.filename)
        unique_fname  = f"{uuid.uuid4()}_{original_name}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_fname)
        file.save(filepath)

        try:
            from utils.data_engine import load_dataset
            df = load_dataset(filepath, ext)
            size_mb = round(os.path.getsize(filepath) / 1024 / 1024, 3)
            desc = request.form.get('description', '')
            dataset = Dataset(
                name=original_name, file_type=ext,
                num_rows=len(df), num_cols=len(df.columns),
                file_size=size_mb, file_path=filepath,
                description=desc,
                user_id=user.id if user else None
            )
            db.session.add(dataset)
            db.session.commit()
            flash(f'✓ "{original_name}" uploaded successfully ({len(df):,} rows, {len(df.columns)} columns).', 'success')
            return redirect(url_for('preview', dataset_id=dataset.id))
        except Exception as e:
            try: os.remove(filepath)
            except: pass
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(request.url)

    return render_template('upload.html', user=user)

# ══════════════════════════════════════════════════════════════
#  PREVIEW
# ══════════════════════════════════════════════════════════════
@app.route('/preview/<int:dataset_id>')
def preview(dataset_id):
    user = current_user()
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        flash('Dataset not found.', 'error')
        return redirect(url_for('datasets'))
    from utils.data_engine import load_dataset, inspect_dataset
    df   = load_dataset(dataset.file_path, dataset.file_type)
    info = inspect_dataset(df)
    preview_rows = df.head(15).to_dict('records')
    cols = list(df.columns)
    return render_template('preview.html', dataset=dataset, info=info,
                           preview_rows=preview_rows, cols=cols, user=user)

# ══════════════════════════════════════════════════════════════
#  ANALYSIS PAGE
# ══════════════════════════════════════════════════════════════
@app.route('/analyze/<int:dataset_id>')
def analyze(dataset_id):
    user = current_user()
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        flash('Dataset not found.', 'error')
        return redirect(url_for('datasets'))
    return render_template('analyze.html', dataset=dataset, user=user)

# ══════════════════════════════════════════════════════════════
#  ANALYSIS API  (called by JS)
# ══════════════════════════════════════════════════════════════
@app.route('/api/analyze/<int:dataset_id>')
def api_analyze(dataset_id):
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    try:
        from utils.data_engine      import load_dataset, clean_dataset
        from utils.analytics_engine import run_analysis
        from utils.viz_engine        import generate_charts
        from utils.insight_engine    import generate_insights

        df       = load_dataset(dataset.file_path, dataset.file_type)
        df_clean = clean_dataset(df)
        stats    = run_analysis(df_clean)
        charts   = generate_charts(df_clean)
        insights = generate_insights(df_clean, stats)

        return jsonify({
            'stats': stats, 'charts': charts, 'insights': insights,
            'shape': {'rows': len(df_clean), 'cols': len(df_clean.columns)},
            'columns': list(df_clean.columns),
            'dtypes': {c: str(df_clean[c].dtype) for c in df_clean.columns}
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# ══════════════════════════════════════════════════════════════
#  REPORT GENERATION
# ══════════════════════════════════════════════════════════════
@app.route('/report/generate/<int:dataset_id>', methods=['POST'])
def generate_report(dataset_id):
    user    = current_user()
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    try:
        payload     = request.get_json() or {}
        report_type = payload.get('type', 'pdf')

        from utils.data_engine      import load_dataset, clean_dataset
        from utils.analytics_engine import run_analysis
        from utils.viz_engine        import generate_charts
        from utils.insight_engine    import generate_insights
        from utils.report_engine     import create_pdf_report, create_excel_report

        df       = load_dataset(dataset.file_path, dataset.file_type)
        df_clean = clean_dataset(df)
        stats    = run_analysis(df_clean)
        charts   = generate_charts(df_clean)
        insights = generate_insights(df_clean, stats)

        ts          = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_name = f"Report_{dataset.name.rsplit('.',1)[0]}_{ts}"
        ext         = 'pdf' if report_type == 'pdf' else 'xlsx'
        fname       = f"{uuid.uuid4()}_{report_name}.{ext}"
        report_path = os.path.join(app.config['REPORTS_FOLDER'], fname)

        if report_type == 'pdf':
            create_pdf_report(report_path, dataset, df_clean, stats, charts, insights)
        else:
            create_excel_report(report_path, dataset, df_clean, stats, insights)

        size_mb = round(os.path.getsize(report_path) / 1024 / 1024, 3)
        report  = Report(name=report_name, dataset_id=dataset_id,
                         file_path=report_path, report_type=ext,
                         file_size=size_mb, user_id=user.id if user else None)
        db.session.add(report)
        db.session.commit()

        return jsonify({'success': True, 'report_id': report.id,
                        'report_name': report_name, 'size': size_mb})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# ══════════════════════════════════════════════════════════════
#  REPORTS LIST
# ══════════════════════════════════════════════════════════════
@app.route('/reports')
def reports():
    user = current_user()
    if user:
        all_reports = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).all()
    else:
        all_reports = Report.query.filter_by(user_id=None).order_by(Report.created_at.desc()).all()
    return render_template('reports.html', reports=all_reports, user=user)

@app.route('/report/download/<int:report_id>')
def download_report(report_id):
    report = db.session.get(Report, report_id)
    if not report or not os.path.exists(report.file_path):
        flash('Report file not found.', 'error')
        return redirect(url_for('reports'))
    ext  = report.report_type
    mime = 'application/pdf' if ext == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return send_file(report.file_path, as_attachment=True,
                     download_name=f"{report.name}.{ext}", mimetype=mime)

@app.route('/report/delete/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    report = db.session.get(Report, report_id)
    if report:
        try:
            if os.path.exists(report.file_path): os.remove(report.file_path)
        except: pass
        db.session.delete(report)
        db.session.commit()
        flash('Report deleted.', 'success')
    return redirect(url_for('reports'))

# ══════════════════════════════════════════════════════════════
#  DATASETS LIST
# ══════════════════════════════════════════════════════════════
@app.route('/datasets')
def datasets():
    user = current_user()
    if user:
        all_datasets = Dataset.query.filter_by(user_id=user.id).order_by(Dataset.uploaded_at.desc()).all()
    else:
        all_datasets = Dataset.query.filter_by(user_id=None).order_by(Dataset.uploaded_at.desc()).all()
    return render_template('datasets.html', datasets=all_datasets, user=user)

@app.route('/dataset/delete/<int:dataset_id>', methods=['POST'])
def delete_dataset(dataset_id):
    dataset = db.session.get(Dataset, dataset_id)
    if dataset:
        try:
            if os.path.exists(dataset.file_path): os.remove(dataset.file_path)
        except: pass
        db.session.delete(dataset)
        db.session.commit()
        flash('Dataset deleted.', 'success')
    return redirect(url_for('datasets'))

# ══════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user     = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id']  = user.id
            session['username'] = user.username
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html', user=None)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('user_id'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(request.url)
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return redirect(request.url)
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(request.url)
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return redirect(request.url)
        import random
        colors = ['#6366f1','#06b6d4','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899']
        user = User(username=username, email=email,
                    password_hash=generate_password_hash(password),
                    avatar_color=random.choice(colors))
        db.session.add(user)
        db.session.commit()
        session['user_id']  = user.id
        session['username'] = user.username
        flash(f'Account created! Welcome, {username}!', 'success')
        return redirect(url_for('index'))
    return render_template('signup.html', user=None)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    user = current_user()
    datasets = Dataset.query.filter_by(user_id=user.id).order_by(Dataset.uploaded_at.desc()).all()
    reports  = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).all()
    return render_template('profile.html', user=user, datasets=datasets, reports=reports)

# ══════════════════════════════════════════════════════════════
#  DASHBOARD REALTIME API
# ══════════════════════════════════════════════════════════════
@app.route('/api/dashboard/stats')
def api_dashboard_stats():
    user = current_user()
    if user:
        datasets = Dataset.query.filter_by(user_id=user.id).all()
        reports  = Report.query.filter_by(user_id=user.id).all()
    else:
        datasets = Dataset.query.all()
        reports  = Report.query.all()

    # Activity timeline (last 7 days)
    from collections import defaultdict
    from datetime import timedelta
    today = datetime.utcnow().date()
    activity = {str(today - timedelta(days=i)): {'uploads': 0, 'reports': 0} for i in range(6, -1, -1)}
    for d in datasets:
        k = str(d.uploaded_at.date())
        if k in activity: activity[k]['uploads'] += 1
    for r in reports:
        k = str(r.created_at.date())
        if k in activity: activity[k]['reports'] += 1

    file_types = defaultdict(int)
    for d in datasets: file_types[d.file_type.upper()] += 1

    return jsonify({
        'total_datasets': len(datasets),
        'total_reports':  len(reports),
        'total_rows':     sum(d.num_rows or 0 for d in datasets),
        'total_size_mb':  round(sum(d.file_size or 0 for d in datasets), 2),
        'activity':       activity,
        'file_types':     dict(file_types),
        'recent_datasets': [{'id': d.id, 'name': d.name, 'rows': d.num_rows,
                              'cols': d.num_cols, 'type': d.file_type,
                              'uploaded_at': d.uploaded_at.strftime('%b %d, %Y %H:%M')}
                             for d in sorted(datasets, key=lambda x: x.uploaded_at, reverse=True)[:5]],
        'recent_reports':  [{'id': r.id, 'name': r.name, 'type': r.report_type,
                              'size': r.file_size, 'dataset_name': r.dataset.name if r.dataset else 'N/A',
                              'dataset_id': r.dataset_id,
                              'created_at': r.created_at.strftime('%b %d, %Y %H:%M')}
                             for r in sorted(reports, key=lambda x: x.created_at, reverse=True)[:5]],
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5055)
