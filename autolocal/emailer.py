import datetime as dt
import time
import smtplib
import json
import urllib
import urllib.request

def extract_emails():
    emailsToSend = []
    url = "http://web.stanford.edu/~erindb/autolocal/ad_hoc_relevance_ranking_output.json"
    response = urllib.request.urlopen(url)
    buf = response.read()
    result = json.loads(buf.decode('utf-8'))
    for x in range(0, len(result)):
        email = []
        print('user id: ' + result[0]['user_id'])
        email_address = 'autolocalnews@gmail.com'
        email.append(email_address)
        for y in range(0, len(result[x]['document_sections'])):
            notice = []
            notice.append('Type of document: ' + result[x]['document_sections'][y]['doc_name'] + '\n')
            notice.append('Link to document: ' + result[x]['document_sections'][y]['doc_url'] + '\n')
            notice.append('Relevant page number: ' + result[x]['document_sections'][y]['doc_url'] + '\n')
            notice.append('Excerpt: ' + result[x]['document_sections'][y]['text'] + '\n')
            email.append(notice)
        emailsToSend.append(email)
    return emailsToSend

def send_emails():
    emailsToSend = extract_emails() #contains elements of format: [email_address, [title, url, blurb]]
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
            message = (message + emailsToSend[0][x][0] + '\n' + emailsToSend[0][x][1] + '\n' + emailsToSend[0][x][2] + '\n' + emailsToSend[0][x][3] + '\n\n\n')
        server.sendmail(email_user, emailsToSend[0][0], message)
        emailsToSend.pop(0);
    server.quit()

def send_emails_at(send_time):
    time.sleep(send_time.timestamp() - time.time())
    send_emails()
    print('email sent')


first_email_time = dt.datetime(2019,11,21,17,32,0) # set your sending time in UTC
interval = dt.timedelta(minutes=1) # set the interval for sending the email

send_time = first_email_time
while True:
    send_emails_at(send_time)
    send_time = send_time + interval
