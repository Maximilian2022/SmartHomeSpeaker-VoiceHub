from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.scheduler_service import scheduler_service

router = APIRouter()

@router.get("/api/schedules")
async def get_schedules():
    return {
        "schedules": scheduler_service.get_schedules(),
        "history": scheduler_service.get_history()
    }

@router.post("/api/schedules")
async def add_schedule(data: Dict[str, Any]):
    try:
        new_s = scheduler_service.add_schedule(data)
        return new_s
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/api/schedules/{sched_id}")
async def update_schedule(sched_id: str, data: Dict[str, Any]):
    updated = scheduler_service.update_schedule(sched_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return updated

@router.delete("/api/schedules/{sched_id}")
async def delete_schedule(sched_id: str):
    success = scheduler_service.delete_schedule(sched_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"success": True}

@router.post("/api/schedules/{sched_id}/toggle")
async def toggle_schedule(sched_id: str):
    res = scheduler_service.toggle_schedule(sched_id)
    if not res:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return res

@router.post("/api/schedules/{sched_id}/run")
async def run_schedule_now(sched_id: str):
    try:
        res = await scheduler_service.run_schedule_now(sched_id)
        return {"success": True, "result": res}
    except ValueError:
        raise HTTPException(status_code=404, detail="Schedule not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
