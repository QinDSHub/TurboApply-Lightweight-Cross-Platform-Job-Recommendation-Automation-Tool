# TurboApply
## A Lightweight, Cross-platform Job Recommendation Automation Tool for More Efficient Job Search

TurboApply is a lightweight, rule-based, cross-platform job recommendation automation tool designed to help job seekers decide faster which opportunities are actually worth applying for.

Instead of trying to help candidates find more jobs, TurboApply focuses on reducing the time spent on repetitive search, screening, duplicate checking, and cross-platform browsing.

**🚀Search less. Decide faster. Apply better. Let automation handle the routine.**

**⚡In a nutshell, the steps are:**
* **Download and unzip the repository (make sure Python and Poetry are installed).**
* **Run `poetry install --no-root`.**
* **Download the required HTML files from LinkedIn and IrishJobs.**
* **Update the relevant variables in `one_click_run.sh`.**
* **Run `poetry run bash one_click_run.sh`.**

The recommendations for today will be generated in less than a minute, and you can apply directly by clicking the URLs provided in the recommendations.

**🎯Fun Scalability Ideas:**
* **Expand job platform coverage:** Platforms like Indeed would also be valuable to integrate. You could simply download the Indeed HTML pages and use Claude Code to help build the corresponding parser scripts.
* **Add customizable features:** You could directly extend the tool with new functions based on specific needs—for example, using it to track company/job alerts for companies that don't provide their own job alert functionality.

### 1. Why TurboApply?

For intensive job seekers, the biggest challenge is often not a lack of opportunities.

It is the opposite: Too many listings, too much repetition, and too many decisions.

When you first start using a job platform, a simple search such as: Job Title + Ireland + Posted in the past 24 hours, can feel surprisingly efficient. Many of the results look relevant, and the decision of whether to apply is relatively straightforward.

However, as the search becomes more intensive, several challenges emerge.

#### Challenge #1 — Persistent Listings Can Dilute the Signal

After browsing several pages, candidates may encounter a significant proportion of long-running or sponsored listings.

These positions are not necessarily irrelevant. The challenge is that, at a particular point in time, only a small subset may represent genuinely strong opportunities for a specific candidate.

The result is a growing gap between: Listings you can see and Listings actually worth acting on.

#### Challenge #2 — Duplicate Applications Consume Time

A position applied for a few days ago may reappear with a fresh posting date.

It can look like a new opportunity, leading to:

- Repeated screening;
- Repeated decision-making;
- Potential duplicate applications;
- Lost time that could otherwise be spent discovering new opportunities.

Candidates therefore face a difficult choice: Apply again — or keep scrolling? Either way, valuable time is consumed.

#### Challenge #3 — More Platforms Can Mean More Complexity

To increase coverage, candidates naturally expand their search across LinkedIn, Indeed, IrishJobs, and other platforms.

But additional platforms can also introduce:

- Duplicate listings;
- Persistent postings;
- Different search interfaces;
- Information overload;
- Repeated manual screening.

In other words: More data does not automatically mean more actionable opportunities.

This creates an important distinction between Search Coverage and Actionable Opportunity Coverage.

TurboApply focuses on the latter.

### 2. The Core Idea

TurboApply was not built to help you find more jobs.

It was built to help you: Decide faster which jobs are actually worth applying for — for you, at this particular point in time.

The goal is to recreate the initial-state experience of a job platform:

Open the recommendation table -> See the jobs worth applying for today -> Click URL -> Apply

No endless scrolling.

No repeated screening.

No wondering whether you have already applied.

The goal is simple: Spend less time searching, and more time acting on the opportunities that actually matter.

### 3. Core Philosophy
Rule-Based Recommendation Can Still Be High-Value

A common assumption in recommendation systems is that a recommendation system only becomes sophisticated once it incorporates ML or deep learning.

TurboApply takes a more pragmatic approach.

In many recommendation scenarios, well-designed rules based on:

- User behavior;
- Historical decisions;
- Time-based signals;
- Business constraints;
- Domain knowledge;

can capture a large proportion of high-value recommendations.

ML/DL can then be introduced when the incremental improvement justifies the additional:

- Engineering effort;
- System complexity;
- Maintenance cost;
- Operational overhead.

The key question is therefore not: "Can we use ML?", but: "Is the additional complexity justified by the value it delivers?"

