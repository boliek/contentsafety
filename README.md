# Content Safety System with Human in the Loop

## Goal
This is a technical demonstration of a response to the question, "Design a Human in the loop content review system." This demonstration showcases an actual working backend system with documentation and design considerations described by this document.

## Suggested flow for first time users
1) Pinners -> select image -> Submit -> Return to splash page  
2) Reviewers -> Next complaint -> Submit -> Return to splash page  
3) Pinners -> note that the image is gone -> browser back button  
4) Managers -> Reset Content -> Pinner page -> note that the image is back

## Table of Contents
[Summary](#summary)  
[High level design](#high_level_design)  
[Demonstration flow](#demonstration_flow)  
[Database schema](#database_schema)  
[Technologies demonstrated](#technologies_demonstrated)  
[Considerations not demonstrated](#considerations_not_demonstrated)
- Fault tolerance and exception handling
- Maintenance and modularity
- Security
- Scalability and performance
- Cache handling
- Analytics
- Testing

## <a name="summary"></a>Summary
There are three roles in the this system — pinners (users), content reviewers, and managers. Pinners can select and tag objectionable content. This creates a record (row) and a queue message delivered to reviewers. A number of reviewers, working in parallel, can access queue and evaluate the tagged content. If the decision is to remove the content, the content metadata (in the database) is updated and it will no longer be displayed. Finally, a manager can see the progress of the whole system.

Here is the link: [https://2fvi665xoi.execute-api.us-west-2.amazonaws.com/api/](https://2fvi665xoi.execute-api.us-west-2.amazonaws.com/api/)

The system is implemented in AWS with Lambdas for web serving and database access, RDS for the database, SQS for the messaging, and Cloudwatch for the logging. It is written in Python 3.6 with SQLAlchemey for the database interface and Jinja2 for templating. The entire coding effort took me the better part of a day and is entirely in the free tier of AWS. (A full list of the technologies used can be found [here](#technologies_demonstrated).)

Just as important as the system design demonstrated here are the factors and features that are not implemented. Important parts of the system (e.g. the databases and queues) could be scaled with mostly devops effort. There is no serious security implemented, nor are there analytics or log management functions. Nevertheless, some important fault tolerance is demonstrated in the design in the way the queue and database interacts. (These considerations and more are discussed [here](#considerations_not_demonstrated).)

Note that the software installation; lambda, database and queue setup; and the AWS console monitoring are not documented here.

## <a name="high_level_design"></a>High level design
There are only two critical Python scripts in this system. The ```app.py``` has all of the API definitions and all the I/O with the website. The ```chalicelib/process.py``` module handles the business logic and the interactions with the database and queue. There are templates for each page in ```chaliclib/templates```.

Below is a block diagram of the dataflow in the design. Note that every web page and step is stateless and uses a API call implemented in API Gateway + Lambda (not shown).

![Design diagram](https://github.com/boliek/contentsafety/blob/master/design.png "Design diagram")




## <a name="database_schema"></a>Database schema
There are four tables and a queues. The pinners table is a list of pinners (users) and is not changed by this system. Likewise, the reviewer table is a list of reviews and is not changed.

The content table has all the content metadata including the display_status which is altered by the content safety actions.

The complaint table has the complaint instances which are updated at various points in the dataflow. It is created when a pinner files a complaint and updated when a reviewer reviews that complaint.

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

## <a name="technologies_demonstrated"></a>Technologies demonstrated
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

## <a name="considerations_not_demonstrated"></a>Considerations not demonstrated
While I hope this system demonstrates my abilities to craft a design and implement it, there are important considerations that are not demonstrated by this system. The following discusses some of these issues.

#### Fault tolerance and exception handling
The weakest point of failure in the current design is the database. It is a single instance. With AWS it is a matter of devops to create a multiple Availability Zone (AZ) and multiple region version of RDS with performance routing and fail over capabilities.

That said, there are two other ways that this system can determine and recover if there were database errors. The logs in Cloudwatch can be monitored for consistency. And the messages in the SQS queue could be reconciled if there is inconsistency.

The SQS queue is another point of failure. The database can be automatically queried for old unresolved complaints and reconciled against the SQS queue. This would compensate from messages that were somehow dropped. There could be a log (or database record) of work in progress (SQS messages in flight, i.e. read and not displayed but not yet deleted) so this is not duplicated. (Or we could not worry about it. Infrequent duplication of reviewer effort is less important than missing complaints.)

The Lambda function (I think) is inherently multi-AZ so there is good redundancy. For performance, we can also make that multi-Region.

#### Maintenance and modularity
This system is very simple. With less than 1000 lines of Python and rather repetitive HTML templates, it took only hours to write and could be understood in minute.

That said, the greatest problem with this system is that the data and data operations are not objects. Because of this, the system is sensitive to unintended consequences of any schema change. Refactoring with object orientation would not take long and would make the code more robust and maintainable.

Specifically, interaction with the database tables, the SQS queue, and the form requests should all be handled by objects.

#### Security
There is no security in the demonstration. Clearly, the pinners and reviewers will have to log in to receive access.

More importantly, the content is in the open. Content found to be objectionable is not removed from the public site. It would necessarily be removed in a real system.

The database is open to the Internet for development. In a real system, it would be behind a closed VPC and only Lambda would have access.

One note, the database and queue access information are stored in a secure file on S3. Only Lambda or a machine with AWS credentials can access. This is important in general, but necessary for this demo when posting the software on GitHub.

#### Scalability and performance
The discussion of fault tolerant fail over RDS instances (in both multi-AZ and multi-Region), coupled with latency routing, should enable scaling and better performance. An elastic approach can be taken with the system, spinning up instances as necessary.

Just a note, with 10,000 human in the loop complaints a day worldwide, we are not yet stressing systems.

#### Cache handling
The demonstration does nothing to refresh the user's browser cache.

Also, the demo does not use CDN functions. However, it is important that Pinterest's CDNs be flushed of any content deemed objectionable. (Interestingly, this is a function for which AWS Cloudwatch charges. I don't think there are large costs associated with this function. I just think it is so universally important that companies are willing to pay.)

#### Analytics
There are not explicit analytics functions in the demo. The database and logs could be mined. But I would recommend a more thoughtful approach.

It would be interesting to see if the complaint rate increases linearly with content volume, with number of users, with unique content access, and with other metrics of system usage. Also, what is the correlation between the rate of success of the proactive content safety measures (automatic content evaluation system) and the complaint rate.

Obviously, there are interesting correlations to demographics of the pinners as well.

#### Testing
The testing of the demo was rudimentary. I apologize for any difficulties you encouter.

The ```process.py``` module can have unit tests. That is where the classes would be.

The rest of the system is API based and can have automated tests.

As for user testing, it can be set up in a canary system and the interactions monitored and compared with existing implementations. The reviewers can be surveyed for their reactions.
