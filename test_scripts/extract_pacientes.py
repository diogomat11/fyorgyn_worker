import json
from bs4 import BeautifulSoup
import pandas as pd
import os
import re

input_file = r"c:\dev\Agenda_hub_MultiConv\Prompts_implantacoes\Contextos\pacientes_evoluir.json"
output_file = r"c:\dev\Agenda_hub_MultiConv\Prompts_implantacoes\Contextos\pacientes_evoluir.xlsx"

with open(input_file, 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')

data = []
rows = soup.find_all('div', class_=lambda c: c and 'user-row' in c and 'cursor-pointer' in c)

for row in rows:
    data_id = row.get('data-id', '')
    
    nome_span = row.find('span', class_='nome-usuario')
    nome = nome_span.text.strip() if nome_span else ''
    
    idade_span = row.find('span', class_='idade-usuario')
    idade = idade_span.text.strip() if idade_span else ''
    
    patologia = ''
    plano = ''
    telefone = ''
    
    labels = row.find_all('span', class_='label-table')
    for label in labels:
        label_text = label.text.strip()
        if 'Patologia:' in label_text:
            # The structure is <span class="nome-usuario"> <span class="label-table">Patologia:</span> Sem Cid </span>
            parent = label.parent
            if parent:
                patologia = parent.text.replace('Patologia:', '').strip()
        elif 'Plano:' in label_text:
            parent = label.parent
            if parent:
                plano = parent.text.replace('Plano:', '').strip()
        elif 'Telefone:' in label_text:
            parent = label.parent
            if parent:
                telefone = parent.text.replace('Telefone:', '').strip()
                
    # Clean up multiline whitespaces
    telefone = re.sub(r'\s+', ' ', telefone).strip()
    patologia = re.sub(r'\s+', ' ', patologia).strip()
    plano = re.sub(r'\s+', ' ', plano).strip()
                
    data.append({
        'nome-usuario': nome,
        'idade-usuario': idade,
        'Telefone': telefone,
        'data-id': data_id,
        'Plano': plano,
        'Patologia': patologia
    })

df = pd.DataFrame(data)
df.to_excel(output_file, index=False)
print(f"Extracted {len(data)} patients. Saved to {output_file}")
