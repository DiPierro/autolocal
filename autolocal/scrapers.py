from time import sleep

def init_scrapers(documents):
    return [Scraper(documents)]

class Scraper(object): 
    def __init__ (self,
        documents):
        self.baseURL = "http://gridley.ca.us/government-and-departments/city-council/"
        
    def run(self): 
        while True:            
            print('Scraper ping')
            sleep(10)

