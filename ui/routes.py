"""
Routes module for RecycleRight web interface.
"""

import os
import uuid
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pymongo.errors
import logging

from data.database import get_db
from models.waste_classifier import WasteClassifier
from api.geolocation import GeolocationService
import config

logger = logging.getLogger(__name__)

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
        app.config['classifier'] = classifier  # Store with correct key
    except Exception as e:
        classifier = None
        app.logger.error(f"Error initializing waste classifier: {e}")

    try:
        geo_service = GeolocationService()
    except Exception as e:
        geo_service = None
        app.logger.error(f"Error initializing geolocation service: {e}")
        
    # Initialize points system if db is available
    points_system = None
    if db:
        try:
            from gamification.points_system import PointsSystem
            points_system = PointsSystem(db)
        except Exception as e:
            app.logger.error(f"Error initializing points system: {e}")

    # Make services available to the routes
    app.config['database'] = db
    app.config['geo_service'] = geo_service
    app.config['points_system'] = points_system
    
    # Add Google Maps API key to app config
    app.config['GOOGLE_MAPS_API_KEY'] = config.GOOGLE_MAPS_API_KEY

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
        """Check if file is allowed based on extension."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

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
            if not user:
                flash('User not found. Please log in again.', 'error')
                return redirect(url_for('logout'))
                
            # Get user stats
            stats = db.get_user_stats(session['user_id'])
            if not stats:
                stats = {
                    "user_id": session['user_id'],
                    "points": user.get('points', 0),
                    "level": user.get('level', 'Beginner'),
                    "rank": 1,
                    "next_level": "Intermediate",
                    "points_to_next_level": 100,
                    "level_progress": 0,
                    "items_scanned": 0,
                    "items_recycled": 0
                }
            
            # Get active challenges
            challenges = db.get_user_active_challenges(session['user_id'])
            if challenges is None:
                challenges = []
                
            # Get nearby recycling centers using default location
            recycling_centers = []
            user_location = user.get('location', None)
            
            if geo_service and user_location:
                try:
                    recycling_centers = geo_service.find_recycling_centers(
                        user_location.get('lat', 37.7749),  # Default to San Francisco
                        user_location.get('lng', -122.4194),
                        radius=10
                    )
                    
                    # Convert distance from km to miles
                    for center in recycling_centers:
                        if 'distance' in center:
                            # Convert km to miles (1 km = 0.621371 miles)
                            center['distance'] = center['distance'] * 0.621371
                except Exception as e:
                    app.logger.error(f"Error finding recycling centers: {e}", exc_info=True)
            
            # Get recent activity (mock data for now)
            recent_activity = []
            try:
                # Get recent scans
                scans = db.db.scans.find(
                    {"user_id": db.get_object_id(session['user_id'])},
                    sort=[("timestamp", -1)],
                    limit=5
                )
                
                for scan in scans:
                    recent_activity.append({
                        "date": scan.get("timestamp").strftime("%Y-%m-%d %H:%M") if scan.get("timestamp") else "Unknown",
                        "type": "Scan",
                        "details": f"Scanned {scan.get('waste_type', 'unknown item')}",
                        "points": scan.get("points_earned", 0)
                    })
            except Exception as e:
                app.logger.error(f"Error getting recent activity: {e}", exc_info=True)
                
            # If we have less than 5 items, add some mock data
            if len(recent_activity) < 5:
                recent_activity.append({
                    "date": "2023-01-15 10:30",
                    "type": "Challenge",
                    "details": "Completed 'First Steps' challenge",
                    "points": 50
                })
            
            return render_template('dashboard.html', 
                                  user=user, 
                                  stats=stats, 
                                  challenges=challenges,
                                  recycling_centers=recycling_centers,
                                  recent_activity=recent_activity)
        except Exception as e:
            app.logger.error(f"Dashboard error: {e}", exc_info=True)
            flash('Error loading dashboard. Please try again later.', 'error')
            return redirect(url_for('home'))

    @app.route('/scan')
    def scan():
        """Render scan page."""
        if 'user_id' not in session:
            flash('Please log in to use scanning features.', 'warning')
            return redirect(url_for('login'))
            
        return render_template('scan.html')

    @app.route('/api/upload_image', methods=['POST'])
    def upload_image():
        """Handle image upload and classification."""
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
            
        try:
            if 'image' not in request.files:
                return jsonify({'error': 'No image uploaded'}), 400
                
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No image selected'}), 400
                
            if not file or not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type. Please upload a valid image.'}), 400
            
            # Save uploaded file
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Create directory if it doesn't exist
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)
            
            app.logger.info(f"Saved image to {file_path}")
            
            # Get the classifier from app config - FIXED: use correct config key
            classifier = app.config.get('classifier')
            if not classifier:
                app.logger.error("Waste classifier not configured")
                # Return a default prediction for plastic bottles with high confidence
                mock_predictions = [
                    {"label": "plastic_bottle", "confidence": 0.95},
                    {"label": "plastic_container", "confidence": 0.45},
                    {"label": "glass_bottle", "confidence": 0.35}
                ]
                app.logger.warning("Using mock predictions as fallback")
                return jsonify({
                    'success': True,
                    'file_path': file_path,
                    'predictions': mock_predictions,
                    'top_prediction': mock_predictions[0],
                    'message': 'Using mock classification (classifier not available)'
                }), 200
                
            predictions = classifier.get_all_predictions(file_path)
            top_prediction = predictions[0] if predictions else None
            
            # Award points for scanning
            if 'user_id' in session and top_prediction:
                try:
                    points_system = app.config.get('points_system')
                    user_id = session['user_id']
                    
                    if points_system:
                        points_earned = points_system.award_scan_points(
                            user_id=user_id,
                            waste_type=top_prediction['label'],
                            image_path=file_path
                        )
                        app.logger.info(f"Awarded {points_earned} points to user {user_id} for scanning {top_prediction['label']}")
                    else:
                        app.logger.warning("Points system not configured")
                except Exception as e:
                    app.logger.error(f"Error awarding points: {e}", exc_info=True)
            
            # Return the predictions
            return jsonify({
                'success': True,
                'file_path': file_path,
                'predictions': predictions,
                'top_prediction': top_prediction
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error processing image upload: {e}", exc_info=True)
            return jsonify({'error': 'Error processing image. Please try again.'}), 500

    @app.route('/leaderboard')
    def leaderboard():
        """Render leaderboard page."""
        try:
            # Get database from app config
            db = app.config.get('database')
            if not db:
                app.logger.error("Database not configured")
                flash('Leaderboard service is currently unavailable.', 'error')
                users = []
            else:
                users = db.get_leaderboard(limit=10)
                
            # Get current user rank if logged in
            user_rank = None
            if 'user_id' in session and db:
                try:
                    user_id = session['user_id']
                    user_rank = db.get_user_rank(user_id)
                except Exception as e:
                    app.logger.error(f"Error getting user rank: {e}", exc_info=True)
            
            return render_template('leaderboard.html', users=users, user_rank=user_rank)
        except Exception as e:
            app.logger.error(f"Error loading leaderboard: {e}", exc_info=True)
            flash('Error loading leaderboard. Please try again later.', 'error')
            return render_template('leaderboard.html', users=[], user_rank=None)
            
    @app.route('/api/leaderboard')
    def api_leaderboard():
        """API endpoint for leaderboard data."""
        try:
            top_users = db.get_leaderboard(limit=10)
            return jsonify({
                'success': True,
                'leaderboard': top_users
            })
        except Exception as e:
            logger.error(f"Error fetching leaderboard: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Error loading leaderboard data'
            }), 500
            
    @app.route('/api/confirm_disposal', methods=['POST'])
    def confirm_disposal():
        """Handle waste disposal confirmation."""
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
            
        try:
            data = request.get_json()
            if not data or 'waste_type' not in data:
                return jsonify({'error': 'Missing waste type information'}), 400
                
            waste_type = data['waste_type']
            
            # Award points for proper disposal
            points_earned = 0
            try:
                points_system = app.config.get('points_system')
                user_id = session['user_id']
                
                if points_system:
                    points_earned = points_system.award_disposal_points(
                        user_id=user_id,
                        waste_type=waste_type
                    )
                    app.logger.info(f"Awarded {points_earned} points to user {user_id} for disposing {waste_type}")
            except Exception as e:
                app.logger.error(f"Error awarding disposal points: {e}", exc_info=True)
                
            return jsonify({
                'success': True,
                'message': 'Thank you for recycling responsibly!',
                'points_earned': points_earned
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error confirming disposal: {e}", exc_info=True)
            return jsonify({'error': 'Error processing your request. Please try again.'}), 500

    @app.route('/centers', methods=['GET', 'POST'])
    def centers():
        """Show recycling centers page"""
        # Default location - Massachusetts
        user_location = {"lat": 42.4072, "lon": -71.3824}
        address = None  # Initialize address variable
        search_error = None
        
        # Check if we're coming from a POST request (address search)
        if request.method == 'POST' and request.form.get('address'):
            address = request.form.get('address')
            logger.info(f"Searching for recycling centers near address: {address}")
            
            try:
                # Convert address to coordinates
                geo_service = GeolocationService()
                location_result = geo_service.get_location_from_address(address)
                
                if location_result:
                    # Update user location - handle tuple or dict return type
                    if isinstance(location_result, tuple) and len(location_result) == 2:
                        # Tuple format (lat, lon)
                        user_location = {"lat": location_result[0], "lon": location_result[1]}
                    elif isinstance(location_result, dict) and 'lat' in location_result and 'lon' in location_result:
                        # Dictionary format
                        user_location = location_result
                    
                    logger.info(f"Address converted to coordinates: {user_location}")
                    
                    # Store address in session for future reference
                    session['last_address'] = address
                    session['user_location'] = user_location
                else:
                    # Failed to geocode address
                    logger.warning(f"Failed to geocode address: {address}")
                    flash("Could not find the location you entered. Showing recycling centers in Massachusetts instead. Please use this format: street address, town, state, zip code (example: '12 River Road, Andover, MA 01810')", "warning")
                    search_error = "Using default Massachusetts location - your location could not be found"
                    # Use the default location
                    user_location = {"lat": 42.4072, "lon": -71.3824}  # Massachusetts
            except Exception as e:
                logger.error(f"Error in address search: {e}", exc_info=True)
                flash("An error occurred while searching. Please try again.", "danger")
                search_error = str(e)
        
        # Get address from URL parameter if present
        elif request.args.get('address'):
            address = request.args.get('address')
            logger.info(f"Searching for recycling centers near address from URL: {address}")
            
            try:
                # Convert address to coordinates
                geo_service = GeolocationService()
                location_result = geo_service.get_location_from_address(address)
                
                if location_result:
                    # Update user location - handle tuple or dict return type
                    if isinstance(location_result, tuple) and len(location_result) == 2:
                        # Tuple format (lat, lon)
                        user_location = {"lat": location_result[0], "lon": location_result[1]}
                    elif isinstance(location_result, dict) and 'lat' in location_result and 'lon' in location_result:
                        # Dictionary format
                        user_location = location_result
                    
                    logger.info(f"Address converted to coordinates: {user_location}")
                    
                    # Store address in session for future reference
                    session['last_address'] = address
                    session['user_location'] = user_location
                else:
                    # Failed to geocode address
                    logger.warning(f"Failed to geocode address: {address}")
                    flash("Could not find the location you entered. Showing recycling centers in Massachusetts instead. Please use this format: street address, town, state, zip code (example: '12 River Road, Andover, MA 01810')", "warning")
                    search_error = "Using default Massachusetts location - your location could not be found"
                    # Use the default location
                    user_location = {"lat": 42.4072, "lon": -71.3824}  # Massachusetts
            except Exception as e:
                logger.error(f"Error in address search: {e}", exc_info=True)
                flash("An error occurred while searching. Please try again.", "danger")
                search_error = str(e)
        
        # If not searching by address, use last known location if available
        elif session.get('user_location'):
            user_location = session.get('user_location')
            address = session.get('last_address')
            logger.info(f"Using session location: {user_location}")
        
        # Find recycling centers near the user's location
        geo_service = GeolocationService()
        centers = geo_service.find_recycling_centers(
            user_location['lat'], 
            user_location['lon']
        )
        
        logger.info(f"Found {len(centers)} recycling centers")
        
        return render_template(
            'centers.html', 
            centers=centers, 
            address=address,
            user_location=user_location,
            search_error=search_error,
            config=config
        )

    @app.route('/api/guidelines/<waste_type>', methods=['GET'])
    def get_recycling_guidelines(waste_type):
        """Get recycling guidelines for a specific waste type."""
        try:
            # Get database from app config
            db = app.config.get('database')
            if not db:
                app.logger.error("Database not configured")
                return jsonify({'error': 'Service temporarily unavailable'}), 503
                
            # Get guidelines from database
            guidelines = db.get_recycling_guidelines(waste_type)
            if not guidelines:
                # Define recyclable waste types
                recyclable_types = [
                    'plastic_bottle', 'glass_bottle', 'aluminum_can', 'paper',
                    'cardboard', 'plastic_container', 'metal', 'tetra_pak'
                ]
                
                # Provide basic guidelines if none found
                guidelines = {
                    'waste_type': waste_type,
                    'recyclable': waste_type in recyclable_types,
                    'preparation': 'Clean and remove labels if possible. Ensure item is empty and dry.',
                    'bin_color': 'blue' if waste_type in recyclable_types else 'black',
                    'facts': 'Recycling helps reduce landfill waste and conserves natural resources.'
                }
                
            return jsonify({
                'success': True,
                'guidelines': guidelines
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error getting recycling guidelines: {e}", exc_info=True)
            return jsonify({'error': 'Error retrieving guidelines. Please try again.'}), 500

    @app.route('/achievements')
    def achievements():
        """Render achievements page."""
        if 'user_id' not in session:
            return redirect(url_for('login'))
            
        if not check_db():
            flash('Service temporarily unavailable. Please try again later.', 'error')
            return redirect(url_for('home'))
            
        try:
            # Get user
            user = db.get_user(user_id=session['user_id'])
            if not user:
                flash('User not found', 'error')
                return redirect(url_for('logout'))
                
            # Get achievements (mock data for now)
            achievements = [
                {
                    'title': 'Recycling Rookie',
                    'description': 'Recycle your first item',
                    'completed': True,
                    'date_earned': '2023-01-15',
                    'icon': 'fa-recycle'
                },
                {
                    'title': 'Waste Warrior',
                    'description': 'Recycle 10 items',
                    'completed': False,
                    'progress': 6,
                    'goal': 10,
                    'icon': 'fa-shield'
                },
                {
                    'title': 'Earth Champion',
                    'description': 'Recycle 50 items',
                    'completed': False,
                    'progress': 6,
                    'goal': 50,
                    'icon': 'fa-globe'
                }
            ]
            
            return render_template('achievements.html', user=user, achievements=achievements)
        except Exception as e:
            app.logger.error(f"Error loading achievements: {e}", exc_info=True)
            flash('Error loading achievements. Please try again later.', 'error')
            return redirect(url_for('home'))
            
    @app.route('/recycling_centers')
    def recycling_centers():
        """Redirect to centers page."""
        return redirect(url_for('centers'))

    @app.route('/api/set_location', methods=['POST'])
    def set_location():
        """Set user's location."""
        try:
            data = request.get_json()
            if not data or 'lat' not in data or 'lng' not in data:
                return jsonify({'error': 'Missing location data'}), 400
                
            # Store location in session
            session['location'] = {
                'lat': data['lat'],
                'lng': data['lng']
            }
            
            # Update user's location in database if logged in
            if 'user_id' in session and db:
                try:
                    db.update_user_location(session['user_id'], data['lat'], data['lng'])
                except Exception as e:
                    app.logger.error(f"Error updating user location: {e}", exc_info=True)
            
            return jsonify({'success': True}), 200
            
        except Exception as e:
            app.logger.error(f"Error setting location: {e}", exc_info=True)
            return jsonify({'error': 'Error setting location. Please try again.'}), 500

    @app.route('/api/recycling-centers')
    def api_recycling_centers():
        """API endpoint for finding recycling centers."""
        try:
            lat = request.args.get('lat', type=float)
            lon = request.args.get('lon', type=float)
            waste_type = request.args.get('waste_type')
            
            if not lat or not lon:
                # Default to San Francisco if no coordinates provided
                lat = 37.7749
                lon = -122.4194
            
            # Get geolocation service
            geo_service = app.config.get('geo_service')
            
            if not geo_service:
                app.logger.error("Geolocation service not configured")
                return jsonify({
                    'success': False,
                    'message': 'Geolocation service unavailable',
                    'centers': []
                }), 503
            
            # Find recycling centers
            centers = geo_service.find_recycling_centers(
                lat=lat,
                lon=lon,
                waste_type=waste_type,
                radius=10
            )
            
            return jsonify({
                'success': True,
                'centers': centers
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error finding recycling centers: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Error finding recycling centers',
                'centers': []
            }), 500

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500 