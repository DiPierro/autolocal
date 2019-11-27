import datetime as dt
import time
import smtplib

def send_emails():
    emailsToSend = [] #contains elements of format: [email_address, [title, url, blurb]]
    #TODO: Add code to extract structs like those below from a webpage / wherever Erin puts them
    testEmail = ['autolocalnews@gmail.com', ['Electric vehicle news in Palo Alto', 'https://www.cityofpaloalto.org/civicax/filebank/blobdload.aspx?t=52629.88&BlobID=73974', 'See the consent calendar for more info.'], ['Electric vehicle news in Palo Alto', 'https://www.cityofpaloalto.org/civicax/filebank/blobdload.aspx?t=52629.88&BlobID=73974', 'There are two notices in this email.']]
    testEmail2 = ['autolocalnews@gmail.com', ['Electric vehicle news in Palo Alto', 'https://www.cityofpaloalto.org/civicax/filebank/blobdload.aspx?t=52629.88&BlobID=73974', 'This is a second email for testing purposes.']]
    emailsToSend.append(testEmail)
    emailsToSend.append(testEmail2)
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
            message = (message + emailsToSend[0][x][0] + '\n' + emailsToSend[0][x][1] + '\n' + emailsToSend[0][x][2] + '\n\n')
        server.sendmail(email_user, emailsToSend[0][0], message)
        emailsToSend.pop(0);
    server.quit()

def send_emails_at(send_time):
    time.sleep(send_time.timestamp() - time.time())
    send_emails()
    print('email sent')

first_email_time = dt.datetime(2019,11,15,18,27,0) # set your sending time in UTC
interval = dt.timedelta(minutes=1) # set the interval for sending the email

send_time = first_email_time
while True:
    send_emails_at(send_time)
    send_time = send_time + interval
