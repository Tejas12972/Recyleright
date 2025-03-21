#!/bin/bash
# RecycleRight Application Startup Script

# Create required directories
mkdir -p logs
mkdir -p uploads
mkdir -p models/labels
mkdir -p ui/static/uploads
mkdir -p ui/static/images

# Create waste_labels.txt if it doesn't exist
if [ ! -f "models/labels/waste_labels.txt" ]; then
    echo "Creating waste_labels.txt..."
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
fi

# Create placeholder images if they don't exist
if [ ! -f "ui/static/images/logo.png" ]; then
    echo "Creating placeholder logo.png..."
    # Create a simple text file since we can't generate an actual image
    echo "RecycleRight Logo Placeholder" > ui/static/images/logo.png
fi

if [ ! -f "ui/static/images/favicon.ico" ]; then
    echo "Creating placeholder favicon.ico..."
    # Create a simple text file since we can't generate an actual icon
    echo "RecycleRight Favicon Placeholder" > ui/static/images/favicon.ico
fi

# Start the application
echo "Starting RecycleRight application..."
python app.py 