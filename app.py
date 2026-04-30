from flask import Flask, render_template, request, redirect, session, url_for, flash
from models import db, User, Course, Staff, OpeningHours
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'gyme.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


@app.route('/')
def index():
    courses = Course.query.all()
    staff = Staff.query.all()
    hours = OpeningHours.query.all()
    return render_template('index.html', courses=courses, staff=staff, hours=hours)


@app.route('/courses')
def courses():
    return render_template('pages/courses.html')


@app.route('/admin')
def admin():
    return render_template('pages/admin.html')


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
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
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


@app.route('/users')
def users():
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('index'))

    all_users = User.query.all()
    return render_template('pages/users.html', users=all_users, is_admin=is_admin)


@app.route('/users/update-role', methods=['POST'])
def update_user_role():
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('index'))

    user_id = request.form.get('user_id')
    new_role = request.form.get('role')

    if new_role not in ['admin', 'customer', 'trainer']:
        flash('Invalid role', 'error')
        return redirect(url_for('users'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('users'))

    user.role = new_role
    try:
        db.session.commit()
        flash(f'Updated {user.username} role to {new_role}', 'success')
    except Exception:
        db.session.rollback()
        flash('Error updating user role', 'error')

    return redirect(url_for('users'))


@app.route('/admin-dashboard')
def admin_dashboard():
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('index'))

    total_users = User.query.count()
    total_courses = Course.query.count()
    total_staff = Staff.query.count()

    return render_template('pages/admin-dashboard.html',
                         total_users=total_users,
                         total_courses=total_courses,
                         total_staff=total_staff)


@app.route('/admin/courses')
def admin_courses():
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('index'))

    courses = Course.query.all()
    return render_template('pages/admin-courses.html', courses=courses)


@app.route('/admin/courses/add', methods=['GET', 'POST'])
def admin_add_course():
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        duration = request.form.get('duration')
        schedule = request.form.get('schedule')
        instructor = request.form.get('instructor')
        image_url = request.form.get('image_url')

        if not all([name, description, duration, schedule, instructor]):
            flash('All fields are required', 'error')
            return redirect(url_for('admin_add_course'))

        course = Course(
            name=name,
            description=description,
            duration=int(duration),
            schedule=schedule,
            instructor=instructor,
            image_url=image_url
        )

        try:
            db.session.add(course)
            db.session.commit()
            flash(f'Course "{name}" added successfully', 'success')
            return redirect(url_for('admin_courses'))
        except Exception:
            db.session.rollback()
            flash('Error adding course', 'error')

    return render_template('pages/admin-add-course.html')


@app.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])
def admin_edit_course(course_id):
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('index'))

    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        course.name = request.form.get('name')
        course.description = request.form.get('description')
        course.duration = int(request.form.get('duration'))
        course.schedule = request.form.get('schedule')
        course.instructor = request.form.get('instructor')
        course.image_url = request.form.get('image_url')

        try:
            db.session.commit()
            flash(f'Course "{course.name}" updated successfully', 'success')
            return redirect(url_for('admin_courses'))
        except Exception:
            db.session.rollback()
            flash('Error updating course', 'error')

    return render_template('pages/admin-edit-course.html', course=course)


@app.route('/admin/courses/<int:course_id>/delete', methods=['POST'])
def admin_delete_course(course_id):
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('index'))

    course = Course.query.get_or_404(course_id)
    course_name = course.name

    try:
        db.session.delete(course)
        db.session.commit()
        flash(f'Course "{course_name}" deleted successfully', 'success')
    except Exception:
        db.session.rollback()
        flash('Error deleting course', 'error')

    return redirect(url_for('admin_courses'))


@app.route('/admin/staff')
def admin_staff():
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('index'))

    staff = Staff.query.all()
    return render_template('pages/admin-staff.html', staff=staff)


@app.route('/admin/staff/add', methods=['GET', 'POST'])
def admin_add_staff():
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        bio = request.form.get('bio')
        photo_url = request.form.get('photo_url')

        if not all([name, role, bio, photo_url]):
            flash('All fields are required', 'error')
            return redirect(url_for('admin_add_staff'))

        staff = Staff(name=name, role=role, bio=bio, photo_url=photo_url)

        try:
            db.session.add(staff)
            db.session.commit()
            flash(f'Staff member "{name}" added successfully', 'success')
            return redirect(url_for('admin_staff'))
        except Exception:
            db.session.rollback()
            flash('Error adding staff member', 'error')

    return render_template('pages/admin-add-staff.html')


@app.route('/admin/staff/<int:staff_id>/edit', methods=['GET', 'POST'])
def admin_edit_staff(staff_id):
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('index'))

    staff = Staff.query.get_or_404(staff_id)

    if request.method == 'POST':
        staff.name = request.form.get('name')
        staff.role = request.form.get('role')
        staff.bio = request.form.get('bio')
        staff.photo_url = request.form.get('photo_url')

        try:
            db.session.commit()
            flash(f'Staff member "{staff.name}" updated successfully', 'success')
            return redirect(url_for('admin_staff'))
        except Exception:
            db.session.rollback()
            flash('Error updating staff member', 'error')

    return render_template('pages/admin-edit-staff.html', staff=staff)


@app.route('/admin/staff/<int:staff_id>/delete', methods=['POST'])
def admin_delete_staff(staff_id):
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('index'))

    staff = Staff.query.get_or_404(staff_id)
    staff_name = staff.name

    try:
        db.session.delete(staff)
        db.session.commit()
        flash(f'Staff member "{staff_name}" deleted successfully', 'success')
    except Exception:
        db.session.rollback()
        flash('Error deleting staff member', 'error')

    return redirect(url_for('admin_staff'))


@app.route('/admin/hours')
def admin_hours():
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('index'))

    hours = OpeningHours.query.all()
    return render_template('pages/admin-hours.html', hours=hours)


@app.route('/admin/hours/<int:hours_id>/edit', methods=['GET', 'POST'])
def admin_edit_hours(hours_id):
    is_admin = session.get('role') == 'admin'

    if not is_admin:
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('index'))

    hours = OpeningHours.query.get_or_404(hours_id)

    if request.method == 'POST':
        hours.opening_time = request.form.get('opening_time')
        hours.closing_time = request.form.get('closing_time')

        try:
            db.session.commit()
            flash(f'Opening hours for {hours.day} updated successfully', 'success')
            return redirect(url_for('admin_hours'))
        except Exception:
            db.session.rollback()
            flash('Error updating opening hours', 'error')

    return render_template('pages/admin-edit-hours.html', hours=hours)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
