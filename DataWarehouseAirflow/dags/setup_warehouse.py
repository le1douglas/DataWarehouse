# the setup of the warehouse: dbt build of everything no load builds, the seeds, the ref_ models, the dims over them and
# elementary's tables. started by hand, on a new database after its ddl (Database/01_create_schemas_and_tables.sql) and
# before its first load, and again after a seed or one of these models changes
import os
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag

# the reference data and what is built on it: the seeds, ref_ models and gold, and elementary's tables. without
# anything downstream of silver: silver takes the accepted load, so only a load's publish builds it and what reads it,
# and writes published. a test runs only when every model it reads is selected (cautious), so staging's tests, which
# read ref_ models too, are left to the audit of a load
_SELECT = "resource_type:seed path:models/ref path:models/gold package:elementary"
_EXCLUDE = "path:models/silver+"


@dag(
    dag_id="setup_warehouse",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    # a failed build is looked at before it runs again
    default_args={"retries": 0},
    tags=["setup"],
)
def setup_warehouse():
    BashOperator(
        task_id="build",
        bash_command=f'dbt build --select {_SELECT} --exclude "{_EXCLUDE}" --indirect-selection cautious',
        # dbt reads the project from the folder it runs in. set by the image and by the dev container
        # (docker/airflow/Dockerfile, docker/dev/Dockerfile), as DBT_PROFILES_DIR, which dbt reads by itself
        cwd=os.environ["DBT_PROJECT_DIR"],
    )


setup_warehouse()
