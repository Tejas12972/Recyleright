"""
Routes module for RecycleRight web interface.
"""

import os
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pymongo.errors

from app import app
from data.database import get_db
from models.waste_classifier import WasteClassifier
from api.geolocation import GeolocationService

def register_routes(app):
    """Register routes with the Flask application."""
    
    # Initialize services
    try:
        db = get_db()
    except pymongo.errors.ServerSelectionTimeoutError:
        db = None
        app.logger.warning("MongoDB not available. Some features will be limited.")

    try:
        classifier = WasteClassifier(app.config['MODEL_PATH'], app.config['LABELS_PATH'])
    except Exception as e:
        classifier = None
        app.logger.error(f"Error initializing waste classifier: {e}")

    try:
        geo_service = GeolocationService()
    except Exception as e:
        geo_service = None
        app.logger.error(f"Error initializing geolocation service: {e}")

    def check_db():
        """Check if database is available and reconnect if necessary."""
        nonlocal db
        if db is None:
            try:
                db = get_db()
            except Exception as e:
                app.logger.error(f"Database connection failed: {e}")
                return False
        return True

    def allowed_file(filename):
        """Check if file extension is allowed."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    @app.route('/')
    def home():
        """Render home page."""
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Handle user login."""
        if not check_db():
            flash('Service temporarily unavailable. Please try again later.', 'error')
            return render_template('login.html')
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            try:
                user = db.get_user(username=username)
                if user and check_password_hash(user['password_hash'], password):
                    session['user_id'] = user['id']
                    flash('Login successful!', 'success')
                    return redirect(url_for('dashboard'))
                
                flash('Invalid username or password', 'error')
            except Exception as e:
                app.logger.error(f"Login error: {e}")
                flash('Service temporarily unavailable. Please try again later.', 'error')
        
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Handle user registration."""
        if not check_db():
            flash('Service temporarily unavailable. Please try again later.', 'error')
            return render_template('register.html')
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            try:
                if db.get_user(username=username):
                    flash('Username already exists', 'error')
                    return render_template('register.html')
                
                password_hash = generate_password_hash(password)
                user_id = db.add_user(username, email, password_hash)
                
                if user_id:
                    flash('Registration successful! Please login.', 'success')
                    return redirect(url_for('login'))
                
                flash('Error during registration', 'error')
            except Exception as e:
                app.logger.error(f"Registration error: {e}")
                flash('Service temporarily unavailable. Please try again later.', 'error')
        
        return render_template('register.html')

    @app.route('/logout')
    def logout():
        """Handle user logout."""
        session.pop('user_id', None)
        flash('You have been logged out', 'info')
        return redirect(url_for('home'))

    @app.route('/dashboard')
    def dashboard():
        """Render user dashboard."""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        if not check_db():
            flash('Service temporarily unavailable. Please try again later.', 'error')
            return redirect(url_for('home'))
        
        try:
            user = db.get_user(user_id=session['user_id'])
            stats = db.get_user_stats(session['user_id'])
            challenges = db.get_user_active_challenges(session['user_id'])
            
            return render_template('dashboard.html', user=user, stats=stats, challenges=challenges)
        except Exception as e:
            app.logger.error(f"Dashboard error: {e}")
            flash('Error loading dashboard. Please try again later.', 'error')
            return redirect(url_for('home'))

    @app.route('/scan', methods=['GET', 'POST'])
    def scan():
        """Handle waste scanning."""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        if not check_db() or not classifier:
            flash('Service temporarily unavailable. Please try again later.', 'error')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'error': 'File type not allowed'}), 400
            
            try:
                # Save file
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Process image
                waste_type, confidence = classifier.get_top_prediction(filepath)
                
                if waste_type:
                    # Record scan
                    scan_id = db.record_scan(session['user_id'], waste_type, confidence, filepath)
                    
                    # Get recycling guidelines
                    guidelines = db.get_recycling_guidelines(waste_type, 'default')
                    
                    return jsonify({
                        'success': True,
                        'waste_type': waste_type,
                        'confidence': confidence,
                        'guidelines': guidelines
                    })
                
                return jsonify({'error': 'Could not classify waste'}), 400
                
            except Exception as e:
                app.logger.error(f"Error processing scan: {e}")
                return jsonify({'error': 'Error processing image'}), 500
        
        return render_template('scan.html')

    @app.route('/centers')
    def centers():
        """Show nearby recycling centers."""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        if not check_db() or not geo_service:
            flash('Service temporarily unavailable. Please try again later.', 'error')
            return redirect(url_for('dashboard'))
        
        try:
            user = db.get_user(user_id=session['user_id'])
            if not user.get('location'):
                flash('Please update your location first', 'warning')
                return redirect(url_for('dashboard'))
            
            centers = db.get_nearby_recycling_centers(
                user['location_lat'],
                user['location_lon'],
                radius_km=10
            )
            
            return render_template('centers.html', centers=centers)
        except Exception as e:
            app.logger.error(f"Error loading recycling centers: {e}")
            flash('Error loading recycling centers. Please try again later.', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/leaderboard')
    def leaderboard():
        """Show leaderboard."""
        if not check_db():
            flash('Service temporarily unavailable. Please try again later.', 'error')
            return redirect(url_for('home'))
        
        try:
            leaders = db.get_leaderboard(limit=10)
            return render_template('leaderboard.html', leaders=leaders)
        except Exception as e:
            app.logger.error(f"Error loading leaderboard: {e}")
            flash('Error loading leaderboard. Please try again later.', 'error')
            return redirect(url_for('home'))

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500 