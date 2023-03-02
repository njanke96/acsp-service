"""
Database Queries
"""
from datetime import datetime

import sqlalchemy as sqla
from databases import Database
from databases.interfaces import Record

from acsps.database.tables import lap_times


async def get_lap_pr(
    db: Database,
    driver_guid: str,
    track_name: str,
    track_config: str,
    car_model: str,
) -> Record | None:
    query = (
        lap_times.select()
        .where(
            lap_times.c.driver_guid == driver_guid,
            lap_times.c.track_name == track_name,
            lap_times.c.track_config == track_config,
            lap_times.c.car_model == car_model,
        )
    )

    result = await db.fetch_one(query)
    return result


async def record_lap_pr(
    db: Database,
    driver_guid: str,
    track_name: str,
    track_config: str,
    driver_name: str,
    lap_time_ms: int,
    car_model: str,
    grip_level: float,
) -> bool:
    """
    Record a lap PR, only updates if lap_time_ms is less than the previous PR for the track/config.
    returns true when the record was updated, false otherwise
    """
    record = await get_lap_pr(db, driver_guid, track_name, track_config, car_model)
    if record is None or record["lap_time_ms"] > lap_time_ms:
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
        return True
    else:
        return False


async def get_lap_records(db: Database, track_name: str, track_config: str, car_model: str):
    """
    Return the top 10 lap records for a track/config/car.
    """
    query = (
        lap_times.select()
        .where(
            lap_times.c.track_name == track_name,
            lap_times.c.track_config == track_config,
            lap_times.c.car_model == car_model,
        )
        .order_by(sqla.asc(lap_times.c.lap_time_ms))
        .limit(10)
    )

    results = await db.fetch_all(query)

    return results
