#!/usr/bin/env python
"""Initialize GymE database with demo admin, trainer and member data."""

from app import app, db, ensure_member_columns
from models import User, Course, ClassSession, Staff, OpeningHours, Booking, Plan, Customer


def init_db():
    with app.app_context():
        print("Creating database tables...")
        db.drop_all()
        db.create_all()
        ensure_member_columns()
        print("✓ Database reset and tables created")


def create_users():
    with app.app_context():
        users = [
            User(username='admin', email='admin@gyme.com', role='admin'),
            User(username='trainer', email='trainer@gyme.com', role='trainer'),
            User(username='member', email='member@gyme.com', role='customer'),
        ]
        users[0].set_password('admin123')
        users[1].set_password('trainer123')
        users[2].set_password('member123')
        db.session.add_all(users)
        db.session.commit()
        print("✓ Demo users created")
        print("  Admin: admin / admin123")
        print("  Trainer: trainer / trainer123")
        print("  Member: member / member123")


def create_default_plans():
    with app.app_context():
        plans = [
            Plan(name='Basic', price=18.00, description='Access to all basic gym facilities and group classes'),
            Plan(name='Pro', price=25.00, description='Premium access with personal training sessions and priority booking'),
            Plan(name='Pro Plus', price=39.00, description='Unlimited premium access with 1-on-1 coaching and nutrition consultation'),
        ]
        db.session.add_all(plans)
        db.session.commit()
        print(f"✓ Created {len(plans)} membership plans")


def create_customer_profiles():
    with app.app_context():
        users = User.query.all()
        basic_plan = Plan.query.filter_by(name='Basic').first()

        for user in users:
            if not user.customer:
                plan_id = basic_plan.id if user.role == 'customer' else None
                customer = Customer(user_id=user.id, plan_id=plan_id, balance=0)
                db.session.add(customer)

        db.session.commit()
        print("✓ Customer profiles created for all users")


def create_initial_courses():
    with app.app_context():
        courses = [
            Course(name='Yoga Basics', description='A beginner-friendly yoga class focusing on relaxation, mobility and flexibility.', duration=60, schedule='Mondays and Wednesdays, 7:00 AM', instructor='Bimala Nepali', image_url='/static/images/course-yoga.jpg', capacity=12),
            Course(name='HIIT Training', description='High-intensity interval training for calorie burn, stamina and fitness improvement.', duration=45, schedule='Tuesdays and Thursdays, 6:00 PM', instructor='Ariyan', image_url='/static/images/course-hiit.jpg', capacity=10),
            Course(name='Strength Training', description='Build muscle and strength with guided weight training sessions.', duration=90, schedule='Fridays, 5:00 PM', instructor='Afsar Ahmed', image_url='/static/images/course-strength.jpg', capacity=8),
            Course(name='Pilates Core', description='Focus on core strength, balance, stability and controlled movement.', duration=50, schedule='Saturdays, 10:00 AM', instructor='Bimala Nepali', image_url='/static/images/course-pilates.jpg', capacity=10),
            Course(name='Zumba Dance', description='Fun and energetic dance workout combining music, movement and cardio.', duration=60, schedule='Sundays, 11:00 AM', instructor='Ariyan', image_url='/static/images/course-zumba.jpg', capacity=15),
            Course(name='Boxing Fitness', description='Learn boxing techniques while getting a full-body conditioning workout.', duration=55, schedule='Mondays and Fridays, 6:30 PM', instructor='Afsar Ahmed', image_url='/static/images/course-boxing.jpg', capacity=10),
        ]
        db.session.add_all(courses)
        db.session.commit()
        print(f"✓ Created {len(courses)} courses")



def create_initial_sessions():
    with app.app_context():
        from datetime import datetime, timedelta
        course_lookup = {course.name: course for course in Course.query.all()}
        pattern = [
            ('Yoga Basics', 1, '07:00', 'Bimala Nepali'),
            ('HIIT Training', 2, '18:00', 'Ariyan'),
            ('Strength Training', 3, '17:00', 'Afsar Ahmed'),
            ('Pilates Core', 4, '10:00', 'Bimala Nepali'),
            ('Zumba Dance', 5, '11:00', 'Ariyan'),
            ('Boxing Fitness', 6, '18:30', 'Afsar Ahmed'),
            ('Yoga Basics', 7, '09:00', 'Bimala Nepali'),
            ('HIIT Training', 8, '19:30', 'Ariyan'),
            ('Strength Training', 9, '18:00', 'Afsar Ahmed'),
        ]
        today = datetime.now().date()
        sessions = []
        for name, offset, time, trainer in pattern:
            c = course_lookup.get(name)
            if c:
                sessions.append(ClassSession(course_id=c.id, session_date=(today + timedelta(days=offset)).strftime('%Y-%m-%d'), session_time=time, trainer=trainer, capacity=c.capacity, created_by='system'))
        db.session.add_all(sessions)
        db.session.commit()
        print(f"✓ Created {len(sessions)} class sessions")


def create_demo_bookings():
    with app.app_context():
        member = User.query.filter_by(username='member').first()
        trainer = User.query.filter_by(username='trainer').first()
        sessions = ClassSession.query.limit(2).all()
        if member and sessions:
            db.session.add(Booking(user_id=member.id, course_id=sessions[0].course_id, session_id=sessions[0].id, booking_date=sessions[0].session_date, booking_time=sessions[0].session_time))
        if trainer and len(sessions) > 1:
            db.session.add(Booking(user_id=trainer.id, course_id=sessions[1].course_id, session_id=sessions[1].id, booking_date=sessions[1].session_date, booking_time=sessions[1].session_time))
        db.session.commit()
        print("✓ Demo bookings created")

def create_initial_trainers():
    with app.app_context():
        trainers = [
            Staff(name='Afsar Ahmed', role='Strength & Boxing Trainer', bio='Project Owner and trainer profile. Supports members with strength plans, boxing fitness and gym confidence.', photo_url='/static/images/trainer-afsar.jpg'),
            Staff(name='Bimala Nepali', role='Yoga & Pilates Trainer', bio='Scrum Master and trainer profile. Specialises in yoga, Pilates, mobility and beginner-friendly coaching.', photo_url='/static/images/trainer-bimala.jpg'),
            Staff(name='Ariyan', role='HIIT & Zumba Trainer', bio='Developer and trainer profile. Leads high-energy HIIT, cardio and group fitness sessions.', photo_url='/static/images/trainer-ariyan.jpg'),
        ]
        db.session.add_all(trainers)
        db.session.commit()
        print(f"✓ Created {len(trainers)} trainers")


def create_initial_opening_hours():
    with app.app_context():
        hours = [
            OpeningHours(day='Monday-Friday', opening_time='06:00', closing_time='23:00'),
            OpeningHours(day='Saturday', opening_time='08:00', closing_time='22:00'),
            OpeningHours(day='Sunday', opening_time='08:00', closing_time='22:00'),
            OpeningHours(day='Bank Holidays', opening_time='10:00', closing_time='18:00'),
        ]
        db.session.add_all(hours)
        db.session.commit()
        print(f"✓ Created opening hours")


if __name__ == '__main__':
    init_db()
    create_users()
    create_default_plans()
    create_customer_profiles()
    create_initial_courses()
    create_initial_trainers()
    create_initial_sessions()
    create_demo_bookings()
    create_initial_opening_hours()
    print("\n✓ GymE database initialization complete!")
