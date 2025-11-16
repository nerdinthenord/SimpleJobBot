import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import html as html_mod
import requests
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Output folder inside the container
OUTPUT_ROOT = Path("/app/output")

# Ollama settings
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.environ.get("JOBBOT_MODEL", "llama3")

# How we show the path to the user
# Default is a relative looking path that makes sense in the repo
HOST_OUTPUT_ROOT = os.environ.get("HOST_OUTPUT_ROOT", "./job-packages")

app = FastAPI(title="Simple Job Bot")


class JobInput(BaseModel):
    resume_text: str
    company: str
    title: str
    location: Optional[str] = None
    job_description: str
    seniority_hint: Optional[str] = None


class PackageOutput(BaseModel):
    fit_score: float
    fit_label: str
    reasoning: str
    cover_letter: str
    resume: str
    short_answers: List[str]
    container_folder: str
    host_folder: Optional[str] = None


def call_ollama(system_prompt: str, user_prompt: str) -> str:
    url = f"{OLLAMA_HOST}/api/chat"
    body = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    try:
        resp = requests.post(url, json=body, timeout=300)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Error calling Ollama at {url}: {exc}")
    data = resp.json()
    message = data.get("message") or {}
    content = message.get("content")
    if not content:
        raise RuntimeError(f"Ollama returned no content. Raw response: {data}")
    return content


def sanitize_part(text: str) -> str:
    if not text:
        return "job"
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text)
    cleaned = cleaned.strip("_")
    return cleaned or "job"


def create_job_folder(job: JobInput):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{stamp}_{sanitize_part(job.company)}_{sanitize_part(job.title)}"
    job_dir = OUTPUT_ROOT / name
    job_dir.mkdir(parents=True, exist_ok=True)

    # What we show as the host path in the UI
    host_path = f"{HOST_OUTPUT_ROOT}/{name}" if HOST_OUTPUT_ROOT else None
    return job_dir, host_path, name


def map_score_to_label(score: float) -> str:
    if score >= 85:
        return "Strong fit"
    if score >= 70:
        return "Good fit"
    if score >= 55:
        return "Moderate fit"
    return "Low fit"


def clean_model_text(text: str) -> str:
    """Normalize model output for plain text files."""
    if not text:
        return ""
    s = str(text)

    # Replace literal escape sequences with real characters
    s = s.replace("\\n", "\n")
    s = s.replace("\\r", "\r")
    s = s.replace("\\t", "\t")

    # Unicode double quote written as a literal sequence
    s = s.replace("\\u0022", '"')

    # Strip code fences
    s = s.replace("```", "")

    # Collapse markdown links: [label](url) -> label
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)

    # Remove useless placeholder lines like "..." or "... (continued)"
    cleaned_lines: List[str] = []
    for line in s.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if stripped.startswith("..."):
            continue
        if "continued" in lower and "..." in stripped:
            continue
        cleaned_lines.append(line)
    s = "\n".join(cleaned_lines)

    # Tidy blank lines
    s = re.sub(r"\n{3,}", "\n\n", s)

    return s.strip()


def get_recent_jobs(limit: int = 20):
    jobs = []
    if not OUTPUT_ROOT.exists():
        return jobs

    for entry in sorted(OUTPUT_ROOT.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue
        try:
            with meta_path.open("r", encoding="utf8") as f:
                meta = json.load(f)
        except Exception:
            continue
        jobs.append(
            {
                "folder": str(entry),
                "host_folder": meta.get("host_folder", ""),
                "company": meta.get("company", ""),
                "title": meta.get("title", ""),
                "location": meta.get("location", ""),
                "fit_score": meta.get("fit_score", ""),
                "fit_label": meta.get("fit_label", ""),
            }
        )
        if len(jobs) >= limit:
            break
    return jobs


def extract_block(text: str, start_tag: str, end_tag: str) -> str:
    """Extract text between start_tag and end_tag (exclusive)."""
    start_idx = text.find(start_tag)
    if start_idx == -1:
        return ""
    start_idx += len(start_tag)
    end_idx = text.find(end_tag, start_idx)
    if end_idx == -1:
        end_idx = len(text)
    return text[start_idx:end_idx].strip()


def parse_model_output(raw: str):
    """
    Parse the tagged plain text format:

    FIT_SCORE: <number>
    REASONING:
    ...
    COVER_LETTER:
    ...
    END_COVER_LETTER
    RESUME:
    ...
    END_RESUME
    SHORT_ANSWERS:
    ...
    END_SHORT_ANSWERS
    """
    text = raw

    # Fit score
    m = re.search(r"FIT_SCORE:\s*([0-9]+(?:\.[0-9]+)?)", text)
    if not m:
        raise HTTPException(
            status_code=500,
            detail=f"Could not find FIT_SCORE in model output. Snippet: {text[:300]}",
        )
    fit_score = float(m.group(1))

    # Reasoning block
    reasoning = extract_block(text, "REASONING:\n", "COVER_LETTER:")
    if not reasoning:
        reasoning = extract_block(text, "REASONING:", "COVER_LETTER:")
    reasoning = clean_model_text(reasoning)

    # Cover letter
    cover_letter = extract_block(text, "COVER_LETTER:\n", "END_COVER_LETTER")
    if not cover_letter:
        cover_letter = extract_block(text, "COVER_LETTER:", "END_COVER_LETTER")
    cover_letter = clean_model_text(cover_letter)

    # Resume
    resume = extract_block(text, "RESUME:\n", "END_RESUME")
    if not resume:
        resume = extract_block(text, "RESUME:", "END_RESUME")
    resume = clean_model_text(resume)

    # Short answers
    sa_block = extract_block(text, "SHORT_ANSWERS:\n", "END_SHORT_ANSWERS")
    if not sa_block:
        sa_block = extract_block(text, "SHORT_ANSWERS:", "END_SHORT_ANSWERS")
    sa_block = clean_model_text(sa_block)

    short_answers: List[str] = []
    for line in sa_block.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[0-9]+\s*[\).\-\:]\s*", "", line)
        short_answers.append(line)
    if len(short_answers) > 3:
        short_answers = short_answers[:3]
    while len(short_answers) < 3:
        short_answers.append("")

    return fit_score, reasoning, cover_letter, resume, short_answers


