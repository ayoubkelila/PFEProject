#!/usr/bin/env python
# coding: utf-8

# In[24]:


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


# In[25]:


source_conn = pyodbc.connect(STAGING_CONNECTION_STRING)
source_connection = pygrametl.ConnectionWrapper(source_conn)
source_cursor = source_connection.cursor()
source_cursor.execute("SELECT @@version;")
result = source_cursor.fetchone()
print(f"connected to {result[0]}!")


# In[26]:


dwh_conn = pyodbc.connect(DWH_CONNECTION_STRING)
dwh_connection = pygrametl.ConnectionWrapper(dwh_conn)
dwh_cursor = dwh_connection.cursor()
dwh_cursor.execute("SELECT @@version;")
result = dwh_cursor.fetchone()
print(f"connected to {result[0]}!")
dwh_connection.setasdefault()


# In[27]:


create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Payment]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Payment (
        Payment_ID INT PRIMARY KEY,
        Payment_Mode VARCHAR(50)
    );
END
"""
dwh_cursor.execute(create_table_sql)
dwh_connection.commit()


# In[28]:


from pygrametl.tables import Dimension
Dim_Payment = pygrametl.tables.Dimension(
    name='Dim_Payment',
    key='Payment_ID',

    attributes=[
        'Payment_Mode'
    ] , lookupatts=['Payment_ID']
)    


# In[30]:


payment_source=source_cursor.execute("SELECT Distinct(ModePaiement) FROM source")
for row in payment_source:

    payment_data = {
        "Payment_Mode" : row.ModePaiement
    }
    print(payment_data)
    Dim_Payment.ensure(payment_data)
dwh_connection.commit()
dwh_cursor.close()
dwh_connection.close()

