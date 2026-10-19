import os
import sys
import importlib.util

# Ensure paths for modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class ScraperFactory:
    @staticmethod
    def get_scraper(id_convenio, db=None, headless=True, user_id=None, id_integrador=None):
        worker_dir = os.path.dirname(os.path.abspath(__file__))

        # ── Resolução por INTEGRADOR (envelope carimbado pelo backend_worker a
        # partir de convenios.id_integrador). Rotinas pertencem ao integrador;
        # o scraper recebe o id_convenio original p/ credenciais (user_convenios).
        # Fallback: id_convenio legado p/ jobs antigos sem carimbo. ──
        if id_integrador == 102 or (id_integrador is None and id_convenio == 16): # CAESAN
             target_file = os.path.join(worker_dir, "102-caesan", "core", "scraper.py")
             spec = importlib.util.spec_from_file_location("caesan_scraper", target_file)
             caesan_module = importlib.util.module_from_spec(spec)
             spec.loader.exec_module(caesan_module)
             return caesan_module.CaesanScraper(id_convenio=id_convenio, db=db, headless=headless, user_id=user_id)

        if id_integrador == 3 or (id_integrador is None and id_convenio == 3): # UNIMED GOIANIA (+ Intercâmbio conv 21)
             target_file = os.path.join(worker_dir, "3-unimed_goiania", "core", "scraper.py")
             spec = importlib.util.spec_from_file_location("goiania_scraper", target_file)
             goiania_module = importlib.util.module_from_spec(spec)
             spec.loader.exec_module(goiania_module)
             return goiania_module.UnimedScraper(id_convenio=id_convenio, db=db, headless=headless, user_id=user_id)

        if id_convenio == 1: # BRADESCO
             target_file = os.path.join(worker_dir, "1-bradesco", "core", "scraper.py")
             spec = importlib.util.spec_from_file_location("bradesco_scraper", target_file)
             bradesco_module = importlib.util.module_from_spec(spec)
             spec.loader.exec_module(bradesco_module)
             return bradesco_module.BradescoScraper(id_convenio=id_convenio, db=db, headless=headless, user_id=user_id)

        elif id_convenio == 6: # IPASGO
             target_file = os.path.join(worker_dir, "6-ipasgo", "core", "scraper.py")
             spec = importlib.util.spec_from_file_location("ipasgo_scraper", target_file)
             ipasgo_module = importlib.util.module_from_spec(spec)
             spec.loader.exec_module(ipasgo_module)
             return ipasgo_module.IpasgoScraper(id_convenio=id_convenio, db=db, headless=headless, user_id=user_id)

        elif id_convenio == 2: # UNIMED ANAPOLIS
             target_file = os.path.join(worker_dir, "2-unimed_anapolis", "core", "scraper.py")
             spec = importlib.util.spec_from_file_location("anapolis_scraper", target_file)
             anapolis_module = importlib.util.module_from_spec(spec)
             spec.loader.exec_module(anapolis_module)
             return anapolis_module.UnimedAnopolisScraper(id_convenio=id_convenio, db=db, headless=headless, user_id=user_id)

        elif id_convenio == 100: # EVOLUIR
             target_file = os.path.join(worker_dir, "100-evoluir", "core", "scraper.py")
             spec = importlib.util.spec_from_file_location("evoluir_scraper", target_file)
             evoluir_module = importlib.util.module_from_spec(spec)
             spec.loader.exec_module(evoluir_module)
             return evoluir_module.EvoluirScraper(id_convenio=id_convenio, db=db, headless=headless, user_id=user_id)

        elif id_convenio == 101: # ABA_CLMF
             target_file = os.path.join(worker_dir, "101-aba_clmf", "core", "scraper.py")
             spec = importlib.util.spec_from_file_location("aba_clmf_scraper", target_file)
             aba_module = importlib.util.module_from_spec(spec)
             spec.loader.exec_module(aba_module)
             return aba_module.AbaClmfScraper(id_convenio=id_convenio, db=db, headless=headless, user_id=user_id)

        else:
             raise ValueError(f"No scraper implemented for id_convenio={id_convenio} / id_integrador={id_integrador}")

