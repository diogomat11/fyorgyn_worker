import sys
import traceback

sys.path.append('Worker')

try:
    from factory import ScraperFactory
    ScraperFactory.get_scraper(2)
except Exception as e:
    with open('test_scripts/diag_factory2.txt', 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
    print("Error written to test_scripts/diag_factory2.txt")
