// RecycleRight Main JavaScript File

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Fade in elements with the fade-in class
    const fadeElements = document.querySelectorAll('.fade-in');
    fadeElements.forEach((element, index) => {
        setTimeout(() => {
            element.style.opacity = '1';
        }, 100 * index);
    });

    // Slide in elements with the slide-in-up class
    const slideElements = document.querySelectorAll('.slide-in-up');
    slideElements.forEach((element, index) => {
        setTimeout(() => {
            element.style.transform = 'translateY(0)';
            element.style.opacity = '1';
        }, 100 * index);
    });

    // Handle the image file upload in the scan page
    const fileUpload = document.getElementById('waste-image-upload');
    const dropArea = document.querySelector('.drop-area');

    if (fileUpload && dropArea) {
        setupImageUpload(fileUpload, dropArea);
    }

    // Handle the camera functionality in the scan page
    const startCameraBtn = document.getElementById('start-camera');
    if (startCameraBtn) {
        setupCamera();
    }

    // Setup form validation
    const forms = document.querySelectorAll('.needs-validation');
    setupFormValidation(forms);

    // Setup geolocation for recycling centers
    const locationBtn = document.getElementById('get-location');
    if (locationBtn) {
        setupGeolocation(locationBtn);
    }
});

// Setup Image Upload functionality
function setupImageUpload(fileUpload, dropArea) {
    // Preview the uploaded image
    fileUpload.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            previewFile(file);
            document.getElementById('upload-form').classList.remove('d-none');
        }
    });

    // Handle drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    dropArea.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropArea.classList.add('highlight');
    }

    function unhighlight() {
        dropArea.classList.remove('highlight');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        fileUpload.files = dt.files;
        previewFile(file);
        document.getElementById('upload-form').classList.remove('d-none');
    }

    function previewFile(file) {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onloadend = function() {
            const img = document.getElementById('image-preview');
            img.src = reader.result;
            document.querySelector('.preview-container').classList.remove('d-none');
        }
    }

    // Handle the form submission
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show loading spinner
            document.querySelector('.loading-spinner').classList.remove('d-none');
            
            const formData = new FormData(uploadForm);
            
            fetch('/upload_image', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading spinner
                document.querySelector('.loading-spinner').classList.add('d-none');
                
                // Display results
                displayResults(data);
            })
            .catch(error => {
                console.error('Error:', error);
                // Hide loading spinner
                document.querySelector('.loading-spinner').classList.add('d-none');
                // Show error message
                alert('An error occurred while processing your image. Please try again.');
            });
        });
    }
}

