import pandas as pd
import os
p = os.path.abspath(os.path.join('..','data','sla_tickets','Tickets with PII update.xlsx'))
print('Checking file:', p)
try:
    df = pd.read_excel(p, engine='openpyxl')
    print('Rows:', len(df))
    found = df.astype(str).apply(lambda row: row.str.contains('IN0042923', case=False, na=False)).any(axis=1)
    if found.any():
        print('Found ticket in rows:')
        print(df[found])
    else:
        print('Ticket not found in this file')
except Exception as e:
    print('Error reading file:', e)
