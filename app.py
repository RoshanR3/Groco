import requests
from flask import Flask, render_template, redirect, request, url_for
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import json
from algoliasearch.search_client import SearchClient

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# ckeditor = CKEditor(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"
# Bootstrap(app)
db = SQLAlchemy()
db.init_app(app)
f = open('data.json')
data = json.load(f)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    family = db.Column(db.String(1000))
    order = db.Column(db.String(1000))
    genus = db.Column(db.String(1000))
    calories = db.Column(db.Float)
    fat = db.Column(db.Float)
    sugar = db.Column(db.Float)
    carbohydrate = db.Column(db.Float)
    protein = db.Column(db.Float)
    link = db.Column(db.String(1000))
    price = db.Column(db.String(1000))


with app.app_context():
    db.create_all()
    # for d in data:
    #     new_product = Product(name=d["name"], family=d["family"], order=d["order"], genus=d["genus"], calories=d["nutritions"]["calories"], fat=d["nutritions"]["fat"], sugar=d["nutritions"]["sugar"], carbohydrate=d["nutritions"]["carbohydrates"], protein=d["nutritions"]["protein"], link=d["link"], price="50" )
    #     db.session.add(new_product)
    #     db.session.commit()
    d = Product.query.all()



@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('signup'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@app.route('/')
def home():
    return render_template('index.html', data=d)

@app.route("/products")
def products():
    return render_template('products.html', data=d)

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        if name == "" or email == "" or request.form.get("password") == "":
            return render_template('signup.html', l=1, p=0)
        if len(request.form.get("password")) < 8:
            return render_template('signup.html', l=0, p=1)
        password = (generate_password_hash(request.form.get("password"), method='pbkdf2:sha256:260000',
                                           salt_length=8))[21:]
        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect("/")
    return render_template("signup.html", l=0, p=0)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        meth = 'pbkdf2:sha256:260000$'
        o = User.query.filter_by(email=email).first()
        try:
            if o.email == email and check_password_hash(f"{meth}{o.password}", password):
                login_user(o)
                return redirect("/")
            else:
                return render_template("login.html", l=1)
        except AttributeError:
            return render_template("login.html", l=1)
    return render_template("login.html", l=0)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")
if __name__ == '__main__':
    app.run()
