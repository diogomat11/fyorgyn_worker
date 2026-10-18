"""
Reload condicional de módulos do integrador cujo arquivo em disco mudou.

As OPs (op/*.py) são carregadas dinamicamente a cada job via importlib no
scraper, mas os módulos core/ (ex.: core.webplan_client) ficam cacheados em
sys.modules — mudanças em core/ só entram em vigor após restart do worker
(incidente do job #19062: OP11 nova chamando método novo do WebPlanClient
com a classe antiga em memória → AttributeError).

Estratégia: na primeira passada sobre um módulo (sem carimbo __load_mtime__),
recarrega incondicionalmente — cobre módulos importados antes do reloader
existir (estado de workers já em execução) e módulos core são stateless.
Nas passadas seguintes, compara o mtime do disco com o carimbo e recarrega
apenas o que mudou. Sem dependências externas — testável isoladamente.
"""
import importlib
import os
import sys


def _module_mtime(module):
    file = getattr(module, "__file__", None)
    if not file or not os.path.isfile(file):
        return None
    try:
        return os.path.getmtime(file)
    except OSError:
        return None


def reload_stale_modules(module_path, log=None):
    """Recarrega módulos já importados que pertençam a `module_path` (raiz do
    integrador): incondicionalmente na primeira passada (sem carimbo) e, depois,
    apenas quando o arquivo em disco mudou desde o último load/reload.

    Retorna a lista dos nomes recarregados.
    """
    module_path = os.path.abspath(module_path)
    reloaded = []
    for name, module in list(sys.modules.items()):
        if module is None or not isinstance(module, type(sys)):
            continue
        file = getattr(module, "__file__", None)
        if not file:
            continue
        try:
            if not os.path.abspath(file).startswith(module_path + os.sep):
                continue
        except Exception:
            continue

        disk_mtime = _module_mtime(module)
        if disk_mtime is None:
            continue

        loaded_mtime = getattr(module, "__load_mtime__", None)
        if loaded_mtime is not None and disk_mtime <= loaded_mtime:
            continue  # em dia com o disco

        try:
            fresh = importlib.reload(module)
        except Exception as reload_err:
            if log:
                log(f"Falha ao recarregar {name} (segue versão em memória): {reload_err}")
            continue

        try:
            fresh.__load_mtime__ = disk_mtime
        except Exception:
            pass
        reloaded.append(name)
        if log:
            motivo = "primeira passada" if loaded_mtime is None else "arquivo alterado em disco"
            log(f"Módulo recarregado ({motivo}): {name}")

    return reloaded
