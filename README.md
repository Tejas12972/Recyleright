# RecycleRight 🌱

RecycleRight is an AI-powered waste management application that helps users properly classify and recycle waste items. The application uses machine learning to identify waste items from images and provides guidance on proper disposal methods.

![RecycleRight Banner](ui/static/images/logo.png)

## ✨ Features

- **AI Waste Classification**: Upload photos to get instant AI classification of waste items
- **Real-time Recycling Guidance**: Receive specific instructions for proper disposal
- **Interactive Map**: Find nearby recycling centers based on your location
- **User Dashboard**: Track your recycling statistics and environmental impact
- **Gamification**: Earn points and achievements for responsible waste disposal
- **Leaderboard**: Compete with others to increase recycling participation

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- MongoDB (local instance or Atlas cloud account)
- Google Maps API key (for recycling center locations)
- OpenAI API key (optional, for enhanced analysis with GPT)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/recycleright.git
   cd recycleright
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file and add your API keys and configurations.

5. **Run the setup script**
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
   This will create necessary directories and initialize required files.

### Running the Application

**Option 1: Using the run script**
```bash
./run.sh
```

**Option 2: Manual start**
```bash
python app.py
```

The application will be available at http://localhost:5001

## 🧩 Project Structure

```
recycleright/
├── api/                 # External API integrations
├── app/                 # Core application modules
├── assets/              # Static assets 
├── data/                # Database models and operations
├── gamification/        # Points and achievement system
├── logs/                # Application logs
├── models/              # ML models for waste classification
├── ui/                  # User interface
│   ├── static/          # CSS, JavaScript, images
│   └── templates/       # HTML templates
├── uploads/             # User-uploaded images (temporary)
├── .env.example         # Example environment variables
├── app.py               # Main application entry point
├── config.py            # Application configuration
├── requirements.txt     # Python dependencies
└── run.sh               # Startup script
```

## 📱 Usage Guide

1. **Create an Account**: Sign up to track your recycling progress
2. **Upload Waste Images**: Take a photo of an item or upload from your gallery
3. **Review Classification**: Get AI-powered identification and recycling instructions
4. **Find Recycling Centers**: View nearby locations for proper waste disposal
5. **Track Progress**: View your dashboard to see your recycling statistics
6. **Earn Rewards**: Collect points and badges for your environmental contributions

## 🛠️ Development

### Testing
```bash
pytest
```

### Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔐 Security Notes

- Never commit your `.env` file or any files containing API keys
- Generate a strong unique secret key for your Flask application
- Ensure MongoDB access is properly secured
- Use HTTPS in production environments

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- TensorFlow for machine learning models
- OpenAI for GPT-4o integration
- Google Maps API for location services
- The Sustainable Recycling Alliance for waste classification guidelines