"""
Boba Shop.

This script runs a Flask web server, manages a sqlite3 database for orders,
handles a customer cart, creates an invoice and order history
and tracks loyalty points.
"""

import json
import datetime
import sqlite3
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

app = Flask(__name__)
app.secret_key = 'WinnerWinnerChickenDinner'


def initialise_database():
    """Initialise SQLite database and create an orders table."""
    with sqlite3.connect('boba_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            customer_name TEXT,
            phone TEXT,
            items TEXT,
            total REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')


# Calculate's total price based on the cart (drink prices AND topping prices)
def calculate_total(cart):
    """Calculate the total price of the current cart."""
    return sum(
        (item['price'] + item['topping_price']) * item['quantity']
        for item in cart
    )


# Loyalty points system
def load_phone_numbers():
    """Load customer phone numbers and points data from JSON file."""
    with open('data/phone_numbers.json') as file:
        return json.load(file)


def save_phone_numbers(phone_numbers):
    """Save the updated customer phone numbers and points data to JSON."""
    with open('data/phone_numbers.json', 'w') as file:
        json.dump(phone_numbers, file, indent=4)


@app.route('/')


@app.route('/menu')
def menu():
    """Open and render the menu and addons JSON files."""
    with open('data/menu.json') as file:
        menu_data = json.load(file)

    with open('data/addons.json') as file:
        addons = json.load(file)

    return render_template(
        'menu.html',
        menu=menu_data,
        toppings=addons['toppings'],
        sugar_level=addons['sugar_level'],
        ice_level=addons['ice_level'],
    )


@app.route('/invoices')
def invoices():
    """Render and return the invoices page."""
    return render_template('invoices.html')


@app.route('/orders')
def order_history():
    """Render the order history page, fetch past orders from database."""
    with sqlite3.connect('boba_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders ORDER BY date DESC")
        rows = cursor.fetchall()
        orders = []
        for row in rows:
            orders.append({
                'order_id': row[0],
                'invoice_number': row[1],
                'customer_name': row[2],
                'phone': row[3],
                'items': json.loads(row[4]),
                'total': row[5],
                'date': row[6]
            })
    return render_template('order_history.html', orders=orders)


@app.route('/cart_display')
def cart_display():
    """Get current cart and price from session and render the cart page."""
    cart = session.get('cart', [])
    total = calculate_total(cart)
    return render_template('cart_display.html', cart=cart, total=total)


@app.route('/select_addon', methods=['POST'])
def select_addon():
    """Add the selected drink with chosen addons to the session cart."""
    # Get cart list from session or start empty list
    cart = session.get('cart', [])

    with open('data/menu.json') as file:
        menu_data = json.load(file)

    with open('data/addons.json') as file:
        addons = json.load(file)

    item_name = request.form.get('item_name')
    toppings = request.form.get('toppings')
    sugar_level = request.form.get('sugar_level')
    ice_level = request.form.get('ice_level')

    # Count how many of the drink is in the cart (ignoring toppings/sugar/ice)
    current_drink_count = sum(
        item['quantity']
        for item in cart
        if item['item_name'] == item_name
    )

    # Stops more than 3 of the same drink being added
    # (only 3 drinks avaliable per drink for 1 order)
    if current_drink_count >= 3:
        flash(f"There is a max limit of 3 {item_name} per order.", "cart")
        return redirect(url_for('cart_display'))

    drink_price = None
    for category, items in menu_data.items():
        if item_name in items:
            drink_price = items[item_name]['price']
            break

    topping_price = addons['toppings'].get(toppings, {}).get('price', 0)
    cart_key = f"{item_name} | {toppings} | {sugar_level} | {ice_level}"

    # Search for an existing matching item in the cart list
    item_exists = False
    for item in cart:
        if item['cart_key'] == cart_key:
            item['quantity'] += 1
            item_exists = True
            break

    # If it's a new item combination, append it to the end of the list
    if not item_exists:
        cart.append({
            'cart_key': cart_key,
            'item_name': item_name,
            'price': drink_price,
            'toppings': toppings,
            'topping_price': topping_price,
            'sugar_level': sugar_level,
            'ice_level': ice_level,
            'quantity': 1
        })

    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart_display'))


@app.route('/remove_from_cart/<item>')
def remove_from_cart(item):
    """Decrease quantity of a drink or remove it from the session cart."""
    cart = session.get('cart', [])
    new_cart = []

    for cart_item in cart:
        if cart_item['cart_key'] == item:
            if cart_item['quantity'] > 1:
                # If there's more than one, lower the quantity by 1
                cart_item['quantity'] -= 1
                new_cart.append(cart_item)
        else:
            # Keep all other drinks untouched
            new_cart.append(cart_item)

    session['cart'] = new_cart
    session.modified = True
    flash("Updated cart.")
    return redirect(url_for('cart_display'))


# Checkout cart
@app.route('/checkout', methods=['POST'])
def checkout():
    """Process checkout, validate inputs, update points, and save order."""
    # 1. Validate customer name
    customer_name = request.form['customer_name'].strip().title()

    # Check if a customer name has been entered
    if not customer_name:
        flash("Customer name is required")
        return redirect(url_for('cart_display'))

    # 2. Get cart
    cart = session.get('cart', [])

    # 3. Check that the cart is not empty
    if not cart:
        flash('Your cart is empty')
        return redirect(url_for('cart_display'))

    # 4. Calculate total cost
    total = calculate_total(cart)

    # 5. Phone number loyalty points sytem
    phone = request.form.get('customer_number', '').strip()

    if phone:
        # Check if the input includes anything but numbers (eg-letters)
        if not phone.isdigit():
            flash("Only numbers allowed", "cart")
            return redirect(url_for('cart_display'))

        # Check if the number of digits is 10 or not
        if len(phone) != 10:
            flash("Phone number must be exactly 10 digits.", "cart")
            return redirect(url_for('cart_display'))

        customer_phone_numbers = load_phone_numbers()

        customer = None
        for person in customer_phone_numbers:
            if person['phone'] == phone:
                customer = person

        if customer is None:
            customer = {'phone': phone, 'points': 0}
            customer_phone_numbers.append(customer)

        # Check if customer has 30 or more points to redeem a 15% discount
        if customer['points'] >= 30:
            # Apply 15% discount
            total = total * 0.85
            # Take away the used up 30 points
            customer['points'] = customer['points'] - 30
            flash(
                "You have collected 30 points! A 15% discount applied!",
                "invoice"
            )
        else:
            # $1 = 1 Bubbly point
            customer['points'] += int(total)
            flash(
                f"You now have {customer['points']} bubbly points!",
                "invoice"
            )

        save_phone_numbers(customer_phone_numbers)

    # 6. Calculate the invoice number and date
    invoice_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    invoice_number = (
        f"INV_{customer_name.replace(' ', '_')}_"
        f"{invoice_date.replace(':', '').replace(' ', '_')}"
    )

    # 7. Save the order to SQlite database
    with sqlite3.connect('boba_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (
                invoice_number,
                customer_name,
                phone,
                items,
                total
            )

            VALUES (?, ?, ?, ?, ?)
        ''', (invoice_number, customer_name, phone, json.dumps(cart), total))

    # 8. Generate an invoice file
    invoice_filename = f"{invoice_number}.txt"

    with open(invoice_filename, 'w') as f:
        f.write("--- Boba Shop Invoice ---\n\n")
        f.write(f"Invoice number: {invoice_number}\n")
        f.write(f"Customer Name: {customer_name}\n")
        f.write(f"Customer Phone: {phone}\n")
        f.write(f"Date: {invoice_date}\n\n")
        f.write("Items:\n")
        for item in cart:
            line_total = (
                item['price'] + item['topping_price']
            ) * item['quantity']
            f.write(
                f"- {item['item_name']} ({item['toppings']}, {item['sugar_level']} sugar, "
                f"{item['ice_level']} ice): {item['quantity']} x ${total:.2f} "
                f"= ${line_total:.2f}\n\n"
            )
        f.write(f"Total: ${total:.2f}\n")

    # 9. Update stock in menu.json
    with open('data/menu.json', 'r') as file:
        menu_data = json.load(file)

    for cart_item in cart:
        for category, drinks in menu_data.items():
            if cart_item['item_name'] in drinks:
                drinks[cart_item['item_name']]['stock'] -= (
                    cart_item['quantity']
                )
                if drinks[cart_item['item_name']]['stock'] < 0:
                    drinks[cart_item['item_name']]['stock'] = 0
                break

    with open('data/menu.json', 'w') as file:
        json.dump(menu_data, file, indent=4)

    # 10. Clear the cart and give thank you message after order is placed
    session.pop('cart', None)
    session.modified = True
    flash(f"Thank you {customer_name}, your order has been placed.", "invoice")
    return render_template(
        'invoices.html',
        customer_name=customer_name,
        cart=cart, total=total,
        invoice_date=invoice_date,
        invoice_number=invoice_number,
        phone=phone
    )


@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    """Cancel the entire current session cart."""
    session.pop('cart', None)
    session.modified = True
    flash("Order Cancelled. Your cart has been emptied.", "order_history")
    return redirect(url_for('cart_display'))


@app.route('/cancel_saved_order/<int:order_id>', methods=['POST'])
def cancel_saved_order(order_id):
    """Cancel the selected order."""
    with sqlite3.connect('boba_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
        conn.commit()
    flash("Order cancelled.")
    return redirect(url_for('order_history'))


if __name__ == '__main__':
    initialise_database()
    app.run(debug=True)
