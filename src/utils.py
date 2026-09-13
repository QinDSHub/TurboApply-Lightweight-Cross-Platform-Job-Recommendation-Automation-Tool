# import linktransformer as lt

# df1 = pd.read_csv(Path('./extracted_from_raw_data/irishjobs_data.csv'))
# df2 = pd.read_csv(Path('./applied_data/my_applied_data.csv'))

# df1 = df1[['company']].drop_duplicates().reset_index(drop=True)
# df2 = df2[['company']].drop_duplicates().reset_index(drop=True)

# # 用 LinkTransformer 进行链接
# # 它会自动将 df 中的 'CompanyName' 与 master_df 中的 'CompanyName' 匹配，
# # 并返回匹配上的标准名称
# merged_df = lt.merge(df1, df2, merge_type='1:m', on="company")

# # 问题：（1）匹配结果并不好；（2）只能根据df1标准的1：1匹配，即df1中的一个样本找到df2中最相似的一个样本；放弃！

import pandas as pd
from pathlib import Path
import jellyfish
import os, shutil
import yaml
from dataclasses import dataclass

@dataclass
class JobInfo:
    job_id: str
    title: str
    company: str
    location: str
    salary: str
    posted_date: str
    job_url: str = "" 
    scrape_date: str = "" 
    recommend: str = ""
    apply_date: str = ""

def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def fuzzy_match(name, master_list, threshold=0.80):
    best_match = None
    best_score = 0
    for master in master_list:
        # ✅ 使用 jellyfish.jaro_winkler_similarity 替换
        score = jellyfish.jaro_winkler_similarity(name.lower(), master.lower())
        if score > best_score and score >= threshold:
            best_score = score
            best_match = master
    return best_match, best_score

# 使用Jaro-Winkler轻量级模糊匹配，尤其适合短文本
def match_company(main_table_path: Path, apply_data_path: Path, standard_company_path: Path):
      all_data = pd.read_csv(main_table_path)
      all_data['company'] = all_data['company'].apply(lambda x:x.lower())
      master_list = all_data[['company']].drop_duplicates().sort_values(by=['company'])
      master_list = master_list['company'].unique().tolist()

      df = pd.read_csv(apply_data_path)
      df['company'] = df['company'].apply(lambda x:x.lower())
      name_list = df[['company']].drop_duplicates().sort_values(by=['company'])
      name_list = name_list['company'].unique().tolist()

      print('开始模糊匹配')
      res = []
      for name in name_list:
            match, score = fuzzy_match(name, master_list)
            if match is None:
                  res.append([name, name, 2])
            else:
                  res.append([name, match, score])

      # 对应的是我投递数据的un-standard company, standard company, score
      match_df = pd.DataFrame(res, columns=['company', 'united_company', 'score'])
      match_df = match_df.sort_values(by=['company','united_company']).reset_index(drop=True)

      # 手动预处理下，保存后不要删除
      match_df.to_csv(standard_company_path,index=False,encoding='utf-8-sig')
      print(match_df.shape)
      print('预处理完成，可以手动进行调整下，保存以后就不要动了！')


def get_last_apply(standard_company_path:Path, apply_data_path:Path, last_apply_path: Path):
      # 从我的申请表中提取每家公司的最后一个apply_date
      df = pd.read_csv(apply_data_path)
      standard_df = pd.read_csv(standard_company_path)
      apply_df = df.merge(standard_df, on='company', how='left')
      last_df = apply_df[['apply_date','united_company']].drop_duplicates().sort_values(by=['united_company','apply_date'], ascending=False).drop_duplicates(subset='united_company',keep='first')
      last_df.rename(columns={'united_company':'company'},inplace=True)
      last_df.to_csv(last_apply_path, index=False, encoding='utf-8-sig')
      print('提取历史最后一次申请的日期，已完成，并保存表格，后续可以直接调用！')


def update_new_scraped_data(processed_table_path:Path, last_apply_path:Path, is_save: False):
      data = pd.read_csv(processed_table_path)
      if 'apply_date' in data.columns.tolist():
           del data['apply_date']

      last_df = pd.read_csv(last_apply_path)
      # 更新apply_date到增量表
      data = data.merge(last_df[['company','apply_date']], on='company', how='left')
      print(pd.isnull(data).sum())
      print('更新last apply date完成！')
      if is_save:
         data.to_csv(processed_table_path, index=False, encoding='utf-8-sig')
      else:
           return data

def clear_folder_os(folder_path):
    """使用 os 清空文件夹"""
    if not os.path.exists(folder_path):
        return
    
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)  # 删除文件夹及其内容
        else:
            os.remove(item_path)      # 删除文件
    print("已清空文件夹！")

def clear_file_os(file_path):
     if not os.path.exists(file_path):
          return
     os.remove(file_path)
     
def get_all_jobs():
      # 手动创建初始总表
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
#       # 如果第一次run并更新总表的话：
#       main_table_path = Path('../linkedin/irishjobs_data.csv')
#       apply_data_path = Path('../applied_data/my_applied_data.csv')
#       standard_company_path=Path('../applied_data/match_company.csv')
#       last_apply_path = Path('../applied_data/last_apply_data.csv')
#       match_company(main_table_path, apply_data_path, standard_company_path)
#       get_last_apply(standard_company_path, apply_data_path, last_apply_path)
#       update_new_scraped_data(main_table_path, last_apply_path, is_save=True) # 第一次更新总表需要保存的
      