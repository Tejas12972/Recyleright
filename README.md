# RecycleRight

RecycleRight is an AI-powered waste management application that helps users properly classify and recycle waste items.

## Features

- **AI Waste Classification**: Upload images of waste items to get AI-powered classification and recycling guidance
- **Recycling Centers**: Find nearby recycling centers based on your location
- **User Dashboard**: Track your recycling activity and progress
- **Gamification**: Earn points and achievements for responsible waste disposal
- **Leaderboard**: Compete with other users to see who's making the biggest environmental impact

## Prerequisites

- Python 3.8 or higher
- MongoDB (local or cloud instance)
- OpenCV for image processing
- Flask web framework

## Installation

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

3. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root with the following variables:
   ```
   FLASK_APP=app.py
   FLASK_DEBUG=1
   SECRET_KEY=your_secret_key_here
   MONGODB_URI=mongodb://localhost:27017/recycleright
   ```

## Running the Application

### Using the Run Script

The easiest way to run the application is by using the provided `run.sh` script, which ensures all required directories exist and creates necessary files:

1. Make the script executable:
   ```
   chmod +x run.sh
   ```

2. Run the application:
   ```
   ./run.sh
   ```

### Manual Setup

If you prefer to set up the environment manually:

1. Create required directories:
   ```
   mkdir -p logs
   mkdir -p uploads
   mkdir -p models/labels
   mkdir -p ui/static/uploads
   mkdir -p ui/static/images
   ```

2. Create a labels file for waste classification:
   ```
   cat > models/labels/waste_labels.txt << EOL
   plastic_bottle
   glass_bottle
   aluminum_can
   paper
   cardboard
   plastic_bag
   food_waste
   styrofoam
   electronic_waste
   batteries
   light_bulb
   clothing
   metal
   plastic_container
   tetra_pak
   EOL
   ```

3. Start the application:
   ```
   python app.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:5001
   ```

## Project Structure

- `app.py`: Main application entry point
- `config.py`: Configuration settings
- `api/`: API modules for external services
- `data/`: Database and data management
- `models/`: ML models for waste classification
- `ui/`: User interface components
  - `static/`: Static assets (CSS, JS, images)
  - `templates/`: HTML templates
- `gamification/`: Points and achievement system

## Usage

1. **Sign Up/Login**: Create an account or login to access all features
2. **Scan Waste**: Upload an image of a waste item or use your camera to capture one
3. **View Classification**: Get AI-powered classification and recycling guidance
4. **Find Centers**: Locate nearby recycling centers for proper disposal
5. **Track Progress**: Monitor your recycling activity and earned points on your dashboard
6. **View Leaderboard**: See how you rank against other users

## Troubleshooting

If you encounter any issues running the application:

- Check the logs in the `logs/recycleright.log` file
- Ensure MongoDB is running and accessible
- Verify that all required directories exist
- Make sure environment variables are properly set

## License

This project is licensed under the MIT License - see the LICENSE file for details.