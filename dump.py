import pandas as pd
df = pd.read_excel('template.xlsx')
with open('cols.txt', 'w', encoding='utf-8') as f:
    f.write(str(df.columns.tolist()) + '\n\n')
    for record in df.to_dict(orient='records'):
        f.write(str(record) + '\n')
