import subprocess
from fastapi import APIRouter, BackgroundTasks

router = APIRouter(
    prefix="/webhook",
    tags=["webhook"],
)

def run_git_pull():
    subprocess.run(["git", "pull", "origin", "main"], check=True)

@router.post("/deploy")
async def deploy_webhook(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_git_pull)
    return {"status": "Pull triggered"}