import os
import glob

def clean_project(base_path):
    print("Iniciando limpeza do projeto...")
    
    files_to_remove = [
        "backend/out_seed.txt",
        "Local_worker/test_op3.log",
        "backend/error.log",
        "backend/error2.log",
        "backend/uvicorn.log",
        "scripts/error.log",
        "test_scripts/db_debug_worker.log",
        "test_scripts/test.log"
    ]
    
    # Specific targeted patterns
    patterns_to_remove = [
        "scripts/touch_err*.log",
        "test_scripts/diag*.log",
        "backend/test_scripts/*.log",
        "Local_worker/Worker/**/*.log",
        "Local_worker/Worker/*.log",
        "backend/scripts/seed_*.py", # Seeding scripts
        "backend/migrations/*_seed_*.sql"
    ]
    
    count = 0
    
    # Remove direct files
    for f in files_to_remove:
        path = os.path.join(base_path, os.path.normpath(f))
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"  Removido: {path}")
                count += 1
            except Exception as e:
                print(f"  [ERRO] Não foi possível remover {path}: {e}")
                
    # Remove pattern files
    for p in patterns_to_remove:
        search_pattern = os.path.join(base_path, os.path.normpath(p))
        for match in glob.glob(search_pattern, recursive=True):
            if os.path.isfile(match):
                try:
                    os.remove(match)
                    print(f"  Removido: {match}")
                    count += 1
                except Exception as e:
                    print(f"  [ERRO] Não foi possível remover {match}: {e}")
                    
    print(f"\nLimpeza concluída! Foram removidos {count} arquivos.")

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    clean_project(project_root)
