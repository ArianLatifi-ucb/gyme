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
    return render_template('pages/courses.html', courses=courses, sessions=sessions, selected_date=selected_date, all_session_dates=all_session_dates)


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
                return redirect(url_for('admin_login'))
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

    courses = Course.query.limit(3).all()
    bookings = Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).all()
    return render_template('pages/customer-dashboard.html', user=user, courses=courses, bookings=bookings)


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

    selected_plan = request.args.get('plan') or user.membership_plan or 'Basic' #bug:AttributeError: 'User' object has no attribute 'membership_plan'
    allowed_plans = ['Basic', 'Pro', 'Pro Plus']
    if selected_plan not in allowed_plans:
        selected_plan = 'Basic'
    amount = get_plan_price(selected_plan)

    if request.method == 'POST':
        selected_plan = request.form.get('plan', selected_plan)
        amount = get_plan_price(selected_plan)
        payment_method = request.form.get('payment_method', 'Demo Card')
        cardholder_name = request.form.get('cardholder_name')
        billing_email = request.form.get('billing_email') or user.email

        payment = Payment(
            user_id=user.id,
            plan=selected_plan,
            amount=amount,
            payment_method=payment_method,
            cardholder_name=cardholder_name,
            billing_email=billing_email,
            status='Paid'
        )
        user.membership_plan = selected_plan

        try:
            db.session.add(payment)
            db.session.commit()
            flash(f'Payment successful. Your {selected_plan} membership is now active.', 'success')
            return redirect(url_for('customer_dashboard'))
        except Exception:
            db.session.rollback()
            flash('There was a problem saving the payment. Please try again.', 'error')

    return render_template('pages/billing.html', user=user, selected_plan=selected_plan, amount=amount)


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

    booking = Booking(user_id=user.id, course_id=course.id, session_id=session_obj.id if session_obj else None, booking_date=booking_date, booking_time=booking_time)
    db.session.add(booking)
    db.session.commit()
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

        db.session.add(Course(name=name, description=description, duration=int(duration), schedule=schedule, instructor=instructor, image_url=image_url, capacity=int(capacity)))
        db.session.commit()
        flash('Course created by trainer.', 'success')
        return redirect(url_for('trainer_dashboard'))

    return render_template('pages/admin-add-course.html', trainer_mode=True)


@app.route('/trainer/courses/<int:course_id>/edit', methods=['GET', 'POST'])
def trainer_edit_course(course_id):
    if not trainer_required():
        return redirect(url_for('index'))
    course = Course.query.get_or_404(course_id)
    if request.method == 'POST':
        course.name = request.form.get('name')
        course.description = request.form.get('description')
        course.duration = int(request.form.get('duration'))
        course.schedule = request.form.get('schedule')
        course.instructor = request.form.get('instructor')
        course.image_url = request.form.get('image_url')
        course.capacity = int(request.form.get('capacity') or course.capacity or 12)
        db.session.commit()
        flash('Course updated by trainer.', 'success')
        return redirect(url_for('trainer_dashboard'))
    return render_template('pages/admin-edit-course.html', course=course, trainer_mode=True)


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
    return render_template('admin/dashboard.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
