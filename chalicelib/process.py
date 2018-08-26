#!/usr/bin/env python3
"""
    mb process

    pinterest logic
"""

__copyright__ = '(c) Martin Boliek, All Rights Reserved'
__author__ = 'Martin Boliek'
__author_email__ = 'martin@boliek.net'
__version__ = '0.0.1'
__date__ = '25 August 2018'
__modules__ = ''

# standard libraries
import os                   # os operations
import io                   # io operations
import sys                  # system operations
import re                   # regular expressions
import json                 # json load and dump
import copy                 # copy data structures
import time                 # time utilities
import datetime             # date and time utilities
import platform             # platform

# logging setup
import logging
from logging import debug as deb, info as inf, warning as war, error as err
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers: root.removeHandler(handler)
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(module)s.%(funcName)s l=%(lineno)s %(levelname)s: %(message)s', 
    datefmt='%y-%m-%dT%H:%M:%S%Z')

# special libraries
import boto3 
from sqlalchemy import *
import sqlalchemy

# globals
AWSregion = 'us-west-2'
session = boto3.Session(region_name=AWSregion)
s3 = boto3.client('s3')
gp_obj = s3.get_object(Bucket='boliek', Key='secrets.json')
gp = json.loads(gp_obj['Body'].read())

# s3 buckets
s3_bucket = 'animals'
s3_baseurl = 'https://s3-us-west-2.amazonaws.com/boliek-public'

# sqs queue
queue_name = gp['queue_name']
queue_url = gp['queue_url']

# database setup
mysql = "mysql+pymysql://{user}:{password}@{server}/{database}".format(
    user=gp['user'], 
    password=gp['password'],
    server=gp['server'],
    database=gp['database']
)
db = create_engine(mysql, echo=False)
#db = create_engine('sqlite:///content_safety.db', echo=False)
metadata = MetaData(db)


# ------------------------------------------------------------------------------
class DecimalEncoder(json.JSONEncoder):
    """ Helper class to convert a DynamoDB arithmetic item to JSON
    """
    def default(self, o):
        if isinstance(o, decimal.Decimal): return int(o)
        return super(DecimalEncoder, self).default(o)


# ------------------------------------------------------------------------------
def JsonPretty(jsonData):
    """ Returns a pretty version a JSON data structure
        in: jsonData
        return pretty json text
    """
    return json.dumps(jsonData, sort_keys=True, indent=2, separators=(',', ': '), cls=DecimalEncoder)


# ------------------------------------------------------------------------------
def put_sqsmessage(comp):
    """ puts a complaint message in the sqs queue
        in: complaint json
        out: sqs message
        return sqs message id
    """
    try:
        sqs = session.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=queue_name)
        response = queue.send_message(MessageBody=json.dumps(comp))
    except:
        err("cannot send message to sqs")
        return 'error'
    else:
        return response.get('MessageId')


# ------------------------------------------------------------------------------
def get_sqsmessage():
    """ gets a complaint message from the sqs queue
        in: sqs message, sqs message id
        return sqs message, sqs message id, sqs message receipt handle
    """
    try: 
        sqs = session.client('sqs')
        response = sqs.receive_message(
                                        QueueUrl=queue_url,
                                        AttributeNames=['SentTimestamp'],
                                        MaxNumberOfMessages=1,
                                        MessageAttributeNames=['All'],
                                        VisibilityTimeout=600 # ten minutes
                                        #VisibilityTimeout=10 # ten seconds
        )
    except:
        err("problem reading queue {}".format(pp['queue_name']))
        return 'error', 'error', 'error'
    else:
        # handle message
        if 'Messages' in response.keys():
            message = response['Messages'][0]
            return json.loads(message['Body']), message['MessageId'], message['ReceiptHandle']
        else: 
            return None, None, None


# ------------------------------------------------------------------------------
def delete_sqsmessage(sqs_handle):
    """ deletes an sqs message from the sqs queue
        in: sqs message id
        out: deleted sqs message
        return success
    """
    try:
        sqs = session.client('sqs')
        response = sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=sqs_handle
        )
    except: return False
    else: return True
    
    
# ------------------------------------------------------------------------------
def update_content(comp):
    """ updates content in the contents table
        in: content json
        out: updated complaint row
    """
    contents = Table('contents', metadata, autoload=True)
    rs = contents.update().where(contents.c.content_id == comp['content_id']).values(comp)
    rs.execute()


# ------------------------------------------------------------------------------
def update_complaint(comp):
    """ updates  in the complaints table
        in: complaint json
        out: updated complaint row
    """
    complaints = Table('complaints', metadata, autoload=True)
    rs = complaints.update().where(complaints.c.complaint_id == comp['complaint_id']).values(comp)
    rs.execute()


# ------------------------------------------------------------------------------
def put_complaint(comp):
    """ puts a complaint in the complaints table
        in: complaint json
        out: new complaint row
        return complaint_id
    """
    complaints = Table('complaints', metadata, autoload=True)
    rs = complaints.insert()
    out = rs.execute(comp)

    return out.lastrowid


# ------------------------------------------------------------------------------
def get_complaint(cid):
    """ queries the content table and returns a single value
        in: content_id
        return content row
    """
    complaint = None
    complaints = Table('complaints', metadata, autoload=True)
    rs = complaints.select().where(complaints.c.complaint_id == str(cid))
    rss = rs.execute()
    for row in rss: complaint = dict(row)
    
    return complaint


# ------------------------------------------------------------------------------
def get_content(cid):
    """ queries the content table and returns a single value
        in: content_id
        return content row
    """
    content = None
    contents = Table('contents', metadata, autoload=True)
    rs = contents.select().where(contents.c.content_id == str(cid))
    rss = rs.execute()
    for row in rss: content = dict(row)
    
    return content


