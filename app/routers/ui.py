from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from ..models import JobInput, SeniorityHint
from ..services.generation import generate_full_package
from ..services.diagnostics import record_error, get_dashboard_stats

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    stats = get_dashboard_stats()
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "stats": stats,
            "last_job": None,
            "error_message": None,
        },
    )


@router.post("/submit", response_class=HTMLResponse)
async def submit(
    request: Request,
    resume_text: str = Form(...),
    company: str = Form(...),
    title: str = Form(...),
    location: str = Form(""),
    job_description: str = Form(...),
    seniority_hint: str = Form(""),
):
    templates = request.app.state.templates
    try:
        hint = None
        if seniority_hint:
            try:
                hint = SeniorityHint(seniority_hint)
            except ValueError:
                hint = None

        job_input = JobInput(
            resume_text=resume_text,
            company=company,
            title=title,
            location=location or None,
            job_description=job_description,
            seniority_hint=hint,
        )

        result = await generate_full_package(job_input)
        stats = get_dashboard_stats()

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "stats": stats,
                "last_job": result,
                "error_message": None,
            },
        )

    except Exception as exc:
        record_error(exc)
        stats = get_dashboard_stats()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "stats": stats,
                "last_job": None,
                "error_message": str(exc),
            },
            status_code=500,
        )
