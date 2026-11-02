from pathlib import Path
import sqlite3

from flask import Flask, flash, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "entrepreneurs.db"
app = Flask(__name__)
app.secret_key = "women-entrepreneurship-platform-local"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS entrepreneurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                city TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entrepreneur_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL CHECK (price >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entrepreneur_id) REFERENCES entrepreneurs(id)
                    ON DELETE CASCADE
            );
            """
        )
        if connection.execute("SELECT COUNT(*) FROM entrepreneurs").fetchone()[0] == 0:
            founders = [
                ("Ananya Rao", "ananya@example.com", "+91 98765 43210", "Hyderabad", "Handmade & Crafts"),
                ("Meera Iyer", "meera@example.com", "+91 98765 43211", "Chennai", "Food & Beverage"),
                ("Sana Khan", "sana@example.com", "+91 98765 43212", "Bengaluru", "Fashion & Lifestyle"),
            ]
            connection.executemany(
                """INSERT INTO entrepreneurs (name, email, phone, city, category)
                   VALUES (?, ?, ?, ?, ?)""",
                founders,
            )
            founder_ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM entrepreneurs ORDER BY id"
                ).fetchall()
            ]
            products = [
                (founder_ids[0], "Terracotta Tableware", "Hand-finished serveware inspired by the Deccan.", 850),
                (founder_ids[1], "Little Millet Bites", "Small-batch, wholesome snacks made with local millet.", 320),
                (founder_ids[2], "Everyday Tote", "A sturdy, thoughtfully made carryall for everyday use.", 690),
            ]
            connection.executemany(
                """INSERT INTO products (entrepreneur_id, name, description, price)
                   VALUES (?, ?, ?, ?)""",
                products,
            )


@app.route("/")
def index():
    with get_db_connection() as connection:
        entrepreneurs_count = connection.execute(
            "SELECT COUNT(*) FROM entrepreneurs"
        ).fetchone()[0]
        products_count = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]
        businesses = connection.execute(
            """SELECT e.*, COUNT(p.id) AS product_count
               FROM entrepreneurs e
               LEFT JOIN products p ON p.entrepreneur_id = e.id
               GROUP BY e.id
               ORDER BY e.created_at DESC, e.id DESC
               LIMIT 3"""
        ).fetchall()
        products = connection.execute(
            """SELECT p.*, e.name AS entrepreneur_name
               FROM products p
               JOIN entrepreneurs e ON e.id = p.entrepreneur_id
               ORDER BY p.created_at DESC, p.id DESC
               LIMIT 3"""
        ).fetchall()
    return render_template(
        "index.html",
        entrepreneurs_count=entrepreneurs_count,
        products_count=products_count,
        businesses=businesses,
        products=products,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        city = request.form.get("city", "").strip()
        category = request.form.get("category", "").strip()
        if not all((name, email, phone, city, category)):
            flash("Please complete every field before registering.", "error")
            return render_template("register.html", form=request.form)
        try:
            with get_db_connection() as connection:
                connection.execute(
                    """INSERT INTO entrepreneurs (name, email, phone, city, category)
                       VALUES (?, ?, ?, ?, ?)""",
                    (name, email, phone, city, category),
                )
        except sqlite3.IntegrityError:
            flash("That email is already registered. Please use another email.", "error")
            return render_template("register.html", form=request.form)
        flash("Your business profile is ready. Welcome to the community!", "success")
        return redirect(url_for("businesses"))
    return render_template("register.html", form={})


@app.route("/businesses")
def businesses():
    with get_db_connection() as connection:
        entrepreneurs = connection.execute(
            """SELECT e.*, COUNT(p.id) AS product_count
               FROM entrepreneurs e
               LEFT JOIN products p ON p.entrepreneur_id = e.id
               GROUP BY e.id
               ORDER BY e.name COLLATE NOCASE"""
        ).fetchall()
    return render_template("businesses.html", entrepreneurs=entrepreneurs)


@app.route("/products/add", methods=["GET", "POST"])
def add_product():
    with get_db_connection() as connection:
        entrepreneurs = connection.execute(
            "SELECT id, name, city FROM entrepreneurs ORDER BY name COLLATE NOCASE"
        ).fetchall()
    if request.method == "POST":
        entrepreneur_id = request.form.get("entrepreneur_id", type=int)
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        try:
            price = float(request.form.get("price", ""))
            if price < 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid price of zero or more.", "error")
            return render_template(
                "add_product.html", entrepreneurs=entrepreneurs, form=request.form
            )
        if not entrepreneur_id or not name or not description:
            flash("Please complete every field before adding a product.", "error")
            return render_template(
                "add_product.html", entrepreneurs=entrepreneurs, form=request.form
            )
        with get_db_connection() as connection:
            founder = connection.execute(
                "SELECT id FROM entrepreneurs WHERE id = ?", (entrepreneur_id,)
            ).fetchone()
            if founder is None:
                flash("Choose a registered entrepreneur.", "error")
                return render_template(
                    "add_product.html", entrepreneurs=entrepreneurs, form=request.form
                )
            connection.execute(
                """INSERT INTO products (entrepreneur_id, name, description, price)
                   VALUES (?, ?, ?, ?)""",
                (entrepreneur_id, name, description, price),
            )
        flash("Product added to the marketplace.", "success")
        return redirect(url_for("index"))
    return render_template("add_product.html", entrepreneurs=entrepreneurs, form={})


init_db()


if __name__ == "__main__":
    app.run(debug=True)
