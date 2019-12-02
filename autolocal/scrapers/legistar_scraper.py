import pandas as pd
import numpy as np
from urllib import parse
from urllib import request
import bs4 as bs
from copy import  deepcopy

from urllib.parse import urlparse

import selenium as se
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import StaleElementReferenceException

from tqdm import tqdm
import time
from datetime import datetime

import os, sys

from autolocal.databases import S3DocumentManager
from autolocal import AUTOLOCAL_HOME


class LegistarScraper(object):

    def __init__(
        self,
        city_name,
        scrape_url,
        save_dir,
        base_url=None,
        headless=True,
        log_path=None,
        ):
                
        self.city_name = city_name
        self.city_name_lower = self.city_name.lower().replace(' ', '-')
        self.scrape_url = scrape_url
        if base_url is None:
            self.base_url = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(self.scrape_url))
        else:
            self.base_url = base_url
        self.save_dir = save_dir
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        if log_path is not None:
            print('logging: {}'.format(log_path))
            sys.stdout = open(log_path, 'w')

        options = Options()    
        options.headless = headless
        self.driver = Firefox(options=options)
        self.driver.get(self.scrape_url)

        print('Initialized scraper for {}'.format(self.city_name))

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
        # sig  = ''
        # elm_id = 'ctl00_ContentPlaceHolder1_lstYears_Input'        
        # sig += self.driver.find_element_by_id(elm_id).get_attribute('value')
        elm_id = 'ctl00_ContentPlaceHolder1_gridCalendar_ctl00__0'
        return self.driver.find_element_by_id(elm_id).text.strip()

    def _wait_for_table_load(self, page_signature, max_wait=None):
        sig_match = True
        expired = False
        while sig_match and not expired:
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
                try:
                    i = filter_options.index(filter_args[field])
                except ValueError:
                    print('scraper: unable to find item {} in list {}, aborting'.format(
                        filter_args[field], field))
                    return []
                filter_elm = elms[i]
            else:
                # if not, select first option in dropdown
                filter_elm = self.driver.find_element_by_xpath(dropdown_xpath)         
            self._click(filter_elm)

            # click search button
            search_button_id = 'ctl00_ContentPlaceHolder1_btnSearch'
            search_button = self.driver.find_element_by_id(search_button_id)
            self._click(search_button)

        # click through pages and save html
        c = 1
        page_data = []
        while True:
            # scrape the page data
            print('Scraping page {}'.format(c))
            page_data.append(self.driver.page_source)            

            # increase page count
            c += 1

            # get page links, if any
            pages, pagelinks = self._get_page_links(self.driver)
            page_signature = self._get_page_signature()
            if pages:
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
            else:
                break

            #  wait for page to load
            self._wait_for_table_load(page_signature)                

        return page_data


    def extract_table_data(
        self,
        page_source,
        table_id='#ctl00_ContentPlaceHolder1_gridCalendar_ctl00'
        ):
        # find table in page
        soup = bs.BeautifulSoup(page_source, features='lxml')
        table = soup.select(table_id)[0]        

        # extract column headers
        header_data = [''.join(cell.stripped_strings) for cell in table.find_all('th')]
        header_data = [h for h in header_data if h!='Data pager']
        num_cols = len(header_data)
        # num_cols = int(table.td.get('colspan'))

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


    def extract_doc_list(self, page_data):
        
        doc_list = []
        for i, row in page_data.iterrows():
            meeting_data = {
                'city': self.city_name,
                'date': pd.to_datetime(row['Meeting Date Text']),
                'committee': row['Name Text'],
                'doc_format': 'pdf',
            }        
            url_col_pairs = [
                ('Agenda', 'Agenda URL'),
                ('Minutes', 'Minutes URL'),
                ('Minutes', 'Official Minutes URL')
            ]
            for doc_type, url_col in url_col_pairs:
                try:
                    url = row[url_col]
                    if isinstance(url, str):
                        row_data = deepcopy(meeting_data)
                        row_data['url'] = url
                        row_data['doc_type'] = doc_type
                        doc_list.append(row_data)
                except:
                    pass
        
        return pd.DataFrame(doc_list)

    def extract_all_table_data(self, saving=True, **filter_args):
        
        # get htmls of pages
        page_htmls = self.scrape_all_pages(**filter_args)
        if not page_htmls:
            return [], ''
        print('Scraped {} pages'.format(len(page_htmls)))
        
        # convert to dataframes and concatenate
        page_dfs = [self.extract_table_data(page) for page in tqdm(page_htmls)]
        page_data = pd.concat(page_dfs)
        print('Recovered {} meetings'.format(len(page_data)))

        # extract document list
        doc_list = self.extract_doc_list(page_data)
        print('Recovered {} documents'.format(len(doc_list)))

        # save
        if saving:
            fname = '{}.csv'.format(self.city_name_lower)

            scraped_tables_dir = os.path.join(self.save_dir, 'scraped_tables')
            scraped_tables_csv = os.path.join(scraped_tables_dir, fname)
            if not os.path.exists(scraped_tables_dir):
                os.mkdir(scraped_tables_dir)
            page_data.to_csv(scraped_tables_csv)

            doc_list_dir = os.path.join(self.save_dir, 'document_list')
            doc_list_csv = os.path.join(doc_list_dir, fname)
            if not os.path.exists(doc_list_dir):
                os.mkdir(doc_list_dir)            
            doc_list.to_csv(doc_list_csv)

        return page_data, doc_list_csv


