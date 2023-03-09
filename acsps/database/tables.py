"""
Database Tables
"""
import sqlalchemy as sqla

table_metadata = sqla.MetaData()

lap_times = sqla.Table(
    "lap_personal_records",
    table_metadata,
    sqla.Column("driver_guid", sqla.String, primary_key=True),
    sqla.Column("track_name", sqla.String, primary_key=True),
    sqla.Column("track_config", sqla.String, primary_key=True),
    sqla.Column("perf_class", sqla.String, primary_key=True),
    sqla.Column("car", sqla.String, nullable=False),
    sqla.Column("driver_name", sqla.String, nullable=False),
    sqla.Column("lap_time_ms", sqla.Integer, nullable=False),
    sqla.Column("grip_level", sqla.Float, nullable=False),
    sqla.Column("timestamp", sqla.DateTime, nullable=False)
)
