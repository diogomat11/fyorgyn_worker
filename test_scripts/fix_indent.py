import os

file_path = "c:\\dev\\Agenda_hub_MultiConv\\Local_worker\\Worker\\6-ipasgo\\op\\op3_import_guias.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(504, 603):
    if lines[i].strip():
        lines[i] = "    " + lines[i]

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
