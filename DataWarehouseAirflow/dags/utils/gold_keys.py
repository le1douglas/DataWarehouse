# the last task of every dag that builds gold: the key tests of gold alone, so dbt_constraints adds back every key that
# a build dropped and did not restore. its on-run-start hook drops the keys of each gold table a build selects, with
# CASCADE, so a dim built again also loses the foreign keys pointing at it from other tables, and its on-run-end hook
# adds back only the keys whose test that same build ran. a build of a dim alone, or one whose model failed, leaves
# keys missing, and nothing reports it. dbt test builds no model, so it drops no key: it adds the missing ones and
# leaves the rest. a key whose test fails stays missing and fails the task
import os

from airflow.providers.standard.operators.bash import BashOperator

# every primary, unique and foreign key test of gold (models/gold/*.yml): each selector is the intersection of gold's
# folder and one test name
_SELECT = " ".join(
    f'"path:models/gold,test_name:{test_name}"' for test_name in ("primary_key", "unique_key", "foreign_key")
)


def gold_keys(**operator_args) -> BashOperator:
    # operator_args go to the task, such as the pool
    return BashOperator(
        task_id="gold_keys",
        bash_command=f"dbt test --select {_SELECT}",
        # dbt reads the project from the folder it runs in, and DBT_PROFILES_DIR by itself. set by the image and by the
        # dev container (docker/airflow/Dockerfile, docker/dev/Dockerfile)
        cwd=os.environ["DBT_PROJECT_DIR"],
        **operator_args,
    )
