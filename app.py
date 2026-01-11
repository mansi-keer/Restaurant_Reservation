from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mail import Mail, Message
from datetime import datetime, timedelta, date, time
from models import db, Customer, Table, Reservation, MenuItem, Admin, ContactMessage
from config import Config
import os
import requests
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
mail = Mail(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Helper functions
def is_admin_logged_in():
    """Check if admin is logged in"""
    return 'admin_id' in session


def fetch_food_image(food_name):
    """Automatically fetch food image matching the dish name"""
    try:
        print(f"Attempting to fetch image for: {food_name}")
        
        # Try Pexels API (free, requires API key but we'll use public endpoint)
        # Using a search-based approach
        search_term = food_name.lower().replace(' ', '+')
        
        # Try using DuckDuckGo image search via serper (free alternative)
        # Using a simple image search API
        try:
            # Using Pexels free API endpoint
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Try multiple search terms for better results
            search_queries = [
                f"{food_name} food",
                f"{food_name} dish",
                food_name
            ]
            
            for query in search_queries:
                try:
                    # Using Lorem Flickr (free, searches Flickr)
                    url = f"https://loremflickr.com/800/600/{query.replace(' ', ',')},food"
                    response = requests.get(url, timeout=8, headers=headers)
                    
                    if response.status_code == 200 and len(response.content) > 1000:
                        unique_filename = f"{uuid.uuid4().hex}.jpg"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        
                        print(f"Image saved successfully from LoremFlickr: {unique_filename}")
                        return f"/static/uploads/{unique_filename}"
                except Exception as e:
                    print(f"LoremFlickr attempt failed for '{query}': {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Search-based fetch failed: {str(e)}")
        
        # Final fallback: Foodish API (random food images)
        try:
            url = "https://foodish-api.com/api/"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                image_url_external = data.get('image')
                
                if image_url_external:
                    img_response = requests.get(image_url_external, timeout=5)
                    if img_response.status_code == 200:
                        unique_filename = f"{uuid.uuid4().hex}.jpg"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
                        
                        print(f"Image saved successfully from Foodish: {unique_filename}")
                        return f"/static/uploads/{unique_filename}"
        except Exception as e:
            print(f"Foodish API failed: {str(e)}")
            
    except Exception as e:
        print(f"Error fetching image: {str(e)}")
    
    return None


def send_confirmation_email(reservation, customer):
    """Send reservation confirmation email to customer"""
    try:
        status_text = "received and is pending approval" if reservation.status == 'pending' else "confirmed"
        msg = Message(
            subject=f"Reservation Confirmation - {app.config['RESTAURANT_NAME']}",
            recipients=[customer.email],
            body=f"""
Dear {customer.first_name} {customer.last_name},

Your table reservation request has been {status_text}!

Reservation Details:
- Date: {reservation.reservation_date.strftime('%B %d, %Y')}
- Time: {reservation.reservation_time.strftime('%I:%M %p')}
- Party Size: {reservation.party_size} guests
- Status: {reservation.status.upper()}

{"We will review your reservation and send you a confirmation email shortly." if reservation.status == 'pending' else "Your table is reserved!"}

{app.config['RESTAURANT_NAME']}
{app.config['RESTAURANT_ADDRESS']}
Phone: {app.config['RESTAURANT_PHONE']}

Thank you for choosing us!
            """.strip()
        )
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")


def send_admin_notification(reservation, customer):
    """Send new reservation notification to admin"""
    try:
        admin_email = app.config.get('RESTAURANT_EMAIL', 'admin@restaurant.com')
        msg = Message(
            subject=f"New Reservation Request - {reservation.reservation_date.strftime('%b %d')}",
            recipients=[admin_email],
            body=f"""
New Reservation Request

Customer: {customer.first_name} {customer.last_name}
Email: {customer.email}
Phone: {customer.phone}

Reservation Details:
- Date: {reservation.reservation_date.strftime('%B %d, %Y')}
- Time: {reservation.reservation_time.strftime('%I:%M %p')}
- Party Size: {reservation.party_size} guests
- Table: #{reservation.table.table_number}
- Special Requests: {reservation.special_requests or 'None'}

Status: PENDING APPROVAL

Please log in to the admin panel to approve or cancel this reservation.
            """.strip()
        )
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send admin notification: {e}")


# Public routes
@app.route('/')
def index():
    """Homepage"""
    featured_items = MenuItem.query.filter_by(is_available=True).limit(6).all()
    return render_template('index.html', featured_items=featured_items)


@app.route('/menu')
def menu():
    """Display restaurant menu"""
    category = request.args.get('category', 'all')
    
    if category == 'all':
        items = MenuItem.query.filter_by(is_available=True).all()
    else:
        items = MenuItem.query.filter_by(category=category, is_available=True).all()
    
    categories = ['appetizer', 'main', 'dessert', 'beverage']
    return render_template('menu.html', items=items, categories=categories, current_category=category)


@app.route('/reservation', methods=['GET', 'POST'])
def reservation():
    """Make a reservation"""
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            reservation_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            reservation_time = datetime.strptime(request.form.get('time'), '%H:%M').time()
            party_size = int(request.form.get('party_size'))
            special_requests = request.form.get('special_requests', '')
            
            # Validate date
            if reservation_date < date.today():
                flash('Cannot book for past dates', 'error')
                return redirect(url_for('reservation'))
            
            if reservation_date > date.today() + timedelta(days=app.config['BOOKING_ADVANCE_DAYS']):
                flash(f'Cannot book more than {app.config["BOOKING_ADVANCE_DAYS"]} days in advance', 'error')
                return redirect(url_for('reservation'))
            
            # Find available table
            available_table = Table.query.filter(
                Table.capacity >= party_size,
                Table.is_available == True
            ).first()
            
            if not available_table:
                flash('No tables available for your party size', 'error')
                return redirect(url_for('reservation'))
            
            # Check for existing customer or create new
            customer = Customer.query.filter_by(email=email).first()
            if not customer:
                customer = Customer(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone
                )
                db.session.add(customer)
                db.session.flush()
            
            # Create reservation
            new_reservation = Reservation(
                customer_id=customer.id,
                table_id=available_table.id,
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                party_size=party_size,
                special_requests=special_requests,
                status='pending'
            )
            
            db.session.add(new_reservation)
            db.session.commit()
            
            # Send confirmation email to customer
            send_confirmation_email(new_reservation, customer)
            
            # Send notification to admin
            send_admin_notification(new_reservation, customer)
            
            flash('Reservation request submitted! Check your email for confirmation.', 'success')
            return redirect(url_for('reservation_success', reservation_id=new_reservation.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error making reservation: {str(e)}', 'error')
            return redirect(url_for('reservation'))
    
    # GET request
    min_date = date.today().strftime('%Y-%m-%d')
    max_date = (date.today() + timedelta(days=app.config['BOOKING_ADVANCE_DAYS'])).strftime('%Y-%m-%d')
    
    return render_template('reservation.html', min_date=min_date, max_date=max_date)


@app.route('/reservation/success/<int:reservation_id>')
def reservation_success(reservation_id):
    """Reservation confirmation page"""
    reservation = Reservation.query.get_or_404(reservation_id)
    return render_template('reservation_success.html', reservation=reservation)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    if request.method == 'POST':
        try:
            message = ContactMessage(
                name=request.form.get('name'),
                email=request.form.get('email'),
                subject=request.form.get('subject'),
                message=request.form.get('message')
            )
            db.session.add(message)
            db.session.commit()
            flash('Message sent successfully!', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error sending message: {str(e)}', 'error')
    
    return render_template('contact.html')


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    if is_admin_logged_in():
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    # Statistics
    total_reservations = Reservation.query.count()
    pending_reservations = Reservation.query.filter_by(status='pending').count()
    today_reservations = Reservation.query.filter_by(reservation_date=date.today()).count()
    total_customers = Customer.query.count()
    total_tables = Table.query.count()
    total_messages = ContactMessage.query.count()
    unread_messages = ContactMessage.query.filter_by(is_read=False).count()
    
    # Recent reservations
    recent_reservations = Reservation.query.order_by(Reservation.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_reservations=total_reservations,
                         pending_reservations=pending_reservations,
                         today_reservations=today_reservations,
                         total_customers=total_customers,
                         total_tables=total_tables,
                         total_messages=total_messages,
                         unread_messages=unread_messages,
                         recent_reservations=recent_reservations)


@app.route('/admin/reservations')
def admin_reservations():
    """Manage reservations"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    status = request.args.get('status', 'all')
    date_filter = request.args.get('date')
    
    query = Reservation.query
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    if date_filter:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        query = query.filter_by(reservation_date=filter_date)
    
    reservations = query.order_by(Reservation.reservation_date.desc(), Reservation.reservation_time.desc()).all()
    
    return render_template('admin/reservations.html', reservations=reservations, current_status=status)


@app.route('/admin/reservation/<int:id>/cancel', methods=['POST'])
def admin_cancel_reservation(id):
    """Cancel a reservation"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    reservation = Reservation.query.get_or_404(id)
    reservation.status = 'cancelled'
    db.session.commit()
    
    # Send cancellation email to customer
    try:
        customer = reservation.customer
        msg = Message(
            subject=f"Reservation Cancelled - {app.config['RESTAURANT_NAME']}",
            recipients=[customer.email],
            body=f"""
Dear {customer.first_name} {customer.last_name},

Your reservation has been cancelled.

Reservation Details:
- Date: {reservation.reservation_date.strftime('%B %d, %Y')}
- Time: {reservation.reservation_time.strftime('%I:%M %p')}
- Party Size: {reservation.party_size} guests

If you have any questions, please contact us at {app.config['RESTAURANT_PHONE']}.

{app.config['RESTAURANT_NAME']}
            """.strip()
        )
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send cancellation email: {e}")
    
    flash('Reservation cancelled successfully', 'success')
    return redirect(url_for('admin_reservations'))


@app.route('/admin/reservation/<int:id>/approve', methods=['POST'])
def admin_approve_reservation(id):
    """Approve a pending reservation"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    reservation = Reservation.query.get_or_404(id)
    reservation.status = 'approved'
    db.session.commit()
    
    # Send approval email to customer
    try:
        customer = reservation.customer
        msg = Message(
            subject=f"Reservation Approved - {app.config['RESTAURANT_NAME']}",
            recipients=[customer.email],
            body=f"""
Dear {customer.first_name} {customer.last_name},

Great news! Your reservation has been approved and confirmed.

Reservation Details:
- Date: {reservation.reservation_date.strftime('%B %d, %Y')}
- Time: {reservation.reservation_time.strftime('%I:%M %p')}
- Party Size: {reservation.party_size} guests
- Table: #{reservation.table.table_number}

Your table is reserved for {reservation.reservation_date.strftime('%b %d')}, {reservation.reservation_time.strftime('%I:%M %p')}

We look forward to serving you!

{app.config['RESTAURANT_NAME']}
{app.config['RESTAURANT_ADDRESS']}
Phone: {app.config['RESTAURANT_PHONE']}
            """.strip()
        )
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send approval email: {e}")
    
    flash('Reservation approved successfully', 'success')
    return redirect(url_for('admin_reservations'))


@app.route('/admin/tables')
def admin_tables():
    """Manage tables"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    tables = Table.query.order_by(Table.table_number).all()
    return render_template('admin/tables.html', tables=tables)


@app.route('/admin/table/add', methods=['POST'])
def admin_add_table():
    """Add a new table"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    try:
        table = Table(
            table_number=int(request.form.get('table_number')),
            capacity=int(request.form.get('capacity')),
            location=request.form.get('location'),
            is_available=True
        )
        db.session.add(table)
        db.session.commit()
        flash('Table added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding table: {str(e)}', 'error')
    
    return redirect(url_for('admin_tables'))


@app.route('/admin/table/<int:table_id>/toggle-availability')
def admin_toggle_table(table_id):
    """Toggle table availability"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    table = Table.query.get_or_404(table_id)
    table.is_available = not table.is_available
    db.session.commit()
    status = 'available' if table.is_available else 'unavailable'
    flash(f'Table #{table.table_number} marked as {status}', 'success')
    return redirect(url_for('admin_tables'))


@app.route('/admin/table/<int:table_id>/edit', methods=['POST'])
def admin_edit_table(table_id):
    """Edit table details"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    try:
        table = Table.query.get_or_404(table_id)
        table.table_number = int(request.form.get('table_number'))
        table.capacity = int(request.form.get('capacity'))
        table.location = request.form.get('location')
        db.session.commit()
        flash(f'Table #{table.table_number} updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating table: {str(e)}', 'error')
    
    return redirect(url_for('admin_tables'))


@app.route('/admin/menu')
def admin_menu():
    """Manage menu items"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    items = MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    return render_template('admin/menu.html', items=items)


@app.route('/admin/menu/add', methods=['POST'])
def admin_add_menu_item():
    """Add menu item"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    try:
        print("Adding menu item...")
        # Handle image upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                print(f"Manual image upload detected: {file.filename}")
                filename = secure_filename(file.filename)
                # Create unique filename
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                unique_filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                image_url = f"/static/uploads/{unique_filename}"
                print(f"Manual image saved: {image_url}")
        
        # Check if fetched URL was provided from preview
        if not image_url and request.form.get('auto_fetched_url'):
            image_url = request.form.get('auto_fetched_url')
            print(f"Using previewed image: {image_url}")
        
        # If still no image, try to auto-fetch
        if not image_url:
            food_name = request.form.get('name')
            print(f"No image provided, attempting auto-fetch for: {food_name}")
            try:
                image_url = fetch_food_image(food_name)
                if image_url:
                    print(f"Auto-fetched image: {image_url}")
                else:
                    print("Auto-fetch failed, proceeding without image")
            except:
                print("Auto-fetch exception, proceeding without image")
                image_url = None
        
        item = MenuItem(
            name=request.form.get('name'),
            description=request.form.get('description'),
            price=float(request.form.get('price')),
            category=request.form.get('category'),
            image_url=image_url,
            is_vegetarian=bool(request.form.get('is_vegetarian')),
            is_vegan=bool(request.form.get('is_vegan')),
            is_gluten_free=bool(request.form.get('is_gluten_free')),
            is_non_veg=bool(request.form.get('is_non_veg')),
            is_available=True
        )
        db.session.add(item)
        db.session.commit()
        print(f"Menu item added successfully: {item.name}")
        flash('Menu item added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error adding menu item: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error adding menu item: {str(e)}', 'error')
    
    return redirect(url_for('admin_menu'))


@app.route('/admin/menu/<int:item_id>/toggle-availability')
def admin_toggle_menu(item_id):
    """Toggle menu item availability"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    item = MenuItem.query.get_or_404(item_id)
    item.is_available = not item.is_available
    db.session.commit()
    status = 'available' if item.is_available else 'unavailable'
    flash(f'{item.name} marked as {status}', 'success')
    return redirect(url_for('admin_menu'))


@app.route('/admin/menu/<int:item_id>/edit', methods=['POST'])
def admin_edit_menu(item_id):
    """Edit menu item"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    try:
        item = MenuItem.query.get_or_404(item_id)
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Create unique filename
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                unique_filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                item.image_url = f"/static/uploads/{unique_filename}"
        
        # Check if auto-fetched URL was provided
        if not item.image_url or request.form.get('auto_fetched_url'):
            auto_url = request.form.get('auto_fetched_url')
            if auto_url:
                item.image_url = auto_url
        
        item.name = request.form.get('name')
        item.description = request.form.get('description')
        item.price = float(request.form.get('price'))
        item.category = request.form.get('category')
        item.is_vegetarian = bool(request.form.get('is_vegetarian'))
        item.is_vegan = bool(request.form.get('is_vegan'))
        item.is_gluten_free = bool(request.form.get('is_gluten_free'))
        item.is_non_veg = bool(request.form.get('is_non_veg'))
        db.session.commit()
        flash(f'{item.name} updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating menu item: {str(e)}', 'error')
    
    return redirect(url_for('admin_menu'))


@app.route('/admin/menu/<int:item_id>/fetch-image')
def admin_fetch_menu_image(item_id):
    """Auto-fetch image for menu item"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    try:
        item = MenuItem.query.get_or_404(item_id)
        image_url = fetch_food_image(item.name)
        if image_url:
            item.image_url = image_url
            db.session.commit()
            flash(f'Image fetched successfully for {item.name}', 'success')
        else:
            flash('Could not fetch image, please try again', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error fetching image: {str(e)}', 'error')
    
    return redirect(url_for('admin_menu'))


@app.route('/admin/customers')
def admin_customers():
    """View customers"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    customers = Customer.query.order_by(Customer.created_at.desc()).all()
    return render_template('admin/customers.html', customers=customers)


@app.route('/admin/messages')
def admin_messages():
    """View contact messages"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=messages)


@app.route('/admin/messages/<int:message_id>/mark-read')
def admin_mark_message_read(message_id):
    """Mark a message as read"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    
    message = ContactMessage.query.get_or_404(message_id)
    message.is_read = True
    db.session.commit()
    flash('Message marked as read', 'success')
    return redirect(url_for('admin_messages'))


# API endpoints
@app.route('/api/fetch-food-image')
def api_fetch_food_image():
    """API to fetch food image preview without saving"""
    food_name = request.args.get('name', '')
    if not food_name:
        return jsonify({'success': False, 'error': 'No name provided'})
    
    try:
        image_url = fetch_food_image(food_name)
        if image_url:
            return jsonify({'success': True, 'url': image_url})
        else:
            return jsonify({'success': False, 'error': 'Could not fetch image'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/available-times', methods=['POST'])
def api_available_times():
    """Get available time slots for a date"""
    try:
        data = request.get_json()
        reservation_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
        party_size = int(data.get('party_size', 2))
        
        # Get all reservations for the date
        existing_reservations = Reservation.query.filter_by(
            reservation_date=reservation_date
        ).all()
        
        # Generate time slots
        time_slots = []
        for hour in range(app.config['OPENING_TIME'], app.config['CLOSING_TIME']):
            for minute in [0, 30]:
                time_slot = time(hour, minute)
                time_slots.append(time_slot.strftime('%H:%M'))
        
        return jsonify({'times': time_slots})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Initialize database
@app.cli.command('init-db')
def init_db():
    """Initialize the database"""
    with app.app_context():
        db.create_all()
        
        # Create admin user
        admin = Admin.query.filter_by(username=app.config['ADMIN_USERNAME']).first()
        if not admin:
            admin = Admin(
                username=app.config['ADMIN_USERNAME'],
                email='admin@restaurant.com'
            )
            admin.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin)
        
        # Create sample tables
        if Table.query.count() == 0:
            tables = [
                Table(table_number=1, capacity=2, location='Window'),
                Table(table_number=2, capacity=2, location='Window'),
                Table(table_number=3, capacity=4, location='Indoor'),
                Table(table_number=4, capacity=4, location='Indoor'),
                Table(table_number=5, capacity=6, location='Indoor'),
                Table(table_number=6, capacity=8, location='Patio'),
                Table(table_number=7, capacity=4, location='Patio'),
                Table(table_number=8, capacity=2, location='Indoor'),
            ]
            db.session.add_all(tables)
        
        # Create sample menu items
        if MenuItem.query.count() == 0:
            menu_items = [
                MenuItem(name='Caesar Salad', description='Fresh romaine lettuce with parmesan and croutons', 
                        price=12.99, category='appetizer', is_vegetarian=True,
                        image_url='https://images.unsplash.com/photo-1546793665-c74683f339c1?w=600&q=80'),
                MenuItem(name='Bruschetta', description='Toasted bread with tomatoes, garlic, and basil', 
                        price=10.99, category='appetizer', is_vegan=True,
                        image_url='https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=600&q=80'),
                MenuItem(name='Grilled Salmon', description='Atlantic salmon with lemon butter sauce', 
                        price=28.99, category='main', is_gluten_free=True,
                        image_url='https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=600&q=80'),
                MenuItem(name='Ribeye Steak', description='12oz ribeye with garlic butter', 
                        price=35.99, category='main',
                        image_url='https://images.unsplash.com/photo-1558030006-450675393462?w=600&q=80'),
                MenuItem(name='Pasta Primavera', description='Fresh vegetables in creamy sauce', 
                        price=22.99, category='main', is_vegetarian=True,
                        image_url='https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=600&q=80'),
                MenuItem(name='Tiramisu', description='Classic Italian dessert', 
                        price=8.99, category='dessert',
                        image_url='https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=600&q=80'),
                MenuItem(name='Chocolate Lava Cake', description='Warm chocolate cake with vanilla ice cream', 
                        price=9.99, category='dessert', is_vegetarian=True,
                        image_url='https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=600&q=80'),
                MenuItem(name='House Wine', description='Red or white', 
                        price=8.00, category='beverage',
                        image_url='https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?w=600&q=80'),
                MenuItem(name='Sparkling Water', description='San Pellegrino', 
                        price=4.00, category='beverage', is_vegan=True,
                        image_url='https://images.unsplash.com/photo-1523362628745-0c100150b504?w=600&q=80'),
            ]
            db.session.add_all(menu_items)
        
        db.session.commit()
        print('Database initialized successfully!')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
