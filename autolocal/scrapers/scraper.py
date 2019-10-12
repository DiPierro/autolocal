from time import sleep

class Scraper(object): 
    def __init__ (self,
        documents):
        self.baseURL = "http://gridley.ca.us/government-and-departments/city-council/"
        
    def scrape(self): 
        while True:            
            print('Scraper ping')
            sleep(10)

