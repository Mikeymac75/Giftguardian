from . import db

class Relation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    people = db.relationship('Person', backref='relation', lazy=True)

class Occasion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    gifts = db.relationship('Gift', backref='occasion', lazy=True)
    # Allows finding all people who celebrate this occasion
    person_occasions = db.relationship('PersonOccasion', backref='occasion', lazy=True)

class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    relation_id = db.Column(db.Integer, db.ForeignKey('relation.id'), nullable=True)
    birthday_month = db.Column(db.Integer, nullable=False)
    birthday_day = db.Column(db.Integer, nullable=False)
    birthday_year = db.Column(db.Integer, nullable=True)
    gifts = db.relationship('Gift', backref='person', lazy=True)
    occasions = db.relationship('PersonOccasion', backref='person', lazy=True, cascade="all, delete-orphan")

class PersonOccasion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    occasion_id = db.Column(db.Integer, db.ForeignKey('occasion.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=True)

class Gift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=True)
    occasion_id = db.Column(db.Integer, db.ForeignKey('occasion.id'), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='Idea') # Idea, Bought, Given
    image_path = db.Column(db.String(200), nullable=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
