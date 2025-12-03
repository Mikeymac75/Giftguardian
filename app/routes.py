import os
import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from . import db
from .models import Relation, Occasion, Person, Gift

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main.route('/')
def index():
    # Logic for upcoming birthdays
    today = datetime.date.today()
    people = Person.query.all()
    upcoming_birthdays = []

    for person in people:
        # Determine next birthday date
        try:
            bday_this_year = datetime.date(today.year, person.birthday_month, person.birthday_day)
        except ValueError:
            # Handle leap years (e.g. Feb 29 on non-leap year)
            bday_this_year = datetime.date(today.year, 3, 1)

        if bday_this_year < today:
            try:
                bday_next_year = datetime.date(today.year + 1, person.birthday_month, person.birthday_day)
            except ValueError:
                bday_next_year = datetime.date(today.year + 1, 3, 1)
            next_bday = bday_next_year
        else:
            next_bday = bday_this_year

        days_until = (next_bday - today).days

        # Only show birthdays within the next 60 days (optional filter, but good for "Upcoming")
        # Or just show top 5 sorted by days_until
        person.days_until = days_until
        upcoming_birthdays.append(person)

    # Sort by days until birthday
    upcoming_birthdays.sort(key=lambda x: x.days_until)

    # Get recent gifts (just the last 5 added)
    recent_gifts = Gift.query.order_by(Gift.id.desc()).limit(5).all()

    return render_template('dashboard.html', upcoming_birthdays=upcoming_birthdays[:5], recent_gifts=recent_gifts)

@main.route('/settings')
def settings():
    relations = Relation.query.all()
    occasions = Occasion.query.all()
    return render_template('settings.html', relations=relations, occasions=occasions)

@main.route('/settings/relation/add', methods=['POST'])
def add_relation():
    name = request.form.get('name')
    if name:
        if Relation.query.filter_by(name=name).first():
            flash('Relation already exists!', 'warning')
        else:
            new_relation = Relation(name=name)
            db.session.add(new_relation)
            db.session.commit()
            flash('Relation added successfully!', 'success')
    return redirect(url_for('main.settings'))

@main.route('/settings/relation/delete/<int:id>', methods=['POST'])
def delete_relation(id):
    relation = Relation.query.get_or_404(id)
    db.session.delete(relation)
    db.session.commit()
    flash('Relation deleted.', 'success')
    return redirect(url_for('main.settings'))

@main.route('/settings/occasion/add', methods=['POST'])
def add_occasion():
    name = request.form.get('name')
    if name:
        if Occasion.query.filter_by(name=name).first():
            flash('Occasion already exists!', 'warning')
        else:
            new_occasion = Occasion(name=name)
            db.session.add(new_occasion)
            db.session.commit()
            flash('Occasion added successfully!', 'success')
    return redirect(url_for('main.settings'))

@main.route('/settings/occasion/delete/<int:id>', methods=['POST'])
def delete_occasion(id):
    occasion = Occasion.query.get_or_404(id)
    db.session.delete(occasion)
    db.session.commit()
    flash('Occasion deleted.', 'success')
    return redirect(url_for('main.settings'))

@main.route('/people')
def people_list():
    people = Person.query.order_by(Person.name).all()
    relations = Relation.query.all()
    return render_template('people.html', people=people, relations=relations)

@main.route('/people/add', methods=['POST'])
def add_person():
    name = request.form.get('name')
    relation_id = request.form.get('relation_id')
    month = request.form.get('month')
    day = request.form.get('day')
    year = request.form.get('year')

    if name and relation_id and month and day:
        try:
             year_val = int(year) if year else None
             new_person = Person(
                 name=name,
                 relation_id=int(relation_id),
                 birthday_month=int(month),
                 birthday_day=int(day),
                 birthday_year=year_val
             )
             db.session.add(new_person)
             db.session.commit()
             flash(f'Added {name} successfully!', 'success')
        except ValueError:
             flash('Invalid input data.', 'danger')
    else:
        flash('Missing required fields.', 'warning')

    return redirect(url_for('main.people_list'))

@main.route('/people/edit/<int:id>', methods=['GET', 'POST'])
def edit_person(id):
    person = Person.query.get_or_404(id)
    if request.method == 'POST':
        person.name = request.form.get('name')
        person.relation_id = int(request.form.get('relation_id'))
        person.birthday_month = int(request.form.get('month'))
        person.birthday_day = int(request.form.get('day'))
        year = request.form.get('year')
        person.birthday_year = int(year) if year else None

        db.session.commit()
        flash('Person updated.', 'success')
        return redirect(url_for('main.people_list'))

    relations = Relation.query.all()
    return render_template('edit_person.html', person=person, relations=relations)

@main.route('/people/delete/<int:id>', methods=['POST'])
def delete_person(id):
    person = Person.query.get_or_404(id)
    db.session.delete(person)
    db.session.commit()
    flash('Person deleted.', 'success')
    return redirect(url_for('main.people_list'))

@main.route('/gifts')
def gifts_list():
    gifts = Gift.query.order_by(Gift.id.desc()).all()
    people = Person.query.order_by(Person.name).all()
    occasions = Occasion.query.all()
    current_year = datetime.date.today().year
    return render_template('gifts.html', gifts=gifts, people=people, occasions=occasions, current_year=current_year)

@main.route('/gifts/add', methods=['POST'])
def add_gift():
    item_name = request.form.get('item_name')
    person_id = request.form.get('person_id')
    occasion_id = request.form.get('occasion_id')
    price = request.form.get('price')
    year = request.form.get('year')
    status = request.form.get('status')

    if item_name and person_id and status:
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Ensure unique filename to prevent overwrites
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{timestamp}_{filename}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                image_path = filename

        new_gift = Gift(
            item_name=item_name,
            person_id=int(person_id),
            occasion_id=int(occasion_id) if occasion_id else None,
            price=float(price) if price else 0.0,
            year=int(year) if year else None,
            status=status,
            image_path=image_path
        )
        db.session.add(new_gift)
        db.session.commit()
        flash('Gift added successfully!', 'success')
    else:
        flash('Missing required fields for gift.', 'warning')

    return redirect(url_for('main.gifts_list'))

@main.route('/gifts/edit/<int:id>', methods=['GET', 'POST'])
def edit_gift(id):
    gift = Gift.query.get_or_404(id)
    if request.method == 'POST':
        gift.item_name = request.form.get('item_name')
        gift.person_id = int(request.form.get('person_id'))
        occasion_id = request.form.get('occasion_id')
        gift.occasion_id = int(occasion_id) if occasion_id else None
        price = request.form.get('price')
        gift.price = float(price) if price else 0.0
        year = request.form.get('year')
        gift.year = int(year) if year else None
        gift.status = request.form.get('status')

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{timestamp}_{filename}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

                # Delete old image if exists (optional, keeping it simple for now)
                # if gift.image_path: ...

                gift.image_path = filename

        db.session.commit()
        flash('Gift updated.', 'success')
        return redirect(url_for('main.gifts_list'))

    people = Person.query.order_by(Person.name).all()
    occasions = Occasion.query.all()
    return render_template('edit_gift.html', gift=gift, people=people, occasions=occasions)

@main.route('/gifts/delete/<int:id>', methods=['POST'])
def delete_gift(id):
    gift = Gift.query.get_or_404(id)
    # Ideally delete the image file here too
    db.session.delete(gift)
    db.session.commit()
    flash('Gift deleted.', 'success')
    return redirect(url_for('main.gifts_list'))
