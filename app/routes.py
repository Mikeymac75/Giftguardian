import os
import datetime
from werkzeug.utils import secure_filename
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, send_from_directory)
from . import db
from .models import Relation, Occasion, Person, Gift, PersonOccasion

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MONTH_NAMES = ['', 'January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']
STATUS_CYCLE = ['Idea', 'Bought', 'Given']


# ── helpers ──────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file):
    """Save an uploaded image file; return filename or None."""
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        filename = f"{timestamp}_{filename}"
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None


def delete_image(image_path):
    """Delete an uploaded image file, logging any errors."""
    if image_path:
        try:
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_path)
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            current_app.logger.error(f"Error deleting image: {e}")


def next_occurrence(today, month, day):
    """Return (next_date, days_until) for a recurring annual date."""
    try:
        this_year = datetime.date(today.year, month, day)
    except ValueError:
        this_year = datetime.date(today.year, 3, 1)   # Feb 29 fallback

    if this_year < today:
        try:
            next_date = datetime.date(today.year + 1, month, day)
        except ValueError:
            next_date = datetime.date(today.year + 1, 3, 1)
    else:
        next_date = this_year

    return next_date, (next_date - today).days


def urgency(days):
    if days == 0:
        return 'danger', 'Today!'
    if days <= 7:
        return 'danger', f'In {days} day{"s" if days != 1 else ""}'
    if days <= 30:
        return 'warning', f'In {days} days'
    return 'secondary', f'In {days} days'


def get_available_years():
    rows = (db.session.query(Gift.year)
            .distinct()
            .filter(Gift.year.isnot(None))
            .order_by(Gift.year.desc())
            .all())
    years = [r[0] for r in rows]
    current = datetime.date.today().year
    if current not in years:
        years.insert(0, current)
    return years


# ── uploads ──────────────────────────────────────────────────────────────────

@main.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


# ── dashboard ────────────────────────────────────────────────────────────────

@main.route('/')
def index():
    today = datetime.date.today()
    people = Person.query.all()
    upcoming_events = []

    for person in people:
        next_date, days = next_occurrence(today, person.birthday_month, person.birthday_day)
        age = (next_date.year - person.birthday_year) if person.birthday_year else None
        u_level, u_label = urgency(days)
        upcoming_events.append({
            'name': f"{person.name}'s Birthday",
            'date': next_date,
            'days_until': days,
            'type': 'Birthday',
            'icon': 'bi-cake2-fill',
            'person': person,
            'age': age,
            'urgency': u_level,
            'urgency_label': u_label,
        })

        for occ in person.occasions:
            next_date, days = next_occurrence(today, occ.month, occ.day)
            u_level, u_label = urgency(days)
            upcoming_events.append({
                'name': f"{person.name}'s {occ.occasion.name}",
                'date': next_date,
                'days_until': days,
                'type': occ.occasion.name,
                'icon': 'bi-calendar-heart-fill',
                'person': person,
                'age': None,
                'urgency': u_level,
                'urgency_label': u_label,
            })

    upcoming_events.sort(key=lambda x: x['days_until'])
    recent_gifts = (Gift.query
                    .filter(Gift.person_id.isnot(None))
                    .order_by(Gift.id.desc())
                    .limit(5)
                    .all())

    return render_template('dashboard.html',
                           upcoming_events=upcoming_events[:10],
                           urgent_count=sum(1 for e in upcoming_events if e['days_until'] <= 30),
                           recent_gifts=recent_gifts,
                           today=today,
                           month_names=MONTH_NAMES)


# ── settings ─────────────────────────────────────────────────────────────────

@main.route('/settings')
def settings():
    relations = Relation.query.all()
    occasions = Occasion.query.all()
    return render_template('settings.html', relations=relations, occasions=occasions)


@main.route('/settings/relation/add', methods=['POST'])
def add_relation():
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('main.settings'))
    if Relation.query.filter_by(name=name).first():
        flash('Relation already exists.', 'warning')
    else:
        db.session.add(Relation(name=name))
        db.session.commit()
        flash(f'"{name}" added.', 'success')
    return redirect(url_for('main.settings'))


