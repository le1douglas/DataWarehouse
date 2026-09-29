#TODO
from datawarehouse.sql_server_database import SQLServerDatabase
import pytest

def test_init():
    db_server = "test"
    db_name = "test2"
    db = SQLServerDatabase(db_server, db_name)
     #print(db.engine.url) == mssql+pyodbc://{db_server}/{db_name}"
      #                          "?driver=ODBC+Driver+18+for+SQL+Server"
       #                         "&trusted_connection=yes"
        #                        "&TrustServerCertificate=yes"
