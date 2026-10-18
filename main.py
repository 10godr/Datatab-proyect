from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes.upload import router as upload_router
from app.routes.analysis import router as analysis_router

app = FastAPI(title="DataTab", version="3.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(upload_router)
app.include_router(analysis_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
