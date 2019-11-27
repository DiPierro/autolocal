#!/usr/bin/env python
# coding: utf-8

import urllib
import urllib.request
from bs4 import BeautifulSoup
import re

source_urls = [
  "https://sanjose.legistar.com/DepartmentDetail.aspx?ID=21676&GUID=ACCCCFF5-F14A-4E1A-8540-9065F45A8A90&R=13cecec7-6202-44c8-9972-ba79e74be851",
  # "https://sanjose.legistar.com/DepartmentDetail.aspx?ID=-1&GUID=920296E4-80BE-4CA2-A78F-32C5EFCF78AF&R=56d4d04b-4ff5-4487-901a-d01c245bf466", # all meeting bodies
  "https://sunnyvaleca.legistar.com/Calendar.aspx"
]

def read_page(url):
    with urllib.request.urlopen(url) as f:
        page = f.read()
    return BeautifulSoup(page)

def get_site_url(url):
    return re.match("([^/]*//[^/]*/)", url).groups()[0]

def get_link(a, url):
    href = a.get("href")
    if not href:
        return None
    # ingore empty URLs
    if href == "":
        return None
    # ignore javascript calls (TODO: is this correct?)
    if re.match("javascript", href):
        return None
        return None
    # ignore anchors
    if href[0] == "#":
        return None
    site_url = get_site_url(url)
    # if it's a full url AND a subpage of this site, return the url
    if re.match(site_url, href):
        return href
    # but if it's a full url from some other site, ignore it
    if re.match("https?://", href):
        return None
    return "{}{}".format(site_url, href)
    
# links_from_this_page = set([get_link(a, source_url) for a in page.find_all("a") if get_link(a, source_url)])
# links_from_this_page

with open("../data/crawled_urls/urls_searched.txt") as f:
  urls_searched = set([x.strip() for x in f.readlines()])
searched_file = open("urls_searched.txt", "a")

with open("../data/crawled_urls/urls_that_are_not_html.txt") as f:
  urls_that_are_not_html = set([x.strip() for x in f.readlines()])
collected_file = open("urls_that_are_not_html.txt", "a")

with open("../data/crawled_urls/urls_to_search.txt") as f:
  urls_to_search = set(source_urls + [x.strip() for x in f.readlines()])

try:
  # t = 0
  # while len(urls_to_search) > 0 and t < 20:
  while len(urls_to_search) > 0:
      url = urls_to_search.pop()
      print("reading page: {}".format(url))
      with urllib.request.urlopen(url) as f:
          contents = f.read()
      if re.search(b'DOCTYPE html', contents):
          print("it's an html page, so we're searching it.")
          page = BeautifulSoup(contents)
          links_from_this_page = set([get_link(a, url) for a in page.find_all("a") if get_link(a, url)])
          new_links_to_search = links_from_this_page.difference(urls_searched).difference(urls_to_search)
          urls_to_search.update(new_links_to_search)
          print("{} new links found".format(len(new_links_to_search)))
      else:
          print("it's not an html page, so we're just keeping track of the url")
          urls_that_are_not_html.add(url)
          collected_file.write(url + "\n")
      print("{} total read, {} terminal files collected, {} still need to be read".format(
          len(urls_searched),
          len(urls_that_are_not_html),
          len(urls_to_search)))
      urls_searched.add(url)
      searched_file.write(url + "\n")
      print("***")
      # t+=1
  #     links_to_search = [link for link in links_from_this_page if not link in urls_searched]
  # urls_to_search
except:
  with open("../data/crawled_urls/urls_to_search.txt", "w") as w:
    w.write("\n".join(urls_to_search))
  searched_file.close()
  collected_file.close()

with open("../data/crawled_urls/urls_to_search.txt", "w") as w:
  w.write("\n".join(urls_to_search))
searched_file.close()
collected_file.close()

