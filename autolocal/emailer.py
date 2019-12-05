import datetime as dt
import time
import smtplib
import json
import urllib
import urllib.request
import pickle
import re

# def read_results():
#     return pickle.load(open("results.p", "rb"))

def extract_emails(results):
    emailsToSend = []
    # result = read_results()
    # url = "http://web.stanford.edu/~erindb/autolocal/ad_hoc_relevance_ranking_output.json"
    # response = urllib.request.urlopen(url)
    # buf = response.read()
    for result in results:
        for email_address in ["promo@erindb.com", "hs4man21@stanford.edu", result["user_id"]]:
          if email_address == "emily" or email_address == "patwei@stanford.edu":
              # email_address = 'promo@erindb.com'
              email_address = 'hs4man21@stanford.edu'
          email = []
          email.append(email_address)
          email.append('Keywords: ' + ", ".join([k.strip() for k in result["document_sections"][0]["keywords"]]) + '\n')
          for section in result["document_sections"]:
              section_text = section["text"]
              page = section["page_number"]
              doc_name = section["doc_name"]
              url = section["doc_url"]
              email.append('Type of document: ' + doc_name + '\n')
              email.append('Link to document: ' + url + '\n')
              email.append('Relevant page number: ' + str(page) + '\n')
              email.append('Excerpt: ' + section_text + '\n')
              email.append("\n\n")
          emailsToSend.append(email)
    return emailsToSend


def send_emails(results=None):
    emailsToSend = extract_emails(results) #contains elements of format: [email_address, [title, url, blurb]]
    if len(emailsToSend) > 0:
        email_user = 'autolocalnews@gmail.com'
        server = smtplib.SMTP ('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_user, 'cs206rocksy\'all!')
        for email in emailsToSend:
            message = 'Subject: {}\n\n'.format(email[1])
            message += "\n".join(email[1:])
            message += "\n\n\n"
            # print(message)
            print(email[0])
            print(email[1][:-2])
            server.sendmail(email_user, email[0], message)
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