This leads to one of the core engineering principles behind TurboApply: Use the simplest approach that can reliably solve the problem, and introduce additional complexity only when the incremental value justifies it.

The recommendation engine is therefore intentionally:

- Rule-based
- Lightweight
- Explainable
- Configurable
- User-specific
- Extensible

### 4. Overall Architecture

TurboApply consists of five major stages:

```text
┌─────────────────────────────┐
│       Job Platforms         │
│ LinkedIn / IrishJobs / ...  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 1. Data Acquisition         │
│ Incremental Job Data        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 2. Historical Data Loading  │
│ Application History         │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 3. Preprocessing &          │
│    Feature Extraction       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 4. Rule-Based Filtering &   │
│    Recommendation           │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 5. Application Tracking &   │
│    Master Dataset           │
│    Maintenance              │
└──────────────┬──────────────┘
               │
               └───────────────┐
                               ▼
                    Updated Application
                          History
                               │
                               └──────► Future
                                     Recommendations
```

The system therefore forms a closed feedback loop:

Historical Applications -> Recommendation -> New Applications -> Updated History -> Future Recommendations

### 5. Data Processing Pipeline
#### 5.1 Data Acquisition

Collect incremental job data from supported job platforms.

The system is designed to process newly available listings while minimizing unnecessary reprocessing of historical data.

#### 5.2 Historical Data Loading

Load the user's historical application records and reconcile them with platform data.

For company-name matching, the system uses: jellyfish.jaro_winkler_similarity()

This helps bridge minor naming differences.

For example:

Personal Record:
ABC Company

Platform:
ABC Company Ireland

The similarity-based matching allows these records to be associated with the same company.

#### 5.3 Data Preprocessing & Feature Extraction

Raw platform data is:

- Cleaned;
- Parsed;
- Normalized;
- Structured;
- Enriched with relevant features.

The result is a consistent representation that can be consumed by the recommendation engine.

#### 5.4 Rule-Based Recommendation

The recommendation engine applies user-specific rules based primarily on:

Posting Time
      +
Application History
      +
Application Strategy

The rules are intentionally transparent and configurable.

#### 5.5 Application Tracking

Newly submitted applications are appended to the historical master dataset.

This maintains information such as:

last_apply_date

which is then used by future recommendation cycles.

### 6. Recommendation Rules

The current system contains two eligibility rules and one prioritization rule.

Rule	Condition	Level
1	Posted within the last 7 days + never applied to the company before	Must-apply
2	Posted within the last 3 days + more than 30 days since the last application to the company	Must-apply
3	Sort all recommended jobs by posting time, descending	Priority

```text
(1) Rule 1 — New Company
Posted ≤ 7 days
+
Never applied to company
        ↓
Must-apply

The objective is to identify genuinely new opportunities and avoid repeatedly targeting the same companies.

(2) Rule 2 — Re-engagement After a Sufficient Interval
Posted ≤ 3 days
+
Last application > 30 days ago
        ↓
Must-apply

This allows previously targeted companies to become relevant again after a reasonable interval.

(3) Rule 3 — Recent Opportunities First

Among qualifying recommendations, more recently posted positions receive higher priority.

The basic principle is: Use recentness to identify opportunities, historical application behavior to control repetition, and posting time to prioritize the final recommendation list.
```

### 7. Evolution of the Architecture
V1 — Fully Automated Workflow

The initial architecture aimed for a fully automated, zero-touch workflow:

```text
Platform
   ↓
Automated Crawler
   ↓
Historical Data
   ↓
Preprocessing
   ↓
Recommendation Rules
   ↓
today_recommendation.csv
```

The crawler automatically collected incremental listings from LinkedIn and IrishJobs.

Under ideal conditions, this was highly efficient.

However, real-world platform access constraints exposed an important limitation.

V1 Bottleneck — Platform Access Constraints

During development, the crawler encountered platform-specific access limitations.

Observed behavior included approximately:

Platform	Observed Constraint
LinkedIn	Approximately 10 job postings per page, with around 4 pages accessible through the crawler
IrishJobs	Approximately 4 pages accessible; subsequent access could be denied and repeated attempts could trigger IP-level restrictions

These observations reflect the behavior encountered during development and may change as the platforms evolve.

The fundamental problem was: A recommendation system depends on opportunity coverage, while the crawler's coverage depends on platform-specific access behavior.

