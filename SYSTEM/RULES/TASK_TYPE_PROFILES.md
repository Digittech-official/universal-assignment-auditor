# Task-Type Profiles

Used by Agent 1 (classification), Agent 4 (blueprint), Agent 7 (specialist review) and Agent 9 (coherence chain).
Everything in the "Typical conventions" column is **BEST PRACTICE** unless a supplied document requires it.
"Do NOT impose" lists conventions that must not be applied to that task type unless explicitly required.

| Task type | Specialist reviews | Typical conventions (best practice only) | Logical chain (Agent 9) | Do NOT impose |
|---|---|---|---|---|
| Academic Essay | WRITTEN_WORK | Thesis statement, introduction/body/conclusion, argument with evidence, critical engagement, consistent referencing | Question → Thesis → Arguments → Evidence → Counter-arguments → Conclusion answers question | Chapters, methodology, research questions, abstract, literature-review chapter, code/testing conventions |
| Dissertation / Thesis | WRITTEN_WORK, RESEARCH_METHODS (+ DATA_STATISTICS if quantitative) | Abstract, introduction, literature review, methodology, findings, discussion, conclusion, recommendations, references, appendices; ethics where human participants | Title → Aim → Objectives → Research questions → Literature → Methodology → Findings → Discussion → Conclusion → Recommendations | Coding conventions (unless software artefact), presentation conventions |
| Research Report | WRITTEN_WORK, RESEARCH_METHODS | Aims, method, results, discussion, limitations | Aim → Method → Results → Discussion → Conclusion | Dissertation chapter lengths, abstract unless asked |
| Literature Review | WRITTEN_WORK | Search strategy/scope, thematic synthesis, critical comparison, gaps | Scope/question → Themes → Synthesis → Gaps → Conclusion | Primary-data methodology, results chapter |
| Business / Management Report | WRITTEN_WORK, BUSINESS_ANALYSIS | Executive summary, analysis with frameworks, evidence, recommendations with justification, implementation | Purpose → Situation analysis → Findings → Options → Recommendations → Implementation | Research questions, methodology chapter, hypothesis testing |
| Case Study | WRITTEN_WORK, BUSINESS_ANALYSIS (if business) | Case facts, issue identification, theory application, evaluation, recommendations | Case facts → Issues → Theory/analysis → Evaluation → Recommendations | Dissertation structure |
| Reflective Assignment | WRITTEN_WORK, REFLECTIVE_PRACTICE | Reflective model (e.g. Gibbs, Kolb) if relevant, first person, critical insight, action plan | Experience → Reflection → Analysis/theory → Learning → Action plan | Third-person impersonal requirement, research methodology, literature-review chapter |
| Scientific / Laboratory Report | WRITTEN_WORK, SCIENTIFIC_LAB (+ DATA_STATISTICS) | Aim/hypothesis, method replicable, results with units/uncertainty, discussion vs theory, error analysis | Aim/Hypothesis → Method → Results → Analysis → Discussion → Conclusion | Literature-review chapter, recommendations section |
| Technical Report | WRITTEN_WORK, TECHNICAL_DOCUMENTATION (+ CODE / DATA if artefacts supplied) | Problem definition, specification, design, implementation, evaluation, conclusions | Problem → Requirements/spec → Design → Implementation → Evaluation → Conclusion | Dissertation research-question chain, essay thesis structure |
| Coding / Software Project | CODE (+ TECHNICAL_DOCUMENTATION if report) | Meets specification, correct logic, input validation, error handling, tests, readable structure, documentation/README | Specification → Design → Implementation → Tests → Outputs → Documentation | Literature review, academic referencing (unless required), essay argument structure, word counts |
| Data Analysis / Statistics | DATA_STATISTICS (+ CODE if scripts/notebooks, WRITTEN_WORK if report) | Clear question, data description/cleaning, appropriate methods, assumptions checked, correct interpretation, reproducibility, labelled charts | Question → Data → Method → Results → Interpretation → Conclusion/limitations | Dissertation chapters, essay conventions |
| Presentation | PRESENTATION | Clear narrative, one idea per slide, legible visuals, evidence, conclusion, speaker notes if required | Objective → Key messages → Evidence per slide → Conclusion/call to action | Word-count and dense-paragraph conventions, dissertation structure |
| Project Documentation | TECHNICAL_DOCUMENTATION | Scope, requirements, plan, risks, status, deliverables | Scope → Requirements → Plan → Delivery → Evaluation | Academic essay/dissertation conventions |
| Mixed Assignment | Union of the components' reviews | Each component judged by its own profile | Chain per component + cross-component consistency (e.g. report claims match code/data) | Applying one component's conventions to another |
| Other | WRITTEN_WORK by default | Only general quality conventions | Purpose → Content → Conclusion | Any discipline-specific convention without evidence |

Specialist review codes: CODE, DATA_STATISTICS, PRESENTATION, WRITTEN_WORK, RESEARCH_METHODS, SCIENTIFIC_LAB,
BUSINESS_ANALYSIS, REFLECTIVE_PRACTICE, TECHNICAL_DOCUMENTATION.

Consistency rule: `coding_review_required` ⇔ CODE is listed; `statistical_review_required` ⇔ DATA_STATISTICS;
`presentation_review_required` ⇔ PRESENTATION. `validate.py` enforces this and rejects reviews that were run
when not required.
