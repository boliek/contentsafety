"""
    pinerest content safety demo app
    
    Create a website with chalice and lambda
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
import datetime             # date and time utilities

# special libraries
import boto3                # AWS services
from chalicelib import process

# setup chalice
from chalice import Chalice, Response           # python serverless engine
app = Chalice(app_name='pinterest_chalice')     # create app, empower decorators
app.debug = True

# setup jinja2 templates
from jinja2 import Environment, FileSystemLoader
template_dir = os.path.join(os.path.dirname(__file__), 'chalicelib', 'templates')
j2_env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True)

# sign on
print('Pinterest')


# ------------------------------------------------------------------------------
@app.route('/')
def index():
    """ splash page
    """
    mydict = {}
    t = j2_env.get_template('index.html')

    return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})


# ------------------------------------------------------------------------------
@app.route('/home')
def index():
    """ splash page
    """
    mydict = {}
    t = j2_env.get_template('index.html')

    return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})


# ------------------------------------------------------------------------------
@app.route('/pinner', methods=['GET'])
def pinner_call():
    """ pinner page with all the selectable content
    """
    contents = process.get_content_list()
    mydict = {}
    for c in contents:
        if c['display_status'] == 'good':
            mydict['cid' + str(c['content_id'])] = str(c['content_id'])
            mydict['url' + str(c['content_id'])] = c['url']
        else:
            mydict['cid' + str(c['content_id'])] = None
            mydict['url' + str(c['content_id'])] = ""
            
    # get template
    t = j2_env.get_template('pinner.html')

    return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})


# ------------------------------------------------------------------------------
@app.route('/content_safety', methods=['GET'])
def pinner_cs_call():
    """ pinner content safety complaint page
    """
    request = app.current_request
    content = process.get_content(request.query_params['content_id'])
    pinners = process.get_pinners_list()
    mydict = content
    for p in pinners:
         mydict['pinner' + str(p['pinner_id'])] = str(p['pinner_id'])
         mydict['email' + str(p['pinner_id'])] = p['email']
    # get template
    t = j2_env.get_template('pinner_cs.html')

    return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})


# ------------------------------------------------------------------------------
@app.route('/cs_submit', methods=['GET'])
def pinner_cs_submit_call():
    """ pinner submission response page
    """
    request = app.current_request
    complaint_id = process.file_complaint(request.query_params)
    t = j2_env.get_template('pinner_cs_submit.html')

    return Response(body=t.render(complaint_id=complaint_id), status_code=200, headers={'Content-Type': 'text/html'})


# ------------------------------------------------------------------------------
@app.route('/reviewer', methods=['GET'])
def reviewer_call():
    """ reviewer page
    """
    mydict = {}
    t = j2_env.get_template('reviewer.html')
    
    return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})
    
    
# ------------------------------------------------------------------------------
@app.route('/re_pop')
def reviewer_pop_call():
    """ reviewer image to review page
    """
    mydict = {}
    sqsmessage, sqs_id, sqs_handle = process.get_sqsmessage()
    
    if sqsmessage == None or sqsmessage == "error":
        t = j2_env.get_template('re_pop1.html')
        
        return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})
        
    else:
        content = process.get_content(sqsmessage['content_id'])
        reviewers = process.get_reviewers_list()
        
        for r in reviewers: mydict['email' + str(r['reviewer_id'])] = r['email']
        mydict['url'] = content['url']
        mydict['complaint_id'] = sqsmessage['complaint_id']
        mydict['sqs_handle'] = sqs_handle
        
        t = j2_env.get_template('re_pop2.html')
        
        return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})


# ------------------------------------------------------------------------------
@app.route('/re_submit')
def reviewer_submit_call():
    """ reviewer submission page
    """
    request = app.current_request
    success = process.review_complaint(request.query_params)
    
    mydict = {}
    t = j2_env.get_template('re_submit.html')
    
    return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})
    

# ------------------------------------------------------------------------------
@app.route('/manager', methods=['GET'])
def manager_call():
    """ display the complaints data
    """
    mydict = {}
    comp = []
    review = []
    done = []
    
    complaints = process.get_complaint_list()
    for c in complaints:
        c['complaint_timestamp'] = str(c['complaint_timestamp'])
        if c['review_timestamp'] != None: c['review_timestamp'] = str(c['review_timestamp'])
        if c['process_status'] == 'complaint': comp.append(c)
        elif c['process_status'] == 'review': review.append(c)
        elif c['process_status'] == 'done': done.append(c)
    mydict['complaint'] = comp
    mydict['review'] = review
    mydict['done'] = done

    t = j2_env.get_template('manager.html')
    
    return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})


# ------------------------------------------------------------------------------
@app.route('/reset', methods=['GET'])
def manager_call():
    """ display the complaints data
    """
    process.reset_content()
    
    mydict = {}
    t = j2_env.get_template('reset.html')
    
    return Response(body=t.render(my_dict=mydict), status_code=200, headers={'Content-Type': 'text/html'})
    

