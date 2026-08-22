import numpy as np
import pandas as pd
from pathlib import Path
import re

def parse_applied_data(apply_data_path: Path):
      all_file_names = []
      for p in apply_data_path.iterdir():
            for files in p.iterdir():
                  all_file_names.append(files.name)
      print(f"Have applied {len(all_file_names)} jobs")

      datas = []
      for name in all_file_names:
            lst = name.split('-')
            if not lst:
                  continue
            
            company = re.split('[,，]', lst[0])[0] if lst[0] else 'Unknown'
            
            try:
                  parts = re.split('[,，]', lst[0])
                  position = parts[1] if len(parts) > 1 else 'AI/ML Engineer'
            except (IndexError, AttributeError):
                  position = 'AI/ML Engineer'
            
            try:
                  if len(lst) > 1 and lst[-1]:
                        date = lst[-1].split()[0] 
                  else:
                        date = '20260101'
            except (IndexError, AttributeError):
                  date = '20260101'
            
            datas.append([company, position, date])
            
      cols = ['company', 'title', 'apply_date']
      df = pd.DataFrame(datas, columns=cols)
      df['company'] = df['company'].apply(lambda x:str(x).lower())
      return df

if __name__=='__main__':
      apply_data_path = Path("../")
      df = parse_applied_data(apply_data_path)
      save_path = Path('../applied_data')
      save_path.mkdir(parents=True, exist_ok=True)
      df.to_csv(save_path / 'my_applied_data.csv', index=False, encoding='utf-8-sig')
      print('Historical applied data has been processed successfully！')