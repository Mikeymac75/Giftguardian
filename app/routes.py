import os
import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from . import db
from .models import Relation, Occasion, Person, Gift, PersonOccasion

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main.route('/')
def index():
    # Logic for upcoming birthdays and occasions
    today = datetime.date.today()
    people = Person.query.all()
    upcoming_events = []

    # Process Birthdays
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
            next_date = bday_next_year
        else:
            next_date = bday_this_year

        days_until = (next_date - today).days

        upcoming_events.append({
            'name': f"{person.name}'s Birthday",
            'date': next_date,
            'days_until': days_until,
            'type': 'Birthday',
            'person': person
        })

        # Process Other Occasions
        for occ in person.occasions:
            try:
                occ_this_year = datetime.date(today.year, occ.month, occ.day)
            except ValueError:
                 occ_this_year = datetime.date(today.year, 3, 1)

            if occ_this_year < today:
                try:
                    occ_next_year = datetime.date(today.year + 1, occ.month, occ.day)
                except ValueError:
                    occ_next_year = datetime.date(today.year + 1, 3, 1)
                next_occ_date = occ_next_year
            else:
                next_occ_date = occ_this_year

            occ_days_until = (next_occ_date - today).days

            upcoming_events.append({
                'name': f"{person.name}'s {occ.occasion.name}",
                'date': next_occ_date,
                'days_until': occ_days_until,
                'type': 'Occasion',
                'person': person
            })

    # Sort by days until
    upcoming_events.sort(key=lambda x: x['days_until'])

    # Get recent gifts (just the last 5 added)
    recent_gifts = Gift.query.order_by(Gift.id.desc()).limit(5).all()

    return render_template('dashboard.html', upcoming_birthdays=upcoming_events[:5], recent_gifts=recent_gifts)

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

@main.route('/people/view/<int:id>')
def person_profile(id):
    person = Person.query.get_or_404(id)
    occasions = Occasion.query.all()
    return render_template('person_profile.html', person=person, occasions=occasions)

@main.route('/people/<int:id>/occasion/add', methods=['POST'])
def add_person_occasion(id):
    person = Person.query.get_or_404(id)
    occasion_id = request.form.get('occasion_id')
    month = request.form.get('month')
    day = request.form.get('day')
    year = request.form.get('year')

    if occasion_id and month and day:
        try:
            year_val = int(year) if year else None
            new_occ = PersonOccasion(
                person_id=person.id,
                occasion_id=int(occasion_id),
                month=int(month),
                day=int(day),
                year=year_val
            )
            db.session.add(new_occ)
            db.session.commit()
            flash('Occasion added!', 'success')
        except ValueError:
            flash('Invalid date or data.', 'danger')
    else:
        flash('Missing fields.', 'warning')

    return redirect(url_for('main.person_profile', id=person.id))

@main.route('/people/occasion/delete/<int:id>', methods=['POST'])
def delete_person_occasion(id):
    occ = PersonOccasion.query.get_or_404(id)
    person_id = occ.person_id
    db.session.delete(occ)
    db.session.commit()
    flash('Occasion removed.', 'success')
    return redirect(url_for('main.person_profile', id=person_id))


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
    query = Gift.query

    # Filtering
    person_ids = request.args.getlist('person_id')
    if person_ids and '' not in person_ids:
        query = query.filter(Gift.person_id.in_(person_ids))

    occasion_id = request.args.get('occasion_id')
    if occasion_id:
        query = query.filter_by(occasion_id=occasion_id)

    year = request.args.get('year')
    if year:
        try:
            year_val = int(year)
            query = query.filter_by(year=year_val)
        except ValueError:
            pass

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    search = request.args.get('search')
    if search:
        query = query.filter(Gift.item_name.ilike(f'%{search}%'))

    # Sorting
    sort_by = request.args.get('sort_by', 'id_desc')
    if sort_by == 'price_asc':
        query = query.order_by(Gift.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Gift.price.desc())
    elif sort_by == 'name_asc':
        query = query.order_by(Gift.item_name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Gift.item_name.desc())
    else:
        # Default sort
        query = query.order_by(Gift.id.desc())

    gifts = query.all()
    people = Person.query.order_by(Person.name).all()
    occasions = Occasion.query.all()

    # Get all distinct years from gifts for the filter dropdown
    available_years = db.session.query(Gift.year).distinct().filter(Gift.year.isnot(None)).order_by(Gift.year.desc()).all()
    available_years = [y[0] for y in available_years]

    current_year = datetime.date.today().year

    if not available_years and current_year not in available_years:
        available_years.append(current_year)

    return render_template('gifts.html', gifts=gifts, people=people, occasions=occasions, current_year=current_year, available_years=available_years)

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
    if gift.image_path:
        try:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], gift.image_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            # Log the error but continue to delete the gift from DB
            current_app.logger.error(f"Error deleting image file: {e}")

    db.session.delete(gift)
    db.session.commit()
    flash('Gift deleted.', 'success')
    return redirect(url_for('main.gifts_list'))

@main.route('/stats')
def stats():
    from sqlalchemy import func

    # Filter by year if provided
    year = request.args.get('year')
    current_year = datetime.date.today().year

    query = db.session.query(
        Person.name,
        Person.id,
        func.count(Gift.id).label('total_gifts'),
        func.coalesce(func.sum(Gift.price), 0.0).label('total_spent')
    ).outerjoin(Gift, Person.id == Gift.person_id)

    if year:
        try:
            year_val = int(year)
            query = query.filter(Gift.year == year_val)
        except ValueError:
            pass

    # Group by person
    query = query.group_by(Person.id)

    # Execute query
    stats_data = query.all()

    # Get all distinct years from gifts for the filter dropdown
    available_years = db.session.query(Gift.year).distinct().filter(Gift.year.isnot(None)).order_by(Gift.year.desc()).all()
    available_years = [y[0] for y in available_years]

    if not available_years and current_year not in available_years:
        available_years.append(current_year)

    return render_template('stats.html', stats=stats_data, available_years=available_years, selected_year=year)
