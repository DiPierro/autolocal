# autolocal
## Automated Local News
This repository contains the code which runs [AgendaWatch](http://www.agendawatch.org), an app which sends personalized email alerts about relevant upcoming public meetings. 

It also contains various other code used for prototyping and analysis.

## Directory structure

`notebooks`: Jupyter notebooks for data analysis/exploratory stuff

`autolocal` : code base

---`mailer`: Email subscription management

---`documentdb`: Document database management

---`recommender`: NLP-based recommender algorithm

---`www`: website

---`biglocaldocs`: a previous iteration of the app and website

`scripts`: shell scripts

## Dependencies

The project is built to work with specific Amazon Web Services resources (SES, DynamoDB, S3, API Gateway, AWS Lambda).

Most of the code is written in Python 3; there is also some JavaScript/CSS/HTML. 

The packages `numpy`, `pandas`, and `tqdm` are used ubiquitously.

We assume `awscli` and `boto3` are installed, and that they has been configured in a role with sufficient permissions.

The recommender requires `allennlp`, `editdistance`, and `sklearn`.

The scraper requires `selenium` for Python with Firefox/Geckodriver, as well as `pdfminer.six` and `beautifulsoup`.

Code in `biglocaldocs` (not part of the current version of our app) requires `dash` and `flask`.
