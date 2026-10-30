import asyncio
import json
import logging
import os

import psycopg
from nicegui import Event, background_tasks

from webapps.queries import engine

# the dbt project: copied into the image, in dev the one of the mounted repo, at the same path
DBT_PROJECT_DIR = "/usr/app/DataWarehouseDbt"

# seconds
RECONNECT_SECONDS = 5

# a dbt command has ended, with the command: build, test. one event for the whole app, on purpose: every open page
# subscribes to it, and is unsubscribed when it closes
run_ended = Event[str]()

# one build at a time in the app: two would rebuild the same relations at once
_build_lock = asyncio.Lock()


# runs dbt build on the whole project, and returns whether it passed: false when a test fails, as in the review loop,
# or when dbt cannot run. the output goes to the log only when it did not pass.
# the end is announced by the notify of on-run-end, as for any dbt command (see _listen_run_end).
# an MVP until an orchestrator runs dbt: the web apps run it with their own connection, mapped onto the variables
# DataWarehouseDbt/profiles.yml reads
async def run_dbt_build() -> bool:
    env = os.environ | {
        "DBT_HOST": os.environ["POSTGRESQL_SERVER"],
        "DBT_PORT": os.environ["POSTGRESQL_PORT"],
        "DBT_DBNAME": os.environ["POSTGRESQL_DB"],
        "DBT_USER": os.environ["POSTGRESQL_USER"],
        "DBT_ENV_SECRET_PASSWORD": os.environ["POSTGRESQL_PASSWORD"],
    }
    async with _build_lock:
        process = await asyncio.create_subprocess_exec(
            "dbt",
            "build",
            cwd=DBT_PROJECT_DIR,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        output, _ = await process.communicate()
    if process.returncode != 0:
        logging.warning(f"dbt build did not pass:\n{output.decode()}")
    return process.returncode == 0


# the app listens to dbt as long as it runs. a task, not the startup handler itself, which would never return
def start_run_end_listener() -> None:
    background_tasks.create(_listen_run_end(), name="listen-run-end")


# the dbt commands as they end: dbt notifies on dbt_run_end at the end of every command
# (DataWarehouseDbt/macros/notify_run_end.sql), and run_ended emits the command of each: build, test.
# one connection for the whole app. when it drops, it connects again after RECONNECT_SECONDS; a command that ends while
# it is down is missed, postgres keeps no notifies
async def _listen_run_end() -> None:
    conninfo = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    while True:
        try:
            async with await psycopg.AsyncConnection.connect(conninfo, autocommit=True) as connection:
                await connection.execute("LISTEN dbt_run_end")
                async for notify in connection.notifies():
                    run_ended.emit(json.loads(notify.payload)["command"])
        except psycopg.OperationalError as error:
            logging.warning(f"listening to dbt_run_end: connecting again in {RECONNECT_SECONDS} s: {error}")
        await asyncio.sleep(RECONNECT_SECONDS)
