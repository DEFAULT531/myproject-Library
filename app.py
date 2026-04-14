from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pymysql

app = Flask(__name__)

# MySQL 配置 (密码: 123456)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@localhost:3306/library'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'library-secret-key'

db = SQLAlchemy(app)


# 数据库模型
class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True)
    category = db.Column(db.String(50))
    stock = db.Column(db.Integer, default=1)

    borrows = db.relationship('Borrow', backref='book', lazy=True)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))

    borrows = db.relationship('Borrow', backref='user', lazy=True)


class Borrow(db.Model):
    __tablename__ = 'borrows'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    borrow_date = db.Column(db.Date, default=datetime.now().date)
    return_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='借阅中')


# 初始化数据库
def init_db():
    # 创建数据库
    connection = pymysql.connect(host='localhost', port=3306, user='root', password='123456')
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS library")
        connection.commit()
    finally:
        connection.close()

    # 创建表
    with app.app_context():
        db.create_all()


# 首页 - 图书列表
@app.route('/')
def index():
    books = Book.query.all()
    return render_template('index.html', books=books)


# 图书管理
@app.route('/books')
def books():
    books = Book.query.all()
    return render_template('book.html', books=books)


@app.route('/book/add', methods=['POST'])
def add_book():
    title = request.form.get('title')
    author = request.form.get('author')
    isbn = request.form.get('isbn')
    category = request.form.get('category')
    stock = request.form.get('stock', type=int, default=1)

    if not title or not author:
        return redirect(url_for('books'))

    book = Book(title=title, author=author, isbn=isbn, category=category, stock=stock)
    db.session.add(book)
    db.session.commit()
    return redirect(url_for('books'))


@app.route('/book/edit/<int:id>', methods=['POST'])
def edit_book(id):
    book = Book.query.get_or_404(id)
    title = request.form.get('title')
    author = request.form.get('author')

    if not title or not author:
        return redirect(url_for('books'))

    book.title = title
    book.author = author
    book.isbn = request.form.get('isbn')
    book.category = request.form.get('category')
    book.stock = request.form.get('stock', type=int)
    db.session.commit()
    return redirect(url_for('books'))


@app.route('/book/delete/<int:id>')
def delete_book(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('books'))


# 用户管理
@app.route('/users')
def users():
    users = User.query.all()
    return render_template('user.html', users=users)


@app.route('/user/add', methods=['POST'])
def add_user():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')

    user = User(name=name, email=email, phone=phone)
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/user/edit/<int:id>', methods=['POST'])
def edit_user(id):
    user = User.query.get_or_404(id)
    user.name = request.form.get('name')
    user.email = request.form.get('email')
    user.phone = request.form.get('phone')
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/user/delete/<int:id>')
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('users'))


# 借阅管理
@app.route('/borrows')
def borrows():
    borrows = Borrow.query.order_by(Borrow.borrow_date.desc()).all()
    return render_template('borrow.html', borrows=borrows)


@app.route('/borrow/add', methods=['POST'])
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
def delete_borrow(id):
    borrow = Borrow.query.get_or_404(id)
    # 如果是借阅中状态，归还库存
    if borrow.status == '借阅中':
        book = Book.query.get(borrow.book_id)
        if book:
            book.stock += 1
    db.session.delete(borrow)
    db.session.commit()
    return redirect(url_for('borrows'))


# API 接口
@app.route('/api/books')
def api_books():
    books = Book.query.all()
    return jsonify([{
        'id': b.id, 'title': b.title, 'author': b.author,
        'isbn': b.isbn, 'category': b.category, 'stock': b.stock
    } for b in books])


@app.route('/api/users')
def api_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id, 'name': u.name, 'email': u.email, 'phone': u.phone
    } for u in users])


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)