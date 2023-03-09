"""
Database Queries
"""
from datetime import datetime

import sqlalchemy as sqla
from databases import Database
from databases.interfaces import Record

from acsps.database.tables import lap_times

DEFAULT_QUERY_LIMIT = 100


car_classes = {
    "gt4_alpine_a110": "gt4",
    "gt4_aston_martin_vantage": "gt4",
    "gt4_audi_r8": "gt4",
    "gt4_bmw_m4": "gt4",
    "gt4_camaro": "gt4",
    "gt4_ford_mustang": "gt4",
    "gt4_ginetta_g55": "gt4",
    "gt4_ktm_xbow": "gt4",
    "gt4_mclaren_570s": "gt4",
    "gt4_mercedes_amg": "gt4",
    "gt4_panoz_avezzano": "gt4",
    "gt4_porsche_cayman_718": "gt4",
    "gt4_saleen_s1": "gt4",
    "gt4_sin_r1": "gt4",
    "gt4_toyota_supra": "gt4",
    "lotus_2_eleven_gt4": "gt4",
    "ks_maserati_gt_mc_gt4": "gt4",
    "ks_porsche_cayman_gt4_clubsport": "gt4",
}


async def get_lap_pr(
    db: Database,
    driver_guid: str,
    track_name: str,
    track_config: str,
    car_model: str,
) -> Record | None:
    car_class = car_classes.get(car_model, None) or car_model

    query = lap_times.select().where(
        lap_times.c.driver_guid == driver_guid,
        lap_times.c.track_name == track_name,
        lap_times.c.track_config == track_config,
        lap_times.c.perf_class == car_class,
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
    car_class = car_classes.get(car_model, None) or car_model

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
            lap_times.c.perf_class == car_class,
        ))

        await db.execute(
            lap_times.insert(),
            values={
                "driver_guid": driver_guid,
                "track_name": track_name,
                "track_config": track_config,
                "perf_class": car_class,
                "points": 0,
                "driver_name": driver_name,
                "lap_time_ms": lap_time_ms,
                "car": car_model,
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
    car_class = car_classes.get(car_model, None) or car_model
    query = (
        lap_times.select()
        .where(
            lap_times.c.track_name == track_name,
            lap_times.c.track_config == track_config,
            lap_times.c.perf_class == car_class,
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
    car_class = car_classes.get(car_model, None) or car_model
    query = (
        lap_times.select()
        .where(
            lap_times.c.track_name == track_name,
            lap_times.c.track_config == track_config,
            lap_times.c.perf_class == car_class,
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
            lap_times.c.perf_class,
        )
        .select_from(lap_times)
        .group_by(
            lap_times.c.track_name, lap_times.c.track_config, lap_times.c.perf_class
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
                lap_times.c.perf_class == sqla.literal_column("sub.perf_class"),
            ),
        )
        .order_by(sqla.desc(lap_times.c.timestamp))
        .limit(DEFAULT_QUERY_LIMIT)
    )

    return await db.fetch_all(query)
