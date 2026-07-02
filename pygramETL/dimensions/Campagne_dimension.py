#!/usr/bin/env python
# coding: utf-8

# In[2]:


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


# In[3]:


source_conn = pyodbc.connect(STAGING_CONNECTION_STRING)
source_connection = pygrametl.ConnectionWrapper(source_conn)
source_cursor = source_connection.cursor()
source_cursor.execute("SELECT @@version;")
result = source_cursor.fetchone()
print(f"connected to {result[0]}!")


# In[4]:


dwh_conn = pyodbc.connect(DWH_CONNECTION_STRING)
dwh_connection = pygrametl.ConnectionWrapper(dwh_conn)
dwh_cursor = dwh_connection.cursor()
dwh_cursor.execute("SELECT @@version;")
result = dwh_cursor.fetchone()
print(f"connected to {result[0]}!")
dwh_connection.setasdefault()


# In[5]:


create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Channel]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Channel (
        channel_ID INT PRIMARY KEY,
        channel_name VARCHAR(100),
    );
END
"""
dwh_cursor.execute(create_table_sql)
dwh_connection.commit()


# In[6]:


from pygrametl.tables import Dimension
Dim_Campagne = pygrametl.tables.Dimension(
    name='Dim_Campagne',

    key='Campaign_ID',

    attributes=[
        'Campaign_Name'
    ],
    lookupatts=['Campaign_ID']
)    


# In[7]:


campaign_source=source_cursor.execute("SELECT Distinct Campagne FROM source")
for row in campaign_source:
    campaign_data = {
        "Campaign_Name" : row.NomCampagne
    }
    print(campaign_data)
    Dim_Campagne.ensure(campaign_data)
dwh_connection.commit()
dwh_cursor.close()
dwh_connection.close()

