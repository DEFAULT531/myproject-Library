from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pymysql
app = Flask(__name__)

# MySQL 配置 (密码: 123456)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@localhost:3306/library'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'library-secret-key'

db = SQLAlchemy(app)

# Flask-Login 配置
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# 数据库模型
class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True)
    category = db.Column(db.String(50))
    stock = db.Column(db.Integer, default=1)
    is_delete = db.Column(db.String(1), default='N')

    borrows = db.relationship('Borrow', backref='book', lazy=True)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    is_delete = db.Column(db.String(1), default='N')

    borrows = db.relationship('Borrow', backref='user', lazy=True)


class Borrow(db.Model):
    __tablename__ = 'borrows'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    borrow_date = db.Column(db.Date, default=datetime.now().date)
    return_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='借阅中')
    is_delete = db.Column(db.String(1), default='N')


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)


# 组织管理
class Organization(db.Model):
    __tablename__ = 'organizations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    description = db.Column(db.String(500))
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_delete = db.Column(db.String(1), default='N')

    children = db.relationship('Organization', backref=db.backref('parent', remote_side=[id]), lazy=True)


# 菜单管理
class Menu(db.Model):
    __tablename__ = 'menus'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(50))
    url = db.Column(db.String(200))
    parent_id = db.Column(db.Integer, db.ForeignKey('menus.id'))
    sort_order = db.Column(db.Integer, default=0)
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_delete = db.Column(db.String(1), default='N')

    children = db.relationship('Menu', backref=db.backref('parent', remote_side=[id]), lazy=True)


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# 初始化数据库
def init_db():
    # 创建数据库
    connection = pymysql.connect(host='localhost', port=3306, user='root', password='123456')
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS library")
            cursor.execute("USE library")
            # 为已存在的表添加/更新is_delete字段
            cursor.execute("SHOW COLUMNS FROM books LIKE 'is_delete'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE books ADD COLUMN is_delete VARCHAR(1) DEFAULT 'N'")
            else:
                cursor.execute("ALTER TABLE books MODIFY COLUMN is_delete VARCHAR(1) DEFAULT 'N'")

            cursor.execute("SHOW COLUMNS FROM users LIKE 'is_delete'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN is_delete VARCHAR(1) DEFAULT 'N'")
            else:
                cursor.execute("ALTER TABLE users MODIFY COLUMN is_delete VARCHAR(1) DEFAULT 'N'")

            cursor.execute("SHOW COLUMNS FROM borrows LIKE 'is_delete'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE borrows ADD COLUMN is_delete VARCHAR(1) DEFAULT 'N'")
            else:
                cursor.execute("ALTER TABLE borrows MODIFY COLUMN is_delete VARCHAR(1) DEFAULT 'N'")

            cursor.execute("SHOW COLUMNS FROM organizations LIKE 'is_delete'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE organizations ADD COLUMN is_delete VARCHAR(1) DEFAULT 'N'")
            else:
                cursor.execute("ALTER TABLE organizations MODIFY COLUMN is_delete VARCHAR(1) DEFAULT 'N'")

            cursor.execute("SHOW COLUMNS FROM menus LIKE 'is_delete'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE menus ADD COLUMN is_delete VARCHAR(1) DEFAULT 'N'")
            else:
                cursor.execute("ALTER TABLE menus MODIFY COLUMN is_delete VARCHAR(1) DEFAULT 'N'")
        connection.commit()
    finally:
        connection.close()

    # 创建表
    with app.app_context():
        db.create_all()
        # 创建默认管理员
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(
                username='admin',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
# 首页 - 图书列表
@app.route('/')
@login_required
def index():
    books = Book.query.filter_by(is_delete='N').all()
    return render_template('index.html', books=books)


# 图书管理
@app.route('/books')
@login_required
def books():
    books = Book.query.filter_by(is_delete='N').all()
    return render_template('book.html', books=books)


@app.route('/book/add', methods=['POST'])
@login_required
def add_book():
    title = request.form.get('title')
    author = request.form.get('author')
    isbn = request.form.get('isbn')
    category = request.form.get('category')
    stock = request.form.get('stock', type=int, default=1)

    if not title or not author:
        return redirect(url_for('books'))

    # 唯一性校验：检查ID+书名+作者+分类+ISBN是否已存在
    existing = Book.query.filter(
        Book.is_delete == 'N',
        Book.title == title,
        Book.author == author,
        Book.category == category
    ).first()
    if existing:
        return render_template('book.html', books=Book.query.filter_by(is_delete='N').all(), error='书名+作者+分类组合已存在，不能重复')

    book = Book(title=title, author=author, isbn=isbn, category=category, stock=stock)
    db.session.add(book)
    db.session.commit()
    return redirect(url_for('books'))


@app.route('/book/edit/<int:id>', methods=['POST'])
@login_required
def edit_book(id):
    book = Book.query.get_or_404(id)
    title = request.form.get('title')
    author = request.form.get('author')

    if not title or not author:
        return redirect(url_for('books'))

    # 唯一性校验：检查书名+作者+分类+ISBN是否已存在（排除自身）
    existing = Book.query.filter(
        Book.id != id,
        Book.is_delete == 'N',
        Book.title == title,
        Book.author == author,
        Book.category == request.form.get('category')
    ).first()
    if existing:
        return render_template('book.html', books=Book.query.filter_by(is_delete='N').all(), error='书名+作者+分类组合已存在，不能重复')

    book.title = title
    book.author = author
    book.isbn = request.form.get('isbn')
    book.category = request.form.get('category')
    book.stock = request.form.get('stock', type=int)
    db.session.commit()
    return redirect(url_for('books'))


@app.route('/book/delete/<int:id>')
@login_required
def delete_book(id):
    book = Book.query.get_or_404(id)
    book.is_delete='Y'
    db.session.commit()
    return redirect(url_for('books'))


# 用户管理
@app.route('/users')
@login_required
def users():
    users = User.query.filter_by(is_delete='N').all()
    return render_template('user.html', users=users)


@app.route('/user/add', methods=['POST'])
@login_required
def add_user():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')

    user = User(name=name, email=email, phone=phone)
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/user/edit/<int:id>', methods=['POST'])
@login_required
def edit_user(id):
    user = User.query.get_or_404(id)
    user.name = request.form.get('name')
    user.email = request.form.get('email')
    user.phone = request.form.get('phone')
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/user/delete/<int:id>')
@login_required
def delete_user(id):
    user = User.query.get_or_404(id)
    user.is_delete='Y'
    db.session.commit()
    return redirect(url_for('users'))


# 借阅管理
@app.route('/borrows')
@login_required
def borrows():
    borrows = Borrow.query.filter_by(is_delete='N').order_by(Borrow.borrow_date.desc()).all()
    return render_template('borrow.html', borrows=borrows)


@app.route('/borrow/add', methods=['POST'])
@login_required
def add_borrow():
    book_id = request.form.get('book_id', type=int)
    user_id = request.form.get('user_id', type=int)
    return_date = request.form.get('return_date')

    # 检查库存
    book = Book.query.get(book_id)
    if book and book.stock > 0:
        book.stock -= 1
        borrow = Borrow(book_id=book_id, user_id=user_id, return_date=return_date, status='借阅中')
        db.session.add(borrow)
        db.session.commit()

    return redirect(url_for('borrows'))


@app.route('/borrow/return/<int:id>')
@login_required
def return_book(id):
    borrow = Borrow.query.get_or_404(id)
    if borrow.status == '借阅中':
        borrow.status = '已归还'
        book = Book.query.get(borrow.book_id)
        if book:
            book.stock += 1
        db.session.commit()
    return redirect(url_for('borrows'))


@app.route('/borrow/delete/<int:id>')
@login_required
def delete_borrow(id):
    borrow = Borrow.query.get_or_404(id)
    # 如果是借阅中状态，归还库存
    if borrow.status == '借阅中':
        book = Book.query.get(borrow.book_id)
        if book:
            book.stock += 1
    borrow.is_delete='Y'
    db.session.commit()
    return redirect(url_for('borrows'))


# API 接口
@app.route('/api/books')
def api_books():
    books = Book.query.filter_by(is_delete='N').all()
    return jsonify([{
        'id': b.id, 'title': b.title, 'author': b.author,
        'isbn': b.isbn, 'category': b.category, 'stock': b.stock
    } for b in books])


@app.route('/api/users')
def api_users():
    users = User.query.filter_by(is_delete='N').all()
    return jsonify([{
        'id': u.id, 'name': u.name, 'email': u.email, 'phone': u.phone
    } for u in users])


# 组织管理
@app.route('/organizations')
@login_required
def organizations():
    orgs = Organization.query.filter_by(is_delete='N').all()
    return render_template('organization.html', organizations=orgs)


@app.route('/organization/add', methods=['POST'])
@login_required
def add_organization():
    name = request.form.get('name')
    code = request.form.get('code')
    parent_id = request.form.get('parent_id', type=int)
    description = request.form.get('description')

    if not name or not code:
        return redirect(url_for('organizations'))

    org = Organization(name=name, code=code, parent_id=parent_id, description=description)
    db.session.add(org)
    db.session.commit()
    return redirect(url_for('organizations'))


@app.route('/organization/edit/<int:id>', methods=['POST'])
@login_required
def edit_organization(id):
    org = Organization.query.get_or_404(id)
    org.name = request.form.get('name')
    org.code = request.form.get('code')
    org.parent_id = request.form.get('parent_id', type=int)
    org.description = request.form.get('description')
    db.session.commit()
    return redirect(url_for('organizations'))


@app.route('/organization/delete/<int:id>')
@login_required
def delete_organization(id):
    org = Organization.query.get_or_404(id)
    org.is_delete='Y'
    db.session.commit()
    return redirect(url_for('organizations'))


# 菜单管理
@app.route('/menus')
@login_required
def menus():
    menu_list = Menu.query.filter_by(is_delete='N').order_by(Menu.sort_order).all()
    return render_template('menu.html', menus=menu_list)


@app.route('/menu/add', methods=['POST'])
@login_required
def add_menu():
    name = request.form.get('name')
    icon = request.form.get('icon')
    url = request.form.get('url')
    parent_id = request.form.get('parent_id', type=int)
    sort_order = request.form.get('sort_order', type=int, default=0)

    if not name:
        return redirect(url_for('menus'))

    menu = Menu(name=name, icon=icon, url=url, parent_id=parent_id, sort_order=sort_order)
    db.session.add(menu)
    db.session.commit()
    return redirect(url_for('menus'))


@app.route('/menu/edit/<int:id>', methods=['POST'])
@login_required
def edit_menu(id):
    menu = Menu.query.get_or_404(id)
    menu.name = request.form.get('name')
    menu.icon = request.form.get('icon')
    menu.url = request.form.get('url')
    menu.parent_id = request.form.get('parent_id', type=int)
    menu.sort_order = request.form.get('sort_order', type=int, default=0)
    db.session.commit()
    return redirect(url_for('menus'))


@app.route('/menu/delete/<int:id>')
@login_required
def delete_menu(id):
    menu = Menu.query.get_or_404(id)
    menu.is_delete='Y'
    db.session.commit()
    return redirect(url_for('menus'))


# 登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            login_user(admin)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='用户名或密码错误')
    return render_template('login.html')


# 登出
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)