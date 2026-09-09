import json
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'WinnerWinnerChickenDinner'

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
    return render_template('cart_display.html', cart=cart)

@app.route('/select_addon', methods=['POST']) 
def select_addon():
    cart = session.get('cart', {}) # Get cart form session or start a new one

    # Get the selected drink name, toppings, sugar and ice level
    item_name = request.form.get('item_name')
    toppings = request.form.get('toppings')
    sugar_level = request.form.get('sugar_level')
    ice_level = request.form.get('ice_level')

    cart_key = f"{item_name} | {toppings} | {sugar_level} | {ice_level}" # allows users to order the same drink but with different addons selected

    if cart_key in cart:
        cart[cart_key]['quantity'] += 1
    else:
        cart[cart_key] = {
            'item_name': item_name,
            'toppings': toppings,
            'sugar_level': sugar_level,
            'ice_level': ice_level,
            'quantity': 1
        }

    session['cart'] = cart # To update the session
    session.modified = True # Make Flask also save it
    return redirect(url_for('cart_display'))

if __name__ == '__main__':
    app.run(debug=True)