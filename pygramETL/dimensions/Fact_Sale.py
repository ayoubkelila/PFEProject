#!/usr/bin/env python
# coding: utf-8

# In[48]:



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


# In[49]:


source_conn = pyodbc.connect(STAGING_CONNECTION_STRING)
source_connection = pygrametl.ConnectionWrapper(source_conn)
source_cursor = source_connection.cursor()
source_cursor.execute("SELECT @@version;")
result = source_cursor.fetchone()
print(f"connected to {result[0]}!")


# In[50]:


dwh_conn = pyodbc.connect(DWH_CONNECTION_STRING)
dwh_connection = pygrametl.ConnectionWrapper(dwh_conn)
dwh_cursor = dwh_connection.cursor()
dwh_cursor.execute("SELECT @@version;")
result = dwh_cursor.fetchone()
print(f"connected to {result[0]}!")
dwh_connection.setasdefault()


# In[51]:


create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Fact_Sale]') AND type in (N'U'))
BEGIN
    CREATE TABLE Fact_Sale (
        channel_ID INT,
        Client_ID VARCHAR(50),
        Payment_ID INT,
        Product_ID INT,
        FullDate DATE,
        PromotionID INT,
        Montant DECIMAL(10, 2),
        MantantFina DECIMAL(10, 2),
        Marge DECIMAL(10, 2),
        Quantite INT,
        Remise DECIMAL(10, 2),
        NPS INT
    );
END
"""
dwh_cursor.execute(create_table_sql)
dwh_connection.commit()


# In[52]:
from pygrametl.tables import Dimension,FactTable
from dimensions.Promotion_dimension import Dim_Promotion
from dimensions.Channel_dimension import Dim_Channel
from dimensions.Client_dimension import Dim_Client
from dimensions.Campagne_dimension import Dim_Campagne
from dimensions.Payment_dimension import Dim_Payment
from dimensions.Produit_dimension import Dim_Product
from dimensions.Time_dimension import Dim_Time

fact_sale = pygrametl.tables.FactTable(
    name='Fact_Sale',
    keyrefs=['channel_ID', 'PromotionID', 'Client_ID', 'Payment_ID', 'Product_ID', 'FullDate'],
    measures=['Montant', 'MantantFina', 'Marge', 'Quantite , Remise', 'NPS'] )

# In[53]:


Sale_source=source_cursor.execute("SELECT Distinct * FROM source")
for row in Sale_source:
    ChannelID = Dim_Channel.ensure({"ChannelID": row.CanalVente})
    ClientID = Dim_Client.ensure({"ClientID": row.ClientID})
    CampagneID = Dim_Campagne.ensure({"CampagneID": row.Campagne})
    PaymentID = Dim_Payment.ensure({"PaymentID": row.ModePaiement})
    ProductID = Dim_Product.ensure({"ProductID": row.NomProduit})
    TimeID = Dim_Time.ensure({"TimeID": row.DateVente})
    PromotionID = Dim_Promotion.ensure({"CodePromotion": row.CodePromo})
    Sale_data = {
        "CodePromotion": row.CodePromo
    }
    print(Sale_data)
    Dim_Promotion.ensure( Sale_data)
dwh_connection.commit()
dwh_cursor.close()
dwh_connection.close()