@main.route('/settings/relation/delete/<int:id>', methods=['POST'])
def delete_relation(id):
    relation = Relation.query.get_or_404(id)
    if relation.people:
        flash(f'Cannot delete — {len(relation.people)} people use this relation.', 'danger')
        return redirect(url_for('main.settings'))
    db.session.delete(relation)
    db.session.commit()
    flash('Relation deleted.', 'success')
    return redirect(url_for('main.settings'))


@main.route('/settings/occasion/add', methods=['POST'])
def add_occasion():
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('main.settings'))
    if Occasion.query.filter_by(name=name).first():
        flash('Occasion already exists.', 'warning')
    else:
        db.session.add(Occasion(name=name))
        db.session.commit()
        flash(f'"{name}" added.', 'success')
    return redirect(url_for('main.settings'))


@main.route('/settings/occasion/delete/<int:id>', methods=['POST'])
def delete_occasion(id):
    occasion = Occasion.query.get_or_404(id)
    if occasion.gifts or occasion.person_occasions:
        used = len(occasion.gifts) + len(occasion.person_occasions)
        flash(f'Cannot delete — used in {used} place(s).', 'danger')
        return redirect(url_for('main.settings'))
    db.session.delete(occasion)
    db.session.commit()
    flash('Occasion deleted.', 'success')
    return redirect(url_for('main.settings'))


# ── people ────────────────────────────────────────────────────────────────────

@main.route('/people')
def people_list():
    people = Person.query.order_by(Person.name).all()
    relations = Relation.query.all()
    today = datetime.date.today()

    people_data = []
    for person in people:
        next_date, days = next_occurrence(today, person.birthday_month, person.birthday_day)
        age = (next_date.year - person.birthday_year) if person.birthday_year else None
        gift_count = Gift.query.filter_by(person_id=person.id).count()
        u_level, u_label = urgency(days)
        people_data.append({
            'person': person,
            'next_bday': next_date,
            'days_until': days,
            'age': age,
            'gift_count': gift_count,
            'urgency': u_level,
            'urgency_label': u_label,
        })

    return render_template('people.html', people_data=people_data,
                           relations=relations, month_names=MONTH_NAMES)


@main.route('/people/add', methods=['POST'])
def add_person():
    name = request.form.get('name', '').strip()
    relation_id = request.form.get('relation_id')
    month = request.form.get('month')
    day = request.form.get('day')
    year = request.form.get('year')

    if not (name and relation_id and month and day):
        flash('Missing required fields.', 'warning')
        return redirect(url_for('main.people_list'))
    try:
        new_person = Person(
            name=name,
            relation_id=int(relation_id),
            birthday_month=int(month),
            birthday_day=int(day),
            birthday_year=int(year) if year else None,
        )
        db.session.add(new_person)
        db.session.commit()
        flash(f'Added {name}!', 'success')
    except ValueError:
        flash('Invalid input.', 'danger')
    return redirect(url_for('main.people_list'))


@main.route('/people/view/<int:id>')
def person_profile(id):
    person = Person.query.get_or_404(id)
    occasions = Occasion.query.all()
    today = datetime.date.today()

    # Gift history grouped by year
    gifts = (Gift.query
             .filter_by(person_id=person.id)
             .order_by(Gift.year.desc(), Gift.id.desc())
             .all())
    gifts_by_year = {}
    for g in gifts:
        key = g.year or 'No Year'
        gifts_by_year.setdefault(key, []).append(g)
    sorted_years = sorted([k for k in gifts_by_year if k != 'No Year'], reverse=True)
    if 'No Year' in gifts_by_year:
        sorted_years.append('No Year')

    next_date, days = next_occurrence(today, person.birthday_month, person.birthday_day)
    age = (next_date.year - person.birthday_year) if person.birthday_year else None
    u_level, u_label = urgency(days)

    return render_template('person_profile.html',
                           person=person,
                           occasions=occasions,
                           gifts_by_year=gifts_by_year,
                           sorted_years=sorted_years,
                           days_until=days,
                           urgency=u_level,
                           urgency_label=u_label,
                           age=age,
                           next_bday=next_date,
                           month_names=MONTH_NAMES)


