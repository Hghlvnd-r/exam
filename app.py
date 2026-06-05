from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'very-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    fio = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    course_name = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    pay_method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

PAY_METHODS = {
    "cash": "Наличными",
    "phone": "Перевод по номеру телефона",
}

STATUS_LABELS = {
    "new": "Новая",
    "progress": "Банкет назначен",
    "done": "Банкет завершён",
}

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return User.query.get(uid)

@app.context_processor
def inject_globals():
    return dict(
        PAY_METHODS=PAY_METHODS,
        STATUS_LABELS=STATUS_LABELS,
        current_user=current_user(),
        is_admin=session.get('Admin26', False),
    )

@app.route("/")
def index():
    if session.get("admin"):
        return redirect(url_for("admin_panel"))
    if session.get("user_id"):
        return redirect(url_for("user_applications"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        login = request.form.get("login", "").strip()
        password = request.form.get("password", "").strip()
        fio = request.form.get("fio", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        errors = []

        import re
        if not re.fullmatch(r"[A-Za-z0-9]{6,}", login):
            errors.append("Логин должен содержать латинские буквы и цифры, и быть не короче 6 символов.")
        if len(password) < 8:
            errors.append("Пароль должен быть не короче 8 символов.")
        if not re.fullmatch(r"^[А-Яа-яЁё\s\-]{5,}$", fio):
            errors.append("ФИО должно содержать только кириллицу и пробелы.")
        if not re.fullmatch(r"8\(\d{3}\)\d{3}-\d{2}-\d{2}", phone):
            errors.append("Телефон должен быть в формате 8(ХХХ)ХХХ-ХХ-ХХ.")
        if not re.fullmatch(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            errors.append("Адрес электронной почты некорректен.")
        
        if User.query.filter_by(login=login).first():
            errors.append("Пользователь с таким логином уже существует.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html", login=login, fio=fio, phone=phone, email=email)

        user = User(login=login, password=password, fio=fio, phone=phone, email=email)
        db.session.add(user)
        db.session.commit()
        flash("Пользователь успешно создан. Теперь войдите в систему.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "").strip()

        if login_value == "Admin26" and password == "Demo20":
            session.clear()
            session["admin"] = True
            flash("Вы вошли как администратор.", "success")
            return redirect(url_for("admin_panel"))

        user = User.query.filter_by(login=login_value, password=password).first()
        if user is None:
            flash("Неверный логин или пароль.", "danger")
            return render_template("login.html", login=login_value)

        session.clear()
        session["user_id"] = user.id
        flash("Вы успешно вошли в систему.", "success")
        return redirect(url_for("user_applications"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("login"))

def login_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        user = current_user()

        if user is None:
            session.clear()
            flash("Необходимо войти в систему.", "warning")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper

def admin_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            flash("Доступ только для администратора.", "danger")
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper

@app.route("/applications")
@login_required
def user_applications():
    user = current_user()
    apps = Application.query.filter_by(user_id=user.id).order_by(Application.created_at.desc()).all()
    reviews = Review.query.filter_by(user_id=user.id).order_by(Review.created_at.desc()).all()
    can_review = any(app.status != 'new' for app in apps)
    return render_template("applications.html", 
                           applications=apps, 
                           reviews=reviews, 
                           can_review=can_review)
    return render_template("applications.html", applications=apps, reviews=reviews)

@app.route("/applications/new", methods=["GET", "POST"])
@login_required
def new_application():
    if request.method == "POST":
        course_name = request.form.get("course_name", "").strip()
        start_date = request.form.get("start_date", "").strip()
        pay_method = request.form.get("pay_method", "").strip()
        valid_halls = ["Зал", "Ресторан", "Летняя веранда", "Закрытая веранда"]
        if course_name not in valid_halls:
            flash("Выберите корректное помещение.", "danger")
            return render_template("new_application.html")

        errors = []
        if not course_name:
            errors.append("Наименование курса обязательно.")
        if not start_date:
            errors.append("Дата начала обучения обязательна.")
        if pay_method not in PAY_METHODS:
            errors.append("Не выбран способ оплаты.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("new_application.html", course_name=course_name, start_date=start_date, pay_method=pay_method)
            
        user = current_user()
        app_obj = Application(
            user_id=user.id,
            course_name=course_name,
            start_date=start_date,
            pay_method=pay_method,
            status="new",
        )
        db.session.add(app_obj)
        db.session.commit()
        flash("Заявка отправлена администратору.", "success")
        return redirect(url_for("user_applications"))
    return render_template("new_application.html")

@app.route("/reviews", methods=["POST"])
@login_required
def add_review():
    text = request.form.get("text", "").strip()
    if not text:
        flash("Отзыв не может быть пустым.", "danger")
        return redirect(url_for("user_applications"))
    
    user = current_user()
    apps = Application.query.filter_by(user_id=user.id).all()
    can_review = any(app.status != 'new' for app in apps)
    if not can_review:
        flash("Вы можете оставить отзыв только после того, как ваша заявка будет рассмотрена администратором.", "warning")
        return redirect(url_for("user_applications"))
        
    review = Review(user_id=user.id, text=text)
    db.session.add(review)
    db.session.commit()
    flash("Спасибо за ваш отзыв!", "success")
    return redirect(url_for("user_applications"))

@app.route("/admin")
@admin_required
def admin_panel():
    apps = Application.query.order_by(Application.created_at.desc()).all()
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    apps_json = [
        {
            "id": app.id,
            "course_name": app.course_name,
            "start_date": app.start_date,
            "pay_method": app.pay_method,
            "status": app.status,
            "user": {
                "fio": app.user.fio,
                "email": app.user.email
            }
        }
        for app in apps
    ]

    return render_template(
        "admin_panel.html",
        applications=apps,
        applications_json=apps_json,
        reviews=reviews,
        STATUS_LABELS=STATUS_LABELS,
        PAY_METHODS=PAY_METHODS
    )

@app.route("/admin/application/<int:app_id>/status", methods=["POST"])
@admin_required
def change_status(app_id):
    new_status = request.form.get("status")
    if new_status not in STATUS_LABELS:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": "Некорректный статус"}), 400
        flash("Некорректный статус.", "danger")
        return redirect(url_for("admin_panel"))

    app_obj = Application.query.get_or_404(app_id)
    app_obj.status = new_status
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "new_status": new_status})
    
    flash("Статус заявки обновлён.", "success")
    return redirect(url_for("admin_panel"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)