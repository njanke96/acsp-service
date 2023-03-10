"""
Web API Application
"""
from datetime import datetime

from databases import Database
from fastapi.routing import APIRoute
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Query, Depends, Request, HTTPException
from pydantic import BaseModel as PydanticBaseModel, Field

import acsps.database.queries as queries
from acsps.common import format_ms_time
from acsps.database.main import database

app = FastAPI(title="ACSPS Web API", redoc_url=None)

templates = Jinja2Templates(directory="templates")


# Models


class BaseModel(PydanticBaseModel):
    class Config:
        orm_mode = True


class LapRecord(BaseModel):
    driver_guid: str
    track_name: str
    track_config: str
    perf_class: str
    car: str
    points: int = Field(0)
    driver_name: str
    lap_time_ms: int
    grip_level: float
    timestamp: datetime


class RecentServerRecords(BaseModel):
    latest_timestamp: datetime
    count: int
    records: list[LapRecord]


class TopRecords(BaseModel):
    count: int
    records: list[LapRecord]


# Routes


async def get_db():
    async with database.acquire() as db:
        yield db


@app.get("/records/top", response_model=TopRecords)
async def get_top(
    track_name: str = Query(..., description="Track name to show top records for."),
    track_config: str = Query(..., description="Track config to show top records for."),
    car_model: str = Query(..., description="Car to show top records for."),
    db: Database = Depends(get_db),
) -> TopRecords:
    """
    Get top records for a track/config/car combination.
    """
    results = await queries.get_lap_records(db, track_name, track_config, car_model)
    records = [LapRecord.from_orm(result) for result in results]

    return TopRecords(
        count=len(records),
        records=records,
    )


@app.get("/records/server", response_model=RecentServerRecords)
async def get_recent_server_records(
    db: Database = Depends(get_db),
):
    """
    Get server records (most recent first)
    Poll this periodically to stay up to date on server records.
    """
    results = await queries.get_recent_broken_records(db)
    records = [LapRecord.from_orm(result) for result in results]

    latest_timestamp = datetime(1970, 1, 1)
    for record in records:
        if record.timestamp > latest_timestamp:
            latest_timestamp = record.timestamp

    return RecentServerRecords(
        latest_timestamp=latest_timestamp, count=len(records), records=records
    )


@app.get("/records", response_class=HTMLResponse)
async def get_records_page(
    request: Request,
    track: str | None = Query(None),
    car_class: str | None = Query(None),
    db: Database = Depends(get_db),
):
    if track is None or car_class is None:
        records = []
        track_name = None
        track_config = None
    else:
        try:
            track_split = track.split(":")
            track_name = track_split[0]
            track_config = track_split[1]
        except IndexError:
            raise HTTPException(400)

        results = await queries.get_lap_records(db, track_name, track_config, car_class)
        records = [
            (idx + 1, LapRecord.from_orm(result)) for idx, result in enumerate(results)
        ]

    track_choices = await queries.get_unique_tracks_configs(db)
    car_choices = await queries.get_unique_car_names(db)

    return templates.TemplateResponse(
        "records.html",
        {
            "request": request,
            "results": records,
            "format_ms": format_ms_time,
            "track_choices": track_choices,
            "car_choices": car_choices,
            "int": int,
            "selected_track": f"{track_name}:{track_config}"
            if track_name is not None and track_config is not None
            else ":",
            "selected_car": car_class,
        },
    )


def use_route_names_as_operation_ids(fastapi_app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names. This assumes all python functions decorated by a router have a unique name.
    """
    for route in fastapi_app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


use_route_names_as_operation_ids(app)
