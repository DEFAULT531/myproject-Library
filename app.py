from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.routing import IntegerConverter
from datetime import datetime, timedelta
import os
import time
import pymysql

# 雪花ID生成器
class Snowflake:
    def __init__(self, worker_id=1, datacenter_id=1, sequence=0):
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = sequence
        self.last_timestamp = 0

    def _timestamp(self):
        return int(time.time() * 1000)

    def next_id(self):
        timestamp = self._timestamp()
        if timestamp < self.last_timestamp:
            raise Exception("Clock moved backwards")
        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & 0xfff
            if self.sequence == 0:
                timestamp = self._wait_next_timestamp()
        else:
            self.sequence = 0
        self.last_timestamp = timestamp
        return ((timestamp - 1288834974657) << 22) | (self.datacenter_id << 17) | (self.worker_id << 12) | self.sequence

    def _wait_next_timestamp(self):
        while self._timestamp() <= self.last_timestamp:
            pass
        return self._timestamp()

snowflake = Snowflake(worker_id=1, datacenter_id=1)

app = Flask(__name__)

# 自定义BigInteger转换器 (必须在app创建后)
from werkzeug.routing import IntegerConverter
class BigIntegerConverter(IntegerConverter):
    regex = r'\d+'
app.url_map.converters['bigint'] = BigIntegerConverter

# MySQL 配置 (密码: 123456)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@localhost:3306/library'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'library-secret-key'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Flask-Login 配置
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# 数据库模型
class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.BigInteger, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True)
    category = db.Column(db.String(50))
    stock = db.Column(db.Integer, default=1)
    is_delete = db.Column(db.String(1), default='N')
    attachment = db.Column(db.String(500))  # 附件路径

    borrows = db.relationship('Borrow', backref='book', lazy=True)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(200))
    is_delete = db.Column(db.String(1), default='N')
    balance = db.Column(db.Float, default=0)  # 充值余额
    reader_type = db.Column(db.String(50), default='普通会员')  # 读者类型: 普通会员/高级会员/学生/教师
    status = db.Column(db.String(20), default='正常')  # 读者状态: 正常/挂失/注销
    max_borrow = db.Column(db.Integer, default=5)  # 最大借阅数量

    borrows = db.relationship('Borrow', backref='user', lazy=True)


class Borrow(db.Model):
    __tablename__ = 'borrows'
    id = db.Column(db.BigInteger, primary_key=True)
    book_id = db.Column(db.BigInteger, db.ForeignKey('books.id'), nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    borrow_date = db.Column(db.Date, default=datetime.now().date)
    return_date = db.Column(db.Date)
    actual_return_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='借阅中')
    is_delete = db.Column(db.String(1), default='N')


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0)  # 模拟会员余额，用于演示


# 组织管理
class Organization(db.Model):
    __tablename__ = 'organizations'
    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    parent_id = db.Column(db.BigInteger, db.ForeignKey('organizations.id'))
    description = db.Column(db.String(500))
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_delete = db.Column(db.String(1), default='N')

    children = db.relationship('Organization', backref=db.backref('parent', remote_side=[id]), lazy=True)


