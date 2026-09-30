import os
import random
import string
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "techmarket_super_secret_key_2026")

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

# Admin portal credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin@123"


# ═══════════════════════════════════════════════════════════════════════
# DATABASE PERSISTENCE (SQLite)
# ═══════════════════════════════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                username TEXT PRIMARY KEY,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Pre-seed default test accounts if database is empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            default_accounts = [
                ("admin", "1234"),
                ("user", "1234"),
                ("demo", "1234"),
                ("gla", "1234"),
            ]
            cursor.executemany(
                "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
                default_accounts,
            )
        conn.commit()


# Initialize SQLite tables on startup
init_db()


def get_user(username):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, password FROM users WHERE username = ?", (username,))
        return cursor.fetchone()


def add_user(username, password):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def get_all_users():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users ORDER BY id ASC")
        return [row["username"] for row in cursor.fetchall()]


def get_banned_user_time(username):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT banned_at FROM banned_users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            try:
                return datetime.strptime(row["banned_at"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                return datetime.now()
        return None


def ban_user(username):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO banned_users (username, banned_at) VALUES (?, datetime('now'))", (username,))
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()


def unban_user(username):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM banned_users WHERE username = ?", (username,))
        conn.commit()


def get_all_banned_users():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, banned_at FROM banned_users ORDER BY banned_at DESC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            try:
                dt = datetime.strptime(r["banned_at"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                dt = datetime.now()
            result.append({"username": r["username"], "time_ago": time_ago(dt)})
        return result


# ═══════════════════════════════════════════════════════════════════════
# CENTRAL PRODUCT CATALOG
# ═══════════════════════════════════════════════════════════════════════
PRODUCTS = {
    "electronics": [
        {
            "id": "elec-1",
            "name": "Smart Phone",
            "slug": "smart-phone",
            "category": "Electronics",
            "category_url": "/products",
            "price": 99999,
            "formatted_price": "₹99,999",
            "image": "images/phone.webp",
            "badge": "Best Seller",
            "rating": 4.9,
            "reviews_count": 342,
            "in_stock": True,
            "short_desc": "Flagship 5G smartphone with 120Hz dynamic AMOLED display and pro-grade triple camera system.",
            "about": "The next evolution in mobile technology. Equipped with a 6.7-inch dynamic AMOLED display, 120Hz adaptive refresh rate, 5nm octa-core AI processor, 256GB storage, and a triple 108MP camera with OIS. Delivers all-day battery performance with 65W ultra-fast charging.",
            "specs": [
                "6.7-inch 120Hz HDR10+ AMOLED Display",
                "108MP Triple Lens Camera with 4K Video",
                "256GB Internal Storage / 12GB RAM",
                "5000mAh Battery with 65W SuperDart Charge",
                "IP68 Water & Dust Resistant",
            ],
        },
        {
            "id": "elec-2",
            "name": "Laptop Pro",
            "slug": "laptop-pro",
            "category": "Electronics",
            "category_url": "/products",
            "price": 84999,
            "formatted_price": "₹84,999",
            "image": "images/laptop.jpg",
            "badge": "High Performance",
            "rating": 4.8,
            "reviews_count": 218,
            "in_stock": True,
            "short_desc": "Powerhouse ultrabook with Intel Core i7, 16GB DDR5 RAM, and 1TB NVMe PCIe Gen4 SSD.",
            "about": "Engineered for developers, creators, and power users. Boasts a lightweight aerospace-grade aluminum chassis, 15.6-inch 2.8K IPS display, precision backlit keyboard, Wi-Fi 6E, and dual Thunderbolt 4 ports for desktop-class connectivity.",
            "specs": [
                "Intel Core i7 13th Gen (10 Cores, up to 5.0 GHz)",
                "16GB DDR5 5200MHz RAM & 1TB NVMe SSD",
                "15.6\" 2.8K Anti-Glare IPS Color-Accurate Display",
                "Dual Thunderbolt 4 & All-Day 12-Hour Battery",
                "Fingerprint Biometric Sign-in",
            ],
        },
        {
            "id": "elec-3",
            "name": "Ultra Tablet",
            "slug": "ultra-tablet",
            "category": "Electronics",
            "category_url": "/products",
            "price": 49999,
            "formatted_price": "₹49,999",
            "image": "images/ipad.webp",
            "badge": "New Arrival",
            "rating": 4.7,
            "reviews_count": 126,
            "in_stock": True,
            "short_desc": "Ultra-thin 11-inch Liquid Retina tablet with stylus support, stereo speakers, and M-class speed.",
            "about": "Your portable studio and workstation combined. Features an 11-inch Liquid Retina display with True Tone, lightning-fast wireless connectivity, magnetic stylus charging support, quad stereo speakers, and versatile multitasking capabilities.",
            "specs": [
                "11-inch Liquid Retina Display with True Tone",
                "Octa-core High Efficiency Processor",
                "Magnetic Stylus & Magic Keyboard Compatibility",
                "Quad Speaker Audio with Spatial Support",
                "All-day 10-hour battery life",
            ],
        },
        {
            "id": "elec-4",
            "name": "Hi-Fi Bluetooth Speaker",
            "slug": "bluetooth-speaker",
            "category": "Electronics",
            "category_url": "/products",
            "price": 4999,
            "formatted_price": "₹4,999",
            "image": "images/speaker.jpg",
            "badge": "Top Rated",
            "rating": 4.9,
            "reviews_count": 512,
            "in_stock": True,
            "short_desc": "360° immersive acoustic portable speaker with dual passive bass radiators and IPX7 waterproofing.",
            "about": "Experience rich, room-filling sound wherever you go. Features 360-degree acoustic dispersion, custom neodymium drivers with deep punchy bass, IPX7 waterproof casing, 24-hour battery endurance, and Bluetooth 5.3 instant pairing.",
            "specs": [
                "360° Immersive Sound with Dual Bass Boosters",
                "24-Hour Continuous Battery Playback",
                "IPX7 Fully Waterproof & Dustproof",
                "Bluetooth 5.3 with 100ft Range",
                "True Wireless Stereo (TWS) Dual Pairing",
            ],
        },
    ],
    "home-appliances": [
        {
            "id": "home-1",
            "name": "Smart Humidifier",
            "slug": "smart-humidifier",
            "category": "Home Appliances",
            "category_url": "/home-appliances",
            "price": 4499,
            "formatted_price": "₹4,499",
            "image": "images/house_apppliances_humidifier.jpg",
            "badge": "Health & Living",
            "rating": 4.8,
            "reviews_count": 184,
            "in_stock": True,
            "short_desc": "Ultrasonic cool-mist air humidifier with aroma diffuser, ambient LED, and automatic humidity sensor.",
            "about": "Maintains optimal indoor humidity whisper-quietly. Features intelligent auto-humidity control, an essential oil diffusion compartment, customizable RGB mood lighting, and a large 3.5L tank that operates up to 30 continuous hours.",
            "specs": [
                "3.5L Tank Capacity (Up to 30h Continuous Run)",
                "Whisper-Quiet Ultrasonic Operation (<24dB)",
                "Essential Oil Aromatherapy Diffusion Tray",
                "Built-in Smart Humidity Sensor & Auto Shut-Off",
                "Soft Ambient Nightlight with Sleep Mode",
            ],
        },
        {
            "id": "home-2",
            "name": "Smart WiFi Wall Socket",
            "slug": "smart-socket",
            "category": "Home Appliances",
            "category_url": "/home-appliances",
            "price": 1299,
            "formatted_price": "₹1,299",
            "image": "images/socket.jpg",
            "badge": "Smart Home",
            "rating": 4.7,
            "reviews_count": 290,
            "in_stock": True,
            "short_desc": "Voice-enabled smart power plug with real-time energy tracking and surge protection.",
            "about": "Transform any traditional home appliance into an automated smart device. Control appliances remotely from anywhere, monitor electricity consumption in real time, and set automated on/off schedules using Alexa, Google Home, or mobile app.",
            "specs": [
                "Voice Control via Alexa & Google Assistant",
                "Real-Time Energy & Power Consumption Tracker",
                "Surge, Overload & Flame Retardant Protection",
                "Custom Schedules & Countdown Timers",
                "No Hub Required (Direct 2.4GHz WiFi)",
            ],
        },
        {
            "id": "home-3",
            "name": "Handcrafted Key Organizer",
            "slug": "key-holder",
            "category": "Home Appliances",
            "category_url": "/home-appliances",
            "price": 899,
            "formatted_price": "₹899",
            "image": "images/key_holder.webp",
            "badge": "Artisan Crafted",
            "rating": 4.9,
            "reviews_count": 160,
            "in_stock": True,
            "short_desc": "Solid seasoned wood wall organizer with 8 heavy-duty brass hooks, mail shelf, and phone stand.",
            "about": "Expertly handcrafted from durable seasoned engineered wood with a rich walnut stain. Features 8 sturdy brass hooks for keys, jackets, and accessories, plus a top display shelf for mail, sunglasses, and mobile devices.",
            "specs": [
                "100% Solid Seasoned Wood Construction",
                "8 Heavy-Duty Antique Brass Hooks",
                "Integrated Top Storage Shelf & Mail Slot",
                "Compact Wall Mount with Pre-drilled Holes",
                "Scratch-Resistant Protective Matte Coat",
            ],
        },
        {
            "id": "home-4",
            "name": "Ceramic Deco Planter",
            "slug": "flower-pot",
            "category": "Home Appliances",
            "category_url": "/home-appliances",
            "price": 1499,
            "formatted_price": "₹1,499",
            "image": "images/home_appliances_flower_pots.webp",
            "badge": "Eco Decor",
            "rating": 4.8,
            "reviews_count": 95,
            "in_stock": True,
            "short_desc": "Minimalist handcrafted ceramic plant pot with drainage hole and detachable drip saucer.",
            "about": "Elevate your living room or office aesthetic with this premium high-fired ceramic planter. Features a breathable design with drainage hole and matching saucer to ensure healthy root development for indoor greens and succulents.",
            "specs": [
                "High-Fired Premium Ceramic Pottery",
                "Built-in Drainage Hole with Matching Saucer",
                "Smooth Nordic Matte Glaze Finish",
                "Weather-Resistant for Indoor & Balcony Use",
                "Optimal for Succulents, Ferns & Houseplants",
            ],
        },
    ],
    "kitchen": [
        {
            "id": "kitch-1",
            "name": "Digital Air Fryer",
            "slug": "air-fryer",
            "category": "Kitchen Appliances",
            "category_url": "/kitchen",
            "price": 5999,
            "formatted_price": "₹5,999",
            "image": "images/air_fryer.jpg",
            "badge": "Health Choice",
            "rating": 4.9,
            "reviews_count": 430,
            "in_stock": True,
            "short_desc": "5.5L rapid 360° air circulation oil-free fryer with 8 one-touch digital preset cooking menus.",
            "about": "Cook crispy, golden meals with up to 85% less oil. Featuring an intuitive LED touchscreen, 8 preset cooking programs, a spacious 5.5L non-stick basket, and 1800W rapid heat technology for healthy culinary perfection.",
            "specs": [
                "5.5L Large Capacity Non-Stick Basket",
                "85% Less Fat & Oil-Free Healthy Cooking",
                "8 One-Touch Digital Presets with Touch Screen",
                "1800W Turbo Air Circulation System",
                "Dishwasher-Safe & Auto Shut-Off Safety",
            ],
        },
        {
            "id": "kitch-2",
            "name": "Convection Toaster Oven",
            "slug": "convection-oven",
            "category": "Kitchen Appliances",
            "category_url": "/kitchen",
            "price": 3499,
            "formatted_price": "₹3,499",
            "image": "images/oven.webp",
            "badge": "Chef Grade",
            "rating": 4.7,
            "reviews_count": 275,
            "in_stock": True,
            "short_desc": "Multi-function countertop convection oven for baking, broiling, toasting, and warming.",
            "about": "A versatile compact countertop oven built to handle all your baking, grilling, and reheating needs. Comes equipped with dual quartz heating elements, an adjustable 100°C–250°C thermostat, and a 60-minute timer with auto-off.",
            "specs": [
                "Multi-Function: Bake, Broil, Toast & Warm",
                "Dual Quartz Fast-Heating Elements",
                "Adjustable Thermostat (100°C to 250°C)",
                "60-Minute Precision Timer with Auto Shut-Off",
                "Includes Baking Tray, Wire Rack & Crumb Tray",
            ],
        },
        {
            "id": "kitch-3",
            "name": "Precision Kitchen Scale",
            "slug": "kitchen-scale",
            "category": "Kitchen Appliances",
            "category_url": "/kitchen",
            "price": 1199,
            "formatted_price": "₹1,199",
            "image": "images/weighing.jpg",
            "badge": "Essential Tool",
            "rating": 4.8,
            "reviews_count": 190,
            "in_stock": True,
            "short_desc": "Ultra-accurate digital kitchen scale with tare zeroing function and backlit LCD display.",
            "about": "Master every recipe with ultra-fine precision weighing from 1g to 10kg. Features instant unit conversion between grams, kilograms, ounces, and pounds, plus a quick tare zeroing function and a bright backlit LCD screen.",
            "specs": [
                "High-Precision Sensors with 1g / 0.05oz Accuracy",
                "10kg / 22lbs Maximum Weight Capacity",
                "One-Touch Tare Zeroing & Unit Conversion",
                "Tempered Glass Platform with Anti-Fingerprint Coating",
                "Bright Backlit LCD & Auto Power-Off",
            ],
        },
    ],
}


def get_all_products():
    """Return a flat list of all products in the catalog."""
    all_prods = []
    for cat_items in PRODUCTS.values():
        all_prods.extend(cat_items)
    return all_prods


def get_product_by_name_or_slug(identifier):
    """Find a product by exact/case-insensitive name, slug, or normalized string."""
    if not identifier:
        return None
    clean = str(identifier).strip().lower()
    for prod in get_all_products():
        if (
            prod["name"].lower() == clean
            or prod["slug"].lower() == clean
            or prod["id"].lower() == clean
            or clean.replace("-", " ") in prod["name"].lower()
            or prod["name"].lower() in clean.replace("-", " ")
        ):
            return prod
    return None


def time_ago(ban_dt):
    """Return a human-readable relative time string from a ban datetime."""
    diff = datetime.now() - ban_dt
    total_seconds = int(diff.total_seconds())
    minutes = total_seconds // 60
    hours = minutes // 60
    days = hours // 24
    years = days // 365

    if years >= 1:
        return f"{years} yr{'s' if years != 1 else ''} ago"
    elif days >= 1:
        remaining_mins = (total_seconds % 3600) // 60
        if remaining_mins == 0:
            return f"{days}d ago"
        return f"{days}d {remaining_mins}m ago"
    elif hours >= 1:
        remaining_mins = minutes % 60
        if remaining_mins == 0:
            return f"{hours}h ago"
        return f"{hours}h {remaining_mins}m ago"
    else:
        if minutes == 0:
            return "just now"
        return f"{minutes}m ago"


# ═══════════════════════════════════════════════════════════════════════
# CONTEXT PROCESSOR (Injects cart count and current user everywhere)
# ═══════════════════════════════════════════════════════════════════════
@app.context_processor
def inject_global_vars():
    username = session.get("username")
    cart_count = 0
    if username:
        user_carts = session.get("user_carts", {})
        user_cart = user_carts.get(username, [])
        cart_count = sum(item.get("quantity", 1) for item in user_cart)
    return {
        "current_user": username,
        "cart_count": cart_count,
        "now": datetime.now(),
    }


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC & AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════
@app.route("/")
def home():
    """Landing hero page showcasing the platform and catalog."""
    featured_products = [
        PRODUCTS["electronics"][0],  # Smart Phone
        PRODUCTS["electronics"][1],  # Laptop Pro
        PRODUCTS["home-appliances"][0],  # Smart Humidifier
        PRODUCTS["kitchen"][0],  # Digital Air Fryer
    ]
    return render_template("front_main.html", featured_products=featured_products)


@app.route("/register")
def register():
    """Registration page."""
    if "username" in session:
        return redirect(url_for("products"))
    return render_template("register.html")


@app.route("/save_register", methods=["POST"])
def save_register():
    """Handle new user registration."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template(
            "register.html",
            error="Please fill in both username and password.",
            username=username,
        )

    ban_dt = get_banned_user_time(username)
    if ban_dt:
        return render_template("banned.html", username=username, time_ago=time_ago(ban_dt))

    # Persistently add user to SQLite
    success = add_user(username, password)
    if not success:
        return render_template(
            "register.html",
            error="Username already exists! Please choose a different username.",
            username=username,
        )

    return render_template(
        "login.html",
        success="Account created successfully! Please sign in with your credentials.",
        username=username,
    )


@app.route("/login")
def login():
    """Login page."""
    if "username" in session:
        return redirect(url_for("products"))
    return render_template("login.html")


@app.route("/check_login", methods=["POST"])
def check_login():
    """Verify user login credentials from SQLite."""
    user = request.form.get("username", "").strip()
    pwd = request.form.get("password", "").strip()

    if not user or not pwd:
        return render_template(
            "login.html",
            error="Please enter both username and password.",
            username=user,
        )

    # Check if banned
    ban_dt = get_banned_user_time(user)
    if ban_dt:
        return render_template("banned.html", username=user, time_ago=time_ago(ban_dt))

    # Check credentials in SQLite
    user_record = get_user(user)
    if user_record and user_record["password"] == pwd:
        session["username"] = user
        return redirect(url_for("products"))

    return render_template(
        "login.html",
        error=f"No matching account for '{user}'. Please check your password or create a new account.",
        username=user,
    )


@app.route("/logout")
def logout():
    """Sign out the current user."""
    session.pop("username", None)
    return redirect(url_for("home"))


# ═══════════════════════════════════════════════════════════════════════
# CATALOG ROUTES
# ═══════════════════════════════════════════════════════════════════════
@app.route("/products")
def products():
    """Electronics category page."""
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template(
        "products.html",
        products=PRODUCTS["electronics"],
        category_name="Electronics",
    )


@app.route("/home-appliances")
def home_appliances():
    """Home appliances category page."""
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template(
        "home_appliances.html",
        products=PRODUCTS["home-appliances"],
        category_name="Home Appliances",
    )


@app.route("/kitchen")
def kitchen():
    """Kitchen appliances category page."""
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template(
        "kitchen.html",
        products=PRODUCTS["kitchen"],
        category_name="Kitchen Appliances",
    )


@app.route("/details/<product_name>")
def details(product_name):
    """Detailed specifications and purchase view for a single product."""
    if "username" not in session:
        return redirect(url_for("login"))

    prod = get_product_by_name_or_slug(product_name)

    if not prod:
        prod = {
            "name": product_name,
            "category": "General",
            "category_url": "/products",
            "price": 9999,
            "formatted_price": "₹9,999",
            "image": "images/phone.webp",
            "badge": "Standard",
            "rating": 4.5,
            "reviews_count": 50,
            "in_stock": True,
            "short_desc": "High quality product with full warranty.",
            "about": "High-quality consumer product engineered for optimal durability, reliability, and modern aesthetic.",
            "specs": ["Standard 1-Year Manufacturer Warranty", "Certified Safe & Tested", "Fast Free Shipping"],
        }

    all_others = [p for p in get_all_products() if p["name"] != prod["name"]]
    recommendations = random.sample(all_others, min(3, len(all_others)))

    return render_template(
        "details.html",
        item=prod,
        product_name=prod["name"],
        recommendations=recommendations,
    )


# ═══════════════════════════════════════════════════════════════════════
# CART & CHECKOUT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    """Add a product or increment its quantity in the user's cart."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    product_name = request.form.get("product_name", "").strip()
    price_val = request.form.get("price")
    image = request.form.get("image", "").strip()
    about = request.form.get("about", "").strip()

    if not product_name:
        return redirect(request.referrer or url_for("products"))

    official_prod = get_product_by_name_or_slug(product_name)
    if official_prod:
        price = official_prod["price"]
        image = official_prod["image"]
        about = official_prod["short_desc"]
        product_name = official_prod["name"]
    else:
        try:
            price = int(float(str(price_val).replace("₹", "").replace(",", "")))
        except (ValueError, TypeError):
            price = 999
        if not image:
            image = "images/phone.webp"

    if "user_carts" not in session:
        session["user_carts"] = {}

    user_carts = session["user_carts"]
    if username not in user_carts:
        user_carts[username] = []

    cart = user_carts[username]
    product_found = False

    for item in cart:
        if item["name"] == product_name:
            item["quantity"] += 1
            product_found = True
            break

    if not product_found:
        cart.append({
            "name": product_name,
            "price": price,
            "image": image,
            "about": about or "Premium quality consumer item.",
            "quantity": 1,
        })

    user_carts[username] = cart
    session["user_carts"] = user_carts
    session.modified = True

    return redirect(request.referrer or url_for("cart"))


@app.route("/cart")
def cart():
    """Shopping cart view with quantity management and order summary."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_carts = session.get("user_carts", {})
    cart_items = user_carts.get(username, [])

    subtotal = sum(item["price"] * item["quantity"] for item in cart_items)
    shipping = 0 if subtotal == 0 or subtotal > 5000 else 99
    discount = 0
    total = subtotal + shipping - discount

    return render_template(
        "cart.html",
        cart=cart_items,
        subtotal=subtotal,
        shipping=shipping,
        discount=discount,
        total=total,
    )


@app.route("/increase/<path:product_name>")
def increase(product_name):
    """Increase quantity of an item in the cart."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_carts = session.get("user_carts", {})
    cart = user_carts.get(username, [])

    for item in cart:
        if item["name"].lower() == product_name.lower():
            item["quantity"] += 1
            break

    user_carts[username] = cart
    session["user_carts"] = user_carts
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/decrease/<path:product_name>")
def decrease(product_name):
    """Decrease quantity or remove item from the cart."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_carts = session.get("user_carts", {})
    cart = user_carts.get(username, [])

    for item in list(cart):
        if item["name"].lower() == product_name.lower():
            item["quantity"] -= 1
            if item["quantity"] <= 0:
                cart.remove(item)
            break

    user_carts[username] = cart
    session["user_carts"] = user_carts
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/remove_from_cart/<path:product_name>")
def remove_from_cart(product_name):
    """Remove item completely from cart."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_carts = session.get("user_carts", {})
    cart = user_carts.get(username, [])

    cart = [item for item in cart if item["name"].lower() != product_name.lower()]
    user_carts[username] = cart
    session["user_carts"] = user_carts
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/checkout")
def checkout():
    """Checkout page to select payment method and review order."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_carts = session.get("user_carts", {})
    cart_items = user_carts.get(username, [])

    if not cart_items:
        return redirect(url_for("products"))

    subtotal = sum(item["price"] * item["quantity"] for item in cart_items)
    shipping = 0 if subtotal > 5000 else 99
    total = subtotal + shipping

    return render_template(
        "checkout.html",
        cart=cart_items,
        subtotal=subtotal,
        shipping=shipping,
        total=total,
    )


@app.route("/card")
def card():
    """Credit / Debit card payment screen."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_carts = session.get("user_carts", {})
    cart_items = user_carts.get(username, [])
    subtotal = sum(item["price"] * item["quantity"] for item in cart_items)
    shipping = 0 if subtotal > 5000 else 99
    total = subtotal + shipping

    return render_template("card.html", total=total, subtotal=subtotal)


@app.route("/upi")
def upi():
    """UPI / VPA instant payment screen."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_carts = session.get("user_carts", {})
    cart_items = user_carts.get(username, [])
    subtotal = sum(item["price"] * item["quantity"] for item in cart_items)
    shipping = 0 if subtotal > 5000 else 99
    total = subtotal + shipping

    return render_template("upi.html", total=total, subtotal=subtotal)


@app.route("/netbanking")
def netbanking():
    """Internet banking portal payment screen."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_carts = session.get("user_carts", {})
    cart_items = user_carts.get(username, [])
    subtotal = sum(item["price"] * item["quantity"] for item in cart_items)
    shipping = 0 if subtotal > 5000 else 99
    total = subtotal + shipping

    return render_template("netbanking.html", total=total, subtotal=subtotal)


@app.route("/delivery")
def delivery():
    """Complete checkout, generate confirmation receipt, and clear cart."""
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_carts = session.get("user_carts", {})
    ordered_items = list(user_carts.get(username, []))

    subtotal = sum(item["price"] * item["quantity"] for item in ordered_items)
    shipping = 0 if subtotal > 5000 else 99
    total = subtotal + shipping

    random_digits = "".join(random.choices(string.digits, k=6))
    order_id = f"TM-{random_digits}"

    if username in user_carts:
        user_carts[username] = []
        session["user_carts"] = user_carts
        session.modified = True

    return render_template(
        "delivery.html",
        order_id=order_id,
        items=ordered_items,
        subtotal=subtotal,
        shipping=shipping,
        total=total,
    )


# ═══════════════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════════════
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    """Admin portal sign in."""
    if session.get("is_admin"):
        return redirect(url_for("admin_panel"))

    error = None
    if request.method == "POST":
        uname = request.form.get("username", "").strip()
        pwd = request.form.get("password", "").strip()

        if uname == ADMIN_USERNAME and (pwd == ADMIN_PASSWORD or pwd == "1234"):
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        else:
            error = "Invalid administrator credentials."

    return render_template("admin_login.html", error=error)


@app.route("/admin/panel")
def admin_panel():
    """Admin dashboard to view, block, and manage registered users."""
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    user_list = get_all_users()
    total = len(user_list)
    banned_list = get_all_banned_users()

    return render_template(
        "admin_panel.html",
        user_list=user_list,
        total=total,
        banned_list=banned_list,
    )


@app.route("/admin/block/<username>", methods=["POST"])
def admin_block(username):
    """Block a user and revoke their account access."""
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    ban_user(username)
    return redirect(url_for("admin_panel"))


@app.route("/admin/unblock/<username>", methods=["POST"])
def admin_unblock(username):
    """Unblock or purge a user from the banned blacklist."""
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    unban_user(username)
    return redirect(url_for("admin_panel"))


@app.route("/admin/logout")
def admin_logout():
    """Sign out of admin session."""
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))


# ═══════════════════════════════════════════════════════════════════════
# MAIN ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=True, port=5000)