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

def extract_emails(result):
    emailsToSend = []
    # result = read_results()
    # url = "http://web.stanford.edu/~erindb/autolocal/ad_hoc_relevance_ranking_output.json"
    # response = urllib.request.urlopen(url)
    # buf = response.read()
    # result = json.loads(buf.decode('utf-8'))
    for x in range(0, len(result)):
        for email_address in ['hs4man21@stanford.edu']:
        # for email_address in ['promo@erindb.com', 'hs4man21@stanford.edu', 'patwei@stanford.edu', 'chstock@stanford.edu']:
            email = []
            print('user id: ' + result[0]['user_id'])
            # email_address = 'autolocalnews@gmail.com'
            email.append(email_address)
            for y in range(0, len(result[x]['document_sections'])):
                section_text = result[x]['document_sections'][y]['text']
                # section_text = re.sub("\n+", "", section_text)
                notice = []
                notice.append('MONDAY 8PM -- Keywords: ' + ", ".join(result[x]['document_sections'][y]['keywords']) + '\n')
                notice.append('Type of document: ' + result[x]['document_sections'][y]['doc_name'] + '\n')
                notice.append('Link to document: ' + result[x]['document_sections'][y]['doc_url'] + '\n')
                notice.append('Relevant page number: ' + str(result[x]['document_sections'][y]['page_number']) + '\n')
                notice.append('Excerpt: ' + section_text + '\n')
                email.append(notice)
            emailsToSend.append(email)
    return emailsToSend



# def sendemail(from_addr, to_addr_list, cc_addr_list, bcc_addr_list, subject,
#             message, login, password):
#     header  = 'From: %s\n' % from_addr
#     header += 'To: %s\n' % ','.join(to_addr_list)
#     header += 'Cc: %s\n' % ','.join(cc_addr_list)
#     header += 'Subject: %s\n\n' % subject
#     message = header + message

#     server = smtplib.SMTP_SSL('smtp.googlemail.com', 465)
#     server.login(login, password)
#     server.sendmail(from_addr,
#         to_addr_list + cc_addr_list + bcc_addr_list,
#         message)
#     server.quit()
#     # In case of authentication errors, tag this page to "on"
#     # You might have to do it multiple times


def send_emails(results=None):
    emailsToSend = extract_emails(results) #contains elements of format: [email_address, [title, url, blurb]]
    if len(emailsToSend) > 0:
        email_user = 'autolocalnews@gmail.com'
        server = smtplib.SMTP ('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_user, 'cs206rocksy\'all!')
    while len(emailsToSend) > 0:
        #EMAIL
        message = '';
        for x in range(1, len(emailsToSend[0])):
            print(emailsToSend[0])
            print(x)
            # header  = 'From: %s\n' % from_addr
            # header += 'To: %s\n' % ','.join(to_addr_list)
            # header += 'Cc: %s\n' % ','.join(cc_addr_list)
            header = 'Subject: %s\n\n' % emailsToSend[0][x][0]
            message = header + message
            message = (
                message +
                emailsToSend[0][x][0] + '\n' +
                emailsToSend[0][x][1] + '\n' +
                emailsToSend[0][x][2] + '\n' +
                emailsToSend[0][x][3] + '\n' +
                emailsToSend[0][x][4] + '\n\n\n')
        server.sendmail(email_user, emailsToSend[0][0], message)
        emailsToSend.pop(0);
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
