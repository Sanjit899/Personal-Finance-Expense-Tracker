# app.py
from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from datetime import date
from sqlalchemy import func, case
import csv, io

# Import reportlab for PDF generation
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-change-this'  # change to env var for production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --------------------
# Models
# --------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    categories = db.relationship('Category', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='category', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    description = db.Column(db.String(200))
    date = db.Column(db.Date, default=date.today)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --------------------
# Forms
# --------------------
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3,64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(6,128)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class TransactionForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired()])
    type = SelectField('Type', choices=[('expense','Expense'),('income','Income')], validators=[DataRequired()])
    category = SelectField('Category', coerce=int)
    date = DateField('Date', default=date.today, format='%Y-%m-%d')
    description = TextAreaField('Description')
    submit = SubmitField('Save')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(1,64)])
    submit = SubmitField('Add')

# --------------------
# Routes
# --------------------
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing = User.query.filter((User.username==form.username.data)|(User.email==form.email.data)).first()
        if existing:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))
        u = User(username=form.username.data, email=form.email.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        # default categories
        for name in ['Food','Transport','Bills','Salary','Shopping','Other']:
            c = Category(name=name, user=u)
            db.session.add(c)
        db.session.commit()
        flash('Account created. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(username=form.username.data).first()
        if u and u.check_password(form.password.data):
            login_user(u)
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).limit(10).all()
    income = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='income').scalar() or 0
    expense = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='expense').scalar() or 0
    balance = income - expense
    return render_template('dashboard.html', transactions=transactions, income=income, expense=expense, balance=balance)

@app.route('/transactions')
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('q', '', type=str).strip()

    q = Transaction.query.filter_by(user_id=current_user.id)

    if search_term:
        # Match search term against description, category name, or type
        q = q.join(Category, isouter=True).filter(
            db.or_(
                Transaction.description.ilike(f"%{search_term}%"),
                Transaction.type.ilike(f"%{search_term}%"),
                Category.name.ilike(f"%{search_term}%")
            )
        )

    q = q.order_by(Transaction.date.desc())
    transactions = q.paginate(page=page, per_page=20)

    return render_template(
        'transactions.html',
        transactions=transactions
    )

@app.route('/transaction/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        t = Transaction(
            amount=form.amount.data,
            type=form.type.data,
            description=form.description.data,
            date=form.date.data,
            category_id=form.category.data if form.category.data else None,
            user_id=current_user.id
        )
        db.session.add(t)
        db.session.commit()
        flash('Transaction added', 'success')
        return redirect(url_for('transactions'))

    return render_template('add_transaction.html', form=form)

@app.route('/transaction/edit/<int:tx_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(tx_id):
    t = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    form = TransactionForm(obj=t)
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        t.amount = form.amount.data
        t.type = form.type.data
        t.description = form.description.data
        t.date = form.date.data
        t.category_id = form.category.data if form.category.data else None
        db.session.commit()
        flash('Transaction updated successfully.', 'success')
        return redirect(url_for('transactions'))

    return render_template('edit_transaction.html', form=form, transaction=t)

@app.route('/transaction/delete/<int:tx_id>', methods=['POST'])
@login_required
def delete_transaction(tx_id):
    t = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    db.session.delete(t)
    db.session.commit()
    flash('Transaction deleted.', 'info')
    return redirect(url_for('transactions'))

@app.route('/category/add', methods=['GET','POST'])
@login_required
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        c = Category(name=form.name.data, user_id=current_user.id)
        db.session.add(c)
        db.session.commit()
        flash('Category added', 'success')
        return redirect(url_for('add_transaction'))
    return render_template('add_category.html', form=form)

@app.route('/category/edit/<int:cat_id>', methods=['GET', 'POST'])
@login_required
def edit_category(cat_id):
    c = Category.query.filter_by(id=cat_id, user_id=current_user.id).first_or_404()
    form = CategoryForm(obj=c)

    if form.validate_on_submit():
        c.name = form.name.data
        db.session.commit()
        flash('Category updated.', 'success')
        return redirect(url_for('add_transaction'))

    return render_template('edit_category.html', form=form)

@app.route('/category/delete/<int:cat_id>', methods=['POST'])
@login_required
def delete_category(cat_id):
    c = Category.query.filter_by(id=cat_id, user_id=current_user.id).first_or_404()
    # Optional: check if category has transactions, handle accordingly if needed
    db.session.delete(c)
    db.session.commit()
    flash('Category deleted.', 'info')
    return redirect(url_for('add_transaction'))

@app.route('/export/csv')
@login_required
def export_csv():
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date','Type','Amount','Category','Description'])
    txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
    for t in txs:
        cw.writerow([t.date.isoformat(), t.type, t.amount, t.category.name if t.category else '', t.description or ''])
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='transactions.csv')

@app.route('/export/pdf')
@login_required
def export_pdf():
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "Transaction History")

    # Table header
    p.setFont("Helvetica-Bold", 12)
    y = 770
    headers = ['Date', 'Type', 'Amount', 'Category', 'Description']
    x_positions = [50, 150, 220, 290, 400]

    for i, header in enumerate(headers):
        p.drawString(x_positions[i], y, header)

    # Table rows
    p.setFont("Helvetica", 10)
    y -= 20

    txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()

    for t in txs:
        if y < 50:  # new page if near bottom
            p.showPage()
            y = 800
        p.drawString(x_positions[0], y, t.date.strftime("%Y-%m-%d"))
        p.drawString(x_positions[1], y, t.type.capitalize())
        p.drawString(x_positions[2], y, f"{t.amount:.2f}")
        p.drawString(x_positions[3], y, t.category.name if t.category else "")
        p.drawString(x_positions[4], y, t.description or "")
        y -= 15

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='transactions.pdf')

@app.route('/api/summary')
@login_required
def api_summary():
    # SQLAlchemy 2.x style case usage
    income_case = case((Transaction.type == 'income', Transaction.amount), else_=0)
    expense_case = case((Transaction.type == 'expense', Transaction.amount), else_=0)

    rows = db.session.query(
        func.strftime('%Y-%m', Transaction.date).label('ym'),
        func.sum(income_case).label('income'),
        func.sum(expense_case).label('expense')
    ).filter(Transaction.user_id == current_user.id).group_by('ym').order_by('ym').all()

    summary = [{'period': r.ym, 'income': float(r.income or 0), 'expense': float(r.expense or 0)} for r in rows]
    return jsonify(summary)


if __name__ == '__main__':
    app.run(debug=True)