def scrape_city(city_args, filter_args):
    # launch browser-based scraper
    scraper = LegistarScraper(**city_args)
    
    # run scraping tool
    table_results = scraper.extract_all_table_data(**filter_args)
    
    # quit browser
    scraper.driver.quit()
    
    return table_results


if __name__=='__main__':    
    import argparse
    import pandas as pd
    from subprocess import run
    logs_dir = os.path.join(AUTOLOCAL_HOME, 'logs')
    scraping_dir = os.path.join(AUTOLOCAL_HOME, 'data', 'scraping')
    cities_csv_path = os.path.join(scraping_dir, 'cities.csv')

    parser = argparse.ArgumentParser()
    parser.add_argument("--city_list", default=cities_csv_path)
    parser.add_argument("--year", default=str(datetime.utcnow().year))
    parser.add_argument("--bodies")
    parser.add_argument("--no_download", action='store_true')
    parser.add_argument("--logging", action='store_true')
    parser.add_argument("--job_id", default=datetime.utcnow().isoformat())
    args = parser.parse_args()
    job_id = 'legistar_scraper_' + args.job_id

    # report amazon instance details
    using_aws = False
    try:
        for flag_name, flag in [
            ('AWS instance id', '--instance-id'),
            ('hostname', '--public-hostname')]:
            res = run(['ec2metadata', flag], capture_output=True).stdout.decode("utf-8")
            print('{}: {}'.format(flag_name, res))
        using_aws = True
    except:
        pass

    # report
    print(os.path.abspath(__file__))
    print("Usage:\n{0}\n".format(" ".join([x for x in sys.argv])))
    print("All settings used:")
    for k,v in sorted(vars(args).items()):
        print("{0}: {1}".format(k,v))


    # scraper_configuration
    # if args.logging:
        # log_path = os.path.join(logs_dir, job_id + '.log')
    save_dir = os.path.join(scraping_dir, job_id)

    # add query filters
    filters = {}
    if args.year:
        filters['years'] = args.year
    if args.bodies:
        filters['bodies'] = args.bodies

    # parse list of cities
    city_csv_columns = ['city_name', 'scrape_url']    
    city_df = pd.read_csv(args.city_list, header=None, names=city_csv_columns)

    # connect to database
    if not args.no_download:
        documents = S3DocumentManager()

    # scrape each city in turn    
    for _, city_args in city_df.iterrows():        
        city_args = dict(city_args)        
        city_args['save_dir'] = save_dir
        # if args.logging:
            # city_args['log_path'] = log_path
        _, doc_list_csv = scrape_city(city_args, filters)            
        if doc_list_csv and not args.no_download:
            print('Adding documents to database: {}'.format(doc_list_csv))
            documents.add_docs_from_csv(doc_list_csv)

    # move local data to S3
    try:
        if using_aws:    
            s3_dir = 's3://legistar-scraper-logs/legistar_scraper/' + job_id
            aws_cmd = ['aws', 's3', 'mv', save_dir, s3_dir, '--recursive']
            run(aws_cmd)
    except:
        pass

    # import argparse
    # parser = argparse.ArgumentParser()
    # parser.add_argument("city_name")
    # args = parser.parse_args()

    # # get city to scrape (must be one of the cities in CITY_ARGS)
    # city_name = args.city_name
    # for city_args in CITY_ARGS:
    #     if city_args['city_name']==city_name:
    #         break

