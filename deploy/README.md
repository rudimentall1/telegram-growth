# Deployment notes

The systemd unit in this directory is a template, not an installer. Adjust the service user and project path for the target server before installing it.

For an existing installation:

1. Identify the actual project directory and service unit.
2. Back up `group_bot.py`, `growth_db.py`, the SQLite database, and the current service unit.
3. Keep the existing `config.py` private and verify its channel/group IDs before restart.
4. Install dependencies in the project's virtual environment.
5. Run tests and `py_compile` before restarting the service.
6. Restart only the growth bot service, then inspect its status and logs.
7. Verify one controlled join and leave event and compare the database/report.
8. Roll back the two Python files and restart the service if verification fails.

Do not modify a separate news aggregator or its cron job as part of this deployment.

The new `growth_processed_updates` table is created automatically. Existing IDs in `growth_events` are copied into it on connection so old recorded events are not replayed as fresh state changes.