# ------------------------------------------------------------------------------
def get_complaints_for_content(cid):
    """ queries the complaints table for all complaints about a single content
        in: content id
        return all complaints about that content
    """
    comp = []
    complaints = Table('complaints', metadata, autoload=True)
    rs = complaints.select().where(complaints.c.content_id == str(cid))
    rss = rs.execute()
    for row in rss: comp.append(dict(row))
    
    return comp


# ------------------------------------------------------------------------------
def get_reviewer_from_email(email):
    """ queries the reviewers table for reviewer with this email
        assumes a one to one mapping between reviewers and emails
        in: email
        return reviewer
    """
    reviewer = None
    reviewers = Table('reviewers', metadata, autoload=True)
    rs = reviewers.select().where(reviewers.c.email == email)
    rss = rs.execute()
    for row in rss: reviewer = dict(row)
    
    return reviewer


# ------------------------------------------------------------------------------
def get_pinner_from_email(email):
    """ queries the pinners table for pinner with this email
        assumes a one to one mapping between pinners and emails
        in: email
        return pinner
    """
    pinner = None
    pinners = Table('pinners', metadata, autoload=True)
    rs = pinners.select().where(pinners.c.email == email)
    rss = rs.execute()
    for row in rss: pinner = dict(row)
    
    return pinner


# ------------------------------------------------------------------------------
def get_pinners_list():
    """ queries the pinners table and returns the values
        return pinners list
    """
    pin = []
    pinners = Table('pinners', metadata, autoload=True)
    rs = pinners.select()
    rss = rs.execute()
    for row in rss: pin.append(dict(row))
    
    return pin


# ------------------------------------------------------------------------------
def get_reviewers_list():
    """ queries the reviewers table and returns the values
        return reviewers list
    """
    rev = []
    reviewers = Table('reviewers', metadata, autoload=True)
    rs = reviewers.select()
    rss = rs.execute()
    for row in rss: rev.append(dict(row))
    
    return rev


# ------------------------------------------------------------------------------
def get_content_list():
    """ queries the content table and returns the values
        return content list
    """
    conts = []
    contents = Table('contents', metadata, autoload=True)
    rs = contents.select()
    rss = rs.execute()
    for row in rss: conts.append(dict(row))
    
    return conts


# ------------------------------------------------------------------------------
def get_complaint_list():
    """ queries the complaint table and returns the values
        return complaint list
    """
    conts = []
    complaints = Table('complaints', metadata, autoload=True)
    rs = complaints.select()
    rss = rs.execute()
    for row in rss: conts.append(dict(row))
    
    return conts


# ------------------------------------------------------------------------------
def file_complaint(redata):
    """ handles a new complaint, creates complaint row, sends sqs message if 
        complaint is unique
        in: data from cs_submit page
        out: complaint record, SQS message if necessary
        return complaint_id
    """
    sqsmessage = True
    complaint = {}
    
    # create the complaint
    complaint['complaint_timestamp'] = datetime.datetime.now()
    complaint['complaint_type'] = 'objectionable'
    complaint['process_status'] = 'complaint'
    complaint['display_status'] = redata['display_status']
    
    pinner = get_pinner_from_email(redata['pinner'])
    complaint['pinner_id'] = pinner['pinner_id']
    
    complaint['content_id'] = int(redata['content_id'])

    # check to see if this content is already in the queue for review
    # if so, no sqs message is sent
    # we could also search on near by images or image features
    prior_complaints = get_complaints_for_content(complaint['content_id'])
    if not prior_complaints == []: 
        for p in prior_complaints:
            if p['process_status'] == 'complaint':
                sqsmessage = False
    
    # post the complaint to the table
    complaint_id = put_complaint(complaint)
    
    # post the complain to the sqs queue
    if sqsmessage:
        complaint['complaint_timestamp'] = str(complaint['complaint_timestamp'])
        complaint['complaint_id'] = complaint_id
        sqs_id = put_sqsmessage(complaint)
    
    return complaint_id


# ------------------------------------------------------------------------------
def review_complaint(redata):
    """ resolves all complaints related to a given content,
        changes display status if necessary
        in: data from review pop page
        out: update complaint record, update display status if necessary
        return success
    """
    # get data
    complaint = get_complaint(redata['complaint_id'])

    if complaint != None:
        complaint_list = get_complaints_for_content(complaint['content_id'])
        content = get_content(complaint['content_id'])
        reviewer = get_reviewer_from_email(redata['reviewer'])

        # update data
        timestamp = datetime.datetime.now()
        for c in complaint_list:
            c['review_timestamp'] = timestamp
            c['reviewer_id'] = reviewer['reviewer_id']
            c['process_status'] = 'done'

        # pull image from display if necessary
        if redata['comp'] == 'Bad':
            content['display_status'] = complaint['complaint_type']
            update_content(content)
    
            for c in complaint_list:
                c['display_status'] = complaint['complaint_type']

        for c in complaint_list:
            update_complaint(c)

    # delete sqs message
    success = delete_sqsmessage(redata['sqs_handle'])


# ------------------------------------------------------------------------------
def reset_content():
    """ changes the display_status value to 'good' for all content.
        Essentially is starts the content table fresh. 
        The complaints are untouched.
        out: update all content records
    """
    # get data
    contents = get_content_list()
    print(contents)
    
    for c in contents:
        c['display_status'] = 'good'
        update_content(c)


# ------------------------------------------------------------------------
if __name__ == '__main__':
    """ put module tests and development experiments here
    """
    pass
