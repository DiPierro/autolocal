from threading import Thread
from document_manager import DocumentManager
from scraper import Scraper
from webapp import WebApp

# load document manager
documents = DocumentManager()

# run scraper in its own thread
scraper = Scraper(documents)
scraper_thread = Thread(
    scraper.run,
    daemon=True
    )
scraper_thread.start()

# run webapp in its own thread
webapp = WebApp(documents)
webapp_thread = Thread(
    webapp.run,
    )
webbapp_thread.start()
