# RecycleRight

RecycleRight is an AI-powered waste sorting assistant that helps users identify waste items, provides guidance on proper disposal, and locates nearby recycling centers.

## Overview

RecycleRight uses machine learning to analyze images of waste items, classify them, and provide personalized recycling guidelines. The application features a gamification system that rewards users for environmentally responsible behaviors, making recycling more engaging and educational.

## Features

- **AI Waste Classification**: Identify waste items from photos and receive proper disposal recommendations
- **Personalized Recycling Guidelines**: Get customized recycling instructions based on the identified waste type
- **Gamification System**: Earn points, complete challenges, and unlock achievements as you recycle
- **Recycling Center Finder**: Locate nearby facilities for proper disposal of different waste types
- **Educational Content**: Learn about the environmental impact of waste and the benefits of recycling

## Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **AI/ML**: TensorFlow Lite
- **Database**: MongoDB
- **APIs**: OpenCV, Geolocation API

## Setup

### Prerequisites

- Python 3.8+
- MongoDB
- pip (Python package manager)
- Virtual environment (recommended)
- Google Maps API key (for geolocation services)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/recycleright.git
   cd recycleright
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   cp .env.example .env
   ```
   Edit the `.env` file with your specific configuration values (see Environment Variables section below).

5. MongoDB setup:
   - Ensure MongoDB is running
   - Default local connection: `mongodb://localhost:27017/`
   - The application will create the database and collections automatically

6. Create upload and log directories:
   ```
   mkdir -p uploads logs
   mkdir -p ui/static/uploads
   ```

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Flask Settings
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your_secret_key_here
PORT=5000

# Database Settings
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=recycleright

# API Keys
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Model & Asset Paths
MODEL_PATH=models/waste_classifier.tflite
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216

# App Settings
DEFAULT_LATITUDE=37.7749
DEFAULT_LONGITUDE=-122.4194
DEFAULT_RADIUS=10
ITEMS_PER_PAGE=10

# Points System
POINTS_SCAN=5
POINTS_PROPER_DISPOSAL=20
POINTS_CHALLENGE_COMPLETION=50

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/recycleright.log
```

### Running the Application

1. Start the web application in development mode:
   ```
   python app.py
   ```
   or
   ```
   flask run
   ```
   The application will be available at `http://127.0.0.1:5000/`

2. For production deployment:
   ```
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

3. Run with specific environment file:
   ```
   FLASK_APP=app.py FLASK_ENV=production flask run
   ```

4. Run with increased performance:
   ```
   python -O app.py
   ```

### Running with Docker (Optional)

If you have Docker installed, you can use the following commands:

1. Build the Docker image:
   ```
   docker build -t recycleright .
   ```

2. Run the container:
   ```
   docker run -p 5000:5000 --env-file .env recycleright
   ```

## API Reference

RecycleRight provides the following API endpoints:

### Authentication

- **POST /api/auth/register** - Register a new user
  - Payload: `{"username": "user", "password": "pass", "email": "email@example.com"}`

- **POST /api/auth/login** - User login
  - Payload: `{"username": "user", "password": "pass"}`
  - Returns: JWT token

### Waste Classification

- **POST /api/classify** - Classify waste from an image
  - Content-Type: `multipart/form-data`
  - Form field: `image` (file upload)
  - Returns: Classification results and recycling guidelines

### Recycling Centers

- **GET /api/centers** - Get nearby recycling centers
  - Query params: `latitude`, `longitude`, `radius` (km), `waste_type` (optional)
  - Returns: List of recycling centers with location details

### User Data

- **GET /api/user/profile** - Get user profile
- **GET /api/user/points** - Get user points and level
- **GET /api/user/achievements** - Get user achievements
- **GET /api/user/challenges** - Get active user challenges
- **GET /api/leaderboard** - Get user rankings

## Web Interface

The RecycleRight web interface provides the following pages:

- **Home** (`/`): Introduction to RecycleRight and its features
- **Login** (`/login`): User authentication
- **Register** (`/register`): Create a new account
- **Dashboard** (`/dashboard`): User statistics, active challenges, and quick actions
- **Scan** (`/scan`): Upload waste item images or use camera to classify waste
- **Achievements** (`/achievements`): View earned achievements and active challenges
- **Leaderboard** (`/leaderboard`): Compare your recycling progress with other users
- **Recycling Centers** (`/centers`): Find nearby centers based on your location

## Project Structure

```
recycleright/
├── app.py                # Main application entry point
├── app/                  # Core application logic
│   ├── config.py         # Configuration settings
├── api/                  # API modules
│   ├── geolocation.py    # Geolocation service
├── classifiers/          # Waste classification models
│   ├── waste_classifier.py
├── data/                 # Data management
│   ├── database.py       # MongoDB database interface
├── gamification/         # Gamification systems
│   ├── points_system.py  # User points and levels
│   ├── challenges.py     # User challenges and achievements
├── ui/                   # User interface
│   ├── web_interface.py  # Web interface using Flask
│   ├── templates/        # HTML templates
│   ├── static/           # Static assets (CSS, JS, images)
├── models/               # ML model files
├── uploads/              # Temporary storage for uploaded images
├── logs/                 # Application logs
├── .env.example          # Example environment variables
├── .gitignore            # Git ignore file
└── requirements.txt      # Project dependencies
```

## Troubleshooting

### Common Issues

1. **MongoDB Connection Error**:
   - Ensure MongoDB is running
   - Check MongoDB URI in `.env` file
   - Run `mongod --dbpath=/path/to/data/directory`

2. **Missing API Keys**:
   - Ensure all API keys are correctly set in `.env`
   - For testing without Google Maps API, set `SKIP_GEOLOCATION=1` in `.env`

3. **Image Classification Errors**:
   - Check that TensorFlow Lite model exists at path specified in `.env`
   - Ensure image format is supported (JPG, PNG)
   - Check upload directory permissions

### Logs

Application logs are stored in the `logs` directory. To increase log verbosity, set `LOG_LEVEL=DEBUG` in your `.env` file.

## Development

### Running Tests

```
pytest
```

### Adding New Features

1. Fork the repository
2. Create a feature branch
3. Add your feature and tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to all contributors who have helped build RecycleRight
- Data sources for recycling guidelines and environmental education
- Environmental agencies for providing recycling center information