// Setup Camera functionality
function setupCamera() {
    let stream = null;
    let facingMode = 'environment'; // Start with back camera
    const startCameraBtn = document.getElementById('start-camera');
    const captureBtnContainer = document.getElementById('capture-btn-container');
    const captureBtn = document.getElementById('capture-image');
    const switchCameraBtn = document.getElementById('switch-camera');
    const video = document.getElementById('camera-preview');
    const canvas = document.getElementById('capture-canvas');
    const imagePreview = document.getElementById('camera-image-preview');
    
    startCameraBtn.addEventListener('click', async function() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: facingMode },
                audio: false
            });
            video.srcObject = stream;
            startCameraBtn.classList.add('d-none');
            captureBtnContainer.classList.remove('d-none');
        } catch (err) {
            console.error('Error accessing camera:', err);
            alert('Failed to access the camera. Please ensure camera permissions are granted and try again.');
        }
    });
    
    switchCameraBtn.addEventListener('click', function() {
        if (stream) {
            // Stop current stream
            stream.getTracks().forEach(track => track.stop());
            
            // Toggle facing mode
            facingMode = facingMode === 'environment' ? 'user' : 'environment';
            
            // Start new stream
            navigator.mediaDevices.getUserMedia({
                video: { facingMode: facingMode },
                audio: false
            })
            .then(newStream => {
                stream = newStream;
                video.srcObject = stream;
            })
            .catch(err => {
                console.error('Error switching camera:', err);
                alert('Failed to switch camera. Please try again.');
            });
        }
    });
    
    captureBtn.addEventListener('click', function() {
        if (stream) {
            // Get video dimensions
            const videoWidth = video.videoWidth;
            const videoHeight = video.videoHeight;
            
            // Set canvas dimensions to match video
            canvas.width = videoWidth;
            canvas.height = videoHeight;
            
            // Draw video frame to canvas
            const context = canvas.getContext('2d');
            context.drawImage(video, 0, 0, videoWidth, videoHeight);
            
            // Convert to image data URL
            const imageDataUrl = canvas.toDataURL('image/jpeg');
            
            // Display the captured image
            imagePreview.src = imageDataUrl;
            document.getElementById('camera-preview-container').classList.add('d-none');
            document.getElementById('camera-image-preview-container').classList.remove('d-none');
            document.getElementById('camera-form').classList.remove('d-none');
            
            // Add the image data to the form
            document.getElementById('camera-image-data').value = imageDataUrl;
        }
    });
    
    // Handle the camera form submission
    const cameraForm = document.getElementById('camera-form');
    if (cameraForm) {
        cameraForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show loading spinner
            document.querySelector('.loading-spinner').classList.remove('d-none');
            
            const formData = new FormData(cameraForm);
            
            fetch('/process_camera_image', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading spinner
                document.querySelector('.loading-spinner').classList.add('d-none');
                
                // Display results
                displayResults(data);
                
                // Stop the camera stream
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                    stream = null;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Hide loading spinner
                document.querySelector('.loading-spinner').classList.add('d-none');
                // Show error message
                alert('An error occurred while processing your image. Please try again.');
            });
        });
    }
    
    // Handle retake button
    const retakeBtn = document.getElementById('retake-image');
    if (retakeBtn) {
        retakeBtn.addEventListener('click', function() {
            document.getElementById('camera-preview-container').classList.remove('d-none');
            document.getElementById('camera-image-preview-container').classList.add('d-none');
            document.getElementById('camera-form').classList.add('d-none');
        });
    }
}

