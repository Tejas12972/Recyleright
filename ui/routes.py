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
from datetime import datetime, timedelta

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
            app.logger.debug(f"Retrieved user stats: {stats}")
            if not stats:
                app.logger.info("No stats found for user, creating default stats")
                stats = {
                    "user_id": session['user_id'],
                    "points": user.get('points', 0),
                    "level": user.get('level', 'Beginner'),
                    "rank": 1,
                    "next_level": "Intermediate",
                    "points_to_next_level": 100,
                    "level_progress": 0,
                    "items_scanned": 0
                }
            else:
                # Ensure items_scanned is populated
                if 'items_scanned' not in stats or stats['items_scanned'] is None:
                    app.logger.debug("items_scanned not in stats, adding default value")
                    stats['items_scanned'] = db.count_user_scans(session['user_id'])
                    app.logger.debug(f"Set items_scanned to {stats['items_scanned']}")
                
                # Calculate level progress percentage if not already set
                if 'level_progress' not in stats or stats['level_progress'] is None:
                    current_points = stats.get('points', 0)
                    points_to_next = stats.get('points_to_next_level', 100)
                    total_level_points = points_to_next + current_points  # Assuming linear progression
                    stats['level_progress'] = min(int((current_points / total_level_points) * 100), 99)
                    app.logger.debug(f"Calculated level_progress: {stats['level_progress']}%")
            
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
                    # Get points from the scan record or use the default from config
                    points_earned = scan.get("points_earned", 0)
                    
                    # If points_earned is 0 or not set, use the default value from config
                    if points_earned == 0:
                        import config
                        points_earned = config.POINTS_PER_SCAN
                        
                        # Add bonus for certain waste types (similar to how it's handled in points_system.py)
                        waste_type = scan.get('waste_type', '')
                        if waste_type in ["e_waste", "hazardous", "plastic_PVC", "plastic_PS"]:
                            points_earned += 5  # Additional points for hard-to-recycle materials
                    
                    recent_activity.append({
                        "date": scan.get("timestamp").strftime("%Y-%m-%d %H:%M") if scan.get("timestamp") else "Unknown",
                        "type": "Scan",
                        "details": f"Scanned {scan.get('waste_type', 'unknown item')}",
                        "points": points_earned
                    })
            except Exception as e:
                app.logger.error(f"Error getting recent activity: {e}", exc_info=True)
                
            # If we have less than 5 items, add some mock data
            if len(recent_activity) < 5:
                # Import config for consistent values
                import config
                
                # Add some realistic mock data with appropriate point values
                mock_activities = [
                    {
                        "date": "2023-01-15 10:30",
                        "type": "Challenge",
                        "details": "Completed 'First Steps' challenge",
                        "points": 50  # Challenges typically give more points
                    },
                    {
                        "date": "2023-01-10 15:45", 
                        "type": "Scan",
                        "details": "Scanned plastic_bottle",
                        "points": config.POINTS_PER_SCAN
                    },
                    {
                        "date": "2023-01-10 15:50",
                        "type": "Disposal",
                        "details": "Confirmed proper disposal of plastic_bottle",
                        "points": config.POINTS_PER_CORRECT_DISPOSAL
                    },
                    {
                        "date": "2023-01-05 09:20",
                        "type": "Scan",
                        "details": "Scanned e_waste",
                        "points": config.POINTS_PER_SCAN + 5  # Bonus for hard-to-recycle items
                    },
                    {
                        "date": "2023-01-05 09:25",
                        "type": "Achievement",
                        "details": "Earned 'Eco Warrior' badge",
                        "points": 30
                    }
                ]
                
                # Add enough mock activities to reach 5 total items
                needed_items = 5 - len(recent_activity)
                recent_activity.extend(mock_activities[:needed_items])
            
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

    @app.route('/scan/upload', methods=['POST'])
    def scan_upload():
        """Handle image upload for scanning."""
        if 'user_id' not in session:
            app.logger.warning("Scan upload without authentication")
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        app.logger.info("Received scan upload request")
        
        # Check if the post request has the file part
        if 'file' not in request.files:
            app.logger.warning("No file part in scan upload request")
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['file']
        
        app.logger.debug(f"Received scan file: {file.filename}, size: {file.content_length if hasattr(file, 'content_length') else 'unknown'}")
        
        # If user does not select file, browser also submits an empty part
        if file.filename == '':
            app.logger.warning("Empty filename in scan upload")
            return jsonify({'success': False, 'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            # Create a unique filename
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']))
            os.makedirs(user_folder, exist_ok=True)
            filepath = os.path.join(user_folder, filename)
            
            # Save the file
            file.save(filepath)
            app.logger.info(f"Saved scan image to {filepath}")
            
            # Try to use GPT-4o image analyzer first, fall back to classifier if not available
            try:
                # Import the GPT analyzer
                from api.gpt_analyzer import GPTImageAnalyzer
                
                # Initialize the GPT analyzer
                gpt_analyzer = None
                try:
                    gpt_analyzer = GPTImageAnalyzer()
                    app.logger.info("Successfully initialized GPT-4o image analyzer")
                except Exception as e:
                    app.logger.warning(f"Could not initialize GPT-4o analyzer: {e}. Will fall back to classifier.")
                
                # If GPT analyzer is available, use it
                if gpt_analyzer:
                    app.logger.info("Analyzing image with GPT-4o")
                    analysis_result = gpt_analyzer.analyze_image(filepath)
                    
                    # Check if analysis was successful
                    if 'error' in analysis_result and analysis_result['error']:
                        app.logger.error(f"GPT-4o analysis error: {analysis_result['error']}")
                        raise Exception(f"GPT analysis failed: {analysis_result['error']}")
                    
                    # Extract waste type from analysis
                    waste_type = analysis_result.get('waste_type', 'mixed')
                    
                    # Map waste_type to label format expected by the application
                    label_mapping = {
                        'recyclable': 'plastic_bottle',  # Default recyclable type
                        'compostable': 'food_waste',
                        'trash': 'styrofoam',
                        'mixed': 'plastic_container',
                        'unknown': 'plastic_container'
                    }
                    
                    # Find more specific label if available in material composition
                    materials = analysis_result.get('material_composition', [])
                    for material in materials:
                        material_lower = material.lower()
                        if 'aluminum' in material_lower or 'metal' in material_lower:
                            label_mapping['recyclable'] = 'aluminum_can' if 'can' in material_lower else 'metal'
                            break
                        elif 'plastic' in material_lower and 'bottle' in material_lower:
                            label_mapping['recyclable'] = 'plastic_bottle'
                            break
                        elif 'plastic' in material_lower and 'container' in material_lower:
                            label_mapping['recyclable'] = 'plastic_container'
                            break
                        elif 'glass' in material_lower:
                            label_mapping['recyclable'] = 'glass_bottle'
                            break
                        elif 'paper' in material_lower:
                            label_mapping['recyclable'] = 'paper'
                            break
                        elif 'cardboard' in material_lower:
                            label_mapping['recyclable'] = 'cardboard'
                            break
                    
                    # Create a prediction in the format expected by the application
                    top_prediction = {
                        'label': label_mapping.get(waste_type, 'plastic_container'),
                        'confidence': 0.95  # High confidence since GPT-4o is more reliable
                    }
                    
                    # Create additional predictions for UI display
                    predictions = [top_prediction]
                    for material in materials[:2]:  # Add up to 2 additional materials
                        material_lower = material.lower()
                        for waste_label in label_mapping.values():
                            if waste_label != top_prediction['label']:
                                predictions.append({
                                    'label': waste_label,
                                    'confidence': 0.45  # Lower confidence for secondary predictions
                                })
                                break
                    
                    # Add more variety if needed
                    while len(predictions) < 3:
                        for waste_label in label_mapping.values():
                            if all(p['label'] != waste_label for p in predictions):
                                predictions.append({
                                    'label': waste_label,
                                    'confidence': 0.35  # Even lower confidence
                                })
                                break
                    
                    # Record scan and award points
                    scan_id = None
                    points_earned = 0
                    
                    if 'user_id' in session:
                        db = app.config.get('database')
                        points_system = app.config.get('points_system')
                        
                        # Get user location
                        location = None
                        if db:
                            user = db.get_user(user_id=session['user_id'])
                            if user and user.get('location_lat') and user.get('location_lon'):
                                location = (user['location_lat'], user['location_lon'])
                        
                        # Record scan in database
                        if db:
                            app.logger.info("Recording scan in database")
                            scan_id = db.record_scan(
                                user_id=session['user_id'],
                                waste_type=top_prediction['label'],
                                confidence=top_prediction['confidence'],
                                image_path=filepath,
                                location=location
                            )
                        
                        # Award points
                        if points_system:
                            app.logger.info(f"Awarding points for scan to user {session['user_id']}")
                            points_earned = points_system.award_scan_points(
                                user_id=session['user_id'],
                                waste_type=top_prediction['label'],
                                image_path=filepath
                            )
                    
                    # Prepare response with GPT analysis data
                    response = {
                        'success': True,
                        'file_path': filepath,
                        'predictions': predictions,
                        'top_prediction': top_prediction,
                        'item_name': top_prediction['label'].replace('_', ' ').title(),
                        'scan_id': scan_id,
                        'points_earned': points_earned,
                        'gpt_analysis': {
                            'material_composition': analysis_result.get('material_composition', []),
                            'recyclability': analysis_result.get('recyclability', []),
                            'disposal_suggestions': analysis_result.get('disposal_suggestions', []),
                            'waste_type': waste_type
                        }
                    }
                    
                    app.logger.debug(f"Returning GPT-4o scan response: {response}")
                    return jsonify(response), 200
            
            except Exception as e:
                app.logger.warning(f"Error using GPT-4o analyzer, falling back to classifier: {e}", exc_info=True)
            
            # Fall back to the classifier if GPT-4o failed
            # Get the classifier
            classifier = app.config.get('classifier')
            
            if not classifier:
                app.logger.error("Waste classifier not configured for scan")
                # Return mock predictions if classifier is not available
                mock_predictions = [
                    {"label": "plastic_bottle", "confidence": 0.95},
                    {"label": "plastic_container", "confidence": 0.45},
                    {"label": "glass_bottle", "confidence": 0.35}
                ]
                app.logger.warning("Using mock predictions for scan upload")
                
                response = {
                    'success': True,
                    'file_path': filepath,
                    'predictions': mock_predictions,
                    'top_prediction': mock_predictions[0],
                    'item_name': mock_predictions[0]['label'].replace('_', ' ').title(),
                    'scan_id': str(uuid.uuid4()),
                    'message': 'Using mock classification (classifier not available)'
                }
                
                app.logger.debug(f"Returning mock scan response: {response}")
                return jsonify(response), 200
            
            # Process the image with the classifier
            app.logger.info("Getting predictions from classifier for scan")
            try:
                # Get predictions
                predictions = classifier.get_all_predictions(filepath)
                top_prediction = predictions[0] if predictions else None
                
                # Record scan and award points if prediction was successful
                scan_id = None
                points_earned = 0
                
                if top_prediction and 'user_id' in session:
                    db = app.config.get('database')
                    points_system = app.config.get('points_system')
                    
                    # Get user location
                    location = None
                    if db:
                        user = db.get_user(user_id=session['user_id'])
                        if user and user.get('location_lat') and user.get('location_lon'):
                            location = (user['location_lat'], user['location_lon'])
                    
                    # Record scan in database
                    if db:
                        app.logger.info("Recording scan in database")
                        scan_id = db.record_scan(
                            user_id=session['user_id'],
                            waste_type=top_prediction['label'],
                            confidence=top_prediction['confidence'],
                            image_path=filepath,
                            location=location
                        )
                    
                    # Award points
                    if points_system:
                        app.logger.info(f"Awarding points for scan to user {session['user_id']}")
                        points_earned = points_system.award_scan_points(
                            user_id=session['user_id'],
                            waste_type=top_prediction['label'],
                            image_path=filepath
                        )
                
                # Prepare response
                response = {
                    'success': True,
                    'file_path': filepath,
                    'predictions': predictions,
                    'top_prediction': top_prediction,
                    'item_name': top_prediction['label'].replace('_', ' ').title() if top_prediction else 'Unknown Item',
                    'scan_id': scan_id,
                    'points_earned': points_earned
                }
                
                app.logger.debug(f"Returning scan response: {response}")
                return jsonify(response), 200
                
            except Exception as e:
                app.logger.error(f"Error processing scan image: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': 'Error processing image. Please try again.'
                }), 500
        
        app.logger.warning(f"Invalid file type in scan upload: {file.filename}")
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400
    
    @app.route('/scan/camera', methods=['POST'])
    def scan_camera():
        """Handle camera capture for scanning."""
        if 'user_id' not in session:
            app.logger.warning("Scan camera without authentication")
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        app.logger.info("Received scan camera request")
        
        try:
            # Get JSON data 
            data = request.get_json()
            
            if not data or 'image' not in data:
                app.logger.warning("No image data in scan camera request")
                return jsonify({'success': False, 'error': 'No image data'}), 400
            
            app.logger.debug("Received camera image data")
            
            # Get base64 image data
            image_b64 = data['image']
            if image_b64.startswith('data:image'):
                image_b64 = image_b64.split(',')[1]
            
            # Decode base64 data
            import base64
            import numpy as np
            import cv2
            from io import BytesIO
            
            image_data = base64.b64decode(image_b64)
            
            # Create unique filename and save
            filename = f"{uuid.uuid4()}_camera.jpg"
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']))
            os.makedirs(user_folder, exist_ok=True)
            filepath = os.path.join(user_folder, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            app.logger.info(f"Saved camera image to {filepath}")
            
            # Try to use GPT-4o image analyzer first, fall back to classifier if not available
            try:
                # Import the GPT analyzer
                from api.gpt_analyzer import GPTImageAnalyzer
                
                # Initialize the GPT analyzer
                gpt_analyzer = None
                try:
                    gpt_analyzer = GPTImageAnalyzer()
                    app.logger.info("Successfully initialized GPT-4o image analyzer")
                except Exception as e:
                    app.logger.warning(f"Could not initialize GPT-4o analyzer: {e}. Will fall back to classifier.")
                
                # If GPT analyzer is available, use it
                if gpt_analyzer:
                    app.logger.info("Analyzing camera image with GPT-4o")
                    analysis_result = gpt_analyzer.analyze_image(filepath)
                    
                    # Check if analysis was successful
                    if 'error' in analysis_result and analysis_result['error']:
                        app.logger.error(f"GPT-4o analysis error: {analysis_result['error']}")
                        raise Exception(f"GPT analysis failed: {analysis_result['error']}")
                    
                    # Extract waste type from analysis
                    waste_type = analysis_result.get('waste_type', 'mixed')
                    
                    # Map waste_type to label format expected by the application
                    label_mapping = {
                        'recyclable': 'plastic_bottle',  # Default recyclable type
                        'compostable': 'food_waste',
                        'trash': 'styrofoam',
                        'mixed': 'plastic_container',
                        'unknown': 'plastic_container'
                    }
                    
                    # Find more specific label if available in material composition
                    materials = analysis_result.get('material_composition', [])
                    for material in materials:
                        material_lower = material.lower()
                        if 'aluminum' in material_lower or 'metal' in material_lower:
                            label_mapping['recyclable'] = 'aluminum_can' if 'can' in material_lower else 'metal'
                            break
                        elif 'plastic' in material_lower and 'bottle' in material_lower:
                            label_mapping['recyclable'] = 'plastic_bottle'
                            break
                        elif 'plastic' in material_lower and 'container' in material_lower:
                            label_mapping['recyclable'] = 'plastic_container'
                            break
                        elif 'glass' in material_lower:
                            label_mapping['recyclable'] = 'glass_bottle'
                            break
                        elif 'paper' in material_lower:
                            label_mapping['recyclable'] = 'paper'
                            break
                        elif 'cardboard' in material_lower:
                            label_mapping['recyclable'] = 'cardboard'
                            break
                    
                    # Create a prediction in the format expected by the application
                    top_prediction = {
                        'label': label_mapping.get(waste_type, 'plastic_container'),
                        'confidence': 0.95  # High confidence since GPT-4o is more reliable
                    }
                    
                    # Create additional predictions for UI display
                    predictions = [top_prediction]
                    for material in materials[:2]:  # Add up to 2 additional materials
                        material_lower = material.lower()
                        for waste_label in label_mapping.values():
                            if waste_label != top_prediction['label']:
                                predictions.append({
                                    'label': waste_label,
                                    'confidence': 0.45  # Lower confidence for secondary predictions
                                })
                                break
                    
                    # Add more variety if needed
                    while len(predictions) < 3:
                        for waste_label in label_mapping.values():
                            if all(p['label'] != waste_label for p in predictions):
                                predictions.append({
                                    'label': waste_label,
                                    'confidence': 0.35  # Even lower confidence
                                })
                                break
                    
                    # Record scan and award points
                    scan_id = None
                    points_earned = 0
                    
                    if 'user_id' in session:
                        db = app.config.get('database')
                        points_system = app.config.get('points_system')
                        
                        # Get user location
                        location = None
                        if db:
                            user = db.get_user(user_id=session['user_id'])
                            if user and user.get('location_lat') and user.get('location_lon'):
                                location = (user['location_lat'], user['location_lon'])
                        
                        # Record scan in database
                        if db:
                            app.logger.info("Recording camera scan in database")
                            scan_id = db.record_scan(
                                user_id=session['user_id'],
                                waste_type=top_prediction['label'],
                                confidence=top_prediction['confidence'],
                                image_path=filepath,
                                location=location
                            )
                        
                        # Award points
                        if points_system:
                            app.logger.info(f"Awarding points for camera scan to user {session['user_id']}")
                            points_earned = points_system.award_scan_points(
                                user_id=session['user_id'],
                                waste_type=top_prediction['label'],
                                image_path=filepath
                            )
                    
                    # Prepare response with GPT analysis data
                    response = {
                        'success': True,
                        'file_path': filepath,
                        'predictions': predictions,
                        'top_prediction': top_prediction,
                        'item_name': top_prediction['label'].replace('_', ' ').title(),
                        'scan_id': scan_id,
                        'points_earned': points_earned,
                        'gpt_analysis': {
                            'material_composition': analysis_result.get('material_composition', []),
                            'recyclability': analysis_result.get('recyclability', []),
                            'disposal_suggestions': analysis_result.get('disposal_suggestions', []),
                            'waste_type': waste_type
                        }
                    }
                    
                    app.logger.debug(f"Returning GPT-4o camera scan response: {response}")
                    return jsonify(response), 200
            
            except Exception as e:
                app.logger.warning(f"Error using GPT-4o analyzer for camera scan, falling back to classifier: {e}", exc_info=True)
            
            # Convert to OpenCV format for processing
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Get the classifier
            classifier = app.config.get('classifier')
            
            if not classifier or img is None:
                app.logger.error(f"Classifier not configured or invalid image: classifier={classifier is not None}, image={'valid' if img is not None else 'invalid'}")
                # Return mock predictions if classifier is not available
                mock_predictions = [
                    {"label": "plastic_bottle", "confidence": 0.95},
                    {"label": "plastic_container", "confidence": 0.45},
                    {"label": "glass_bottle", "confidence": 0.35}
                ]
                app.logger.warning("Using mock predictions for camera scan")
                
                response = {
                    'success': True,
                    'file_path': filepath,
                    'predictions': mock_predictions,
                    'top_prediction': mock_predictions[0],
                    'item_name': mock_predictions[0]['label'].replace('_', ' ').title(),
                    'scan_id': str(uuid.uuid4()),
                    'message': 'Using mock classification (classifier not available)'
                }
                
                app.logger.debug(f"Returning mock camera scan response: {response}")
                return jsonify(response), 200
            
            # Process the image with the classifier
            app.logger.info("Getting predictions from classifier for camera scan")
            try:
                # Get predictions from preprocessing the image directly
                predictions = classifier.get_predictions_from_array(img)
                top_prediction = predictions[0] if predictions else None
                
                # Record scan and award points if prediction was successful
                scan_id = None
                points_earned = 0
                
                if top_prediction and 'user_id' in session:
                    db = app.config.get('database')
                    points_system = app.config.get('points_system')
                    
                    # Get user location
                    location = None
                    if db:
                        user = db.get_user(user_id=session['user_id'])
                        if user and user.get('location_lat') and user.get('location_lon'):
                            location = (user['location_lat'], user['location_lon'])
                    
                    # Record scan in database
                    if db:
                        app.logger.info("Recording camera scan in database")
                        scan_id = db.record_scan(
                            user_id=session['user_id'],
                            waste_type=top_prediction['label'],
                            confidence=top_prediction['confidence'],
                            image_path=filepath,
                            location=location
                        )
                    
                    # Award points
                    if points_system:
                        app.logger.info(f"Awarding points for camera scan to user {session['user_id']}")
                        points_earned = points_system.award_scan_points(
                            user_id=session['user_id'],
                            waste_type=top_prediction['label'],
                            image_path=filepath
                        )
                
                # Prepare response
                response = {
                    'success': True,
                    'file_path': filepath,
                    'predictions': predictions,
                    'top_prediction': top_prediction,
                    'item_name': top_prediction['label'].replace('_', ' ').title() if top_prediction else 'Unknown Item',
                    'scan_id': scan_id,
                    'points_earned': points_earned
                }
                
                app.logger.debug(f"Returning camera scan response: {response}")
                return jsonify(response), 200
                
            except Exception as e:
                app.logger.error(f"Error processing camera scan image: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': 'Error processing image. Please try again.'
                }), 500
                
        except Exception as e:
            app.logger.error(f"Error in camera scan: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'An error occurred processing the camera image.'
            }), 500

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
            app.logger.warning("API call without authentication")
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
        try:
            app.logger.info("Received disposal confirmation request")
            data = request.get_json()
            app.logger.debug(f"Request data: {data}")
            
            if not data or 'waste_type' not in data:
                app.logger.warning("Missing waste_type in request")
                return jsonify({'success': False, 'error': 'Missing waste type information'}), 400
                
            waste_type = data['waste_type']
            scan_id = data.get('scan_id')
            app.logger.info(f"Confirming disposal of {waste_type} (scan_id: {scan_id})")
            
            # Award points for proper disposal
            points_earned = 0
            try:
                points_system = app.config.get('points_system')
                user_id = session['user_id']
                
                if points_system:
                    app.logger.info(f"Awarding disposal points to user {user_id}")
                    points_earned = points_system.award_disposal_points(
                        user_id=user_id,
                        waste_type=waste_type,
                        scan_id=scan_id
                    )
                    app.logger.info(f"Awarded {points_earned} points to user {user_id} for disposing {waste_type}")
                else:
                    app.logger.warning("Points system not configured")
            except Exception as e:
                app.logger.error(f"Error awarding disposal points: {e}", exc_info=True)
                
            response = {
                'success': True,
                'message': 'Thank you for recycling responsibly!',
                'points_earned': points_earned
            }
            app.logger.debug(f"Returning response: {response}")
            return jsonify(response), 200
            
        except Exception as e:
            app.logger.error(f"Error confirming disposal: {e}", exc_info=True)
            error_response = {
                'success': False,
                'error': 'Error processing your request. Please try again.'
            }
            app.logger.debug(f"Returning error response: {error_response}")
            return jsonify(error_response), 500

    @app.route('/centers', methods=['GET', 'POST'])
    def centers():
        """Show recycling centers page"""
        # Default location - Massachusetts
        user_location = {"lat": 42.4072, "lon": -71.3824}
        address = None  # Initialize address variable
        search_error = None
        radius = request.form.get('radius', '25')  # Default radius 25 miles if not specified
        
        # Also check for radius in URL parameters
        if request.args.get('radius'):
            radius = request.args.get('radius')
        
        # Convert radius to integer (default to 25 if conversion fails)
        try:
            radius_miles = int(radius)
        except (ValueError, TypeError):
            radius_miles = 25
        
        # Convert miles to kilometers for the API
        radius_km = radius_miles * 1.60934
        
        # Check if we're coming from a POST request (address search)
        if request.method == 'POST' and request.form.get('address'):
            address = request.form.get('address')
            logger.info(f"Searching for recycling centers near address: {address} within {radius_miles} miles")
            
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
                    session['radius'] = radius  # Store radius in session
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
            logger.info(f"Searching for recycling centers near address from URL: {address} within {radius_miles} miles")
            
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
                    session['radius'] = radius  # Store radius in session
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
            # Get radius from session if available
            if session.get('radius'):
                radius = session.get('radius')
                try:
                    radius_miles = int(radius)
                    radius_km = radius_miles * 1.60934
                except (ValueError, TypeError):
                    pass
            logger.info(f"Using session location: {user_location} with radius: {radius_miles} miles")
        
        # Find recycling centers near the user's location
        geo_service = GeolocationService()
        centers = geo_service.find_recycling_centers(
            user_location['lat'], 
            user_location['lon'],
            radius=radius_km  # Pass the radius in kilometers
        )
        
        logger.info(f"Found {len(centers)} recycling centers within {radius_miles} miles")
        
        # Convert km distances to miles for display
        for center in centers:
            if 'distance' in center:
                # Convert kilometers to miles (1 km = 0.621371 miles)
                center['distance'] = center['distance'] * 0.621371
        
        return render_template(
            'centers.html', 
            centers=centers, 
            address=address,
            user_location=user_location,
            search_error=search_error,
            radius=radius_miles,
            config=config
        )

    @app.route('/api/guidelines/<waste_type>', methods=['GET'])
    def get_recycling_guidelines(waste_type):
        """Get recycling guidelines for a specific waste type."""
        try:
            app.logger.info(f"Getting recycling guidelines for waste type: {waste_type}")
            
            # Get database from app config
            db = app.config.get('database')
            if not db:
                app.logger.error("Database not configured")
                return jsonify({'success': False, 'error': 'Service temporarily unavailable'}), 503
                
            # Get guidelines from database
            app.logger.debug(f"Fetching guidelines from database for: {waste_type}")
            guidelines = db.get_recycling_guidelines(waste_type)
            app.logger.debug(f"Guidelines from database: {guidelines}")
            
            if not guidelines:
                app.logger.info(f"No guidelines found for {waste_type}, using defaults")
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
                
            response = {
                'success': True,
                'guidelines': guidelines
            }
            app.logger.debug(f"Returning guidelines response: {response}")
            return jsonify(response), 200
            
        except Exception as e:
            app.logger.error(f"Error getting recycling guidelines: {e}", exc_info=True)
            error_response = {
                'success': False,
                'error': 'Error retrieving guidelines. Please try again.'
            }
            app.logger.debug(f"Returning error response: {error_response}")
            return jsonify(error_response), 500

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
            
            # Get user stats with items_scanned and rank
            stats = db.get_user_stats(session['user_id'])
            app.logger.debug(f"Retrieved user stats for achievements: {stats}")
            if not stats:
                app.logger.info("No stats found for user achievements, creating default stats")
                stats = {
                    "user_id": session['user_id'],
                    "points": user.get('points', 0),
                    "level": user.get('level', 'Beginner'),
                    "rank": 1,
                    "next_level": "Intermediate",
                    "points_to_next_level": 100,
                    "level_progress": 0,
                    "items_scanned": db.count_user_scans(session['user_id'])
                }
            else:
                # Ensure items_scanned is populated
                if 'items_scanned' not in stats or stats['items_scanned'] is None:
                    app.logger.debug("items_scanned not in stats, adding from scan count")
                    stats['items_scanned'] = db.count_user_scans(session['user_id'])
                    app.logger.debug(f"Set items_scanned to {stats['items_scanned']}")
                
            # Get achievements (mock data for now)
            achievements = [
                {
                    'title': 'Recycling Rookie',
                    'description': 'Recycle your first item',
                    'completed': True,
                    'date_earned': datetime.now().strftime('%Y-%m-%d'),
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
                },
                {
                    'title': 'Material Master',
                    'description': 'Recycle 5 different types of materials',
                    'completed': True,
                    'date_earned': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'icon': 'fa-award'
                },
                {
                    'title': 'Consistent Recycler',
                    'description': 'Recycle items for 7 consecutive days',
                    'completed': False,
                    'progress': 3,
                    'goal': 7,
                    'icon': 'fa-calendar-check'
                }
            ]
            
            return render_template('achievements.html', user=user, achievements=achievements, stats=stats)
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
                    # Fix the method call - it takes 3 args (self, user_id, location_dict)
                    location_dict = {'lat': data['lat'], 'lng': data['lng']}
                    db.update_user_location(session['user_id'], location_dict)
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
            app.logger.info("Received request for recycling centers")
            lat = request.args.get('lat', type=float)
            lon = request.args.get('lon', type=float)
            waste_type = request.args.get('waste_type')
            
            app.logger.debug(f"Parameters: lat={lat}, lon={lon}, waste_type={waste_type}")
            
            if not lat or not lon:
                app.logger.warning("No coordinates provided, using defaults")
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
            app.logger.info(f"Finding recycling centers near {lat}, {lon} for {waste_type or 'all waste types'}")
            try:
                centers = geo_service.find_recycling_centers(
                    lat=lat,
                    lon=lon,
                    waste_type=waste_type,
                    radius=10
                )
                app.logger.info(f"Found {len(centers)} recycling centers")
                app.logger.debug(f"Centers: {centers[:2]}..." if centers and len(centers) > 2 else f"Centers: {centers}")
            except Exception as e:
                app.logger.error(f"Error in geo_service.find_recycling_centers: {e}", exc_info=True)
                centers = []
            
            response = {
                'success': True,
                'centers': centers
            }
            
            return jsonify(response), 200
            
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