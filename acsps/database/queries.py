"""
Database Queries
"""
from datetime import datetime

import sqlalchemy as sqla
from databases import Database

from acsps.database.tables import lap_times


async def record_lap_pr(
    db: Database,
    driver_guid: str,
    track_name: str,
    track_config: str,
    driver_name: str,
    lap_time_ms: int,
    car_model: str,
    grip_level: float,
):
    await db.execute(
        lap_times.insert(),
        values={
            "driver_guid": driver_guid,
            "track_name": track_name,
            "track_config": track_config,
            "driver_name": driver_name,
            "lap_time_ms": lap_time_ms,
            "car_model": car_model,
            "grip_level": grip_level,
            "timestamp": datetime.now(),
        },
    )


async def get_lap_records(db: Database, track_name: str, track_config: str):
    """
    Return the top 10 lap records for a track/config.
    """
    query = (
        lap_times.select()
        .where(
            lap_times.c.track_name == track_name,
            lap_times.c.track_config == track_config,
        )
        .order_by(sqla.asc(lap_times.c.lap_time_ms))
        .limit(10)
    )

    results = await db.fetch_all(query)

    return results
