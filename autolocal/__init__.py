from .scrapers.scraper import Scraper
from .document_manager import DocumentManager
from .webapp import WebApp

#from .main import run_app

webapp = WebApp()
server = webapp.server
