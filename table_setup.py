#!/usr/bin/env python3
"""
    example2.py
    
    Practice on SQL DB using SQLAlchemy
    https://www.pythoncentral.io/overview-sqlalchemys-expression-language-orm-queries/
"""

__copyright__ = '(c) 2018 Martin Boliek, All Rights Reserved'
__author__ = 'Martin Boliek'
__author_email__ = 'boliek@ieee.org'
__version__ = '0.0.1'
__date__ = '23 August 2018'
__modules__ = ''

# standard libraries
import os                   # os operations
import sys                  # system operations
import re                   # regular expressions
import json                 # json load and dump
import copy                 # copy data structures
import datetime             # date and time utilities
import time                 # time utilities
import platform             # platform specific parameters
import subprocess           # Unix subprocess
import argparse             # command line arguement parsing
from shutil import copyfile # copy

# special libraries
from sqlalchemy import *
import sqlalchemy
import boto3

# logging
import logging
from logging import debug as deb, info as inf, warning as war, error as err
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(module)s.%(funcName)s l=%(lineno)s %(levelname)s: %(message)s', 
    datefmt='%y-%m-%dT%H:%M:%S%Z')

# global parameters
AWSregion = 'us-west-2'
session = boto3.Session(region_name=AWSregion)
s3 = boto3.client('s3')
gp_obj = s3.get_object(Bucket='boliek', Key='secrets.json')
gp = json.loads(gp_obj['Body'].read())

queue_name = gp['queue_name']
queue_url = gp['queue_url']

# database setup
# mysql://username:password@server/db
mysql = "mysql://{user}:{password}@{server}/{database}".format(
    user=gp['user'], 
    password=gp['password'],
    server=gp['server'],
    database=gp['database']
)
db = create_engine(mysql, echo=False)
#db = create_engine('sqlite:///content_safety.db', echo=False)
metadata = MetaData(db)


# ------------------------------------------------------------------------------
def run(statement, text=None):
    if text != None: print(text)
    rs = statement.execute()
    for row in rs: print(row)
    print("----")


# ------------------------------------------------------------------------------
def create_tables():
    """ Create all four tables for the Content Safety demonstration.
        This is the schema for all the tables.
    """
    inf("Creating tables")
    
    pinners = Table('pinners', metadata,
        Column('pinner_id', Integer, primary_key=True),
        Column('name', String(40)),
        Column('email', String(40))
    )
    pinners.create()
    
    contents = Table('contents', metadata,
        Column('content_id', Integer, primary_key=True),
        Column('url', String(80)),
        Column('display_status', String(20)), # good, objectionable, copyright
        Column('pinner_id', Integer, ForeignKey('pinners.pinner_id'))
    )
    contents.create()

    reviewers = Table('reviewers', metadata,
        Column('reviewer_id', Integer, primary_key=True),
        Column('name', String(40)),
        Column('email', String(40))
    )
    reviewers.create()

    complaints = Table('complaints', metadata,
        Column('complaint_id', Integer, primary_key=True),
        Column('complaint_timestamp', DateTime), # when the complaint was filed
        Column('complaint_type', String(80)), # objectionable, copyright
        Column('process_status', String(20)), # complaint, review, done
        Column('display_status', String(20)), # good, objectionable, copyright
        Column('review_timestamp', DateTime), # when the compliant was resolved
        Column('pinner_id', Integer, ForeignKey('pinners.pinner_id')),
        Column('reviewer_id', Integer, ForeignKey('reviewers.reviewer_id')),
        Column('content_id', Integer, ForeignKey('contents.content_id'))
    )
    complaints.create()
    
    # could create a table of "near by" images and/or near by features and 
    # include these in the review


