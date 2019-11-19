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

import os


class LegistarScraper(object):

    def __init__(
        self,
        city_name,
        scrape_url,
        base_url=None,
        save_dir='../data/scraping/scraped_tables',
        headless=True,
        ):
                
        self.city_name = city_name
        self.scrape_url = scrape_url
        if base_url is None:
            self.base_url = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(self.scrape_url))
        else:
            self.base_url = base_url
        self.save_dir = save_dir
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        options = Options()    
        options.headless = headless
        self.driver = Firefox(options=options)
        self.driver.get(self.scrape_url)

    def _click(self, item):
        self.driver.execute_script("arguments[0].scrollIntoView();", item)
        item.click()
        return


    def _get_page_links(self, driver):
        pagelinks_xpath = "//td[@class='rgPagerCell NumericPages']/div[1]/a"
        pagelinks = driver.find_elements_by_xpath(pagelinks_xpath)
        pagelinks = pagelinks[:int(len(pagelinks)/2)]
        return [l.text for l in pagelinks], pagelinks


    def _get_page_signature(self):
        elm_id = 'ctl00_ContentPlaceHolder1_gridCalendar_ctl00__0'
        return self.driver.find_element_by_id(elm_id).text.strip() #get_attribute('outerHTML')


    def _wait_for_table_load(self, page_signature):
        sig_match = True
        while sig_match:
            try:
                time.sleep(0.1)
                new_sig = self._get_page_signature()
                sig_match = new_sig in [page_signature, '']         
            except StaleElementReferenceException:
                sig_match = False    
        return

    def scrape_all_pages(self, **filter_args):

        dropdown_ids = [
            ('years', 'ctl00_ContentPlaceHolder1_lstYears_Input', 'ctl00_ContentPlaceHolder1_lstYears_DropDown'),
            ('bodies', 'ctl00_ContentPlaceHolder1_lstBodies_Input', 'ctl00_ContentPlaceHolder1_lstBodies_DropDown')
        ]

        page_signature = self._get_page_signature()

        for field, input_id, dropdown_id in dropdown_ids:
            dropdown_xpath = "//div[@id='{}']/div/ul/li".format(dropdown_id)
            
            # click on the dropdown menu
            self._click(self.driver.find_element_by_id(input_id))

            # wait for first list item to populate
            parent_xpath = "//div[@id='{}']..".format(dropdown_id)
            waiting = True
            while waiting:
                time.sleep(0.1)
                dropdown_text = self.driver.find_element_by_xpath(dropdown_xpath).text
                waiting = dropdown_text==''

            # select filter term            
            if field in filter_args.keys():
                # if a particular filter is specified, use that
                elms = self.driver.find_elements_by_xpath(dropdown_xpath)
                filter_options = [elm.text for elm in elms]
                i = filter_options.index(filter_args[field])
                filter_elm = elms[i]
            else:
                # if not, select first option in dropdown
                filter_elm = self.driver.find_element_by_xpath(dropdown_xpath)         
            self._click(filter_elm)

        # wait for table to load
        self._wait_for_table_load(page_signature)

        # input('Manually select all years and all committees, then press enter. ')
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
            self._click(link)
            if c > 1:
                self._wait_for_table_load(page_signature)
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
        df = pd.merge(
            text_df,
            url_df,
            left_index=True,
            right_index=True,
            suffixes=(' Text', ' URL'))
        
        return df


    def extract_all_table_data(self, saving=True, **filter_args):
        
        # get htmls of pages
        page_htmls = self.scrape_all_pages(**filter_args)
        print('Scraped {} pages'.format(len(page_htmls)))
        
        # convert to dataframes and concatenate
        page_dfs = [self.extract_table_data(page) for page in tqdm(page_htmls)]
        data = pd.concat(page_dfs)
        print('Recovered {} records'.format(len(data)))
        
        # save
        if saving:
            save_path = os.path.join(self.save_dir, '{}.csv'.format(self.city_name))                        
            data.to_csv(save_path)
            print('Saved to {}'.format(save_path))

        return data


def scrape_city(city_args, filter_args):
    # launch browser-based scraper
    scraper = LegistarScraper(**city_args)
    
    # run scraping tool
    page_data = scraper.extract_all_table_data(**filter_args)
    
    # quit browser
    scraper.driver.quit()
    
    return None


if __name__=='__main__':    
    import argparse
    import pandas as pd
    parser = argparse.ArgumentParser()
    parser.add_argument("city_list")
    parser.add_argument("--out")
    parser.add_argument("--year")
    parser.add_argument("--bodies")
    args = parser.parse_args()

    # add search filters
    filters = {}
    if args.year:
        filters['years'] = args.year
    if args.bodies:
        filters['bodies'] = args.bodies

    # parse list of cities
    city_csv_columns = ['city_name', 'scrape_url']    
    city_df = pd.read_csv(args.city_list, header=None, names=city_csv_columns)

    # scrape each city in turn    
    for _, city_args in city_df.iterrows():        
        city_args = dict(city_args)
        if args.out:
            city_args['save_dir'] = args.out        

        scrape_city(city_args, filters)            

    # import argparse
    # parser = argparse.ArgumentParser()
    # parser.add_argument("city_name")
    # args = parser.parse_args()

    # # get city to scrape (must be one of the cities in CITY_ARGS)
    # city_name = args.city_name
    # for city_args in CITY_ARGS:
    #     if city_args['city_name']==city_name:
    #         break