# 菜单管理
class Menu(db.Model):
    __tablename__ = 'menus'
    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(50))
    url = db.Column(db.String(200))
    parent_id = db.Column(db.BigInteger, db.ForeignKey('menus.id'))
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

            # 添加attachment字段
            cursor.execute("SHOW COLUMNS FROM books LIKE 'attachment'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE books ADD COLUMN attachment VARCHAR(500)")

            cursor.execute("SHOW COLUMNS FROM users LIKE 'is_delete'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN is_delete VARCHAR(1) DEFAULT 'N'")
            else:
                cursor.execute("ALTER TABLE users MODIFY COLUMN is_delete VARCHAR(1) DEFAULT 'N'")

            # 添加balance字段
            cursor.execute("SHOW COLUMNS FROM users LIKE 'balance'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN balance FLOAT DEFAULT 0")

            # 添加password_hash字段
            cursor.execute("SHOW COLUMNS FROM users LIKE 'password_hash'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(200)")

            # 添加reader_type字段
            cursor.execute("SHOW COLUMNS FROM users LIKE 'reader_type'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN reader_type VARCHAR(50) DEFAULT '普通会员'")

            # 添加status字段
            cursor.execute("SHOW COLUMNS FROM users LIKE 'status'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT '正常'")

            # 添加max_borrow字段
            cursor.execute("SHOW COLUMNS FROM users LIKE 'max_borrow'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN max_borrow INT DEFAULT 5")

            # 兼容已有数据
            cursor.execute("UPDATE users SET reader_type='普通会员' WHERE reader_type IS NULL")
            cursor.execute("UPDATE users SET status='正常' WHERE status IS NULL")
            cursor.execute("UPDATE users SET max_borrow=5 WHERE max_borrow IS NULL")

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

            # 添加admins表的balance字段
            cursor.execute("SHOW COLUMNS FROM admins LIKE 'balance'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE admins ADD COLUMN balance FLOAT DEFAULT 0")
        connection.commit()
    finally:
        connection.close()

    # 创建表
    with app.app_context():
        db.create_all()
        # 创建默认管理员
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(
                id=snowflake.next_id(),
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

    book = Book(id=snowflake.next_id(), title=title, author=author, isbn=isbn, category=category, stock=stock)
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


# 上传附件
@app.route('/book/upload/<int:id>', methods=['POST'])
@login_required
def upload_attachment(id):
    book = Book.query.get_or_404(id)
    if 'file' not in request.files:
        return redirect(url_for('books'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('books'))

    # 获取文件扩展名
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    allowed_exts = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf']
    if ext not in allowed_exts:
        return redirect(url_for('books'))

    # 保存文件
    filename = f"{id}_{int(time.time())}_{file.filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # 更新数据库
    book.attachment = filename
    db.session.commit()
    return redirect(url_for('books'))


# 下载/预览附件
@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# 用户管理
@app.route('/users')
@login_required
def users():
    users = User.query.filter_by(is_delete='N').all()
    return render_template('user.html', users=users)


@app.route('/readers')
@login_required
def readers():
    return redirect(url_for('users'))


@app.route('/user/add', methods=['POST'])
@login_required
def add_user():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')
    reader_type = request.form.get('reader_type', '普通会员')
    status = request.form.get('status', '正常')
    max_borrow = request.form.get('max_borrow', type=int, default=5)

    password_hash = generate_password_hash(password) if password else None
    user = User(id=snowflake.next_id(), name=name, email=email, phone=phone, password_hash=password_hash,
                reader_type=reader_type, status=status, max_borrow=max_borrow)
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
    user.reader_type = request.form.get('reader_type', '普通会员')
    user.max_borrow = request.form.get('max_borrow', type=int, default=5)
    password = request.form.get('password')
    if password:
        user.password_hash = generate_password_hash(password)
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/user/password/<int:id>', methods=['POST'])
@login_required
def change_user_password(id):
    user = User.query.get_or_404(id)
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')

    # 验证旧密码
    if user.password_hash and not check_password_hash(user.password_hash, old_password):
        return render_template('user.html', users=User.query.filter_by(is_delete='N').all(), error='旧密码错误')

    # 设置新密码
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/user/delete/<int:id>')
@login_required
def delete_user(id):
    user = User.query.get_or_404(id)
    user.is_delete='Y'
    db.session.commit()
    return redirect(url_for('users'))


# 用户充值
@app.route('/user/recharge/<string:id>', methods=['POST'])
@login_required
def recharge(id):
    user = User.query.get_or_404(id)
    amount = request.form.get('amount', type=float, default=0)
    if amount > 0:
        user.balance = (user.balance or 0) + amount
        db.session.commit()
    return redirect(url_for('users'))


# 读者状态管理
@app.route('/user/report_loss/<int:id>')
@login_required
def report_loss(id):
    user = User.query.get_or_404(id)
    user.status = '挂失'
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/user/cancel/<int:id>')
@login_required
def cancel_user(id):
    user = User.query.get_or_404(id)
    user.status = '注销'
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/user/restore/<int:id>')
@login_required
def restore_user(id):
    user = User.query.get_or_404(id)
    user.status = '正常'
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

    # 校验读者状态和借阅额度
    reader = User.query.filter_by(id=user_id, is_delete='N').first()
    error = None
    if not reader:
        error = '读者不存在'
    elif reader.status != '正常':
        error = f'读者状态为"{reader.status}"，无法借阅'
    else:
        active_count = Borrow.query.filter_by(
            user_id=user_id, status='借阅中', is_delete='N'
        ).count()
        if active_count >= reader.max_borrow:
            error = f'该读者已达到最大借阅数量（{reader.max_borrow}本），无法继续借阅'

    if error:
        borrows = Borrow.query.filter_by(is_delete='N').order_by(Borrow.borrow_date.desc()).all()
        return render_template('borrow.html', borrows=borrows, error=error)

    # 检查库存
    book = Book.query.get(book_id)
    if book and book.stock > 0:
        book.stock -= 1
        borrow = Borrow(id=snowflake.next_id(), book_id=book_id, user_id=user_id, return_date=return_date, status='借阅中')
        db.session.add(borrow)
        db.session.commit()

    return redirect(url_for('borrows'))


@app.route('/borrow/return/<int:id>')
@login_required
def return_book(id):
    borrow = Borrow.query.get_or_404(id)
    if borrow.status == '借阅中':
        borrow.status = '已归还'
        borrow.actual_return_date = datetime.now().date()
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
    users = User.query.filter_by(is_delete='N', status='正常').all()
    return jsonify([{
        'id': u.id, 'name': u.name, 'email': u.email, 'phone': u.phone,
        'status': u.status, 'reader_type': u.reader_type
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

    org = Organization(id=snowflake.next_id(), name=name, code=code, parent_id=parent_id, description=description)
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

    menu = Menu(id=snowflake.next_id(), name=name, icon=icon, url=url, parent_id=parent_id, sort_order=sort_order)
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


# 管理员充值（用于模拟会员）
@app.route('/admin/recharge', methods=['POST'])
@login_required
def admin_recharge():
    amount = request.form.get('amount', type=float, default=0)
    if amount > 0:
        current_user.balance = (current_user.balance or 0) + amount
        db.session.commit()
    return redirect(url_for('index'))


# 传递会员状态给模板
@app.context_processor
def inject_user():
    is_member = hasattr(current_user, 'balance') and (current_user.balance or 0) >= 500
    return dict(is_member=is_member)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)