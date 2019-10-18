from threading import Thread

from autolocal import WebApp, DocumentManager, scrapers

# load document manager
documents = DocumentManager()

# just for testing - load some documents
print('Downloading sample documents...')
doc_list_path = '../data/misc/meeting_table_prototype_v5.csv'
documents.add_docs_from_csv(doc_list_path)

# run scraper in its own thread
scraper_list = scrapers.init_scrapers(documents)

# scraper = Scraper(documents)
print('Launching scraper...')
for scraper in scraper_list:
    scraper_thread = Thread(
        target=scraper.run,
        daemon=True
        )
    scraper_thread.start()

# run webapp in its own thread
print('Launching webapp...')
webapp = WebApp(documents)
webapp_thread = Thread(
    target=webapp.run,
    )
webapp_thread.start()
