"""
Database Queries
"""
from datetime import datetime

import sqlalchemy as sqla
from databases import Database
from databases.interfaces import Record

from acsps.database.tables import lap_times

DEFAULT_QUERY_LIMIT = 100


async def get_lap_pr(
    db: Database,
    driver_guid: str,
    track_name: str,
    track_config: str,
    car_model: str,
) -> Record | None:
    query = lap_times.select().where(
        lap_times.c.driver_guid == driver_guid,
        lap_times.c.track_name == track_name,
        lap_times.c.track_config == track_config,
        lap_times.c.car_model == car_model,
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
) -> int:
    """
    Record a lap PR, only updates if lap_time_ms is less than the previous PR for the track/config.
    returns the diff in milliseconds. If diff is equal to laptime this was the first record.
    """
    record = await get_lap_pr(db, driver_guid, track_name, track_config, car_model)
    if record is None:
        diff = lap_time_ms
    else:
        diff = lap_time_ms - record["lap_time_ms"]
    if record is None or (diff < 0):
        await db.execute(lap_times.delete().where(
            lap_times.c.driver_guid == driver_guid,
            lap_times.c.track_name == track_name,
            lap_times.c.track_config == track_config,
            lap_times.c.car_model == car_model,
        ))

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
        return diff
    else:
        return diff


async def compare_to_server_record(
    db: Database, track_name: str, track_config: str, car_model: str, lap_time_ms: int,
):
    """
    Compare a record to the server record.
    returns the diff in milliseconds. If diff is equal to laptime this was the first record.
    """
    query = (
        lap_times.select()
        .where(
            lap_times.c.track_name == track_name,
            lap_times.c.track_config == track_config,
            lap_times.c.car_model == car_model,
        )
        .order_by(sqla.asc(lap_times.c.lap_time_ms))
        .limit(1)
    )

    sr = await db.fetch_one(query)

    if sr is None:
        return lap_time_ms
    else:
        return lap_time_ms - sr["lap_time_ms"]


async def get_lap_records(
    db: Database, track_name: str, track_config: str, car_model: str
):
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


async def get_recent_broken_records(db: Database):
    """
    Return the most recently broken lap records. Since there is no separate table for this it will only include
    the most recent record broken on a track/config/car. That is, if a user breaks a record on a
    track/config/car, their most recent record will be the only one to show up here.

    This is intended to be polled periodically to announce records.
    """
    # fastest lap for each track/confg/car
    min_ = sqla.func.min(lap_times.c.lap_time_ms).label("lap_record")
    sub_query = (
        sqla.select(
            min_,
            lap_times.c.track_name,
            lap_times.c.track_config,
            lap_times.c.car_model,
        )
        .select_from(lap_times)
        .group_by(
            lap_times.c.track_name, lap_times.c.track_config, lap_times.c.car_model
        )
        .subquery("sub")
    )

    query = (
        sqla.select(lap_times)
        .select_from(lap_times)
        .join(
            sub_query,
            sqla.and_(
                lap_times.c.lap_time_ms == sqla.literal_column("sub.lap_record"),
                lap_times.c.track_name == sqla.literal_column("sub.track_name"),
                lap_times.c.track_config == sqla.literal_column("sub.track_config"),
                lap_times.c.car_model == sqla.literal_column("sub.car_model"),
            ),
        )
        .order_by(sqla.desc(lap_times.c.timestamp))
        .limit(DEFAULT_QUERY_LIMIT)
    )

    return await db.fetch_all(query)
