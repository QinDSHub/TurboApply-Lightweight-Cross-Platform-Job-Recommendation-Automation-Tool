#!/bin/bash

# 设置错误时退出
set -e

# 注意：在 bash 中，变量赋值时等号两边不能有空格。
linkedin_start_page=1
linkedin_end_page=1
irishjobs_start_page=1
irishjobs_end_page=1

# 需要维护的关键词
# 在 Bash 中：
# = 两边不能有空格（这个你注意到了 ✅）
# 但 Bash 数组要用括号 ()，不是方括号 []
# 元素之间用空格分隔，不是逗号
# title_filter_keywords=['AI', 'ML', 'Data', 'software', 'senior', 'engineer']
# delete_words_in_title=['trainee', 'affairs', 'grain', 'part-time', 'part time', 'intern', 'contract', 'product']
# delete_words_in_company=['human', 'recruitment', 'jobgether', 'recruit', 'fruition', 'talent']

# 用逗号分隔的字符串
title_filter_keywords="AI,ML,Data,software,senior,engineer"
delete_words_in_title="trainee,affairs,grain,part-time,part time,intern,product"
delete_words_in_company="human,recruitment,jobgether,recruit,fruition,talent"
job_alert_company="mastercard,jpmorganchase,citi,bny"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🚀 开始执行数据抓取和推荐任务${NC}"

# 进入 src 目录（子shell方式）
(
    cd src || { echo -e "${RED}❌ 无法进入 src 目录${NC}"; exit 1; }
    
    # 运行 LinkedIn 解析器
    echo -e "${GREEN}[1/3] 解析 LinkedIn 数据...${NC}"
    poetry run python parser_linkedin.py --start_page $linkedin_start_page --end_page $linkedin_end_page
    
    # 运行 IrishJobs 解析器
    echo -e "${GREEN}[2/3] 解析 IrishJobs 数据...${NC}"
    poetry run python parser_irishjobs.py --start_page $irishjobs_start_page --end_page $irishjobs_end_page
    
    # 运行推荐系统
    echo -e "${GREEN}[3/3] 生成推荐...${NC}"
    poetry run python recommend.py \
    --title_filter_keywords "$title_filter_keywords" \
    --delete_words_in_title "$delete_words_in_title" \
    --delete_words_in_company "$delete_words_in_company" \
    --job_alert_company "$job_alert_company"
)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 所有任务成功完成！${NC}"
else
    echo -e "${RED}❌ 任务执行失败${NC}"
    exit 1
fi