# Le Papillon Doré - Restaurant Reservation System

A complete restaurant management system with online reservations, menu management, and admin panel.

## 🌐 Live Demo

**Website:** https://restaurant-reservation-2-kv86.onrender.com/  
**Admin Panel:** https://restaurant-reservation-2-kv86.onrender.com/admin/login

**Admin Login:**
- Username: `admin`
- Password: `admin123`

## What Is This?

This is a full-featured restaurant reservation system that allows:
- **Customers** to browse menu, make reservations, and contact the restaurant
- **Administrators** to manage reservations, tables, menu items, and customer database

## How It Works

1. **Customer Side**: Users visit the website to view menu, make reservations by selecting date/time/party size, and submit contact inquiries
2. **Admin Side**: Restaurant staff login to approve/cancel reservations, manage tables and menu items, track customer data
3. **Database**: All information (customers, reservations, menu) is permanently stored in SQLite database
4. **Email System**: Automatic confirmation emails sent to customers when they make reservations



## Setup Instructions

### Prerequisites
- Python 3.8+
- pip (comes with Python)

### Installation Steps

1. **Download the project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Open in browser**:
   - Website: http://localhost:5000
   - Admin: http://localhost:5000/admin/login (username: `admin`, password: `admin123`)

That's it! The database and sample data are created automatically on first run.



## Why These Technologies?

**Flask (Python)**
- Lightweight and easy to learn web framework
- Perfect for small to medium applications
- Great for rapid development

**SQLite Database**
- No separate server needed - just a file
- Perfect for single-location restaurants
- All data stored permanently in one file
- Easy to backup (just copy the .db file)

**SQLAlchemy**
- Makes database operations simple with Python code
- No need to write complex SQL queries
- Handles relationships between tables automatically

**Bootstrap**
- Professional-looking design out of the box
- Mobile-responsive without extra work
- Consistent UI components

**JavaScript ES6+**
- Modern interactive features
- Form validation before submission
- Smooth user experience

## Technologies Used

- **Backend**: Flask 3.x (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Icons**: Font Awesome 6
- **Authentication**: Werkzeug password hashing
- **Email**: Flask-Mail

---

**Made with ❤️ using Flask, Bootstrap, and SQLite**
