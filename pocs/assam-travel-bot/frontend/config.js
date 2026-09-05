// API URL configuration
// In Docker: http://bot:8000 (service name)
// Locally: http://localhost:8000
const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : `http://${window.location.hostname === 'localhost' ? 'bot' : window.location.hostname}:8000`;
