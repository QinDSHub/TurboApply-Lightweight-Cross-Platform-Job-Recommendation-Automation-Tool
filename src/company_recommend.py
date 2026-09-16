from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import dotenv,os
from pathlib import Path
from pydantic import BaseModel, Field
from utils import load_config
from typing import List, Type
from langchain_core.language_models import BaseChatModel
import argparse
import pandas as pd
dotenv.load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")

class IndustryItem(BaseModel):
    company: str = Field(description="company name")
    sector: str = Field(description="primary industry from list")
    subsector: str = Field(description="sub-industry name, such as Payments / Neobank / Insurance / SaaS")
    tags: list[str] = Field(description="extract 3-6 tags for afterwards search, such as ['payments','fintech']")

class IndustryRes(BaseModel):
    results: list[IndustryItem]

llm_1 = ChatOpenAI(model="gpt-5.6-luna", 
                 temperature=0.3, 
                 api_key=api_key, 
                 base_url=base_url).with_structured_output(IndustryRes)

SECTORS = [
    "Banking / Traditional Financial Services",
    "Insurance",
    "FinTech / Payments / Digital Finance",
    "Asset Management / Wealth / Investment",
    "Crypto / Blockchain",
    "ICT / Technology / Software",
    "Professional / Scientific / Technical Services",
    "Life Sciences / Pharma / MedTech",
    "Industrial / Manufacturing / Engineering",
    "Others",
]

SUBSECTORS = [
    # Banking
    "Retail Banking",
    "Commercial Banking",
    "Corporate Banking",
    "Investment Banking",
    "Consumer Finance",
    "Transaction Banking",

    # Payments / FinTech
    "Payments",
    "Card Networks",
    "Payment Processing",
    "Payment Infrastructure",
    "Neobank",
    "Digital Banking",
    "Lending",
    "InsurTech",

    # Asset Management
    "Asset Management",
    "Wealth Management",
    "Investment Management",

    # Technology
    "Enterprise Software",
    "SaaS",
    "Cloud Infrastructure",
    "Cybersecurity",
    "Developer Tools",
    "Data & Analytics",
    "AI / Machine Learning",
    "IT Services",

    # Professional Services
    "Consulting",
    "Professional Services",
    "Engineering Services",

    # Life Sciences
    "Pharma",
    "Biotechnology",
    "Medical Devices",
    "Healthcare Technology",

    # Industrial
    "Manufacturing",
    "Industrial Automation",
    "Engineering",
    "Automotive",
    "Energy",
]

prompt_1 = ChatPromptTemplate.from_template("""
You are an industry classification expert.

Classify each company into exactly one sector and one subsector from the provided
controlled vocabularies, plus 3-6 useful tags.

Companies:
{interview_company}

Sectors:
{sectors}

Subsectors:
{subsectors}

Rules:
- "sector" MUST exactly match one item in Sectors.
- "subsector" MUST exactly match one item in Subsectors.
- Classify based on the company's primary business, not a specific product, job,
  technology, or department.
- Use 3-6 lowercase English tags describing the company's business, products,
  or market. Avoid generic tags and company names.
- Keep terminology consistent across similar companies.
- If uncertain, use "Others" for sector and explain through tags.
- Return exactly one result per company, in the same order.

Output JSON that strictly matches this schema:
{schema}
""",
partial_variables={
    "sectors": "\n".join(f"- {s}" for s in SECTORS),
    "subsectors": "\n".join(f"- {s}" for s in SUBSECTORS),
    "schema": IndustryRes.model_json_schema(),
},
)


def gain_sector_agent(response_model:Type[IndustryRes], 
                      llm_1: BaseChatModel, 
                      interview_company_settled:str, ) -> IndustryRes:

      chain = prompt_1 | llm_1

      output_1 = chain.invoke({"interview_company":'\n'.join(interview_company_settled)})

      if not isinstance(output_1, response_model):
            raise ValueError(f"Unexpected output type: {type(output_1)}")

      return output_1



class CompanyItem(BaseModel):
    company: str
    rank: int
    reason: str

class ExpandedRes(BaseModel):
    companies: list[CompanyItem]


prompt_2 = ChatPromptTemplate.from_template("""
You are an industry research assistant.
Given a seed company and its industry labels, list similar companies in {region}
that operate in the same subsector.

Seed company: {seed_company}
Sector: {sector}
Subsector: {subsector}
Tags: {tags}

Requirements:
- Return up to {top_k} companies, if fewer qualify, return only the ones you are confident about.
- Only include companies primarily operating in the same subsector as the seed company in {region}.
- Only include real, currently active companies. Do not invent or guess names.
- Do not duplicate companies (e.g. do not list both "JPMorgan" and "JPMorgan Chase").
- Rank the results by how well they fit the subsector, with rank 1 = best fit.
- "rank" must start at 1 and be consecutive and unique.

For each company, return:
- company: common name
- rank: integer, 1 = most recommended
- reason: one sentence explaining why it fits the subsector

Output JSON that strictly matches this schema:
{schema}
""",
partial_variables = {"schema":ExpandedRes.model_json_schema()},
)


llm_2 = ChatOpenAI(model='gpt-5.6-luna', 
                 temperature=0.1, 
                 api_key=api_key, 
                 base_url=base_url).with_structured_output(ExpandedRes)


def company_recommend_agent(seed:BaseModel, 
                            response_model: Type[ExpandedRes], 
                            llm_2: BaseChatModel,
                            region: str,
                            top_k:int,)->ExpandedRes:

      chain_2 = prompt_2 | llm_2

      output_2 = chain_2.invoke(
            {
            "region":region,
            "seed_company":seed.company,
            "sector":seed.sector,
            "subsector":seed.subsector,
            "tags":",".join(seed.tags),
            "top_k":top_k}
      )

      if not isinstance(output_2, response_model):
            raise ValueError(f"Unexpected output type: {type(output_2)}")

      return output_2


if __name__ == "__main__":
    
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    arg_parser = argparse.ArgumentParser(description="get top similar companies corresponding to interview company")
    arg_parser.add_argument("--config", type=str, default=str(PROJECT_ROOT / "config.yaml"))
    args = arg_parser.parse_args()

    cfg = load_config(args.config)
    config_dir = Path(args.config).resolve().parent

    def resolve_path(base: Path, p) -> Path:
        p = Path(p)
        return p if p.is_absolute() else (base / p).resolve()

    similar_company_save_path = resolve_path(config_dir, cfg['similar_company_save_path'])

    interview_company = cfg['interview_company']
    interview_company_list = [c.strip() for c in interview_company.split(',') if c.strip()]
    interview_company_settled = '\n'.join(interview_company_list)

    top_k = cfg['top_k']
    region = cfg['region']

    output = gain_sector_agent(IndustryRes, llm_1, interview_company_settled)

    data = []
    for seed in output.results:
        sub_output = company_recommend_agent(seed, ExpandedRes, llm_2, top_k, region)
        for item in sub_output.companies:
             data.append([item.company, item.rank, item.reason])
    if data:
        df = pd.DataFrame(data, columns=['company','rank','reason'])
        cnt = df.groupby('company').size().rename("cnt")
        df = (df.sort_values(by=['company','rank'],ascending=True).\
              drop_duplicates(subset=['company'],keep='first').\
                merge(cnt,on='company',how='left').\
                    sort_values(by=['cnt','rank'], ascending=[False, True]).\
                        reset_index(drop=True))
        df[['company','reason']].to_csv(similar_company_save_path, index=False, encoding='utf-8-sig')
    else:
        print("No output, pls double check your scripts!")



