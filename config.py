import os

class Config:
    """Application configuration class"""
    
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///restaurant.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email configuration (for reservation confirmations)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@restaurant.com'
    
    # Restaurant configuration
    RESTAURANT_NAME = "Le Papillon Doré"
    RESTAURANT_EMAIL = "info@lepapillondore.com"
    RESTAURANT_PHONE = "+1 (555) 123-4567"
    RESTAURANT_ADDRESS = "123 Gourmet Street, Culinary City, CC 12345"
    
    # Business hours
    OPENING_TIME = 11  # 11 AM
    CLOSING_TIME = 23  # 11 PM
    
    # Reservation settings
    MIN_PARTY_SIZE = 1
    MAX_PARTY_SIZE = 20
    BOOKING_ADVANCE_DAYS = 60  # How many days in advance customers can book
    
    # Upload settings
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Pagination
    ITEMS_PER_PAGE = 10
    
    # Admin credentials (in production, use proper authentication)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
