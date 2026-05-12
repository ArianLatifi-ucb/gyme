from flask import Flask, render_template, request, redirect, session, url_for, flash
from models import db, User, Course, ClassSession, Staff, OpeningHours, Payment, Booking, ContactMessage, Plan, Customer
from datetime import datetime, timedelta
import os
import re

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'gyme.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def ensure_columns():
    """Add new columns to existing database without breaking it."""
    import sqlite3
    db_path = os.path.join(basedir, 'gyme.db')
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    migrations = [
        ("users",     "full_name",         "VARCHAR(120)"),
        ("users",     "phone",             "VARCHAR(30)"),
        ("users",     "membership_plan",   "VARCHAR(30) DEFAULT 'Not selected'"),
        ("users",     "fitness_goal",      "VARCHAR(200)"),
        ("users",     "last_login",        "DATETIME"),
        ("customers", "discount_percent",  "REAL DEFAULT 0"),
        ("customers", "membership_start",  "DATETIME"),
        ("customers", "membership_end",    "DATETIME"),
        ("courses",   "price",             "REAL DEFAULT 0"),
        ("courses",   "trainer_id",        "INTEGER REFERENCES users(id)"),
        ("bookings",  "amount_charged",    "REAL DEFAULT 0"),
    ]
    for table, column, col_type in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def get_or_create_customer(user):
    if user.customer:
        return user.customer
    c = Customer()
    c.user_id = user.id
    c.balance = 0.0
    c.discount_percent = 0.0
    db.session.add(c)
    db.session.commit()
    return c