def process_job(job: JobInput) -> PackageOutput:
    system_prompt = """
You are writing for one specific candidate, based on the resume text that is provided to you.
You receive the candidates resume text and a job description.

Your tasks:
1. Judge how well this candidate fits the job and choose a numeric fit score between 0 and 100.
2. Provide a short, plain language explanation of the match.
3. Write a full tailored resume text for this one job.
4. Write a full tailored cover letter for this one job.
5. Write three short answers for likely online application questions.

Hard constraints:
1. Use simple direct language. Avoid generic corporate buzzwords such as "seasoned", "results driven", "dynamic", "passionate", "leveraging synergies".
2. Do not say that you are an AI or language model.
3. Do not use markdown formatting. No bracket links, no code fences, no markdown emphasis. Use plain text with line breaks.
4. Do not output literal sequences like "\\n" in the resume or cover letter. Use real line breaks.
5. It is forbidden to use any placeholder such as "...", "…", "etc.", "list goes here", "truncated", "continued", or any variation. Never output three consecutive dots. Always write actual content based on the resume.
6. Respect the candidates real experience. Do not invent employers, titles, certifications, or responsibilities that are not supported by the resume.
7. Keep sentences grounded in real work and outcomes.
8. The experience section must include every role from the resume, in reverse chronological order. For older roles you may use fewer lines but they must still appear.

Resume structure:
1. Header with name, location, phone, email, and LinkedIn if available.
2. A short summary of three or four plain sentences.
3. A "Core strengths" section with five to eight short bullet style lines aligned to the job.
4. An "Experience" section in reverse chronological order. For each role in the resume include:
   - title
   - company
   - location if available
   - dates
   - for recent roles: four to six lines describing responsibilities and achievements
   - for older roles: at least two lines each summarizing responsibilities or impact
5. Short "Education" and "Certifications" sections at the end.

Cover letter:
1. One page or less.
2. Address the company and role, explain why the profile is a match, and connect one or two concrete examples to the role.
3. Use short paragraphs in plain language.

Output format (this is critical):
Return plain text only, with these exact sections and tags, in this order:

FIT_SCORE: <number from 0 to 100>
REASONING:
<one short paragraph>

COVER_LETTER:
<full cover letter text>
END_COVER_LETTER

RESUME:
<full resume text>
END_RESUME

SHORT_ANSWERS:
1) <one or two sentence answer about why this company>
2) <one or two sentence answer about why this role>
3) <one or two sentence answer about compensation expectations or range>
END_SHORT_ANSWERS

Do not add any extra commentary before or after these tags.
"""

    user_prompt = f"""
Candidate resume text:
{job.resume_text}

Job title: {job.title}
Company: {job.company}
Location: {job.location}
Seniority hint: {job.seniority_hint}

Job description:
{job.job_description}

Follow the required output format exactly.
"""

    try:
        raw = call_ollama(system_prompt, user_prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error talking to Ollama: {exc}")

    try:
        fit_score, reasoning, cover_letter, resume, short_answers = parse_model_output(raw)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse model output: {exc}. Snippet: {raw[:300]}",
        )

    fit_label = map_score_to_label(fit_score)

    job_dir, host_path, _ = create_job_folder(job)

    (job_dir / "cover_letter.txt").write_text(cover_letter, encoding="utf8")
    (job_dir / "resume_full.txt").write_text(resume, encoding="utf8")

    answers_text = ""
    for idx, ans in enumerate(short_answers, start=1):
        answers_text += f"Answer {idx}:\n{ans}\n\n"
    (job_dir / "short_answers.txt").write_text(answers_text, encoding="utf8")

    meta = {
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "seniority_hint": job.seniority_hint,
        "fit_score": fit_score,
        "fit_label": fit_label,
        "reasoning": reasoning,
        "container_folder": str(job_dir),
        "host_folder": host_path,
    }
    (job_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf8")

    return PackageOutput(
        fit_score=fit_score,
        fit_label=fit_label,
        reasoning=reasoning,
        cover_letter=cover_letter,
        resume=resume,
        short_answers=short_answers,
        container_folder=str(job_dir),
        host_folder=host_path,
    )


@app.get("/", response_class=HTMLResponse)
async def index():
    recent = get_recent_jobs(limit=20)

    rows_html = ""
    for job in recent:
        company = html_mod.escape(str(job["company"]))
        title = html_mod.escape(str(job["title"]))
        location = html_mod.escape(str(job["location"]))
        score = html_mod.escape(str(job["fit_score"]))
        label = html_mod.escape(str(job["fit_label"]))
        host_folder = html_mod.escape(str(job["host_folder"]))
        rows_html += f"""
        <tr>
          <td>{company}</td>
          <td>{title}</td>
          <td>{location}</td>
          <td>{score}</td>
          <td>{label}</td>
          <td>{host_folder}</td>
        </tr>
        """

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Simple Job Bot</title>
</head>
<body>
  <h1>Simple Job Bot</h1>
  <p>Paste your resume, drop in a job posting, and get a tailored resume and cover letter plus a fit score.</p>

  <h2>Recent jobs</h2>
  <table border="1" cellpadding="4" cellspacing="0">
    <tr>
      <th>Company</th>
      <th>Title</th>
      <th>Location</th>
      <th>Fit score (0 to 100)</th>
      <th>Fit label</th>
      <th>Host folder</th>
    </tr>
    {rows_html}
  </table>

  <h2>New job</h2>
  <div id="status" style="margin: 8px 0; color: #444;"></div>
  <form id="job-form" method="post" action="/submit">
    <div>
      <label>Your resume (plain text):</label><br>
      <textarea name="resume_text" rows="16" cols="100" required></textarea>
    </div>
    <div>
      <label>Company:</label><br>
      <input type="text" name="company" style="width: 400px" required>
    </div>
    <div>
      <label>Title:</label><br>
      <input type="text" name="title" style="width: 400px" required>
    </div>
    <div>
      <label>Location:</label><br>
      <input type="text" name="location" style="width: 400px">
    </div>
    <div>
      <label>Seniority hint:</label><br>
      <input type="text" name="seniority_hint" style="width: 400px" placeholder="Director, Senior Manager, etc">
    </div>
    <div>
      <label>Job description:</label><br>
      <textarea name="job_description" rows="16" cols="100" required></textarea>
    </div>
    <div style="margin-top: 8px;">
      <button type="submit" id="submit-button">Generate package</button>
    </div>
  </form>

  <script>
  document.addEventListener("DOMContentLoaded", function() {{
    const form = document.getElementById("job-form");
    const statusDiv = document.getElementById("status");
    const submitButton = document.getElementById("submit-button");
    if (form) {{
      form.addEventListener("submit", function() {{
        if (statusDiv) {{
          statusDiv.textContent = "Calling Ollama and generating your package. This can take a short while...";
        }}
        if (submitButton) {{
          submitButton.disabled = true;
        }}
      }});
    }}
  }});
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/submit", response_class=HTMLResponse)
async def submit(
    resume_text: str = Form(...),
    company: str = Form(...),
    title: str = Form(...),
    location: str = Form(""),
    job_description: str = Form(...),
    seniority_hint: str = Form(""),
):
    job = JobInput(
        resume_text=resume_text,
        company=company,
        title=title,
        location=location or None,
        job_description=job_description,
        seniority_hint=seniority_hint or None,
    )

    try:
        package = process_job(job)
    except HTTPException as exc:
        html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Simple Job Bot error</title>
</head>
<body>
  <h1>Error</h1>
  <p>Status: {exc.status_code}</p>
  <pre>{html_mod.escape(str(exc.detail))}</pre>
  <p><a href="/">Back to main page</a></p>
</body>
</html>
"""
        return HTMLResponse(content=html, status_code=exc.status_code)

    resume_html = html_mod.escape(package.resume)

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Simple Job Bot result</title>
</head>
<body>
  <h1>Job package created</h1>
  <p><strong>Company:</strong> {html_mod.escape(company)}</p>
  <p><strong>Title:</strong> {html_mod.escape(title)}</p>
  <p><strong>Fit score (0 to 100):</strong> {html_mod.escape(str(package.fit_score))}</p>
  <p><strong>Fit label:</strong> {html_mod.escape(package.fit_label)}</p>
  <p><strong>Reasoning:</strong> {html_mod.escape(package.reasoning)}</p>
  <p><strong>Folder on host:</strong> {html_mod.escape(package.host_folder or "")}</p>

  <h2>Generated resume</h2>
  <pre style="white-space: pre-wrap; border: 1px solid #ccc; padding: 8px;">{resume_html}</pre>

  <h2>Files created</h2>
  <ul>
    <li>cover_letter.txt</li>
    <li>resume_full.txt</li>
    <li>short_answers.txt</li>
    <li>meta.json</li>
  </ul>
  <p><a href="/">Back to main page</a></p>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/generate_package", response_model=PackageOutput)
async def generate_package(job: JobInput):
    return process_job(job)
