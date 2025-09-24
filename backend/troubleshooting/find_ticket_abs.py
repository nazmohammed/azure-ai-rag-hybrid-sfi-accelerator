import pandas as pd, glob, os
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
data_dir = os.path.join(project_root, 'data', 'sla_tickets')
print('Project root:', project_root)
print('Looking in:', data_dir)
files = glob.glob(os.path.join(data_dir, '*.xlsx'))
print('files found:', files)
found_any = False
for f in files:
    try:
        df = pd.read_excel(f, engine='openpyxl').astype(str)
        matches = df.apply(lambda row: row.str.contains('IN0042923', case=False, na=False)).any(axis=1)
        if matches.any():
            print('Found in', f)
            print(df[matches])
            found_any = True
        else:
            print('Not found in', f)
    except Exception as e:
        print('err reading', f, e)
if not files:
    print('No Excel files found in data/sla_tickets')
if not found_any and files:
    print('Ticket IN0042923 not found in any files')
