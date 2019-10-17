#!/usr/bin/env python
# coding: utf-8

import urllib
from bs4 import BeautifulSoup
import pandas as pd

__all__ = ['GridleyScraper', 'BiggsScraper', 'LiveOakScraper']

scraper_args = [
    {
        'city_name': 'Gridley',
        'mtg_type': "City Council",
        'site_url': "http://gridley.ca.us",        
        'table_url': "http://gridley.ca.us/government-and-departments/city-council/",
    },
    {
        'city_name': 'Gridley',
        'site_url': "http://gridley.ca.us",
        'mtg_type': "Planning Commission",
        'table_url': "http://gridley.ca.us/government-and-departments/planning-commission/"
    },
    {
        'city_name': 'Biggs',
        'site_url': "https://www.biggs-ca.gov/",
        'table_url': "https://www.biggs-ca.gov/Government/Agendas--Minutes/index.html"
    },    
    {
        'city_name': 'Live Oak',
        'site_url': "http://liveoakca.iqm2.com/Citizens/",
        'table_url': "http://liveoakca.iqm2.com/Citizens/Calendar.aspx?From=1/1/1900&To=12/31/9999"
    }
]

def init_scrapers(documents):
    res = []
    for args in scraper_args:
        if args['city_name']=='Gridley':
            res.append(GridleyScraper(documents, **args))
        elif args['city_name']=='Biggs':
            res.append(BiggsScraper(documents, **args))
        elif args['city_name']=='Live Oak':
            res.append(LiveOakScraper(documents, **args))
    return res


class Scraper(object): 
    def __init__ (self, documents, site_url, table_url, mtg_type = None, city_name=''):
        self.documents = documents
        self.site_url = site_url
        self.table_url = table_url
        self.mtg_type = mtg_type
        self.table_html = None
        self.table_page = None
        self.table_data = None
        self.next_table_url = None
        self.city_name = city_name
        self.data_headers = [
            'city',
            'committee',
            'date',
            'doc_type',
            'url',
            'local_path_pdf',
            'local_path_txt'
        ]
        
    def scrape(self):
        self.read_table_page()
        self.parse_table_html()
        self.data = self.convert_table_data()
        
    def run(self):
        # on a loop
        self.scrape()
        self.update_files()
    
    def update_files(self):
        self.data.apply(lambda df: self.documents.add_doc(df.to_dict()), axis=1)
        
    def read_table_page(self):
        with urllib.request.urlopen(self.table_url) as f:
            self.table_page = f.read()
        self.table_html = BeautifulSoup(self.table_page)
        
    def build_url(self, x):
        if x.a:
            return self.site_url + x.a["href"]

class GridleyScraper(Scraper):
            
    def parse_table_html(self):
        table_of_docs = self.table_html.body.find('table', attrs={'class': 'table-responsve'})
        table_headers = [x.text for x in table_of_docs.find_all('th')]
        table_rows = table_of_docs.tbody.find_all('tr')
        table_data = {h: [] for h in table_headers}
        for row in table_rows:
            elements = row.find_all('td')
            for i, h in enumerate(table_headers):
                element = elements[i]
                table_data[h].append(element)
        self.table_data = pd.DataFrame(table_data)

    def convert_table_data(self):
        def split_date_and_name(x):
            words = x.split(" ")
            return " ".join(words[:3]), " ".join(words[3:])
        def parse_table_row(df):
            date_and_name = df["Date"].text
            meeting_date, meeting_type = split_date_and_name(date_and_name)
            cancelled = "cancel" in meeting_type.lower()
            agenda_elem = df["Agenda"]
            minutes_elem = df["Minutes"]
            doc_types = ["Agenda", "Minutes"]
            return pd.DataFrame({
                "city": self.city_name,
                "committee": self.mtg_type,
                "date": meeting_date,
                "doc_type": doc_types,
                'url': [self.build_url(df[x]) for x in doc_types]})
#         print(self.table_data.apply(parse_table_row, axis=1))
        new_df = pd.concat([parse_table_row(row) for idx, row in self.table_data.iterrows()], ignore_index = True)
        return new_df