// Display the waste classification results
function displayResults(data) {
    const resultsSection = document.getElementById('results-section');
    const wasteTypeElement = document.getElementById('waste-type');
    const confidenceElement = document.getElementById('confidence');
    const guidelinesElement = document.getElementById('recycling-guidelines');
    const centersList = document.getElementById('recycling-centers-list');
    
    // Set waste type and confidence
    wasteTypeElement.textContent = data.waste_type;
    wasteTypeElement.className = 'badge bg-primary'; // Reset class
    
    // Adjust badge color based on recyclability
    if (data.recyclable) {
        wasteTypeElement.className = 'badge bg-success';
    } else {
        wasteTypeElement.className = 'badge bg-danger';
    }
    
    confidenceElement.textContent = `${Math.round(data.confidence * 100)}%`;
    
    // Set guidelines
    guidelinesElement.innerHTML = '';
    data.guidelines.forEach(guideline => {
        const li = document.createElement('li');
        li.className = 'list-group-item';
        li.textContent = guideline;
        guidelinesElement.appendChild(li);
    });
    
    // Set recycling centers
    centersList.innerHTML = '';
    if (data.recycling_centers && data.recycling_centers.length > 0) {
        data.recycling_centers.forEach(center => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.innerHTML = `
                <strong>${center.name}</strong><br>
                ${center.address}<br>
                <small>${center.distance.toFixed(1)} km away</small>
                <a href="https://maps.google.com/?q=${center.lat},${center.lon}" 
                   class="btn btn-sm btn-outline-primary float-end" target="_blank">
                   <i class="fas fa-map-marker-alt"></i> View on Map
                </a>
            `;
            centersList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.className = 'list-group-item text-center';
        li.textContent = 'No recycling centers found nearby for this waste type.';
        centersList.appendChild(li);
    }
    
    // Show confirm disposal button
    document.getElementById('confirm-disposal-container').classList.remove('d-none');
    
    // Show results section
    resultsSection.classList.remove('d-none');
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Handle the confirm disposal button
document.addEventListener('click', function(e) {
    if (e.target && e.target.id === 'confirm-disposal') {
        const wasteType = document.getElementById('waste-type').textContent;
        
        fetch('/confirm_disposal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                waste_type: wasteType
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message and points
                const confirmContainer = document.getElementById('confirm-disposal-container');
                confirmContainer.innerHTML = `
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle"></i> Thanks for recycling!
                        You earned ${data.points} points.
                    </div>
                    <button id="scan-another" class="btn btn-primary mt-3">
                        <i class="fas fa-redo"></i> Scan Another Item
                    </button>
                `;
                
                // Check if the user earned any new achievements
                if (data.new_achievements && data.new_achievements.length > 0) {
                    showNewAchievements(data.new_achievements);
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while confirming disposal. Please try again.');
        });
    }
    
    // Handle scan another button
    if (e.target && e.target.id === 'scan-another') {
        // Reset the scan page
        document.getElementById('results-section').classList.add('d-none');
        document.getElementById('upload-form').classList.add('d-none');
        document.getElementById('camera-form').classList.add('d-none');
        document.querySelector('.preview-container').classList.add('d-none');
        document.getElementById('camera-preview-container').classList.add('d-none');
        document.getElementById('camera-image-preview-container').classList.add('d-none');
        document.getElementById('image-preview').src = '';
        document.getElementById('camera-image-preview').src = '';
        document.getElementById('waste-image-upload').value = '';
        
        // Reset the active tab to upload
        const uploadTab = document.querySelector('button[data-bs-target="#upload-tab"]');
        const uploadTabContent = document.getElementById('upload-tab');
        const cameraTabContent = document.getElementById('camera-tab');
        
        const uploadTabInstance = new bootstrap.Tab(uploadTab);
        uploadTabInstance.show();
        
        uploadTabContent.classList.add('show', 'active');
        cameraTabContent.classList.remove('show', 'active');
        
        // Show the start camera button again
        document.getElementById('start-camera').classList.remove('d-none');
        document.getElementById('capture-btn-container').classList.add('d-none');
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
});

// Show new achievements modal
function showNewAchievements(achievements) {
    const achievementsContainer = document.getElementById('new-achievements-container');
    if (!achievementsContainer) return;
    
    achievementsContainer.innerHTML = '';
    
    achievements.forEach(achievement => {
        const achievementCard = document.createElement('div');
        achievementCard.className = 'card achievement-card mb-3';
        achievementCard.innerHTML = `
            <div class="card-header">
                <i class="fas fa-trophy text-warning"></i> New Achievement Unlocked!
            </div>
            <div class="card-body">
                <h5 class="card-title">${achievement.name}</h5>
                <p class="card-text">${achievement.description}</p>
                <p class="card-text text-muted">
                    <small>Points: +${achievement.points}</small>
                </p>
            </div>
        `;
        achievementsContainer.appendChild(achievementCard);
    });
    
    // Show the modal
    const achievementsModal = new bootstrap.Modal(document.getElementById('new-achievements-modal'));
    achievementsModal.show();
}

// Setup form validation
function setupFormValidation(forms) {
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

// Setup geolocation functionality
function setupGeolocation(locationBtn) {
    locationBtn.addEventListener('click', function() {
        if (navigator.geolocation) {
            locationBtn.disabled = true;
            locationBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Getting location...';
            
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    
                    // Send location to server
                    fetch('/update_location', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            latitude: lat,
                            longitude: lon
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            locationBtn.innerHTML = '<i class="fas fa-check-circle"></i> Location updated';
                            locationBtn.classList.remove('btn-primary');
                            locationBtn.classList.add('btn-success');
                            
                            // Reload recycling centers if on that page
                            if (window.location.pathname === '/recycling_centers') {
                                window.location.reload();
                            }
                        } else {
                            locationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Update Location';
                            locationBtn.disabled = false;
                            alert('Failed to update location. Please try again.');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        locationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Update Location';
                        locationBtn.disabled = false;
                        alert('An error occurred while updating your location. Please try again.');
                    });
                },
                function(error) {
                    console.error('Geolocation error:', error);
                    locationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Update Location';
                    locationBtn.disabled = false;
                    let errorMessage = 'Unable to retrieve your location. ';
                    
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            errorMessage += 'You denied the request for geolocation.';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMessage += 'Location information is unavailable.';
                            break;
                        case error.TIMEOUT:
                            errorMessage += 'The request to get your location timed out.';
                            break;
                        case error.UNKNOWN_ERROR:
                            errorMessage += 'An unknown error occurred.';
                            break;
                    }
                    
                    alert(errorMessage);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        } else {
            alert('Geolocation is not supported by this browser.');
        }
    });
} 