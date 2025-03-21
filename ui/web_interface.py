"""
Web-based user interface for RecycleRight application.
"""

import logging
import os
import sys
import json
import base64
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from dotenv import load_dotenv

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import config using importlib to avoid circular imports
import importlib.util
spec = importlib.util.spec_from_file_location("config", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app/config.py"))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Now import the rest of the modules
from models.waste_classifier import WasteClassifier
from data.database import get_db
from data.recycling_guidelines import RecyclingGuidelines
from api.geolocation import GeolocationService
from gamification.points_system import PointsSystem
from gamification.challenges import ChallengeSystem

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__, 
    static_folder="static",
    template_folder="templates",
    static_url_path="")

# Enable CORS for development
CORS(app)

# Set secret key from environment variable
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# Initialize components
classifier = WasteClassifier(config.MODEL_PATH, config.LABELS_PATH)
guidelines = RecyclingGuidelines(get_db())
geo_service = GeolocationService()
points_system = PointsSystem(get_db())
challenges = ChallengeSystem(get_db())

# File upload settings
UPLOAD_FOLDER = os.path.join(config.ASSETS_DIR, "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        user = db.get_user(username=username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('register.html')
        
        db = get_db()
        
        # Check if username already exists
        existing_user = db.get_user(username=username)
        if existing_user:
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        # Hash password and create user
        password_hash = generate_password_hash(password)
        user_id = db.add_user(username=username, email=email, password_hash=password_hash)
        
        if user_id:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """Render the user dashboard."""
    if 'user_id' not in session:
        flash('Please log in to access the dashboard', 'warning')
        return redirect(url_for('login'))
    
    db = get_db()
    user = db.get_user(user_id=session['user_id'])
    
    # Get user stats
    stats = points_system.get_user_stats(user['id'])
    
    # Get active challenges
    active_challenges = challenges.get_user_active_challenges(user['id'])
    
    # Get recent scans
    recent_scans = get_recent_scans(user['id'])
    
    return render_template(
        'dashboard.html',
        user=user,
        stats=stats,
        challenges=active_challenges,
        recent_scans=recent_scans
    )

@app.route('/scan', methods=['GET'])
def scan_page():
    """Render the scan page."""
    if 'user_id' not in session:
        flash('Please log in to access the scanner', 'warning')
        return redirect(url_for('login'))
    
    return render_template('scan.html')

@app.route('/scan/upload', methods=['POST'])
def scan_upload():
    """Handle image upload for scanning."""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # If user does not select file, browser also submits an empty part
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']))
        os.makedirs(user_folder, exist_ok=True)
        
        # Add timestamp to filename to avoid collisions
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(user_folder, filename)
        file.save(filepath)
        
        # Process the image
        result = process_image(filepath)
        
        return jsonify(result)
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/scan/camera', methods=['POST'])
def scan_camera():
    """Handle camera capture for scanning."""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    # Get base64 image data
    data = request.get_json()
    
    if not data or 'image' not in data:
        return jsonify({'error': 'No image data'}), 400
    
    # Get base64 string and convert to image
    image_b64 = data['image'].split(',')[1]
    image_data = base64.b64decode(image_b64)
    
    # Save image to file
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']))
    os.makedirs(user_folder, exist_ok=True)
    
    filename = f"{timestamp}_camera.jpg"
    filepath = os.path.join(user_folder, filename)
    
    with open(filepath, 'wb') as f:
        f.write(image_data)
    
    # Convert to OpenCV format
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Process the image
    result = process_image(filepath, img)
    
    return jsonify(result)

def process_image(filepath, img=None):
    """
    Process an image to identify waste type and get recycling guidelines.
    
    Args:
        filepath (str): Path to the image file
        img (numpy.ndarray, optional): Image array if already loaded
        
    Returns:
        dict: Result with waste type, confidence, and guidelines
    """
    try:
        # Load image if not provided
        if img is None:
            img = cv2.imread(filepath)
        
        if img is None:
            logger.error(f"Failed to load image: {filepath}")
            return {'error': 'Failed to load image'}
        
        # Get coordinates from user location (from session or database)
        user_id = session['user_id']
        db = get_db()
        user = db.get_user(user_id=user_id)
        
        location = None
        if user.get('location_lat') and user.get('location_lon'):
            location = (user['location_lat'], user['location_lon'])
        
        # Get waste classification
        waste_type, confidence = classifier.get_top_prediction(img)
        
        if not waste_type:
            return {
                'success': False,
                'message': 'Could not identify the waste type with sufficient confidence'
            }
        
        # Record scan in database
        scan_id = db.record_scan(
            user_id=user_id,
            waste_type=waste_type,
            confidence=confidence,
            image_path=filepath,
            location=location
        )
        
        # Award points for scan
        points = points_system.award_points_for_scan(
            user_id=user_id,
            scan_id=scan_id,
            waste_type=waste_type,
            confidence=confidence
        )
        
        # Get region code based on location
        region = "default"
        if location:
            region = geo_service.get_region_from_location(location[0], location[1])
        
        # Get recycling guidelines
        recycling_info = guidelines.get_disposal_instructions(waste_type, region)
        
        # Update challenges progress
        challenges.update_challenge_progress(
            user_id=user_id,
            goal_type="scan_count"
        )
        
        challenges.update_challenge_progress(
            user_id=user_id,
            goal_type="scan_type",
            waste_type=waste_type
        )
        
        # Get nearby recycling centers if location is available
        recycling_centers = []
        if location:
            centers = geo_service.find_recycling_centers(
                db, location[0], location[1], waste_type
            )
            recycling_centers = centers[:3] if centers else []
        
        # Check for new achievements
        new_achievements = challenges.check_achievements(user_id)
        
        # Create final result
        result = {
            'success': True,
            'waste_type': waste_type,
            'confidence': float(confidence),
            'points_earned': points,
            'scan_id': scan_id,
            'guidelines': recycling_info,
            'centers': recycling_centers,
            'new_achievements': new_achievements
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        return {'error': f'Error processing image: {str(e)}'}

@app.route('/confirm-disposal', methods=['POST'])
def confirm_disposal():
    """Confirm that a waste item was properly disposed."""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    data = request.get_json()
    
    if not data or 'scan_id' not in data or 'waste_type' not in data:
        return jsonify({'error': 'Missing required data'}), 400
    
    scan_id = data['scan_id']
    waste_type = data['waste_type']
    
    # Award points for correct disposal
    points = points_system.award_points_for_correct_disposal(
        user_id=session['user_id'],
        waste_type=waste_type
    )
    
    # Update challenges progress
    challenges.update_challenge_progress(
        user_id=session['user_id'],
        goal_type="recycle_type",
        waste_type=waste_type
    )
    
    # Check for new achievements
    new_achievements = challenges.check_achievements(session['user_id'])
    
    return jsonify({
        'success': True,
        'points_earned': points,
        'new_achievements': new_achievements
    })

@app.route('/leaderboard')
def leaderboard():
    """Display the leaderboard."""
    if 'user_id' not in session:
        flash('Please log in to view the leaderboard', 'warning')
        return redirect(url_for('login'))
    
    # Get leaderboard data
    board = points_system.get_leaderboard(limit=10)
    
    # Get user's stats
    stats = points_system.get_user_stats(session['user_id'])
    
    return render_template('leaderboard.html', leaderboard=board, user_stats=stats)

@app.route('/achievements')
def achievements():
    """Display user achievements."""
    if 'user_id' not in session:
        flash('Please log in to view achievements', 'warning')
        return redirect(url_for('login'))
    
    # Get user achievements
    user_achievements = challenges.get_user_achievements(session['user_id'])
    
    return render_template('achievements.html', achievements=user_achievements)

@app.route('/centers')
def centers():
    """Display nearby recycling centers."""
    if 'user_id' not in session:
        flash('Please log in to view recycling centers', 'warning')
        return redirect(url_for('login'))
    
    db = get_db()
    user = db.get_user(user_id=session['user_id'])
    
    centers = []
    if user.get('location_lat') and user.get('location_lon'):
        location = (user['location_lat'], user['location_lon'])
        centers = db.get_nearby_recycling_centers(
            location[0], location[1], 
            radius_km=config.RECYCLING_CENTERS_RADIUS
        )
    
    return render_template('centers.html', centers=centers, user_location=user.get('location'))

def get_recent_scans(user_id, limit=5):
    """Get recent scans for a user."""
    db = get_db()
    
    # This would need to be implemented in the database class
    # For now, we'll return a dummy result
    return []

@app.route('/update-location', methods=['POST'])
def update_location():
    """Update user location."""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    data = request.get_json()
    
    if not data or 'lat' not in data or 'lon' not in data:
        return jsonify({'error': 'Missing coordinates'}), 400
    
    lat = float(data['lat'])
    lon = float(data['lon'])
    
    db = get_db()
    result = db.update_user_location(session['user_id'], (lat, lon))
    
    if result:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update location'}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Development server
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False') == 'True',
            host=os.environ.get('FLASK_HOST', '0.0.0.0'),
            port=int(os.environ.get('FLASK_PORT', 5000))) 