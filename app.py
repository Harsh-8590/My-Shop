from flask import Flask, render_template, request, redirect, session
from config import Config
from models import db, User, Product, Cart, Order, OrderItem
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- HOME ----------------
@app.route("/")
def home():
    products = Product.query.all()

    cart_items = []
    total = 0

    if "user_id" in session:
        items = Cart.query.filter_by(user_id=session["user_id"]).all()

        for item in items:
            product = Product.query.get(item.product_id)
            subtotal = product.price * item.quantity
            total += subtotal

            cart_items.append({
                "name": product.name,
                "quantity": item.quantity,
                "subtotal": subtotal
            })

    return render_template("index.html", 
                           products=products,
                           cart_items=cart_items,
                           total=total)

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        existing_user = User.query.filter_by(email=request.form["email"]).first()
        if existing_user:
            return "Email already registered"

        user = User(
            name=request.form["name"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"]),
            role="user"
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect("/")

        return "Invalid Email or Password"

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- PRODUCTS ----------------
@app.route("/products")
def products():
    if "user_id" not in session:
        return redirect("/login")

    products = Product.query.all()
    return render_template("products.html", products=products)


# ---------------- ADD PRODUCT (Admin Only) ----------------
@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if session.get("role") != "admin":
        return "Unauthorized Access"

    if request.method == "POST":
        product = Product(
            name=request.form["name"],
            price=float(request.form["price"]),
            stock=int(request.form["stock"])
        )
        db.session.add(product)
        db.session.commit()
        return redirect("/products")

    return render_template("add_product.html")


# ---------------- ADD TO CART ----------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if "user_id" not in session:
        return redirect("/login")

    product = Product.query.get(product_id)
    quantity = int(request.args.get("quantity", 1))

    if not product or product.stock < quantity:
        return "Not enough stock available"

    existing_item = Cart.query.filter_by(
        user_id=session["user_id"],
        product_id=product_id
    ).first()

    if existing_item:
        if existing_item.quantity + quantity <= product.stock:
            existing_item.quantity += quantity
    else:
        cart_item = Cart(
            user_id=session["user_id"],
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)

    db.session.commit()
    return redirect("/")

# ---------------- CART ----------------
@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect("/login")

    items = Cart.query.filter_by(user_id=session["user_id"]).all()

    products = []
    total = 0

    for item in items:
        product = Product.query.get(item.product_id)
        subtotal = product.price * item.quantity
        total += subtotal

        products.append({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "quantity": item.quantity,
            "subtotal": subtotal
        })

    return render_template("cart.html", products=products, total=total)


# ---------------- REMOVE FROM CART ----------------
@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    item = Cart.query.filter_by(
        user_id=session["user_id"],
        product_id=product_id
    ).first()

    if item:
        db.session.delete(item)
        db.session.commit()

    return redirect("/cart")


# ---------------- CHECKOUT ----------------
@app.route("/checkout")
def checkout():
    if "user_id" not in session:
        return redirect("/login")

    cart_items = Cart.query.filter_by(user_id=session["user_id"]).all()

    if not cart_items:
        return "Cart is empty"

    total = 0

    # Create Order first
    new_order = Order(user_id=session["user_id"], total_amount=0)
    db.session.add(new_order)
    db.session.commit()

    for item in cart_items:
        product = Product.query.get(item.product_id)

        if product.stock < item.quantity:
            return f"Not enough stock for {product.name}"

        # Reduce stock
        product.stock -= item.quantity

        subtotal = product.price * item.quantity
        total += subtotal

        # Save ordered product
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=item.quantity,
            price=product.price
        )
        db.session.add(order_item)

        # Remove from cart
        db.session.delete(item)

    new_order.total_amount = total
    db.session.commit()

    return render_template("order_success.html", total=total)


# ---------------- VIEW ORDERS ----------------
@app.route("/orders")
def orders():
    if "user_id" not in session:
        return redirect("/login")

    user_orders = Order.query.filter_by(user_id=session["user_id"]).all()
    return render_template("orders.html", orders=user_orders)


if __name__ == "__main__":
    app.run(debug=True)
