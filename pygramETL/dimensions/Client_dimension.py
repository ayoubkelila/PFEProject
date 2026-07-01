#!/usr/bin/env python
# coding: utf-8

# In[1]:


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


# In[2]:


source_conn = pyodbc.connect(STAGING_CONNECTION_STRING)
source_connection = pygrametl.ConnectionWrapper(source_conn)
source_cursor = source_connection.cursor()
source_cursor.execute("SELECT @@version;")
result = source_cursor.fetchone()
print(f"connected to {result[0]}!")


# In[3]:


dwh_conn = pyodbc.connect(DWH_CONNECTION_STRING)
dwh_connection = pygrametl.ConnectionWrapper(dwh_conn)
dwh_cursor = dwh_connection.cursor()
dwh_cursor.execute("SELECT @@version;")
result = dwh_cursor.fetchone()
print(f"connected to {result[0]}!")
dwh_connection.setasdefault()


# In[4]:


create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Customer]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Customer (
        Client_ID VARCHAR(50) PRIMARY KEY,
        Full_Name VARCHAR(100),
        Gender VARCHAR(10),
        Age INT,
        Age_Group VARCHAR(20),
        Registration_Date DATE
    );
END
"""
dwh_cursor.execute(create_table_sql)
dwh_connection.commit()


# In[5]:


from pygrametl.tables import Dimension
Dim_Customer = pygrametl.tables.Dimension(
    name='Dim_Customer',

    key='Client_ID',

    attributes=[
        'Full_Name',
        'Gender',
        'Age',
        'Age_Group',
        'Registration_Date'
    ]
)    


# In[6]:


client_source=source_cursor.execute("SELECT Distinct ClientID,NomClient,Sexe,Age,TrancheAge,ClientType,DateInscription FROM source")
for row in client_source:
    client_data = {
        "Client_ID" : row.ClientID,
        "Full_Name" : row.NomClient,
        "Gender" : row.Sexe,
        "Age" : row.Age,
        "Age_Group" : row.TrancheAge,
        "Registration_Date" : row.DateInscription
    }
    print(client_data)
    Dim_Customer.ensure(client_data)
dwh_connection.commit()
dwh_cursor.close()
dwh_connection.close()

