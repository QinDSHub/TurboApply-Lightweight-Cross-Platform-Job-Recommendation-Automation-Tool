import pandas as pd
from pathlib import Path
import jellyfish
import os, shutil

def fuzzy_match(name, master_list, threshold=0.80):
    best_match = None
    best_score = 0
    for master in master_list:
        # use jellyfish.jaro_winkler_similarity to match company name between my historical applied data and platforms data
        score = jellyfish.jaro_winkler_similarity(name.lower(), master.lower())
        if score > best_score and score >= threshold:
            best_score = score
            best_match = master
    return best_match, best_score


def match_company(main_table_path: Path, apply_data_path: Path, standard_company_path: Path):
      all_data = pd.read_csv(main_table_path)
      all_data['company'] = all_data['company'].apply(lambda x:x.lower())
      master_list = all_data[['company']].drop_duplicates().sort_values(by=['company'])
      master_list = master_list['company'].unique().tolist()

      df = pd.read_csv(apply_data_path)
      df['company'] = df['company'].apply(lambda x:x.lower())
      name_list = df[['company']].drop_duplicates().sort_values(by=['company'])
      name_list = name_list['company'].unique().tolist()

      print('start to match')
      res = []
      for name in name_list:
            match, score = fuzzy_match(name, master_list)
            if match is None:
                  res.append([name, name, 2])
            else:
                  res.append([name, match, score])

      match_df = pd.DataFrame(res, columns=['company', 'united_company', 'score'])
      match_df = match_df.sort_values(by=['company','united_company']).reset_index(drop=True)

      match_df.to_csv(standard_company_path,index=False,encoding='utf-8-sig')
      print(match_df.shape)
      print('After preprocessing, pls double check and adjust manually, and do not forget to save, this only for your first use, afterwards we will update automatically！')


def get_last_apply(standard_company_path:Path, apply_data_path:Path, last_apply_path: Path):
      df = pd.read_csv(apply_data_path)
      standard_df = pd.read_csv(standard_company_path)
      apply_df = df.merge(standard_df, on='company', how='left')
      last_df = apply_df[['apply_date','united_company']].drop_duplicates().sort_values(by=['united_company','apply_date'], ascending=False).drop_duplicates(subset='united_company',keep='first')
      last_df.rename(columns={'united_company':'company'},inplace=True)
      last_df.to_csv(last_apply_path, index=False, encoding='utf-8-sig')
      print('Extracted the date of the last historical application, done, and saved the spreadsheet. You can call it directly later!')


def update_new_scraped_data(processed_table_path:Path, last_apply_path:Path, is_save: False):
      data = pd.read_csv(processed_table_path)
      if 'apply_date' in data.columns.tolist():
           del data['apply_date']

      last_df = pd.read_csv(last_apply_path)
      data = data.merge(last_df[['company','apply_date']], on='company', how='left')
      print(pd.isnull(data).sum())
      print('Complete updating last apply date！')
      if is_save:
         data.to_csv(processed_table_path, index=False, encoding='utf-8-sig')
      else:
           return data

def clear_folder_os(folder_path):
    if not os.path.exists(folder_path):
        return
    
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)  
        else:
            os.remove(item_path)
    print("Have clear raw data file for next round's using！")

def clear_file_os(file_path):
     if not os.path.exists(file_path):
          return
     os.remove(file_path)

def get_all_jobs():

      import pandas as pd

      df1 = pd.read_csv("../irishjobs_data.csv")
      df2 = pd.read_csv("../linkedin_data.csv")
      df = pd.concat([df1,df2],axis=0)
      print(len(df1)+len(df2)==len(df))
      print(df.shape)
      df['company'] = df['company'].apply(lambda x:str(x).lower())
      df['title'] = df['title'].apply(lambda x:str(x).lower())
      df = df.drop_duplicates(subset=['company','title'],keep='first').reset_index(drop=True)
      print(df.shape)
      last_df = pd.read_csv('../applied_data/last_apply_data.csv')
      last_df.head(1)
      if 'apply_date' in df.columns.tolist():
            del df['apply_date']
      df = df.merge(last_df, on='company', how='left')
      df['recommend'] = ''
      pd.isnull(df).sum()
      df.to_csv('../all_jobs.csv',index=False,encoding='utf-8-sig')

# if __name__=='__main__':
#       main_table_path = Path('../linkedin/irishjobs_data.csv')
#       apply_data_path = Path('../applied_data/my_applied_data.csv')
#       standard_company_path=Path('../applied_data/match_company.csv')
#       last_apply_path = Path('../applied_data/last_apply_data.csv')
#       match_company(main_table_path, apply_data_path, standard_company_path)
#       get_last_apply(standard_company_path, apply_data_path, last_apply_path)
#       update_new_scraped_data(main_table_path, last_apply_path, is_save=True)
      