from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from bson import ObjectId
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'  
app.config['MONGO_URI'] = 'mongodb://localhost:27017/ecommerce_db'
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

# ___________database_Schema___________
class User(mongo.db.Document):
  username = mongo.db.StringField(required=True, unique=True)
  password = mongo.db.StringField(required=True)
  email = mongo.db.EmailField(required=True)
  role = mongo.db.StringField(required=True, choices=['seller', 'customer'])

# _______Product_Schema________
class Product(mongo.db.Document):
  name = mongo.db.StringField(required=True, unique=True)
  description = mongo.db.StringField()
  price = mongo.db.DecimalField(required=True, precision=2)
  quantity = mongo.db.IntField(required=True)
  version = mongo.db.IntField(default=1)

#_________Order_Schema__________
class Order(mongo.db.Document):
  user_id = mongo.db.ObjectIdField(required=True)
  product_id = mongo.db.ObjectIdField(required=True)
  quantity = mongo.db.IntField(required=True)
#________ login_required_function______
def seller_login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
      if 'user_id' not in session:
          return redirect(url_for('login_seller'))
      user_id = session['user_id']
      user = User.objects(id=user_id, role='seller').first()
      if not user:
          return jsonify({'error': 'Unauthorized access'}), 403
      return f(*args, **kwargs)
  return decorated_function
#________Home_Page________
@app.route('/')
def home():
    return render_template('home.html')

#_________Seller_Registration_page_________
@app.route('/register/seller', methods=['GET', 'POST'])
def register_seller():
    if request.method == 'POST':
        data = request.form
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        if not username or not password or not email:
            return jsonify({'error': 'Missing required fields'}), 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_seller = User(username=username, password=hashed_password, email=email, role='seller')
        new_seller.save()
        return redirect(url_for('login_seller'))

    return render_template('register_seller.html')

#_________Seller_Login_page________
@app.route('/login/seller', methods=['GET', 'POST'])
def login_seller():
    if request.method == 'POST':
        data = request.form
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400

        seller = User.objects(username=username, role='seller').first()
        if not seller or not bcrypt.check_password_hash(seller.password, password):
            return jsonify({'error': 'Invalid username or password'}), 401

        session['user_id'] = str(seller.id)
        return redirect(url_for('seller_panel'))

    return render_template('login_seller.html')

#_______Seller_Panel_page_______
@seller_login_required
@app.route('/seller/panel')
def seller_panel():
    if 'user_id' not in session:
        return redirect(url_for('login_seller'))

    user_id = session['user_id']
    orders = Order.objects(product_id__in=Product.objects(user_id=ObjectId(user_id)))
    return render_template('seller_panel.html', orders=orders)
#_______Add_Product________
@app.route('/add_product', methods=['POST'])
@seller_login_required
def add_product():
    data = request.form
    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    quantity = data.get('quantity')

    if not name or not price or not quantity:
        return jsonify({'error': 'Missing required fields'}), 400

    existing_product = Product.objects(name=name).first()
    if existing_product:
        return jsonify({'error': 'Product already exists'}), 409

    user_id = session['user_id']
    new_product = Product(name=name, description=description, price=price, quantity=quantity, user_id=ObjectId(user_id))
    new_product.save()
    return jsonify({'message': 'Product added successfully'}), 201

#________Update_Product_________
@app.route('/update_product/<string:product_id>', methods=['PUT'])
@seller_login_required
def update_product(product_id):
    data = request.form
    new_name = data.get('name')
    new_description = data.get('description')
    new_price = data.get('price')
    new_quantity = data.get('quantity')

    product = Product.objects(id=product_id, user_id=ObjectId(session['user_id'])).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    update_data = {}
    if new_name:
        update_data['name'] = new_name
    if new_description:
        update_data['description'] = new_description
    if new_price:
        update_data['price'] = new_price
    if new_quantity:
        update_data['quantity'] = new_quantity

    product.modify(**update_data)
    return jsonify({'message': 'Product updated successfully'}), 200
    

#__________Customer_Registration______
@app.route('/register/customer', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        data = request.form
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        if not username or not password or not email:
            return jsonify({'error': 'Missing required fields'}), 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_customer = User(username=username, password=hashed_password, email=email, role='customer')
        new_customer.save()
        return redirect(url_for('login_customer'))

    return render_template('register_customer.html')

#________Customer_Login_________
@app.route('/login/customer', methods=['GET', 'POST'])
def login_customer():
    if request.method == 'POST':
        data = request.form
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400

        customer = User.objects(username=username, role='customer').first()
        if not customer or not bcrypt.check_password_hash(customer.password, password):
            return jsonify({'error': 'Invalid username or password'}), 401

        session['user_id'] = str(customer.id)
        return redirect(url_for('customer_panel'))

    return render_template('login_customer.html')

#________Customer_Panel_______
@app.route('/customer/panel')
def customer_panel():
    if 'user_id' not in session:
        return redirect(url_for('login_customer'))

    user_id = session['user_id']
    products = Product.objects()
    return render_template('customer_panel.html', products=products)

#_______Place_Order__________
@app.route('/place_order/<string:product_id>', methods=['POST'])
def place_order(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login_customer'))

    user_id = session['user_id']
    product = Product.objects(id=product_id).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    quantity = int(request.form['quantity'])
    if quantity <= 0 or quantity > product.quantity:
        return jsonify({'error': 'Invalid quantity'}), 400

    new_order = Order(user_id=ObjectId(user_id), product_id=ObjectId(product_id), quantity=quantity)
    new_order.save()

    #_____Update_product_quantity_____
    product.quantity -= quantity
    product.save()

    return redirect(url_for('customer_panel'))

# ______Order_History______
@app.route('/order_history')
def order_history():
    if 'user_id' not in session:
        return redirect(url_for('login_customer'))

    user_id = session['user_id']
    orders = Order.objects(user_id=ObjectId(user_id))
    return render_template('order_history.html', orders=orders)

#_______Logout______
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=80)
    
