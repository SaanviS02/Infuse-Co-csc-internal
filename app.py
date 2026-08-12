import json
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'WinnerWinnerChickenDinner'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def menu():
    with open ('menu.json') as f:
        menu_data = json.load(f)
    return render_template('menu.html', menu=menu_data)

@app.route('/invoices')
def invoices():
    return render_template('invoices.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)