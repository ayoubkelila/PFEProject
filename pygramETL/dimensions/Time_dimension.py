#!/usr/bin/env python
# coding: utf-8

# In[8]:


import pyodbc
import pygrametl

# Update these with your actual SSMS details
STAGING_CONNECTION_STRING = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-AR905LJ;"
    "Database=staging;"
    "UID=sa;"
    "PWD=ghom3220;"
)
DWH_CONNECTION_STRING = ( 
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-AR905LJ;"
    "Database=DWH;"
    "UID=sa;"
    "PWD=ghom3220;"
)


# In[9]:


source_conn = pyodbc.connect(STAGING_CONNECTION_STRING)
source_connection = pygrametl.ConnectionWrapper(source_conn)
source_cursor = source_connection.cursor()
source_cursor.execute("SELECT @@version;")
result = source_cursor.fetchone()
print(f"connected to {result[0]}!")


# In[10]:


dwh_conn = pyodbc.connect(DWH_CONNECTION_STRING)
dwh_connection = pygrametl.ConnectionWrapper(dwh_conn)
dwh_cursor = dwh_connection.cursor()
dwh_cursor.execute("SELECT @@version;")
result = dwh_cursor.fetchone()
print(f"connected to {result[0]}!")
dwh_connection.setasdefault()


# In[11]:


create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Time]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Time (
        FullDate DATE PRIMARY KEY,
        Year INT,
        Month varchar(20),
        Day INT,
        MonthName Varchar(20),
        DayOfWeek Varchar(20),
        Trimester Varchar(20),
        IsWeekend BIT,
        IsHoliday BIT
    );
END
"""
dwh_cursor.execute(create_table_sql)
dwh_connection.commit()


# In[ ]:


from pygrametl.tables import Dimension
Dim_Time = pygrametl.tables.Dimension(
    name='Dim_Time',
    key='FullDate',
    attributes=['Year', 'Month', 'Day', 'MonthName', 'DayOfWeek', 'Trimester', 'IsWeekend', 'IsHoliday'], lookupatts=['FullDate']
)  


# In[17]:


from datetime import datetime

Date_source=source_cursor.execute("SELECT Distinct DateVente,Annee,Mois,MoisNum,Trimestre,JourSemaine,EstWeekend,EstJourFerie FROM source")
for row in Date_source:
    date_data = {
        "FullDate": datetime.strptime(row.DateVente, "%Y-%m-%d").date(),
        "Year": row.Annee,
        "Month": row.Mois,
        "Day": row.MoisNum,
        "MonthName": row.Mois,
        "DayOfWeek": row.JourSemaine,
        "Trimester": row.Trimestre,
        "IsWeekend": 1 if row.EstWeekend =="Oui" else 0,
        "IsHoliday": 1 if row.EstJourFerie =="Oui" else 0
    }
    print(date_data)
    Dim_Time.ensure(date_data)
dwh_connection.commit()
dwh_cursor.close()
dwh_connection.close()

