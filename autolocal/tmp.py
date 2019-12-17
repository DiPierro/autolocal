# Make the request
import httplib2
http_session = httplib2.Http()
response = http_session.request("http://localhost:8000/")
status = response[0]["status"]
print(status)
print(response)
