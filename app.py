from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
import pandas as pd
import random
from sklearn.neighbors import NearestNeighbors
from model.trip_planner import load_cleaned_data, get_distinct_cities, recommend_places_ml, generate_daily_itinerary, plan_trip
from flask_mail import Mail, Message
import pymongo
from pymongo import MongoClient
import bcrypt
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kartik2310179@akgec.ac.in'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'etrf leme yhgk bwup'  # Replace with your email password
app.config['MAIL_DEFAULT_SENDER'] = 'kartik2310179@akgec.ac.in'
mail = Mail(app)

# MongoDB configuration
client = MongoClient('mongodb+srv://kartik2310179:2H1yMr6PjfGhyZIL@cluster0.95nrk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['trip_planner_db']
users_collection = db['users']

# Serializer for token-based actions
s = URLSafeTimedSerializer(app.secret_key)

# Routes
@app.route('/plan')
def plan():
    df = load_cleaned_data()
    cities = get_distinct_cities(df)
    return render_template('plan.html', cities=cities)

import json

@app.route('/')
def index():
    if 'user' in session:
        user_email = session['email']
        # Fetch saved trip planner from the database
        user_data = users_collection.find_one({"email": user_email})

        # Log the retrieved user data for debugging
        app.logger.info(f"User data: {user_data}")

        saved_planner = user_data.get('saved_planner', None)  # Get saved planner if exists

        if saved_planner:
            app.logger.info(f"Saved planner: {saved_planner}")
            return render_template('index.html', user=session['user'], email=session['email'], saved_planner=saved_planner)
        else:
            # If no planner is found, show a message
            flash("You don't have any saved trip planner yet.", "warning")
            return render_template('index.html', user=session['user'], email=session['email'], saved_planner=None)

    return render_template('index.html')



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        if users_collection.find_one({"email": email}):
            flash("User already exists!", "danger")
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('signup'))

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users_collection.insert_one({"name": name, "email": email, "password": hashed_password})

        flash("User registered successfully!", "success")
        return redirect(url_for('login'))

    return render_template('sign.html')

@app.route('/save_planner', methods=['POST'])
def save_planner():
    if 'email' not in session:
        return jsonify({"message": "You must be logged in to save your planner!"}), 403

    user_email = session['email']
    data = request.get_json()

    if not data or 'itinerary' not in data:
        return jsonify({"message": "Invalid request data!"}), 400

    try:
        users_collection.update_one(
            {"email": user_email},
            {"$set": {"saved_planner": data['itinerary']}}
        )
        return jsonify({"message": "Your planner has been saved successfully!"})
    except Exception as e:
        app.logger.error(f"Error saving planner: {e}")
        return jsonify({"message": "Failed to save planner!"}), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({"email": email})

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['user'] = user['name']
            session['email'] = user['email']
            flash(f"Hello {user['name']}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password!", "danger")

    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = users_collection.find_one({"email": email})

        if user:
            token = s.dumps(email, salt='password-reset-salt')
            reset_link = url_for('reset_password', token=token, _external=True)

            try:
                msg = Message(
                    subject="Password Reset Request",
                    recipients=[email],
                    body=f"Hello {user['name']},\n\nPlease click the link to reset your password:\n{reset_link}\n\nBest regards,\nTrip Planner Team"
                )
                mail.send(msg)
                flash("Password reset link sent to your email!", "success")
                return redirect(url_for('login'))
            except Exception as e:
                app.logger.error(f"Email sending error: {e}")
                flash("Failed to send email!", "danger")
        else:
            flash("Email not registered!", "danger")

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash("Password reset link expired.", "danger")
        return redirect(url_for('forgot_password'))
    except Exception as e:
        flash(f"Invalid token: {e}", "danger")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm-password']

        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('reset_password', token=token))

        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        users_collection.update_one({"email": email}, {"$set": {"password": hashed_password}})

        flash("Password reset successfully!", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        try:
            msg = Message(
                subject=f"Contact Form Submission from {name}",
                recipients=["kartikkalra2705@gmail.com"],
                body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
            )
            mail.send(msg)
            flash('Message sent successfully!', 'success')
        except Exception as e:
            app.logger.error(f"Error sending message: {e}")
            flash("Failed to send message!", 'danger')

        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('index'))

@app.route('/plan_trip', methods=['POST'])
def plan_trip_route():
    city = request.form['city']
    days = int(request.form['days'])
    rating = float(request.form['rating'])
    max_distance = float(request.form['max_distance'])

    df = load_cleaned_data()
    full_itinerary = plan_trip(city, days, rating, max_distance, df)

    if 'email' in session:
        user_email = session['email']
        users_collection.update_one(
            {"email": user_email},
            {"$set": {"trip_planner": full_itinerary}}
        )
        flash("Trip planner saved!", "success")

    return jsonify(full_itinerary)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Default to 5000 if PORT is not set
    app.run(host="0.0.0.0", port=port)
    # app.run(debug=True)
