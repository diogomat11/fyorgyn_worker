"""Lock global para serializar carga de OPs entre convênios (Worker/*).

Race condition (incidente 26219-26224): execute_op purga sys.modules dos
módulos Worker/<id>-* e insere a raiz do convênio no sys.path antes de
exec_module. Com jobs de convênios DIFERENTES carregando OPs
concorrentemente, o header da OP A (from core.exceptions import ...) podia
resolver 'core' a partir da raiz do convênio B em sys.path[0] →
ModuleNotFoundError: core.exceptions. A purge+carga é região crítica:
todos os scrapers que purgam sys.modules devem segurá-la com este lock.

Uso:
    from op_load_lock import op_load_lock
    with op_load_lock:
        ... purge de sys.modules + spec_from_file_location + exec_module ...
"""
import threading

op_load_lock = threading.Lock()