# ------------------------------------------------------------------------------
def load_tables():
    """ Load the content and pinners tables
    """
    inf("Loading tables")
    
    m_url = 'https://s3-us-west-2.amazonaws.com/boliek-public/animals/'
    
    pinners = Table('pinners', metadata, autoload=True)
    i = pinners.insert()
    i.execute({'name': 'Mary', 'email': 'mary@example.com'},
              {'name': 'John', 'email': 'john@whatits.com'},
              {'name': 'Susan', 'email': 'susan@gadit.com'},
              {'name': 'Carl', 'email': 'carl@where.com'}
    )

    contents = Table('contents', metadata, autoload=True)
    i = contents.insert()
    i.execute({'url': m_url + 'cat0.jpg', 'display_status': 'good', 'pinner_id': 4},
              {'url': m_url + 'cat1.jpg', 'display_status': 'good', 'pinner_id': 4},
              {'url': m_url + 'cat2.jpg', 'display_status': 'good', 'pinner_id': 1},
              {'url': m_url + 'cat3.jpg', 'display_status': 'good', 'pinner_id': 4},
              {'url': m_url + 'dog0.jpg', 'display_status': 'good', 'pinner_id': 1},
              {'url': m_url + 'dog1.jpg', 'display_status': 'good', 'pinner_id': 1},
              {'url': m_url + 'dog2.jpg', 'display_status': 'good', 'pinner_id': 2},
              {'url': m_url + 'dog3.jpg', 'display_status': 'good', 'pinner_id': 2},
              {'url': m_url + 'reptile0.jpg', 'display_status': 'good', 'pinner_id': 1},
              {'url': m_url + 'reptile1.jpg', 'display_status': 'good', 'pinner_id': 2},
              {'url': m_url + 'reptile2.jpg', 'display_status': 'good', 'pinner_id': 3},
              {'url': m_url + 'reptile3.jpg', 'display_status': 'good', 'pinner_id': 3}
    )

    reviewers = Table('reviewers', metadata, autoload=True)
    i = reviewers.insert()
    i.execute({'name': 'Alice', 'email': 'alice@example.com'},
              {'name': 'Bob', 'email': 'bob@whatits.com'},
              {'name': 'Carol', 'email': 'carol@gadit.com'}
    )


# ------------------------------------------------------------------------------
def test_db():
    try: pinners = Table('pinners', metadata, autoload=True)
    except sqlalchemy.exc.NoSuchTableError:
        war("no pinners table")
        create_tables()
        load_tables()
        try: pinners = Table('pinners', metadata, autoload=True)
        except:
            err("could not open pinners table")
            exit(-1)
    contents = Table('contents', metadata, autoload=True)
    complaints = Table('complaints', metadata, autoload=True)
    reviewers = Table('reviewers', metadata, autoload=True)
    
    rs = pinners.select()
    run(rs, text='pinners')

    rs = contents.select()
    run(rs, text='contents')
    
    rs = complaints.select()
    run(rs, text='complaints')
    
    rs = reviewers.select()
    run(rs, text='reviewers')
    
    rs = join(pinners, contents).select()
    run(rs, text='join contents')
    
    rs = select([pinners.c.name, contents.c.url], and_(pinners.c.name == 'Mary', pinners.c.pinner_id == contents.c.pinner_id))
    run(rs, text='Mary contents')
    
    rs = select([pinners.c.pinner_id, contents.c.url, contents.c.content_id], \
        and_(pinners.c.pinner_id == 3, pinners.c.pinner_id == contents.c.pinner_id))
    run(rs, text='3 contents')

    
# ------------------------------------------------------------------------------
def add_complaint():
    """ Mary objects to reptile2.jpg
    """
    complaint = {
        'complaint_timestamp': datetime.datetime.now(),
        'complaint_type': 'objectionable',
        'process_status': 'complaint',
        'display_status': 'good',
        'pinner_id': 4,
        'content_id': 11
    } 
    complaints = Table('complaints', metadata, autoload=True)
    i = complaints.insert()
    out = i.execute(complaint)
    complaint['complaint_id'] = out.lastrowid
    
    print("complaint_id {}".format(complaint['complaint_id']))

    # get the value from the db
    rs = complaints.select().where(complaints.c.complaint_id == complaint['complaint_id'])
    rrs = rs.execute()
    for r in rrs:
        rcomplaint = dict(r)
    print("length {}, value {}".format(len(rcomplaint), rcomplaint))
    
    # now update the value
    rs = complaints.update().where(complaints.c.complaint_id == complaint['complaint_id']).\
                    values(reviewer_id=2, process_status='done')
    rs.execute()
    
    rs = complaints.select()
    run(rs, text='complaints')
    
    # now delete all entries
    rs =  complaints.delete()
    rs.execute()
    
    rs = complaints.select()
    run(rs, text='complaints')

    
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    inf("-- db.py --")
    test_db()
    add_complaint()
    