def get_current_user():
    """Return the currently logged-in user, or None if the session is invalid."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = User.query.get(user_id)
    if user is None:
        session.clear()
    return user


def login_required():
    """Protect member pages from users who are not logged in or have an old broken session."""
    if 'user_id' not in session:
        flash('Please login first to access your member area.', 'error')
        return False
    if get_current_user() is None:
        flash('Your session expired. Please login again.', 'error')
        return False
    return True


def is_strong_password(password):
    return len(password) >= 8 and re.search(r'[A-Z]', password) and re.search(r'[0-9]', password)


def get_plan_price(plan):
    prices = {
        'Basic': 18,
        'Pro': 25,
        'Pro Plus': 39
    }
    return prices.get(plan, 18)


def trainer_required():
    if session.get('role') not in ['trainer', 'admin']:
        flash('Trainer access only.', 'error')
        return False
    return True


# ==================== PUBLIC ROUTES ====================

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        if name and email and message:
            db.session.add(ContactMessage(name=name, email=email, message=message))
            db.session.commit()
            flash('Thanks for contacting GymE. Our team will reply soon.', 'success')
        else:
            flash('Please complete all contact form fields.', 'error')
        return redirect(url_for('index') + '#contact')

    courses = Course.query.all()
    staff = Staff.query.all()
    hours = OpeningHours.query.all()
    return render_template('index.html', courses=courses, staff=staff, hours=hours)


@app.route('/courses')
def courses():
    courses = Course.query.all()
    selected_date = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    sessions = ClassSession.query.filter_by(session_date=selected_date).order_by(ClassSession.session_time).all()
    all_session_dates = [row[0] for row in db.session.query(ClassSession.session_date).distinct().order_by(ClassSession.session_date).all()]
    current_user = get_current_user()
    customer = get_or_create_customer(current_user) if current_user and current_user.role == 'customer' else None
    return render_template('pages/courses.html', courses=courses, sessions=sessions, selected_date=selected_date, all_session_dates=all_session_dates, customer=customer)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.username}!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            if user.role == 'trainer':
                return redirect(url_for('trainer_dashboard'))
            return redirect(url_for('customer_dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('pages/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([username, email, password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('pages/register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('pages/register.html')

        if not is_strong_password(password):
            flash('Password must be at least 8 characters and include one uppercase letter and one number.', 'error')
            return render_template('pages/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('pages/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('pages/register.html')

        user = User(username=username, email=email, role='customer')
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.flush()
            c = Customer()
            c.user_id = user.id
            c.balance = 0.0
            c.discount_percent = 0.0
            db.session.add(c)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration', 'error')

    return render_template('pages/register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))


# ==================== CUSTOMER ROUTES ====================

@app.route('/dashboard')
def customer_dashboard():
    if not login_required():
        return redirect(url_for('login'))

    user = get_current_user()
    if user is None:
        flash('User not found. Please login again.', 'error')
        return redirect(url_for('login'))

    customer = get_or_create_customer(user)
    courses = Course.query.limit(3).all()
    bookings = Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).all()
    payments = Payment.query.filter_by(user_id=user.id).order_by(Payment.created_at.desc()).limit(5).all()
    return render_template('pages/customer-dashboard.html', user=user, customer=customer, courses=courses, bookings=bookings, payments=payments, now=datetime.utcnow())


@app.route('/profile')
def profile():
    if not login_required():
        return redirect(url_for('login'))

    user = get_current_user()
    if user is None:
        flash('User not found. Please login again.', 'error')
        return redirect(url_for('login'))

    return render_template('pages/profile.html', user=user)


@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if not login_required():
        return redirect(url_for('login'))

    user = get_current_user()
    if user is None:
        flash('User not found. Please login again.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        membership_plan = request.form.get('membership_plan')
        fitness_goal = request.form.get('fitness_goal')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if email != user.email and User.query.filter_by(email=email).first():
            flash('This email is already used by another account.', 'error')
            return render_template('pages/edit-profile.html', user=user)

        if new_password:
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return render_template('pages/edit-profile.html', user=user)
            if not is_strong_password(new_password):
                flash('Password must be at least 8 characters and include one uppercase letter and one number.', 'error')
                return render_template('pages/edit-profile.html', user=user)
            user.set_password(new_password)

        user.full_name = full_name
        user.email = email
        user.phone = phone
        user.membership_plan = membership_plan
        user.fitness_goal = fitness_goal

        try:
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('profile'))
        except Exception:
            db.session.rollback()
            flash('There was a problem updating your profile.', 'error')

    return render_template('pages/edit-profile.html', user=user)


@app.route('/membership/select/<plan>', methods=['POST'])
def select_membership(plan):
    if not login_required():
        flash('Please login or create an account before choosing a membership.', 'error')
        return redirect(url_for('login'))

    allowed_plans = ['Basic', 'Pro', 'Pro Plus']
    if plan not in allowed_plans:
        flash('Invalid membership plan selected.', 'error')
        return redirect(url_for('index'))

    return redirect(url_for('billing', plan=plan))


@app.route('/billing', methods=['GET', 'POST'])
def billing():
    if not login_required():
        flash('Please login first to complete billing.', 'error')
        return redirect(url_for('login'))

    user = get_current_user()
    if user is None:
        flash('User not found. Please login again.', 'error')
        return redirect(url_for('login'))

    customer = get_or_create_customer(user)
    allowed_plans = ['Basic', 'Pro', 'Pro Plus']

    if request.method == 'POST':
        action = request.form.get('action_type')

        if action == 'topup':
            try:
                topup_amount = float(request.form.get('topup_amount', 0))
            except ValueError:
                topup_amount = 0
            if topup_amount <= 0:
                flash('Please enter a valid top-up amount.', 'error')
            else:
                customer.balance = (customer.balance or 0) + topup_amount
                payment = Payment()
                payment.user_id = user.id
                payment.plan = 'Top-up'
                payment.amount = topup_amount
                payment.payment_method = request.form.get('payment_method', 'Demo Card')
                payment.cardholder_name = request.form.get('cardholder_name', '')
                payment.billing_email = request.form.get('billing_email') or user.email
                payment.status = 'Paid'
                try:
                    db.session.add(payment)
                    db.session.commit()
                    flash(f'£{topup_amount:.2f} added to your balance.', 'success')
                except Exception:
                    db.session.rollback()
                    flash('There was a problem processing your top-up.', 'error')

        elif action == 'plan':
            selected_plan = request.form.get('plan')
            if selected_plan not in allowed_plans:
                flash('Invalid plan selected.', 'error')
            else:
                amount = get_plan_price(selected_plan)
                if (customer.balance or 0) < amount:
                    flash(f'Insufficient balance (£{customer.balance:.2f}). You need £{amount:.2f} for the {selected_plan} plan. Please top up first.', 'error')
                else:
                    payment_method = request.form.get('payment_method', 'Demo Card')
                    cardholder_name = request.form.get('cardholder_name', '')
                    billing_email = request.form.get('billing_email') or user.email

                    customer.balance = round((customer.balance or 0) - amount, 2)
                    customer.membership_start = datetime.utcnow()
                    customer.membership_end = datetime.utcnow() + timedelta(days=30)
                    user.membership_plan = selected_plan

                    payment = Payment()
                    payment.user_id = user.id
                    payment.plan = selected_plan
                    payment.amount = amount
                    payment.payment_method = payment_method
                    payment.cardholder_name = cardholder_name
                    payment.billing_email = billing_email
                    payment.status = 'Paid'
                    try:
                        db.session.add(payment)
                        db.session.commit()
                        flash(f'{selected_plan} membership activated. £{amount:.2f} deducted from your balance.', 'success')
                    except Exception:
                        db.session.rollback()
                        flash('There was a problem activating your membership.', 'error')

        return redirect(url_for('billing'))

    plan_prices = {p: get_plan_price(p) for p in allowed_plans}
    return render_template('pages/billing.html', user=user, customer=customer, plan_prices=plan_prices, allowed_plans=allowed_plans, now=datetime.utcnow())


@app.route('/courses/book/<int:course_id>', methods=['POST'])
def book_course(course_id):
    if not login_required():
        flash('Please login first to book a class.', 'error')
        return redirect(url_for('login'))

    user = get_current_user()
    course = Course.query.get_or_404(course_id)
    session_id = request.form.get('session_id')
    session_obj = ClassSession.query.get(session_id) if session_id else None

    if session_obj:
        booking_date = session_obj.session_date
        booking_time = session_obj.session_time
        capacity = session_obj.capacity
        if session_obj.status != 'Open':
            flash('This class session is not currently open for booking.', 'error')
            return redirect(url_for('courses', date=booking_date))
    else:
        booking_date = request.form.get('booking_date')
        booking_time = request.form.get('booking_time')
        capacity = course.capacity or 12

    if not booking_date or not booking_time:
        flash('Please choose a date and time before booking.', 'error')
        return redirect(url_for('courses'))

    duplicate = Booking.query.filter_by(user_id=user.id, course_id=course.id, booking_date=booking_date, booking_time=booking_time, status='Confirmed').first()
    if duplicate:
        flash('You have already booked this class time.', 'error')
        return redirect(url_for('courses', date=booking_date))

    existing_count = Booking.query.filter_by(course_id=course.id, booking_date=booking_date, booking_time=booking_time, status='Confirmed').count()
    if existing_count >= capacity:
        flash('This class time is full. Please choose another date or time.', 'error')
        return redirect(url_for('courses', date=booking_date))

    customer = get_or_create_customer(user)
    discount = customer.discount_percent or 0
    course_price = course.price or 0
    charge = round(course_price * (1 - discount / 100), 2)

    if charge > 0 and (customer.balance or 0) < charge:
        flash(f'Insufficient balance (£{customer.balance:.2f}). You need £{charge:.2f} to book this class. Please top up your balance.', 'error')
        return redirect(url_for('billing'))

    booking = Booking()
    booking.user_id = user.id
    booking.course_id = course.id
    booking.session_id = session_obj.id if session_obj is not None else None
    booking.booking_date = booking_date
    booking.booking_time = booking_time
    booking.amount_charged = charge

    if charge > 0:
        customer.balance = round((customer.balance or 0) - charge, 2)

    db.session.add(booking)
    db.session.commit()
    if charge > 0:
        flash(f'Booking confirmed for {course.name} on {booking_date}. £{charge:.2f} deducted from your balance.', 'success')
    else:
        flash(f'Your booking for {course.name} on {booking_date} at {booking_time} is confirmed.', 'success')
    return redirect(url_for('customer_dashboard'))


@app.route('/booking/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    if not login_required():
        return redirect(url_for('login'))
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session.get('user_id') and session.get('role') != 'admin':
        flash('You cannot cancel this booking.', 'error')
        return redirect(url_for('customer_dashboard'))
    booking.status = 'Cancelled'
    db.session.commit()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('customer_dashboard'))


# ==================== TRAINER ROUTES ====================

@app.route('/trainer-dashboard', methods=['GET', 'POST'])
def trainer_dashboard():
    if not trainer_required():
        return redirect(url_for('index'))

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        session_date = request.form.get('session_date')
        session_time = request.form.get('session_time')
        trainer = request.form.get('trainer') or session.get('username')
        capacity = int(request.form.get('capacity') or 12)

        if not all([course_id, session_date, session_time, trainer]):
            flash('Please complete all class schedule fields.', 'error')
        else:
            db.session.add(ClassSession(course_id=course_id, session_date=session_date, session_time=session_time, trainer=trainer, capacity=capacity, created_by=session.get('username')))
            db.session.commit()
            flash('Class session created successfully.', 'success')
        return redirect(url_for('trainer_dashboard'))

    courses = Course.query.all()
    sessions = ClassSession.query.order_by(ClassSession.session_date, ClassSession.session_time).all()
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('pages/trainer-dashboard.html', courses=courses, sessions=sessions, bookings=bookings)


@app.route('/trainer/courses/add', methods=['GET', 'POST'])
def trainer_add_course():
    if not trainer_required():
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        duration = request.form.get('duration')
        schedule = request.form.get('schedule')
        instructor = request.form.get('instructor')
        image_url = request.form.get('image_url')
        capacity = request.form.get('capacity') or 12

        if not all([name, description, duration, schedule, instructor]):
            flash('All fields are required', 'error')
            return redirect(url_for('trainer_add_course'))

        price = float(request.form.get('price') or 0)
        c = Course()
        c.name = name
        c.description = description
        c.duration = int(duration or 0)
        c.schedule = schedule
        c.instructor = instructor
        c.image_url = image_url
        c.capacity = int(capacity)
        c.price = price
        db.session.add(c)
        db.session.commit()
        flash('Course created by trainer.', 'success')
        return redirect(url_for('trainer_dashboard'))

    return render_template('pages/admin-add-course.html', trainer_mode=True, trainers=[])


@app.route('/trainer/courses/<int:course_id>/edit', methods=['GET', 'POST'])
def trainer_edit_course(course_id):
    if not trainer_required():
        return redirect(url_for('index'))
    course = Course.query.get_or_404(course_id)
    if request.method == 'POST':
        course.name = request.form.get('name')
        course.description = request.form.get('description')
        course.duration = int(request.form.get('duration') or course.duration or 0)
        course.schedule = request.form.get('schedule')
        course.instructor = request.form.get('instructor')
        course.image_url = request.form.get('image_url')
        course.capacity = int(request.form.get('capacity') or course.capacity or 12)
        course.price = float(request.form.get('price') or course.price or 0)
        db.session.commit()
        flash('Course updated by trainer.', 'success')
        return redirect(url_for('trainer_dashboard'))
    return render_template('pages/admin-edit-course.html', course=course, trainer_mode=True, trainers=[])


@app.route('/session/<int:session_id>/cancel', methods=['POST'])
def cancel_session(session_id):
    if not trainer_required():
        return redirect(url_for('index'))
    sess = ClassSession.query.get_or_404(session_id)
    sess.status = 'Cancelled'
    db.session.commit()
    flash('Class session cancelled.', 'success')
    return redirect(request.referrer or url_for('trainer_dashboard'))


@app.route('/session/<int:session_id>/open', methods=['POST'])
def open_session(session_id):
    if not trainer_required():
        return redirect(url_for('index'))
    sess = ClassSession.query.get_or_404(session_id)
    sess.status = 'Open'
    db.session.commit()
    flash('Class session reopened.', 'success')
    return redirect(request.referrer or url_for('trainer_dashboard'))


# ==================== ADMIN ROUTES ====================

def admin_required():
    if session.get('role') != 'admin':
        flash('You do not have permission to access this page', 'error')
        return False
    return True


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.role == 'admin':
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials or you are not an admin', 'error')

    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
def admin_dashboard():
    if not admin_required():
        return redirect(url_for('admin_login'))
    total_users = User.query.count()
    total_courses = Course.query.count()
    total_staff = Staff.query.count()
    total_sessions = ClassSession.query.count()
    total_bookings = Booking.query.count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
    total_messages = ContactMessage.query.count()
    return render_template(
        'pages/admin-dashboard.html',
        total_users=total_users,
        total_courses=total_courses,
        total_staff=total_staff,
        total_sessions=total_sessions,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        total_messages=total_messages,
    )


@app.route('/users')
def users():
    if not admin_required():
        return redirect(url_for('index'))
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('pages/users.html', users=all_users, is_admin=True)


@app.route('/users/update-role', methods=['POST'])
def update_user_role():
    if not admin_required():
        return redirect(url_for('index'))
    user_id = request.form.get('user_id')
    role = request.form.get('role')
    if role not in ['admin', 'trainer', 'customer']:
        flash('Invalid role.', 'error')
        return redirect(url_for('users'))
    user = User.query.get_or_404(user_id)
    user.role = role
    db.session.commit()
    flash(f'{user.username} role updated to {role}.', 'success')
    return redirect(url_for('users'))


@app.route('/admin/customer/<int:user_id>/discount', methods=['POST'])
def set_customer_discount(user_id):
    if not admin_required():
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    customer = get_or_create_customer(user)
    try:
        discount = float(request.form.get('discount_percent', 0))
        discount = max(0, min(100, discount))
    except ValueError:
        discount = 0
    customer.discount_percent = discount
    db.session.commit()
    flash(f'Discount for {user.username} set to {discount:.0f}%.', 'success')
    return redirect(url_for('users'))


# ==================== ADMIN COURSE ROUTES ====================

@app.route('/admin/courses')
def admin_courses():
    if not admin_required():
        return redirect(url_for('admin_login'))
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('pages/admin-courses.html', courses=courses)


@app.route('/admin/courses/add', methods=['GET', 'POST'])
def admin_add_course():
    if not admin_required():
        return redirect(url_for('admin_login'))
    trainers = User.query.filter_by(role='trainer').order_by(User.username).all()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        duration = request.form.get('duration')
        schedule = request.form.get('schedule')
        image_url = request.form.get('image_url')
        capacity = int(request.form.get('capacity') or 12)
        price = float(request.form.get('price') or 0)
        trainer_id = request.form.get('trainer_id') or None
        trainer_user = User.query.get(int(trainer_id)) if trainer_id else None
        instructor = (trainer_user.full_name or trainer_user.username) if trainer_user else ''
        if not all([name, description, duration, schedule, trainer_id]):
            flash('All fields are required, including a trainer.', 'error')
            return render_template('pages/admin-add-course.html', trainer_mode=False, trainers=trainers)
        course = Course()
        course.name = name
        course.description = description
        course.duration = int(duration)
        course.schedule = schedule
        course.instructor = instructor
        course.trainer_id = int(trainer_id)
        course.image_url = image_url
        course.capacity = capacity
        course.price = price
        db.session.add(course)
        db.session.commit()
        flash('Course created.', 'success')
        return redirect(url_for('admin_courses'))
    return render_template('pages/admin-add-course.html', trainer_mode=False, trainers=trainers)


@app.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])
def admin_edit_course(course_id):
    if not admin_required():
        return redirect(url_for('admin_login'))
    course = Course.query.get_or_404(course_id)
    trainers = User.query.filter_by(role='trainer').order_by(User.username).all()
    if request.method == 'POST':
        trainer_id = request.form.get('trainer_id') or None
        trainer_user = User.query.get(int(trainer_id)) if trainer_id else None
        course.name = request.form.get('name', course.name)
        course.description = request.form.get('description', course.description)
        course.duration = int(request.form.get('duration') or course.duration)
        course.schedule = request.form.get('schedule', course.schedule)
        course.trainer_id = int(trainer_id) if trainer_id else course.trainer_id
        course.instructor = (trainer_user.full_name or trainer_user.username) if trainer_user else course.instructor
        course.image_url = request.form.get('image_url', course.image_url)
        course.capacity = int(request.form.get('capacity') or course.capacity or 12)
        course.price = float(request.form.get('price') or course.price or 0)
        db.session.commit()
        flash('Course updated.', 'success')
        return redirect(url_for('admin_courses'))
    return render_template('pages/admin-edit-course.html', course=course, trainer_mode=False, trainers=trainers)


@app.route('/admin/courses/<int:course_id>/delete', methods=['POST'])
def admin_delete_course(course_id):
    if not admin_required():
        return redirect(url_for('admin_login'))
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted.', 'success')
    return redirect(url_for('admin_courses'))


# ==================== ADMIN SESSION ROUTES ====================

@app.route('/admin/sessions')
def admin_sessions():
    if not admin_required():
        return redirect(url_for('admin_login'))
    all_sessions = ClassSession.query.order_by(ClassSession.session_date.desc(), ClassSession.session_time).all()
    courses = Course.query.order_by(Course.name).all()
    return render_template('pages/admin-sessions.html', sessions=all_sessions, courses=courses)


@app.route('/admin/sessions/add', methods=['POST'])
def admin_add_session():
    if not admin_required():
        return redirect(url_for('admin_login'))
    course_id = request.form.get('course_id')
    session_date = request.form.get('session_date')
    session_time = request.form.get('session_time')
    capacity = int(request.form.get('capacity') or 12)
    if not all([course_id, session_date, session_time]):
        flash('Course, date and time are all required.', 'error')
        return redirect(url_for('admin_sessions'))
    course = Course.query.get_or_404(course_id)
    if not course.trainer_id:
        flash('This course has no assigned trainer. Please assign a trainer to the course first.', 'error')
        return redirect(url_for('admin_sessions'))
    new_session = ClassSession(
        course_id=course.id,
        session_date=session_date,
        session_time=session_time,
        trainer=course.instructor,
        capacity=capacity,
        created_by=session.get('username')
    )
    db.session.add(new_session)
    db.session.commit()
    flash('Session created.', 'success')
    return redirect(url_for('admin_sessions'))


@app.route('/admin/sessions/<int:session_id>/delete', methods=['POST'])
def admin_delete_session(session_id):
    if not admin_required():
        return redirect(url_for('admin_login'))
    sess = ClassSession.query.get_or_404(session_id)
    db.session.delete(sess)
    db.session.commit()
    flash('Session deleted.', 'success')
    return redirect(url_for('admin_sessions'))


# ==================== ADMIN STAFF ROUTES ====================

@app.route('/admin/staff')
def admin_staff():
    if not admin_required():
        return redirect(url_for('admin_login'))
    staff = Staff.query.order_by(Staff.name).all()
    return render_template('pages/admin-staff.html', staff=staff)


@app.route('/admin/staff/add', methods=['GET', 'POST'])
def admin_add_staff():
    if not admin_required():
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        bio = request.form.get('bio')
        photo_url = request.form.get('photo_url')
        if not all([name, role, bio, photo_url]):
            flash('All fields are required.', 'error')
            return redirect(url_for('admin_add_staff'))
        db.session.add(Staff(name=name, role=role, bio=bio, photo_url=photo_url))
        db.session.commit()
        flash('Trainer added.', 'success')
        return redirect(url_for('admin_staff'))
    return render_template('pages/admin-add-staff.html')


@app.route('/admin/staff/<int:staff_id>/edit', methods=['GET', 'POST'])
def admin_edit_staff(staff_id):
    if not admin_required():
        return redirect(url_for('admin_login'))
    member = Staff.query.get_or_404(staff_id)
    if request.method == 'POST':
        member.name = request.form.get('name', member.name)
        member.role = request.form.get('role', member.role)
        member.bio = request.form.get('bio', member.bio)
        member.photo_url = request.form.get('photo_url', member.photo_url)
        db.session.commit()
        flash('Trainer updated.', 'success')
        return redirect(url_for('admin_staff'))
    return render_template('pages/admin-edit-staff.html', staff=member)


@app.route('/admin/staff/<int:staff_id>/delete', methods=['POST'])
def admin_delete_staff(staff_id):
    if not admin_required():
        return redirect(url_for('admin_login'))
    member = Staff.query.get_or_404(staff_id)
    db.session.delete(member)
    db.session.commit()
    flash('Trainer deleted.', 'success')
    return redirect(url_for('admin_staff'))


# ==================== ADMIN HOURS ROUTES ====================

@app.route('/admin/hours')
def admin_hours():
    if not admin_required():
        return redirect(url_for('admin_login'))
    hours = OpeningHours.query.order_by(OpeningHours.id).all()
    return render_template('pages/admin-hours.html', hours=hours)


@app.route('/admin/hours/<int:hours_id>/edit', methods=['GET', 'POST'])
def admin_edit_hours(hours_id):
    if not admin_required():
        return redirect(url_for('admin_login'))
    hours = OpeningHours.query.get_or_404(hours_id)
    if request.method == 'POST':
        hours.opening_time = request.form.get('opening_time', hours.opening_time)
        hours.closing_time = request.form.get('closing_time', hours.closing_time)
        db.session.commit()
        flash('Opening hours updated.', 'success')
        return redirect(url_for('admin_hours'))
    return render_template('pages/admin-edit-hours.html', hours=hours)


# ==================== ADMIN BILLING ROUTE ====================

@app.route('/admin/billing')
def admin_billing():
    if not admin_required():
        return redirect(url_for('admin_login'))
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
    return render_template('pages/admin-billing.html', payments=payments, total_revenue=total_revenue)


# ==================== ADMIN BOOKINGS ROUTE ====================

@app.route('/admin/bookings')
def admin_bookings():
    if not admin_required():
        return redirect(url_for('admin_login'))
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    sessions = ClassSession.query.order_by(ClassSession.session_date.desc(), ClassSession.session_time).all()
    return render_template('pages/admin-bookings.html', bookings=bookings, sessions=sessions)


@app.route('/admin/booking/<int:booking_id>/<action>', methods=['POST'])
def admin_manage_booking(booking_id, action):
    if not admin_required():
        return redirect(url_for('admin_login'))
    booking = Booking.query.get_or_404(booking_id)
    if action == 'confirm':
        booking.status = 'Confirmed'
        db.session.commit()
        flash('Booking confirmed.', 'success')
    elif action == 'cancel':
        booking.status = 'Cancelled'
        db.session.commit()
        flash('Booking cancelled.', 'success')
    elif action == 'delete':
        db.session.delete(booking)
        db.session.commit()
        flash('Booking deleted.', 'success')
    return redirect(url_for('admin_bookings'))


# ==================== ADMIN MESSAGES ROUTE ====================

@app.route('/admin/messages')
def admin_messages():
    if not admin_required():
        return redirect(url_for('admin_login'))
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('pages/admin-messages.html', messages=messages)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_columns()
    app.run(debug=True, port=5000)
