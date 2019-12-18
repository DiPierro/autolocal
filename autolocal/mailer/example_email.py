from autolocal.mailer.emails import RecommendationEmail

rec0 = {"doc_id": "Alameda_2020-10-19_Public-Utilities-Board_Agenda", "section_text": "lweisiger@alamedaca. gov and contact is Lara Weisiger, City Clerk. In order to assist the Citys efforts to accommodate persons with severe allergies,. environmental illnesses, multiple chemical sensitivity or related disabilities, attendees at. public meetings are reminded that other attendees may be sensitive to various chemical. based products. Please help the City accommodate these individuals", "start_page": 1}
args = {"query_id": "0885ac10678dd09f109d2b76819b612d1afdd7881db674184bd63f8d", "recommendations": [rec0, rec0]}

emailer = RecommendationEmail(record = args)
open("tmp2.html", "w").write(emailer.body_html)