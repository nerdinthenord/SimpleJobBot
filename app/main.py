from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from .routers import ui, health
from .services.diagnostics import init_diagnostics

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.state.templates = templates

app.include_router(ui.router)
app.include_router(health.router)


@app.on_event("startup")
async def startup_event():
    init_diagnostics()
