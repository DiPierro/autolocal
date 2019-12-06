import datetime as dt
import time
import smtplib
import json
import urllib
import urllib.request
import pickle
import re
import os

# def read_results():
#     return pickle.load(open("results.p", "rb"))

def extract_emails(results, email_address):
  # emailsToSend = []
  emails_to_send = {}
  for result in results:
    query_email_address = result["email_address"]
    if email_address == "P":
      email_address = query_email_address
    if email_address not in emails_to_send:
      emails_to_send[email_address] = {}

    keywords = result["Keywords"]
    keywords_str = ", ".join(keywords)
    if keywords_str not in emails_to_send[email_address]:
      emails_to_send[email_address][keywords_str] = []

    section_text = result["section_text"]
    page = result["sentences"][0]["page"]
    doc_name = os.path.basename(result["filename"])
    url = result["url"]
    emails_to_send[email_address][keywords_str].append("\n".join([
      'Type of document: {}'.format(doc_name),
      'Link to document: {}'.format(url),
      'Relevant page number: '.format(page),
      'Excerpt: {}'.format(section_text),
      "\n\n"
    ]))
  return emails_to_send


def send_emails(results=None, args={}):
  if args.email:
    start_date = args.start_date
    end_date = args.end_date
    emails_to_send = extract_emails(results, args.email)
    if emails_to_send != {}:
      from_address = 'autolocalnews@gmail.com'
      server = smtplib.SMTP ('smtp.gmail.com', 587)
      server.starttls()
      server.login(from_address, 'cs206rocksy\'all!')
      for to_address in emails_to_send:
        for keywords in emails_to_send[to_address]:
          message = 'Subject: {}\n\n'.format(keywords)
          sections = emails_to_send[to_address][keywords]
          if start_date and end_date:
            message += "from: {} to {}".format(start_date, end_date) + "\n"
          message += "\n".join(sections)
          message += "\n\n\n"
          server.sendmail(from_address, to_address, message)
      server.quit()

# def send_emails_at(send_time):
#     time.sleep(send_time.timestamp() - time.time())
#     send_emails()
#     print('email sent')


# first_email_time = dt.datetime(2019,11,21,17,32,0) # set your sending time in UTC
# interval = dt.timedelta(minutes=1) # set the interval for sending the email

# send_time = first_email_time
# while True:
#     send_emails_at(send_time)
#     send_time = send_time + interval