When the number of newly posted jobs increased, the crawler could fail to capture the complete set of relevant listings.

### 8. V2 — Manual HTML + Automated Processing

Instead of continuously increasing crawler complexity, TurboApply adopted a pragmatic semi-automated architecture:

```text
Job Platform
     ↓
Manual HTML Download
     ↓
Platform-Specific Parser
     ↓
Common Job Dataset
     ↓
Cross-Platform Deduplication
     ↓
Historical Data Integration
     ↓
Rule Engine
     ↓
Recommendation
```

Only the data acquisition step becomes partially manual.

The downstream pipeline remains automated.

Why?

This change provides several advantages:

- Less dependency on platform-specific access policies
- Greater platform portability
- Greater search flexibility
- Lower crawler maintenance overhead
- Cross-platform integration
- Minimal additional manual effort
- Better operational robustness

Most importantly, the architecture separates: Data acquisition from Data processing and recommendation

This transforms TurboApply from a platform-specific crawler into a more: Portable and extensible job-search intelligence layer

### 9. Cross-Platform Integration

New platforms can be integrated through a platform-specific parser:

```text
LinkedIn ─────► linkedin_parser.py ────┐
IrishJobs ────► irishjobs_parser.py ───┤
Indeed ───────► indeed_parser.py ──────┤
                                       ▼
                              Common Job Schema
                                       │
                                       ▼
                              Recommendation Engine
```

The core recommendation logic remains platform-independent.

The system also applies cross-platform deduplication based on the combination of:

Company + Position

This prevents the same opportunity from appearing repeatedly in the final recommendation set.

### 10. Observed Efficiency Improvement

Previously, completing one valid application could take approximately one hour, including:

```text
Search
  ↓
Screen
  ↓
Check previous applications
  ↓
Evaluate
  ↓
Find application page
  ↓
Apply

With TurboApply:

Recommendation
      ↓
Review
      ↓
Click URL
      ↓
Apply
```

Based on my experience, this reduces the time spent on repetitive search and screening sufficiently to support approximately 5–6 targeted applications within the same hour.

This is an observed personal result, rather than a formal benchmark.

More importantly, the saved time can be redirected toward:

- Interview preparation;
- Job research;
- Personal projects;
- Professional development;
- Rest and recovery.

The goal is therefore not: Apply to more jobs.

It is: Maximize relevant applications per unit of time.

### 11. Who Is TurboApply For?

TurboApply is particularly suitable for users who:

Search across LinkedIn, IrishJobs, or multiple job platforms;
Typically complete only 1–2 meaningful applications per hour;
Want to maintain structured application history;
Want to reduce duplicate applications;
Want personalized, rule-based recommendations;
Want to consolidate opportunities from multiple platforms.
Who May Benefit Less?

If you already consistently identify and submit 5–7 highly relevant applications per hour, your existing workflow may already be highly efficient.

In that case, the marginal benefit of TurboApply may be limited.

This is intentional.

TurboApply is designed around a specific workflow bottleneck rather than trying to become a universal job-search platform.

### 12. Quick Start
Requirements
Python	3.12.7
Poetry	2.4.1

Installation steps as below:

(1) Clone the repository:
git clone https://github.com/QinDSHub/TurboApply_Lightweight_Tool.git
cd TurboApply_Lightweight_Tool

(2) Install dependencies:
poetry install --no-root

(3) Prepare Raw HTML Data
Search for relevant jobs on supported platforms, such as LinkedIn and IrishJobs, using your preferred keywords. Save the downloaded HTML pages as page_1.html, page_2.html, etc. in the corresponding platform directory, as each platform has its own dedicated parser.

For example:
```text
linkedin_raw_data/
├── page_1.html
├── page_2.html
└── ...
Configure the Pipeline
```

(4) Open:one_click_run.sh

(5) Configure:
linkedin_start_page
linkedin_end_page
irishjobs_start_page
irishjobs_end_page
needed_keywords_in_title — Keywords to include in job titles that are relevant to your job search.
delete_words_in_title — Keywords to exclude from job titles. For example, if you are only interested in permanent positions, you can add part-time to filter out part-time roles.
delete_words_in_company — Company names or keywords to exclude from the results. For example, if you want to filter out companies containing a specific keyword, add that keyword to this list.

(6) Run: poetry run bash one_click_run.sh

The pipeline automatically performs:

```text
Parsing
  ↓
Cross-Platform Merge
  ↓
Deduplication
  ↓
Historical Data Integration
  ↓
Data Preprocessing
  ↓
Feature Extraction
  ↓
Recommendation
```

The final output is: today_recommendation.csv

Open the file and use the url column to navigate directly to the corresponding job posting or application page.

### 13. Repository Structure
```text
TurboApply_Lightweight_Tool/
│
├── linkedin_raw_data/
├── irishjobs_raw_data/
│
├── src:
|────────linkedin_parser.py
|────────irishjobs_parser.py
|────────recommend.py
|
├── one_click_run.sh
│
├── today_recommendation.csv
│
├── pyproject.toml
├── README.md
│
└── docs/
    └── ARCHITECTURE.md
```

### 14. Extensibility

The architecture currently supports:

Multi-platform Integration

Add a platform-specific parser without fundamentally changing the recommendation engine.

Cross-platform Deduplication

Identify the same company–job opportunity across multiple sources.

Persistent Application History

Maintain historical application records and update them incrementally.

Extensible Recommendation Rules

Additional rules can be added as application preferences evolve.

The architecture is intentionally designed so that future ML/DL components could be introduced without replacing the entire pipeline.

For example:

Current:
```text
Raw Data
   ↓
Rules
   ↓
Recommendation
```

Potential Future:
```text
Raw Data
   ↓
Rules + ML Ranking
   ↓
Recommendation
```

The ML component would therefore be introduced only if it provides sufficient incremental value.

### 15. Future Direction

One longer-term possibility is that capabilities such as:

Personalized filtering;
Application-history awareness;
Duplicate detection;
Cross-platform consolidation;
Candidate-specific recommendation;

could eventually become an optional candidate-side value-added service built directly into job platforms.

The goal is not necessarily to replace existing platforms.

Instead, TurboApply explores a broader question:

How can the candidate experience become significantly more efficient on top of the infrastructure that already exists?

### 16. Final Thoughts

Throughout the development of TurboApply, one of my deepest realizations has been:

The essence of efficiency is not doing more things. It is making fewer unnecessary decisions.

When the machine can take over the repetitive judgment of:

“Is this job worth applying for?”

the candidate can redirect that cognitive energy toward the question that matters more:

“How can I make this application as strong as possible?”

That is ultimately what TurboApply is trying to achieve.

Not simply: Apply faster.

But: Spend more of your limited time on the parts of the job-search process where human judgment matters most.

### 17. GenAI-Assisted Development

The overall architecture, recommendation strategy, and design evolution of TurboApply are based on my own hands-on experience and experimentation during an intensive job-search process.

At the implementation and documentation level, I also used several GenAI tools as development assistants:

Claude Code — used primarily for platform-specific parser implementation, code generation, debugging, and iterative development.
DeepSeek — used for scripting and automation tasks, as well as Chinese-language optimization and the initial English-language version.
ChatGPT — used for final English-language refinement, technical writing, consistency, and readability improvements.

This experience reinforced another observation: Different GenAI products have different strengths.

Rather than treating these tools as interchangeable, users can combine their respective strengths at different stages of a project.

From a product perspective, these differentiated capabilities may also represent an important source of competitive advantage for GenAI companies.

### 18. Platform Compatibility & Disclaimer

The current platform-specific parsers are functional with the platform versions and page structures used during development.

However, web platforms may change:

- Page structures;
- Access policies;
- HTML layouts;
- Search interfaces;
- Other implementation details.

Future compatibility issues therefore cannot be ruled out.

When such changes occur, parser and integration logic may need to be updated.

TurboApply is a personal open-source engineering project, rather than a production-grade commercial service.

### 19. A Note to Fellow Job Seekers

I hope that everyone on the job-seeking journey can eventually find a position they genuinely enjoy and feel proud of.

Stay strong, keep moving forward, and let's encourage one another along the way.

Documentation

For the complete technical discussion, including the detailed architecture evolution, recommendation rules, implementation considerations, and design trade-offs, see:

docs/ARCHITECTURE.md

Contributing

The project is open source.

You are welcome to:

- Explore the code;
- Report issues;
- Suggest improvements;
- Add support for additional job platforms;
- Improve recommendation rules;
- Submit pull requests.
- Repository

TurboApply: Search less. Decide faster. Apply better.
