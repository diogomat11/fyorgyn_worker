import pandas as pd
import requests
import json
import time

# Script para ler pacientes_evoluir.xlsx, pegar as URLs e solicitar extração via API

EXCEL_PATH = r"C:\dev\Agenda_hub_MultiConv\Prompts_implantacoes\Contextos\pacientes_evoluir.xlsx"
API_URL = "http://localhost:8000/api/relatorios/extrair"

# IMPORTANTE: O API_TOKEN abaixo NÃO é a variável do .env (webscraping_api_token_2025).
# Você DEVE usar o api_key do seu usuário da tabela 'users' no banco de dados.
# Faça login no frontend, abra a aba "Rede/Network" do navegador (F12) e veja o "Bearer XXXXX" enviado nas requisições.
API_KEY = "Ij-Yos8HnQl9QSxMLXrl08Ei3H7FqcyRMd0aNmx1vIA"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def run_extraction():
    try:
        df = pd.read_excel(EXCEL_PATH)
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {EXCEL_PATH}")
        return

    # Certifique-se que a coluna existe, caso contrário, adapte o nome 'URL' para o correto
    if 'URL' not in df.columns:
        print("A coluna 'URL' não foi encontrada no arquivo Excel.")
        print("Colunas disponíveis:", df.columns.tolist())
        return
        
    # 'data-id' foi a coluna gerada no script anterior para o ID (UUID)
    id_col = 'data-id' if 'data-id' in df.columns else 'id_paciente'
    
    count_success = 0
    count_error = 0

    for index, row in df.iterrows():
        url = str(row.get('URL', '')).strip()
        
        # Pula se a URL for vazia ou "nan"
        if not url or url.lower() == 'nan':
            continue
            
        paciente_id = str(row.get(id_col, '')).strip()
        nome_paciente = str(row.get('nome-usuario', '')).strip()
        
        if not paciente_id:
            print(f"Aviso: Linha {index+2} tem URL mas não tem {id_col}. Pulando...")
            continue
            
        print(f"Solicitando extração para paciente: {nome_paciente} (ID: {paciente_id})")
        print(f"URL: {url}")
        
        payload = {
            "id_paciente": paciente_id,
            "url_arquivo": url,
            "nome_paciente": nome_paciente,
            "id_relatorio": None
        }
        
        try:
            # Envia a requisição POST para a API do backend
            # Nota: Este script pressupõe que o backend já está rodando em http://localhost:8000
            response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
            
            if response.status_code in [200, 201]:
                print(f"  -> SUCESSO! Status da extração: {response.json().get('status_extracao')}")
                count_success += 1
            else:
                print(f"  -> ERRO na requisição: {response.status_code} - {response.text}")
                count_error += 1
                
        except requests.exceptions.RequestException as e:
            print(f"  -> FALHA de conexão/timeout: {e}")
            count_error += 1
            
        # Não precisa mais de time.sleep(1) porque o backend gerencia a fila com o Semáforo.
        
    print("-" * 40)
    print("RESUMO DA EXECUÇÃO:")
    print(f"Extrações solicitadas com sucesso: {count_success}")
    print(f"Extrações com erro: {count_error}")

if __name__ == "__main__":
    run_extraction()
