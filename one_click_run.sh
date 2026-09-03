#!/bin/bash

set -e

# pls do not leave space for below number
# for example, "linkedin_start_page = 1" will not work.
linkedin_start_page=1
linkedin_end_page=2
irishjobs_start_page=1
irishjobs_end_page=2

needed_keywords_in_title="AI,ML,Data,software,senior,engineer"
delete_words_in_title="trainee,affairs,grain,part-time,part time,intern,contract,product"
delete_words_in_company="human,recruitment,jobgether,recruit,fruition,talent"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🚀 Start data collecting and recommendation tasks${NC}"

(
    cd src || { echo -e "${RED}❌ The src directory cannot be accessed${NC}"; exit 1; }
    
    echo -e "${GREEN}[1/3] Parse LinkedIn Data...${NC}"
    poetry run python parser_linkedin.py --start_page $linkedin_start_page --end_page $linkedin_end_page
    
    echo -e "${GREEN}[2/3] Parse IrishJobs Data...${NC}"
    poetry run python parser_irishjobs.py --start_page $irishjobs_start_page --end_page $irishjobs_end_page
    
    echo -e "${GREEN}[3/3] Generate Recommendation...${NC}"
    poetry run python recommend.py \
    --needed_keywords_in_title "$needed_keywords_in_title" \
    --delete_words_in_title "$delete_words_in_title" \
    --delete_words_in_company "$delete_words_in_company"
)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tasks done！${NC}"
else
    echo -e "${RED}❌ The tasks failed, pls check!${NC}"
    exit 1
fi