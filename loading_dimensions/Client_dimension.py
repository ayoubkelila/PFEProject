import pygrametl
import pyodbc

CONNECTION_STRING = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-AR905LJ;"
    "Database=staging;"
    "UID=sa;"
    "PWD=ghom3220;"
)

raw_cnx=pyodbc.connect(CONNECTION_STRING)
cnx=pyodbc.ConnectionWrapper(raw_cnx)

cursor=cnx.cursor()
query = 'SELECT TOP (100) * FROM [staging].[dbo].[source]'
cursor.execute(query)