@main.route('/people/<int:id>/occasion/add', methods=['POST'])
def add_person_occasion(id):
    person = Person.query.get_or_404(id)
    occasion_id = request.form.get('occasion_id')
    month = request.form.get('month')
    day = request.form.get('day')
    year = request.form.get('year')

    if not (occasion_id and month and day):
        flash('Missing fields.', 'warning')
        return redirect(url_for('main.person_profile', id=person.id))
    try:
        db.session.add(PersonOccasion(
            person_id=person.id,
            occasion_id=int(occasion_id),
            month=int(month),
            day=int(day),
            year=int(year) if year else None,
        ))
        db.session.commit()
        flash('Occasion added!', 'success')
    except ValueError:
        flash('Invalid date.', 'danger')
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
        try:
            name = request.form.get('name', '').strip()
            relation_id = request.form.get('relation_id')
            month = request.form.get('month')
            day = request.form.get('day')
            year = request.form.get('year')

            if not (name and relation_id and month and day):
                flash('Missing required fields.', 'warning')
                return redirect(url_for('main.edit_person', id=id))

            person.name = name
            person.relation_id = int(relation_id)
            person.birthday_month = int(month)
            person.birthday_day = int(day)
            person.birthday_year = int(year) if year else None
            db.session.commit()
            flash('Person updated.', 'success')
            return redirect(url_for('main.people_list'))
        except ValueError:
            flash('Invalid input.', 'danger')

    relations = Relation.query.all()
    return render_template('edit_person.html', person=person, relations=relations,
                           month_names=MONTH_NAMES)


@main.route('/people/delete/<int:id>', methods=['POST'])
def delete_person(id):
    person = Person.query.get_or_404(id)
    db.session.delete(person)
    db.session.commit()
    flash(f'{person.name} deleted.', 'success')
    return redirect(url_for('main.people_list'))


# ── gifts ─────────────────────────────────────────────────────────────────────

@main.route('/gifts')
def gifts_list():
    # Pool gifts (unassigned — shareable ideas)
    pool_gifts = (Gift.query
                  .filter(Gift.person_id.is_(None))
                  .order_by(Gift.id.desc())
                  .all())

    # Assigned gifts with filters
    query = Gift.query.filter(Gift.person_id.isnot(None))

    person_ids = request.args.getlist('person_id')
    if person_ids and '' not in person_ids:
        query = query.filter(Gift.person_id.in_(person_ids))

    occasion_id = request.args.get('occasion_id')
    if occasion_id:
        query = query.filter_by(occasion_id=occasion_id)

    year = request.args.get('year')
    if year:
        try:
            query = query.filter_by(year=int(year))
        except ValueError:
            pass

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    search = request.args.get('search')
    if search:
        query = query.filter(Gift.item_name.ilike(f'%{search}%'))

    sort_by = request.args.get('sort_by', 'id_desc')
    sort_map = {
        'price_asc': Gift.price.asc(),
        'price_desc': Gift.price.desc(),
        'name_asc': Gift.item_name.asc(),
        'name_desc': Gift.item_name.desc(),
    }
    query = query.order_by(sort_map.get(sort_by, Gift.id.desc()))

    gifts = query.all()
    people = Person.query.order_by(Person.name).all()
    occasions = Occasion.query.all()
    available_years = get_available_years()
    current_year = datetime.date.today().year
    active_tab = 'pool' if request.args.get('tab') == 'pool' else 'gifts'

    return render_template('gifts.html',
                           gifts=gifts,
                           pool_gifts=pool_gifts,
                           people=people,
                           occasions=occasions,
                           current_year=current_year,
                           available_years=available_years,
                           active_tab=active_tab,
                           month_names=MONTH_NAMES)


@main.route('/gifts/add', methods=['POST'])
def add_gift():
    item_name = request.form.get('item_name', '').strip()
    person_id = request.form.get('person_id')
    is_pool = request.form.get('is_pool') == '1'
    occasion_id = request.form.get('occasion_id')
    price = request.form.get('price')
    year = request.form.get('year')
    status = request.form.get('status', 'Idea')
    notes = request.form.get('notes', '').strip() or None
    image_url = request.form.get('image_url', '').strip() or None

    if not item_name:
        flash('Item name is required.', 'warning')
        return redirect(url_for('main.gifts_list'))

    if not is_pool and not person_id:
        flash('Please select a person or add to the Gift Pool.', 'warning')
        return redirect(url_for('main.gifts_list'))

    image_path = save_upload(request.files.get('image'))

    new_gift = Gift(
        item_name=item_name,
        person_id=int(person_id) if person_id else None,
        occasion_id=int(occasion_id) if occasion_id else None,
        price=float(price) if price else None,
        year=int(year) if year else None,
        status=status,
        image_path=image_path,
        image_url=image_url,
        notes=notes,
    )
    db.session.add(new_gift)
    db.session.commit()

    if is_pool or not person_id:
        flash('Added to Gift Pool!', 'success')
        return redirect(url_for('main.gifts_list', tab='pool'))
    flash('Gift added!', 'success')
    return redirect(url_for('main.gifts_list'))


