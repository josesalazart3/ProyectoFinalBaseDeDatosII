# db.py
import cx_Oracle
from config import ORACLE_USERNAME, ORACLE_PASSWORD, ORACLE_DSN

def get_connection():
    return cx_Oracle.connect(
        ORACLE_USERNAME,
        ORACLE_PASSWORD,
        ORACLE_DSN,
        encoding="UTF-8"
    )
