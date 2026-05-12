from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='customer', nullable=False)  # admin, trainer, customer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Plan(db.Model):
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=True)
    balance = db.Column(db.Float, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('customer', uselist=False, cascade='all, delete-orphan'))
    plan = db.relationship('Plan', backref=db.backref('customers', lazy=True))


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    schedule = db.Column(db.String(200), nullable=False)
    instructor = db.Column(db.String(120), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    capacity = db.Column(db.Integer, default=12, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClassSession(db.Model):
    __tablename__ = 'class_sessions'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    session_date = db.Column(db.String(20), nullable=False)
    session_time = db.Column(db.String(20), nullable=False)
    trainer = db.Column(db.String(120), nullable=False)
    capacity = db.Column(db.Integer, default=12, nullable=False)
    status = db.Column(db.String(30), default='Open', nullable=False)
    created_by = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref=db.backref('sessions', lazy=True, cascade='all, delete-orphan'))

    @property
    def confirmed_count(self):
        return Booking.query.filter_by(session_id=self.id, status='Confirmed').count()

    @property
    def seats_left(self):
        return max((self.capacity or 0) - self.confirmed_count, 0)


class Staff(db.Model):
    __tablename__ = 'staff'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.Text, nullable=False)
    photo_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OpeningHours(db.Model):
    __tablename__ = 'opening_hours'

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), unique=True, nullable=False)
    opening_time = db.Column(db.String(10), nullable=False)
    closing_time = db.Column(db.String(10), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), default='Demo Card', nullable=False)
    cardholder_name = db.Column(db.String(120), nullable=True)
    billing_email = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(30), default='Paid', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('payments', lazy=True))


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'), nullable=True)
    booking_date = db.Column(db.String(20), nullable=False)
    booking_time = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), default='Confirmed', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('bookings', lazy=True))
    course = db.relationship('Course', backref=db.backref('bookings', lazy=True))
    session = db.relationship('ClassSession', backref=db.backref('bookings', lazy=True))


class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
