import pytest
import pytest_asyncio
from databases import Database

from acsps.database.tables import lap_times
from acsps.database.queries import record_lap_pr, get_lap_records, get_lap_pr, get_recent_broken_records


@pytest_asyncio.fixture(scope="function")
async def database_client():
    from acsps.database.main import database
    database.create_tables()

    await database.db.connect()

    # the force_rollback context doesn't work here? (sqlite)
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


# noinspection PyUnusedLocal,PyShadowingNames
@pytest.mark.asyncio
async def test_get_recent_broken_records(database_client: Database):
    async with database_client.transaction(force_rollback=True):
        # Driver 1 sets record on track1 gp in ks car
        await record_lap_pr(
            database_client,
            "1",
            "track1",
            "gp",
            "Driver 1",
            2881,
            "ks_car",
            1.0
        )

        # driver 2 breaks the record
        await record_lap_pr(
            database_client,
            "2",
            "track1",
            "gp",
            "Driver 2",
            2440,
            "ks_car",
            1.0
        )

        # driver 3 does not break the record
        await record_lap_pr(
            database_client,
            "3",
            "track1",
            "gp",
            "Driver 3",
            3112,
            "ks_car",
            1.0
        )

        # driver 1 sets a record on track2 national
        await record_lap_pr(
            database_client,
            "1",
            "track2",
            "national",
            "Driver 1",
            2211,
            "ks_car",
            1.0
        )

        # most recent broken records should include driver 2's record on the first track,
        # as well as driver 1 setting a record on the second track, sorted by timestamp
        result = await get_recent_broken_records(database_client)

        assert len(result) == 2
        assert result[0]["lap_time_ms"] == 2211
        assert result[1]["lap_time_ms"] == 2440
