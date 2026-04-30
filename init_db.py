#!/usr/bin/env python
"""Initialize the database and create initial data."""

from app import app, db
from models import User, Course, Staff, OpeningHours

def init_db():
    """Create all database tables."""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created")

def create_admin():
    """Create an initial admin user."""
    with app.app_context():
        admin_exists = User.query.filter_by(username='admin').first()
        if admin_exists:
            print("✓ Admin user already exists")
            return

        print("\nCreating admin user...")
        admin = User(
            username='admin',
            email='admin@gyme.com',
            role='admin'
        )
        admin.set_password('admin123')

        try:
            db.session.add(admin)
            db.session.commit()
            print("✓ Admin user created successfully")
            print("  Username: admin")
            print("  Password: admin123")
            print("  Email: admin@gyme.com")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error creating admin user: {e}")

def create_initial_courses():
    """Create initial courses."""
    with app.app_context():
        if Course.query.first():
            print("✓ Courses already exist")
            return

        print("\nCreating initial courses...")
        courses = [
            Course(
                name='Yoga Basics',
                description='A beginner-friendly yoga class focusing on relaxation and flexibility.',
                duration=60,
                schedule='Mondays and Wednesdays, 7:00 AM',
                instructor='Sarah Johnson',
                image_url='https://fastly.picsum.photos/id/10/400/300'
            ),
            Course(
                name='HIIT Training',
                description='High-Intensity Interval Training for maximum calorie burn and fitness improvement.',
                duration=45,
                schedule='Tuesdays and Thursdays, 6:00 PM',
                instructor='Mike Chen',
                image_url='https://fastly.picsum.photos/id/11/400/300'
            ),
            Course(
                name='Strength Training',
                description='Build muscle and strength with guided weight training sessions.',
                duration=90,
                schedule='Fridays, 5:00 PM',
                instructor='Alex Rodriguez',
                image_url='https://fastly.picsum.photos/id/12/400/300'
            ),
            Course(
                name='Pilates Core',
                description='Focus on core strength and stability with Pilates exercises.',
                duration=50,
                schedule='Saturdays, 10:00 AM',
                instructor='Emma Davis',
                image_url='https://fastly.picsum.photos/id/13/400/300'
            ),
            Course(
                name='Zumba Dance',
                description='Fun and energetic dance workout combining Latin rhythms with easy-to-follow moves.',
                duration=60,
                schedule='Sundays, 11:00 AM',
                instructor='Carlos Martinez',
                image_url='https://fastly.picsum.photos/id/14/400/300'
            ),
            Course(
                name='Boxing Fitness',
                description='Learn boxing techniques while getting a full-body cardio workout.',
                duration=55,
                schedule='Mondays and Fridays, 6:30 PM',
                instructor='James Wilson',
                image_url='https://fastly.picsum.photos/id/15/400/300'
            ),
        ]

        try:
            db.session.add_all(courses)
            db.session.commit()
            print(f"✓ Created {len(courses)} courses")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error creating courses: {e}")

def create_initial_staff():
    """Create initial staff members."""
    with app.app_context():
        if Staff.query.first():
            print("✓ Staff members already exist")
            return

        print("\nCreating initial staff members...")
        staff_members = [
            Staff(
                name='Sarah Johnson',
                role='Yoga Instructor',
                bio='10+ years of experience in yoga and wellness. Certified in multiple yoga disciplines.',
                photo_url='https://via.placeholder.com/250x300'
            ),
            Staff(
                name='Mike Chen',
                role='Personal Trainer & HIIT Specialist',
                bio='Expert in high-intensity interval training and nutrition. Dedicated to helping clients achieve their goals.',
                photo_url='https://via.placeholder.com/300x350'
            ),
            Staff(
                name='Emma Davis',
                role='Pilates Instructor & Core Specialist',
                bio='Specializes in core strengthening and body conditioning. Passionate about proper form and alignment.',
                photo_url='https://via.placeholder.com/280x280'
            ),
        ]

        try:
            db.session.add_all(staff_members)
            db.session.commit()
            print(f"✓ Created {len(staff_members)} staff members")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error creating staff members: {e}")

def create_initial_opening_hours():
    """Create initial opening hours."""
    with app.app_context():
        if OpeningHours.query.first():
            print("✓ Opening hours already exist")
            return

        print("\nCreating initial opening hours...")
        hours = [
            OpeningHours(day='Monday-Friday', opening_time='06:00', closing_time='22:00'),
            OpeningHours(day='Saturday', opening_time='08:00', closing_time='20:00'),
            OpeningHours(day='Sunday', opening_time='08:00', closing_time='18:00'),
            OpeningHours(day='Holidays', opening_time='10:00', closing_time='16:00'),
        ]

        try:
            db.session.add_all(hours)
            db.session.commit()
            print(f"✓ Created opening hours for {len(hours)} day groups")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error creating opening hours: {e}")

if __name__ == '__main__':
    init_db()
    create_admin()
    create_initial_courses()
    create_initial_staff()
    create_initial_opening_hours()
    print("\n✓ Database initialization complete!")
