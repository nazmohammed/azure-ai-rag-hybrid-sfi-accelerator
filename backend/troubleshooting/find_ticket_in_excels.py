import pandas as pd, glob
files = glob.glob('../data/sla_tickets/*.xlsx')
print('files=', files)
for f in files:
    try:
        df = pd.read_excel(f, engine='openpyxl').astype(str)
        matches = df.apply(lambda row: row.str.contains('IN0042923', case=False, na=False)).any(axis=1)
        if matches.any():
            print('Found in', f)
            print(df[matches])
        else:
            print('Not found in', f)
    except Exception as e:
        print('err reading', f, e)
