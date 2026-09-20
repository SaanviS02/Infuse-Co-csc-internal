import json
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'WinnerWinnerChickenDinner'

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart_display'))

# Calculate's total price based on the cart (drink prices AND topping prices)
def calculate_total(cart):
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    total += sum(item['topping_price'] * item['quantity'] for item in cart.values())
    return total

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def menu():
    with open ('data/menu.json') as file:
        menu_data = json.load(file)

    with open('data/addons.json') as file:
        addons = json.load(file)
    
    return render_template('menu.html', menu=menu_data, toppings=addons['toppings'], sugar_level=addons['sugar_level'], ice_level=addons['ice_level'])

@app.route('/invoices')
def invoices():
    return render_template('invoices.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/cart_display')
def cart_display():
    cart = session.get('cart', {})
    total = calculate_total(cart)
    return render_template('cart_display.html', cart=cart, total=total)

@app.route('/select_addon', methods=['POST']) 
def select_addon():
    cart = session.get('cart', {}) # Get cart form session or start a new one

    with open('data/menu.json') as file:
        menu_data = json.load(file)

    with open('data/addons.json') as file:
        addons = json.load(file)

    # Get the selected drink name, toppings, sugar and ice level
    item_name = request.form.get('item_name')
    toppings = request.form.get('toppings')
    sugar_level = request.form.get('sugar_level')
    ice_level = request.form.get('ice_level')

    # Look up the drink's price by searching each drink category (eg: fruit tea, milk tea etc)
    drink_price = None
    for category, items in menu_data.items():
        if item_name in items:
            drink_price = items[item_name]['price']
            break

    # Look up the chosen topping's price (0 if no topping matched)
    topping_price = addons['toppings'].get(toppings, {}).get('price', 0)

    cart_key = f"{item_name} | {toppings} | {sugar_level} | {ice_level}" # allows users to order the same drink but with different addons selected

    if cart_key in cart:
        cart[cart_key]['quantity'] += 1
    else:
        cart[cart_key] = {
            'item_name': item_name,
            'price': drink_price,
            'toppings': toppings,
            'topping_price': topping_price,
            'sugar_level': sugar_level,
            'ice_level': ice_level,
            'quantity': 1
        }

    session['cart'] = cart # To update the session
    session.modified = True # Make Flask also save it
    return redirect(url_for('cart_display'))

@app.route('/remove_from_cart/<item>')
def remove_from_cart(item):
    cart = session.get('cart', {})

    if item in cart:
        del cart[item]
        session['cart'] = cart
        session.modified = True
        flash("Removed item from cart.")
    else:
        flash("Item not found in cart")

    return redirect(url_for('cart_display'))

    # Checkout cart
@app.route('/checkout', methods=['POST'])
def checkout():
    # 1. Validate customer name
    customer_name = request.form['customer_name'].strip().title()

    # Check if a customer name has been entered
    if not customer_name:
        flash("Customer name is required")
        return redirect(url_for('cart_display'))

    # 2. Get cart
    cart = session.get('cart', {}) 

    # 3. Check that the cart is not empty
    if not cart:
        flash('Your cart is empty')
        return redirect(url_for('cart_display'))

    session.pop('cart', None)
    session.modified = True
    flash(f"Thank you {customer_name}, your order has been placed!")
    return redirect(url_for('cart_display'))

@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    session.pop('cart', None)
    session.modified = True
    flash("Order Cancelled. Your cart has been emptied.")
    return redirect(url_for('cart_display'))

if __name__ == '__main__':
    app.run(debug=True)