class BiggsScraper(Scraper): 
        
    def scrape(self):
        self.read_table_page()
        self.parse_table_html()
        self.data = self.convert_table_data()
        print("accessing table from: ", self.next_table_url)
        while self.table_url != self.next_table_url:
            self.table_url = self.next_table_url
            self.read_table_page()
            self.parse_table_html()
            self.data = pd.concat([self.data, self.convert_table_data()], ignore_index = True)
            print("accessing table from: ", self.next_table_url)
    
    def parse_table_html(self):
        table_of_docs = self.table_html.body.find('table')
        table_headers = [x.text.strip() for x in table_of_docs.find("tr").find_all("td")]
        table_rows = table_of_docs.tbody.find_all('tr')[1:]
        table_data = {h: [] for h in table_headers}
        for row in table_rows:
            elements = row.find_all('td')
            if len(elements) == len(table_headers):
                for i, h in enumerate(table_headers):
                    element = elements[i]
                    table_data[h].append(element)
            else:
                # print("next url to lookup: ", self.build_url(elements[0]))
                self.next_table_url = self.build_url(elements[0])
        self.table_data = pd.DataFrame(table_data)

    def convert_table_data(self):
        def split_date_and_name(x):
            words = x.split(" ")
            return " ".join(words[:3]), " ".join(words[3:])
        def parse_table_row(df):
            date = df["Meeting Date"].text.strip()
            time = df["Time"].text.strip()
            if "Type" in df:
                mtg_type = df["Type"].text.strip()
            elif "TYpe" in df:
                mtg_type = df["TYpe"].text.strip()
            else:
                mtg_type = ""
            cancelled = "cancel" in mtg_type.lower()
            if cancelled:
                mtg_type = mtg_type[11:]
            doc_types = ["Agendas", "Minutes"]
            new_doc_types = ["Agendas", "Minutes"]
            return pd.DataFrame({
                "city": self.city_name,
                "committee": mtg_type,
                "date": date,
                "time": time,
                "doc_type": new_doc_types,
                'url': [self.build_url(df[x]) for x in doc_types]})
        new_df = pd.concat([parse_table_row(row) for idx, row in self.table_data.iterrows()], ignore_index = True)
        return new_df


class LiveOakScraper(Scraper):
            
    def parse_table_html(self):
        table_data = []

        month = None
        year = None
        rows = self.table_html.find("div", {"id": "ContentPlaceholder1_pnlMeetings"}).find_all("div", {"class": "Row"})
        for row in rows:
            if "MonthHeader" in row["class"]:
                month, year = row.text.strip().split(", ")
            elif "MeetingRow" in row["class"]:
                cancelled = False
                links = {}
                date = None
                mtg_type = None
                doc_type = None
                for row_part in row.find_all("div", recursive=False):
                    for div in row_part.find_all("div", recursive=False):
                        if "RowIcon" in div["class"]:
                            pass
                        elif "RowLink" in div["class"]:
                            # title of RowLink has lots of info
                            links["mtg_page"] = self.build_url(div)
                            date = div.text.strip()
                        elif "MeetingLinks" in div["class"]:
                            for link in div.find_all("div"):
                                doc_type = div.a.text.strip()
                                partial_url = div.a["href"]
                                if not partial_url in ["javascript:void(0)", "", "#"]:
                                    doc_url = self.build_url(div)
                                    links[doc_type] = doc_url
                        elif "RowDetails" in div["class"]:
                            committee, mtg_type = div.text.strip().split(" - ")
                            pass
                        elif "RowRight" in div["class"]:
                            cancelled = True
                table_data.append((month, year, cancelled, links, mtg_type, date, committee))
        table_data = pd.DataFrame(table_data, columns=["Month", "Year", "Cancelled", "Links", "Type", "Date", "committee"])
        self.table_data = table_data
        
    def build_url(self, x):
        if x.a:
            url = self.site_url + x.a["href"]
            url = url.replace('Citizens//', 'Citizens/')
            url = url.replace('Citizens//', 'Citizens/')
            url = url.replace("Citizens/Citizens/", "Citizens/")
            return url

    def convert_table_data(self):
        # TODO: explore mtg_page document type
        def parse_table_row(df):
            agenda = None
            minutes = None
            links = df["Links"]
            mtg_data = {
                "committee": df["committee"],
                "meeting_type": df["Type"],
                "city": self.city_name,
                "date": df["Date"],
                "month": df["Month"],
                "doc_type": [], 
                "url": []} 
            for doc_type in links:
                url = links[doc_type]
                mtg_data["doc_type"].append(doc_type)
                mtg_data["url"].append(url)
            return pd.DataFrame(mtg_data)
        new_df = pd.concat([parse_table_row(row) for idx, row in self.table_data.iterrows()], ignore_index = True)
        return new_df

# TODO: RL give it url for a town, its action space is to follow a link or add a record or stop
