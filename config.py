import os

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_NAME = os.getenv('DB_NAME', 'ev_charging_db')

# Razorpay configuration
RAZORPAY_KEY = os.getenv('RAZORPAY_KEY', 'your_razorpay_key')
RAZORPAY_SECRET = os.getenv('RAZORPAY_SECRET', 'your_razorpay_secret')

# Flask secret key
SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key_here')

# Device configuration
DEVICE_ID = os.getenv('DEVICE_ID', 'MGTEV001')