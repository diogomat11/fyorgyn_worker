import pandas as pd
from bs4 import BeautifulSoup
import os

excel_file = r"c:\dev\Agenda_hub_MultiConv\Prompts_implantacoes\Contextos\pacientes_evoluir.xlsx"
relatorios_file = r"c:\dev\Agenda_hub_MultiConv\Prompts_implantacoes\Contextos\relatorios.json"

df = pd.read_excel(excel_file)

with open(relatorios_file, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

relatorios_data = {}
for tr in soup.find_all('tr'):
    tds = tr.find_all('td')
    if len(tds) >= 6:
        nome = tds[0].text.strip()
        medico = tds[2].text.strip()
        data = tds[3].text.strip()
        validade = tds[4].text.strip()
        
        a_tag = tds[5].find('a')
        url = a_tag['href'].strip() if a_tag and 'href' in a_tag.attrs else ''
        
        if nome not in relatorios_data:
            relatorios_data[nome] = {
                'Médico': medico,
                'Data': data,
                'Validade': validade,
                'URL': url
            }

df['Médico'] = df['nome-usuario'].map(lambda x: relatorios_data.get(x, {}).get('Médico', ''))
df['Data'] = df['nome-usuario'].map(lambda x: relatorios_data.get(x, {}).get('Data', ''))
df['Validade'] = df['nome-usuario'].map(lambda x: relatorios_data.get(x, {}).get('Validade', ''))
df['URL'] = df['nome-usuario'].map(lambda x: relatorios_data.get(x, {}).get('URL', ''))

df.to_excel(excel_file, index=False)
print(f"Updated Excel file '{excel_file}' with Relatórios data. Found {len(relatorios_data)} unique patients in relatorios.json.")
