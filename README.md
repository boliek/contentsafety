# Content Safety System with Human in the Loop

### Goal
This system is a technical demonstration of a response to the question, "Design a Human in the loop" content review system. This demonstration showcases an actual working backend system with documentation and design considerations described by this document.

### Table of Contents
[Summary](#summary)  
[High level design](#high_level_design)  
[Demonstration flow](#demonstration_flow)  
[Database schema](#database_schema)  
[Technologies demonstrated](#technologies_demonstrated)  
[Considerations not demonstrated](#considerations_not_demonstrated)
- Fault tolerance and exception handling
- Maintenance and modularity
- Security
- Scalability
- Speed performance
- Cache handling
- Analytics
- Testing

### <a name="summary"></a>Summary
There are three roles in the this system — pinners (users), content reviewers, and managers. Pinners can tag objectionable content creating a record (row) and a queue message to be delivered to reviewers. A number of reviewers can access the tagged content and immediately decide whether it should be removed. Removal is automatic. Finally, a manager can see the progress of the whole system.

Here is the link: [https://2fvi665xoi.execute-api.us-west-2.amazonaws.com/api/](https://2fvi665xoi.execute-api.us-west-2.amazonaws.com/api/)

The system is implemented in AWS with Lambdas for web serving and database access, RDS for the database, SQS for the messaging, and Cloudwatch for the logging. It is written in Python 3.6 with SQLAlchemey for the database interface and Jinja2 for templating. The entire coding effort took me the better part of a day and it is entirely in the free tier of AWS. (A full list of the technologies used can be found [here](#technologies_demonstrated).)

Just as important as the system design demonstrated here are the factors and features that are not implemented. Important parts of the system (e.g. the databases and queues) could be scaled with mostly devops effort. There is basically no serious security implemented, nor are there analytics or log management functions. Nevertheless, some important fault tolerance is demonstrated in the design in the way the queue and database interacts. (These considerations and more are discussed [here](#considerations_not_demonstrated).)

### <a name="high_level_design"></a>High level design
Below is a block diagram of the dataflow in the design. Note that every web page and step is stateless and uses a API call implemented in API Gateway + Lambda (not shown).




### <a name="database_schema"></a>Database schema
There are four tables. The pinners table is a list of pinners (users) and is not changed by this system. Likewise, the reviewer table is a list of reviews and is not changed.

The content table has all the content metadata including the display_status that is affected by the content safety actions.

The complaint table has the complaint instances at various points in the dataflow. It is created when a pinner files a complaint and is updated when a reviewer reviews that complaint.

#### Complaints table
```
complaint_id:         Integer, primary_key
complaint_timestamp:  DateTime, when the complaint was filed
complaint_type:       String, tag such as objectionable, copyright
                      (could have text here too)
process_status:       String, tag such as complaint, review, done
display_status:       String, tag from content such as
                      good, objectionable, copyright
review_timestamp:     DateTime, when the compliant was resolved
pinner_id:            Integer, ForeignKey from pinners
reviewer_id:          Integer, ForeignKey from reviewers
content_id:           Integer, ForeignKey from content
```
#### Contents table
```
content_id:           Integer, primary_key
url:                  String, uri for the imagery
display_status:       String, tag such as good, objectionable, copyright
pinner_id:            Integer, ForeignKey from pinners
```
#### Pinners table
```
pinner_id:            Integer, primary_key
name:                 String, user name
email:                String, user email
```
#### Reviewers table
```
reviewer_id:          Integer, primary_key
name:                 String, reviewer name
email:                String, reviewer email
```

#### SQS queue
The SQS queue is used to signal the reviewers that there is something to review. The message contains the same data as the complaint record (although only the complaint_id is necessary.)

If a queue message is not deleted within ten minutes (i.e. the reviewer does not act) the message is placed back on the queue.

The messages in the queue are dedupped, if you will. There is only one message per content that has been complained about. So if several complaints come in for the same content, only one reviewer will have to act. The reviewers actions will be reflected in all of the complaint records.

The message queue allows many reviewers to work in parallel without duplicating efforts. Furthermore, the queue offers some fault tolerance if there is a database failure.

### <a name="technologies_demonstrated"></a>Technologies demonstrated
#### Backend services
- AWS Lambda — all of the web serving and database access
- AWS API Gateway — API handling and web addressing
- AWS S3 — storage and serving of the content and the secret access considerations
- AWS SQS — communication queues
- AWS RDS with MySQL — databases
- GitHub — code repository

#### Software technologies
- Python 3.6 — primary language
- Jinja2 — templating system for web pages
- SQLAlchemey — SQL Python interface
- Chalice — Zappa-like decorators and functions that make programming a website on lambda look like Flask.
- Boto3 — AWS Python developer's library

#### Tools
- AWS console — for setting up connections between S3, SQS, RDS, and Lambdas
- Atom and TextMate editors
- Sequel — database interface

### <a name="considerations_not_demonstrated"></a>Considerations not demonstrated

- Fault tolerance and exception handling
- Maintenance and modularity
- Security
- Scalability
- Speed performance
- Cache handling
- Analytics
- Testing
