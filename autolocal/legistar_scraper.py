import pandas as pd
import numpy as np
from urllib import parse
from urllib import request
import bs4 as bs

from urllib.parse import urlparse

import selenium as se
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import StaleElementReferenceException

from tqdm import tqdm
import time


data_dir = '../data/scraping/scraped_tables/'

CITY_ARGS = [
    {
    'city_name': 'hayward',
    'scrape_url': 'https://hayward.legistar.com/Calendar.aspx',
    },
    {
    'city_name': 'santa_clara',
    'scrape_url': 'https://santaclara.legistar.com/Calendar.aspx',
    }, 
    {
    'city_name': 'mountain_view',
    'scrape_url': 'https://mountainview.legistar.com/Calendar.aspx',
    },
    {
    'city_name': 'sunnyvale',
    'scrape_url': 'https://sunnyvaleca.legistar.com/Calendar.aspx',
    },
    {
    'city_name': 'san_jose',
    'scrape_url': 'https://sanjose.legistar.com/Calendar.aspx'
    },
    {
    'city_name': 'cupertino',
    'scrape_url': 'https://cupertino.legistar.com/Calendar.aspx'
    },
    {
    'city_name': 'san_mateo_county',
    'scrape_url': 'https://sanmateocounty.legistar.com/Calendar.aspx'
    },    
    {
    'city_name': 'burlingame',
    'scrape_url': 'https://burlingameca.legistar.com/Calendar.aspx'
    },
    {
    'city_name': 'san_leandro',
    'scrape_url': 'https://sanleandro.legistar.com/Calendar.aspx'
    },    
    {
    'city_name': 'alameda',
    'scrape_url': 'https://alameda.legistar.com/Calendar.aspx'
    },   
    {
    'city_name': 'oakland',
    'scrape_url': 'https://oakland.legistar.com/Calendar.aspx'
    },
    {
    'city_name': 'san_francisco',
    'scrape_url': 'https://sfgov.legistar.com/Calendar.aspx'
    },
    {
    'city_name': 'hercules',
    'scrape_url': 'https://hercules.legistar.com/Calendar.aspx'
    },
    {
    'city_name': 'stockton',
    'scrape_url': 'https://stockton.legistar.com/Calendar.aspx'
    },
    {
    'city_name': 'south_san_francisco',
    'scrape_url': 'https://ci-ssf-ca.legistar.com/Calendar.aspx'
    },            
    {
    'city_name': 'mtc',
    'scrape_url': 'https://mtc.legistar.com/Calendar.aspx'
    }            
]


class TextChange(object):
    def __init__(self, locator, text):
        self.locator = locator
        self.text = text

    def __call__(self, driver):
        actual_text = _find_element(driver, self.locator).text
        return actual_text != self.text

class LegistarScraper(object):

    def __init__(
        self,
        city_name,
        scrape_url,
        base_url=None,
        save_path=None,
        ):
                
        self.city_name = city_name
        self.scrape_url = scrape_url
        if base_url is None:
            self.base_url = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(self.scrape_url))
        else:
            self.base_url = base_url

        self.driver = Firefox()
        self.driver.get(self.scrape_url)


    def _get_page_links(self, driver):
        pagelinks_xpath = "//td[@class='rgPagerCell NumericPages']/div[1]/a"
        pagelinks = driver.find_elements_by_xpath(pagelinks_xpath)
        pagelinks = pagelinks[:int(len(pagelinks)/2)]
        return [l.text for l in pagelinks], pagelinks


    def _get_page_signature(self):
        elm_id = 'ctl00_ContentPlaceHolder1_gridCalendar_ctl00__0'
        return self.driver.find_element_by_id(elm_id).text.strip() #get_attribute('outerHTML')

    def scrape_all_pages(self):

        input('Manually select all years and all committees, then press enter. ')
        # click through pages and save html
        c = 1
        page_data = []
        while True:
            pages, pagelinks = self._get_page_links(self.driver)
            page_signature = self._get_page_signature()
            try:
                # click on the integer we want
                i = pages.index(str(c))
                link = pagelinks[i]
            except:
                # if it's not there and the list ends with '...', click on '...'
                if pages[-1]=='...':
                    link = pagelinks[-1]
                # if it's not there and the list starts with '...', we are done.
                else:
                    break
            link.click()
            if c > 1:
                sig_match = True
                while sig_match:
                    try:
                        time.sleep(0.1)
                        new_sig = self._get_page_signature()
                        sig_match = new_sig in [page_signature, '']         
                    except StaleElementReferenceException:
                        sig_match = False
            print('Scraping page {}'.format(c))
            page_data.append(self.driver.page_source)
            c += 1

        return page_data


    def extract_table_data(
        self,
        page_source,
        table_id='#ctl00_ContentPlaceHolder1_gridCalendar_ctl00'
        ):
        # find table in page
        soup = bs.BeautifulSoup(page_source, features='lxml')
        table = soup.select(table_id)[0]
        num_cols = int(table.td.get('colspan'))

        # extract column headers
        header_data = [''.join(cell.stripped_strings) for cell in table.find_all('th')]
        header_data = [h for h in header_data if h!='Data pager']
        assert(len(header_data)==num_cols)

        # extract text and URL data from table
        text_data, url_data = [], []
        for row in table.find_all('tr'):
            row_text, row_url = [], []
            for td in row.find_all('td'):
                row_text.append(''.join(td.stripped_strings))
                if td.find('a') and (td.a.get('href') is not None):
                    row_url.append(self.base_url+td.a.get('href'))
                else:
                    row_url.append(np.nan)
                if len(row_text)==num_cols and len(row_url)==num_cols:
                    text_data.append(row_text)
                    url_data.append(row_url)
                    
        # turn into dataframe
        num_cols = table.td.get('colspan')
        text_df = pd.DataFrame(text_data, columns=header_data)
        url_df = pd.DataFrame(url_data, columns=header_data)
        df = pd.merge(text_df, url_df, left_index=True, right_index=True, suffixes=(' Text', ' URL'))
        
        return df

    def extract_all_table_data(self, save_path=None, **kwargs):
        if save_path is None:
            save_path = '../data/scraping/scraped_tables/{}.csv'.format(self.city_name)

        page_htmls = self.scrape_all_pages()
        print('Scraped {} pages'.format(len(page_htmls)))
        page_dfs = [self.extract_table_data(page) for page in tqdm(page_htmls)]
        data = pd.concat(page_dfs)
        print('Recovered {} records'.format(len(data)))
        if save_path:
            print('Saving to {}'.format(save_path))
            data.to_csv(save_path)
        return data


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("city_name")
    args = parser.parse_args()

    # get city to scrape (must be one of the cities in CITY_ARGS)
    city_name = args.city_name
    for city_args in CITY_ARGS:
        if city_args['city_name']==city_name:
            break

    # launch browser-based scraper
    scraper = LegistarScraper(**city_args)

    # run scraping tool
    page_data = scraper.extract_all_table_data()

    # quit browser
    scraper.driver.quit()
