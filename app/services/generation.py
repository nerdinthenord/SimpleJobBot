from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json

from ..models import JobInput
from .ollama_client import ollama_chat
from ..utils import sanitize_part, build_short_answers_text, label_fit

OUTPUT_ROOT = Path("job-packages")


async def generate_resume(job: JobInput) -> str:
    prompt = f"""
You are tailoring a resume for a specific role.

Base resume text
----------------
{job.resume_text}

Job description
---------------
{job.job_description}

Role context
------------
Company  {job.company}
Title    {job.title}
Location {job.location or "unspecified"}
Seniority hint {job.seniority_hint or "unspecified"}

Rules
1. Use only facts that appear in the base resume and job description. Do not invent or guess employers, job titles, dates, locations, certifications, technologies, numbers, or metrics.
2. If the base resume does not mention something, leave it out rather than imagining it.
3. Include every role and experience from the base resume. It is acceptable to compress older roles into one or two short bullets each, but do not drop them entirely.
4. Stay strictly truthful. No made up achievements, percentages, or dollar amounts. If you cannot support a claim directly from the base resume or job description, do not write it.
5. Limit the resume to roughly two pages of text, about 900 to 1100 words. If you need to shorten, compress wording rather than deleting roles.
6. Use a clear, professional, human tone. Avoid AI buzzwords and self congratulatory language.
7. Do not mention AI, language models, ChatGPT, or any tooling in the resume.

Task
Rewrite the resume so it is clearly aligned to the job description and follows all of the rules above.

Return only the final resume text with no extra commentary.
    """.strip()

    return await ollama_chat(prompt)


async def generate_cover_letter(job: JobInput) -> str:
    prompt = f"""
Write a clear, truthful cover letter for this role.

Base resume text
----------------
{job.resume_text}

Job description
---------------
{job.job_description}

Role context
------------
Company  {job.company}
Title    {job.title}
Location {job.location or "unspecified"}
Seniority hint {job.seniority_hint or "unspecified"}

Rules
1. Use only experience and facts that appear in the base resume or are clearly implied by the job description. Do not invent employers, titles, dates, tools, certifications, metrics, or project outcomes.
2. Keep the letter honest and grounded. If a result or metric is not explicitly known from the base resume, describe the impact qualitatively instead of guessing numbers.
3. Aim for about 3 to 6 concise paragraphs that would fit on a single page.
4. Use a direct, professional tone. Avoid generic AI style phrases such as "I am excited to leverage my unique skill set" or "I am confident that my background makes me the ideal candidate."
5. Do not mention AI, language models, or any tooling in the letter.
6. Make sure the letter remains consistent with the roles, dates, and responsibilities in the base resume.

Task
Write the complete cover letter text that follows these rules.

Return only the cover letter text with no extra commentary.
    """.strip()

    return await ollama_chat(prompt)


async def generate_short_answers(job: JobInput) -> List[str]:
    prompt = f"""
You will generate three short, truthful answers for common job application questions.

Base resume text
----------------
{job.resume_text}

Job description
---------------
{job.job_description}

Role context
------------
Company  {job.company}
Title    {job.title}

Rules
1. Use only experience and facts that appear in the base resume. Do not invent projects, employers, dates, tools, certifications, metrics, or titles.
2. If you reference an achievement or improvement and there are no hard numbers, keep it qualitative. Do not fabricate percentages or dollar values.
3. Each answer should be 3 to 6 sentences and easy to read.
4. Keep the tone professional and human. Avoid AI style phrasing and buzzwords.
5. Do not mention AI, language models, ChatGPT, or any tooling.

Questions
1. Why are you a good fit for this role
2. Describe a time you improved a process or reduced risk.
3. Why do you want to work at this company

Task
Write three separate answers in order for the three questions above.

Format
Return the three answers as plain text.
Separate each answer with exactly one blank line.
Do not number them and do not include the questions again.
    """.strip()

    raw = await ollama_chat(prompt)
    parts = [p.strip() for p in raw.split("\n\n") if p.strip()]
    if len(parts) >= 3:
        return parts[:3]
    if parts:
        while len(parts) < 3:
            parts.append(parts[-1])
        return parts[:3]
    return ["", "", ""]


def estimate_fit_score(job: JobInput) -> float:
    base = 70.0
    if job.seniority_hint and job.seniority_hint in {"senior", "lead", "director", "executive"}:
        base += 5.0
    if len(job.job_description) > 1500:
        base += 5.0
    return max(0.0, min(100.0, base))


async def generate_full_package(job: JobInput) -> Dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    folder_name = f"{sanitize_part(job.company, 'company')}_{sanitize_part(job.title, 'title')}_{timestamp}"
    job_dir = OUTPUT_ROOT / folder_name
    job_dir.mkdir(parents=True, exist_ok=True)

    resume_text = await generate_resume(job)
    cover_text = await generate_cover_letter(job)
    short_answers_list = await generate_short_answers(job)

    answers_text = build_short_answers_text(short_answers_list)

    (job_dir / "resume_full.txt").write_text(resume_text, encoding="utf8")
    (job_dir / "cover_letter.txt").write_text(cover_text, encoding="utf8")
    (job_dir / "short_answers.txt").write_text(answers_text, encoding="utf8")

    fit_score = estimate_fit_score(job)
    fit_label = label_fit(fit_score)

    meta = {
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "seniority_hint": job.seniority_hint.value if job.seniority_hint else None,
        "fit_score": fit_score,
        "fit_label": fit_label,
        "folder_name": folder_name,
        "created_at": timestamp,
    }

    (job_dir / "meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf8",
    )

    return {
        "job_dir": str(job_dir),
        "fit_score": fit_score,
        "fit_label": fit_label,
        "folder_name": folder_name,
    }
