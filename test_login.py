import sys
import logging
sys.path.append('Worker')
from database import SessionLocal
from ipasgo_wrapper import IpasgoScraper
from selenium.webdriver.common.by import By
import time

logging.basicConfig(level=logging.DEBUG)

db = SessionLocal()
scraper = IpasgoScraper(db=db, headless=False)  
scraper.start_driver()
scraper.username = '15213080'
scraper.password = 'Brinca2025'

try:
    print("Testing Login Flow Directly...")
    import Worker.6_ipasgo.op.op0_login as op0
    # Provide a faux job data dict
    op0.run(scraper, {"job_id": 999})
    print("Login Flow Finished.")
    print("Current URL:", scraper.driver.current_url)
    
except Exception as e:
    import traceback
    traceback.print_exc()

finally:
    scraper.close_driver()
    db.close()
