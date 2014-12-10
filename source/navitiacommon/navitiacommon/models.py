# encoding: utf-8

#  Copyright (c) 2001-2014, Canal TP and/or its affiliates. All rights reserved.
#
# This file is part of Navitia,
#     the software to build cool stuff with public transport.
#
# Hope you'll enjoy and contribute to this project,
#     powered by Canal TP (www.canaltp.fr).
# Help us simplify mobility and open public transport:
#     a non ending quest to the responsive locomotion way of traveling!
#
# LICENCE: This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Stay tuned using
# twitter @navitia
# IRC #navitia on freenode
# https://groups.google.com/d/forum/navitia
# www.navitia.io

import uuid
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2.types import Geography
from flask import current_app
from sqlalchemy.orm import load_only, backref, aliased
from datetime import datetime
from sqlalchemy import func, and_
from navitiacommon import default_values

db = SQLAlchemy()

class TimestampMixin(object):
    created_at = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(), default=None, onupdate=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.Text, unique=True, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    keys = db.relationship('Key', backref='user', lazy='dynamic')

    authorizations = db.relationship('Authorization', backref='user',
                                     lazy='joined')

    def __init__(self, login=None, email=None, keys=None, authorizations=None):
        self.login = login
        self.email = email
        if keys:
            self.keys = keys
        if authorizations:
            self.authorizations = authorizations

    def __repr__(self):
        return '<User %r>' % self.email

    def add_key(self, app_name, valid_until=None):
        """
        génére une nouvelle clé pour l'utilisateur
        et l'ajoute à sa liste de clé
        c'est à l'appelant de commit la transaction
        :return la clé généré
        """
        key = Key(valid_until=valid_until)
        key.token = str(uuid.uuid4())
        key.app_name = app_name
        self.keys.append(key)
        db.session.add(key)
        return key

    @classmethod
    def get_from_token(cls, token, valid_until):
        query = cls.query.join(Key).filter(Key.token == token,
                                          (Key.valid_until > valid_until)
                                          | (Key.valid_until == None))
        res = query.first()
        return res

    def has_access(self, instance_id, api_name):
        query = Instance.query.join(Authorization, Api)\
            .filter(Instance.id == instance_id,
                    Api.name == api_name,
                    Authorization.user_id == self.id)

        return query.count() > 0


class Key(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                        nullable=False)
    token = db.Column(db.Text, unique=True, nullable=False)
    app_name = db.Column(db.Text, nullable=True)
    valid_until = db.Column(db.Date)

    def __init__(self, token=None, user_id=None, valid_until=None):
        self.token = token
        self.user_id = user_id
        self.valid_until = valid_until

    def __repr__(self):
        return '<Key %r>' % self.token

    @classmethod
    def get_by_token(cls, token):
        return cls.query.filter_by(token=token).first()

class Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    is_free = db.Column(db.Boolean, default=False, nullable=False)

    authorizations = db.relationship('Authorization', backref=backref('instance', lazy='joined'),
            lazy='dynamic')

    jobs = db.relationship('Job', backref='instance', lazy='dynamic')
    # ============================================================
    # params for jormungandr
    # ============================================================
    #the scenario used by jormungandr, by default we use the default scenario (clever isn't it?)
    scenario = db.Column(db.Text, nullable=False, default='default')

    #order of the journey, this order is for clockwise request, else it is reversed
    journey_order = db.Column(db.Enum('arrival_time', 'departure_time', name='journey_order'),
                              default=default_values.journey_order, nullable=False)

    max_walking_duration_to_pt = db.Column(db.Integer, default=default_values.max_walking_duration_to_pt, nullable=False)

    max_bike_duration_to_pt = db.Column(db.Integer, default=default_values.max_bike_duration_to_pt, nullable=False)

    max_bss_duration_to_pt = db.Column(db.Integer, default=default_values.max_bss_duration_to_pt, nullable=False)

    max_car_duration_to_pt = db.Column(db.Integer, default=default_values.max_car_duration_to_pt, nullable=False)

    walking_speed = db.Column(db.Float, default=default_values.walking_speed, nullable=False)

    bike_speed = db.Column(db.Float, default=default_values.bike_speed, nullable=False)

    bss_speed = db.Column(db.Float, default=default_values.bss_speed, nullable=False)

    car_speed = db.Column(db.Float, default=default_values.car_speed, nullable=False)

    max_nb_transfers = db.Column(db.Integer, default=default_values.max_nb_transfers, nullable=False)

    destineo_min_tc_with_car = db.Column(db.Integer, default=default_values.destineo_min_tc_with_car, nullable=False)

    destineo_min_tc_with_bike = db.Column(db.Integer, default=default_values.destineo_min_tc_with_bike, nullable=False)

    destineo_min_tc_with_bss = db.Column(db.Integer, default=default_values.destineo_min_tc_with_bss, nullable=False)

    destineo_min_bike = db.Column(db.Integer, default=default_values.destineo_min_bike, nullable=False)

    destineo_min_bss = db.Column(db.Integer, default=default_values.destineo_min_bss, nullable=False)

    destineo_min_car = db.Column(db.Integer, default=default_values.destineo_min_car, nullable=False)

    factor_too_long_journey = db.Column(db.Float, default=default_values.factor_too_long_journey, nullable=False)

    min_duration_too_long_journey = db.Column(db.Integer, default=default_values.min_duration_too_long_journey, \
            nullable=False)


    def __init__(self, name=None, is_free=False, authorizations=None,
                 jobs=None):
        self.name = name
        self.is_free = is_free
        if authorizations:
            self.authorizations = authorizations
        if jobs:
            self.jobs = jobs

    def last_datasets(self, nb_dataset=1):
        """
        return the n last dataset of each family type loaded for this instance
        """
        family_types = db.session.query(func.distinct(DataSet.family_type)) \
            .filter(Instance.id == self.id) \
            .all()

        result = []
        for family_type in family_types:
            data_sets = db.session.query(DataSet) \
                .join(Job) \
                .join(Instance) \
                .filter(Instance.id == self.id, DataSet.family_type == family_type, Job.state == 'done') \
                .order_by(Job.created_at.desc()) \
                .limit(nb_dataset) \
                .all()
            result += data_sets
        return result

    @classmethod
    def get_by_name(cls, name):
        res = cls.query.filter_by(name=name).first()
        return res

    def __repr__(self):
        return '<Instance %r>' % self.name


class Api(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)

    authorizations = db.relationship('Authorization', backref=backref('api', lazy='joined'),
                                     lazy='dynamic')

    def __init__(self, name=None):
        self.name = name

    def __repr__(self):
        return '<Api %r>' % self.name


class Authorization(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                        primary_key=True, nullable=False)
    instance_id = db.Column(db.Integer,
                            db.ForeignKey('instance.id'),
                            primary_key=True, nullable=False)
    api_id = db.Column(db.Integer,
                       db.ForeignKey('api.id'), primary_key=True,
                       nullable=False)

    def __init__(self, user_id=None, instance_id=None, api_id=None):
        self.user_id = user_id
        self.instance_id = instance_id
        self.api_id = api_id

    def __repr__(self):
        return '<Authorization %r-%r-%r>' \
                % (self.user_id, self.instance_id, self.api_id)


class Job(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    task_uuid = db.Column(db.Text)
    instance_id = db.Column(db.Integer,
                            db.ForeignKey('instance.id'))

    #name is used for the ENUM name in postgreSQL
    state = db.Column(db.Enum('pending', 'running', 'done', 'failed',
                              name='job_state'))

    data_sets = db.relationship('DataSet', backref='job', lazy='dynamic',
                                cascade='delete')

    def __repr__(self):
        return '<Job %r>' % self.id


class DataSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Text, nullable=False)
    family_type = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)

    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))

    def __repr__(self):
        return '<DataSet %r>' % self.id
