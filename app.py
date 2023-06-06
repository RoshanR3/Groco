import requests
from flask import Flask, render_template, redirect, request, url_for
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, Index
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import json
from algoliasearch.search_client import SearchClient
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message, Mail
from flask_caching import Cache


load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("MAIL_DEFAULT_SENDER")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
app.config['SESSION_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True

mail = Mail(app)
cache = Cache(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"
db = SQLAlchemy()
db.init_app(app)
client = SearchClient.create('QTD6N8WZGF', os.environ.get("ADMIN_KEY"))
index = client.init_index('products')
# f = open('data.json')
# data = json.load(f)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(1000))
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

    def to_algolia_dict(self):
        return {
            'objectID': self.id,
            'name': self.name,
            'family': self.family,
            'order': self.order,
            'genus': self.genus,
            'calories': self.calories,
            'fat': self.fat,
            'sugar': self.sugar,
            'carbohydrate': self.carbohydrate,
            'protein': self.protein,
            'link': self.link,
            'price': self.price
        }

Index('idx_products_name', Product.name)
Index('idx_products_family', Product.family)
Index('idx_products_order', Product.order)
Index('idx_products_genus', Product.genus)

def sync_products_with_algolia():
    produc = Product.query.all()
    algolia_products = [product.to_algolia_dict() for product in produc]
    index.save_objects(algolia_products)

with app.app_context():
    db.create_all()
    # for d in data:
    #     new_product = Product(name=d["name"], family=d["family"], order=d["order"], genus=d["genus"], calories=d["nutritions"]["calories"], fat=d["nutritions"]["fat"], sugar=d["nutritions"]["sugar"], carbohydrate=d["nutritions"]["carbohydrates"], protein=d["nutritions"]["protein"], link=d["link"], price="50" )
    #     db.session.add(new_product)
    #     db.session.commit()
    d = Product.query.all()

def get_products():
    return Product.query.all()

def search_products(query):
    results = index.search(query)
    product_ids = [int(hit['objectID']) for hit in results['hits']]
    return Product.query.filter(Product.id.in_(product_ids)).all()

def generate_reset_token(user):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    token = serializer.dumps(user.email, salt='password-reset')
    user.reset_token = token
    db.session.commit()
    return token

def send_reset_email(email, token):
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = Message('Password Reset Request', recipients=[email])
    msg.body = f'Please click the following link to reset your password:\n{reset_url}'
    mail.send(msg)

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('signup'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    products = get_products()
    return render_template('index.html', data=products)

@app.route("/products")
def products():
    products = get_products()
    return render_template('products.html', data=products)

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

@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate a unique token and save it to the user's record
            token = generate_reset_token(user)
            # Send the password reset email containing the token
            send_reset_email(user.email, token)
        # Display a success message (without indicating if the email exists in the system)
        return render_template('forgot.html', success=True)
    return render_template('forgot.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)
        user = User.query.filter_by(email=email).first()
    except:
        return render_template('reset.html', invalid=True)
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            return render_template('reset.html', mismatch=True)
        # Update the user's password
        user.password = generate_password_hash(password)[21:]
        user.reset_token = None  # Clear the reset token
        db.session.commit()
        # Redirect to login page or display a success message
        return redirect(url_for('login'))
    return render_template('reset.html', token=token)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route('/search')
def search():
    query = request.args.get('query', '')
    if query:
        produ = search_products(query=query)
    else:
        produ = get_products()
    return render_template('products.html', data=produ)

if __name__ == '__main__':
    app.run()
