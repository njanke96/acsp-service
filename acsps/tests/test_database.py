import pytest
import pytest_asyncio
from databases import Database

from acsps.database.tables import lap_times
from acsps.database.queries import record_lap_pr, get_lap_records, get_lap_pr


@pytest_asyncio.fixture(scope="function")
async def database_client():
    from acsps.database.main import database
    database.create_tables()

    await database.db.connect()

    # the force_rollback context doesn't work here?
    yield database.db

    await database.db.disconnect()


# noinspection PyUnusedLocal,PyShadowingNames
@pytest.mark.asyncio
async def test_record_lap_pr(database_client: Database):
    async with database_client.transaction(force_rollback=True):
        result = await record_lap_pr(
            database_client,
            "1",
            "track1",
            "gp",
            "Fast Driver",
            2881,
            "ks_car",
            1.0
        )

        assert result

        result = await database_client.fetch_one(lap_times.select())
        assert result["driver_guid"] == "1"
        assert result["track_name"] == "track1"
        assert result["track_config"] == "gp"
        assert result["driver_name"] == "Fast Driver"
        assert result["lap_time_ms"] == 2881
        assert result["car_model"] == "ks_car"
        assert result["grip_level"] == 1.0

        # should not update the personal record if the lap time was slower
        result = await record_lap_pr(
            database_client,
            "1",
            "track1",
            "gp",
            "Fast Driver",
            2888,
            "ks_car",
            1.0
        )

        assert not result

        result = await database_client.fetch_one(lap_times.select())
        assert result["lap_time_ms"] == 2881


# noinspection PyUnusedLocal,PyShadowingNames
@pytest.mark.asyncio
async def test_get_lap_pr(database_client: Database):
    async with database_client.transaction(force_rollback=True):
        await record_lap_pr(
            database_client,
            "1",
            "track1",
            "gp",
            "Fast Driver",
            2881,
            "ks_car",
            1.0
        )

        result = await get_lap_pr(database_client, "1", "track1", "gp", "ks_car")
        assert result["driver_guid"] == "1"
        assert result["track_name"] == "track1"
        assert result["track_config"] == "gp"
        assert result["driver_name"] == "Fast Driver"
        assert result["lap_time_ms"] == 2881
        assert result["car_model"] == "ks_car"
        assert result["grip_level"] == 1.0


# noinspection PyUnusedLocal,PyShadowingNames
@pytest.mark.asyncio
async def test_get_top_records(database_client: Database):
    async with database_client.transaction(force_rollback=True):
        await record_lap_pr(
            database_client,
            "1",
            "track1",
            "gp",
            "Fast Driver 1",
            2881,
            "ks_car",
            1.0
        )
        await record_lap_pr(
             database_client,
             "2",
             "track1",
             "gp",
             "Fast Driver 2",
             2600,
             "ks_car",
             1.0
        )

        results = await get_lap_records(database_client, "track1", "gp", "ks_car")
        assert len(results) == 2