@main.route('/gifts/pool/assign/<int:id>', methods=['POST'])
def assign_pool_gift(id):
    """Copy a pool gift to a specific person (pool gift stays for reuse)."""
    pool_gift = Gift.query.get_or_404(id)
    person_id = request.form.get('person_id')
    if not person_id:
        flash('Please select a person.', 'warning')
        return redirect(url_for('main.gifts_list', tab='pool'))

    person = Person.query.get_or_404(int(person_id))
    new_gift = Gift(
        item_name=pool_gift.item_name,
        person_id=person.id,
        occasion_id=pool_gift.occasion_id,
        price=pool_gift.price,
        year=pool_gift.year or datetime.date.today().year,
        status='Idea',
        image_path=pool_gift.image_path,
        image_url=pool_gift.image_url,
        notes=pool_gift.notes,
    )
    db.session.add(new_gift)
    db.session.commit()
    flash(f'Gift assigned to {person.name}!', 'success')
    return redirect(url_for('main.gifts_list', tab='pool'))


@main.route('/gifts/<int:id>/status', methods=['POST'])
def toggle_gift_status(id):
    """Cycle gift status: Idea → Bought → Given → Idea."""
    gift = Gift.query.get_or_404(id)
    idx = STATUS_CYCLE.index(gift.status) if gift.status in STATUS_CYCLE else 0
    gift.status = STATUS_CYCLE[(idx + 1) % len(STATUS_CYCLE)]
    db.session.commit()
    return redirect(request.referrer or url_for('main.gifts_list'))


@main.route('/gifts/edit/<int:id>', methods=['GET', 'POST'])
def edit_gift(id):
    gift = Gift.query.get_or_404(id)
    if request.method == 'POST':
        gift.item_name = request.form.get('item_name', '').strip()
        person_id = request.form.get('person_id')
        gift.person_id = int(person_id) if person_id else None
        occasion_id = request.form.get('occasion_id')
        gift.occasion_id = int(occasion_id) if occasion_id else None
        price = request.form.get('price')
        gift.price = float(price) if price else None
        year = request.form.get('year')
        gift.year = int(year) if year else None
        gift.status = request.form.get('status', 'Idea')
        gift.notes = request.form.get('notes', '').strip() or None
        gift.image_url = request.form.get('image_url', '').strip() or None

        new_path = save_upload(request.files.get('image'))
        if new_path:
            delete_image(gift.image_path)
            gift.image_path = new_path

        db.session.commit()
        flash('Gift updated.', 'success')
        return redirect(url_for('main.gifts_list'))

    people = Person.query.order_by(Person.name).all()
    occasions = Occasion.query.all()
    return render_template('edit_gift.html', gift=gift, people=people,
                           occasions=occasions, month_names=MONTH_NAMES)


@main.route('/gifts/delete/<int:id>', methods=['POST'])
def delete_gift(id):
    gift = Gift.query.get_or_404(id)
    delete_image(gift.image_path)
    db.session.delete(gift)
    db.session.commit()
    flash('Gift deleted.', 'success')
    return redirect(request.referrer or url_for('main.gifts_list'))


# ── stats ─────────────────────────────────────────────────────────────────────

@main.route('/stats')
def stats():
    from sqlalchemy import func

    year = request.args.get('year')

    query = (db.session.query(
                 Person.name,
                 Person.id,
                 func.count(Gift.id).label('total_gifts'),
                 func.coalesce(func.sum(Gift.price), 0.0).label('total_spent')
             )
             .outerjoin(Gift, Person.id == Gift.person_id))

    if year:
        try:
            query = query.filter(Gift.year == int(year))
        except ValueError:
            pass

    stats_data = query.group_by(Person.id).order_by(Person.name).all()
    available_years = get_available_years()

    return render_template('stats.html',
                           stats=stats_data,
                           available_years=available_years,
                           selected_year=year)
