#!/usr/bin/env python
# coding: utf-8

# In[15]:


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


# In[16]:


source_conn = pyodbc.connect(STAGING_CONNECTION_STRING)
source_connection = pygrametl.ConnectionWrapper(source_conn)
source_cursor = source_connection.cursor()
source_cursor.execute("SELECT @@version;")
result = source_cursor.fetchone()
print(f"connected to {result[0]}!")


# In[17]:


dwh_conn = pyodbc.connect(DWH_CONNECTION_STRING)
dwh_connection = pygrametl.ConnectionWrapper(dwh_conn)
dwh_cursor = dwh_connection.cursor()
dwh_cursor.execute("SELECT @@version;")
result = dwh_cursor.fetchone()
print(f"connected to {result[0]}!")
dwh_connection.setasdefault()


# In[ ]:


create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Promotion]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Promotion (
        PromotionID INT PRIMARY KEY,
        CodePromotion VARCHAR(50)
    );
END
"""
dwh_cursor.execute(create_table_sql)
dwh_connection.commit()


# In[19]:


from pygrametl.tables import Dimension
Dim_Promotion = pygrametl.tables.Dimension(
    name='Dim_Promotion',
    key='PromotionID',
    attributes=['CodePromotion']
)    


# In[20]:


promotion_source=source_cursor.execute("SELECT Distinct CodePromo FROM source")
for row in promotion_source:
    promotion_data = {
        "CodePromotion": row.CodePromo
    }
    print(promotion_data)
    Dim_Promotion.ensure(promotion_data)
dwh_connection.commit()
dwh_cursor.close()
dwh_connection.close()

