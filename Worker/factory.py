import os
import sys
import importlib.util

# Ensure paths for modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class ScraperFactory:
    @staticmethod
    def get_scraper(id_convenio, db=None, headless=True):
        worker_dir = os.path.dirname(os.path.abspath(__file__))
        
        if id_convenio == 6: # IPASGO
             from ipasgo_wrapper import IpasgoScraper
             return IpasgoScraper(id_convenio=id_convenio, db=db, headless=headless)
             
        elif id_convenio == 2: # UNIMED ANAPOLIS
             target_file = os.path.join(worker_dir, "2-unimed_anapolis", "core", "scraper.py")
             spec = importlib.util.spec_from_file_location("anapolis_scraper", target_file)
             anapolis_module = importlib.util.module_from_spec(spec)
             spec.loader.exec_module(anapolis_module)
             return anapolis_module.UnimedAnopolisScraper(id_convenio=id_convenio, db=db, headless=headless)
             
        elif id_convenio == 3: # UNIMED GOIANIA
             target_file = os.path.join(worker_dir, "3-unimed_goiania", "core", "scraper.py")
             spec = importlib.util.spec_from_file_location("goiania_scraper", target_file)
             goiania_module = importlib.util.module_from_spec(spec)
             spec.loader.exec_module(goiania_module)
             return goiania_module.UnimedScraper(id_convenio=id_convenio, db=db, headless=headless)
             
        else:
             raise ValueError(f"No scraper implemented for id_convenio={id_convenio}")
