from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import ErrorHandlerMiddleware
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.invitations.router import router as invitations_router
from app.modules.memberships.router import router as memberships_router
from app.modules.organizations.router import router as organizations_router
from app.modules.tasks.router import router as tasks_router
from app.modules.tools.router import router as tools_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Corvinus Labs Portal", version="0.1.0", lifespan=lifespan)

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(memberships_router)
app.include_router(invitations_router)
app.include_router(tasks_router)
app.include_router(tools_router)
app.include_router(audit_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
