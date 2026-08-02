import pyodbc
import pygrametl
import pickle
import pandas as pd
from datetime import datetime
from pathlib import Path
from pygrametl.tables import Dimension, FactTable

# Folder holding the pretrained clustering artifacts (kmeans_model.pkl, scaler.pkl).
# Put this next to ETLpipeline.py, e.g. ./models/kmeans_model.pkl and ./models/scaler.pkl
MODELS_DIR = Path(__file__).parent / "models"

# ---------------------------------------------------------------------------
# 1. Connections (done once, instead of once per file)
# ---------------------------------------------------------------------------
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

source_conn = pyodbc.connect(STAGING_CONNECTION_STRING)
source_connection = pygrametl.ConnectionWrapper(source_conn)
source_cursor = source_connection.cursor()
source_cursor.execute("SELECT @@version;")
print(f"connected to staging: {source_cursor.fetchone()[0]}!")

dwh_conn = pyodbc.connect(DWH_CONNECTION_STRING)
dwh_connection = pygrametl.ConnectionWrapper(dwh_conn)
dwh_connection.setasdefault()
dwh_cursor = dwh_connection.cursor()
dwh_cursor.execute("SELECT @@version;")
print(f"connected to DWH: {dwh_cursor.fetchone()[0]}!")

# ---------------------------------------------------------------------------
# 2. Create tables (dimensions + fact) if they don't already exist
# ---------------------------------------------------------------------------
create_statements = [
    """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Channel]') AND type = N'U')
    BEGIN
        CREATE TABLE Dim_Channel (
            channel_ID INT PRIMARY KEY,
            channel_name NVARCHAR(100)
        );
    END
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Campagne]') AND type = N'U')
    BEGIN
        CREATE TABLE Dim_Campagne (
            Campaign_ID INT PRIMARY KEY,
            Campaign_Name NVARCHAR(100)
        );
    END
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Client]') AND type = N'U')
    BEGIN
        CREATE TABLE Dim_Client (
            Client_ID VARCHAR(50) PRIMARY KEY,
            Full_Name NVARCHAR(100),
            Gender VARCHAR(10),
            Age INT,
            Age_Group VARCHAR(20),
            Ville NVARCHAR(50),
            Region NVARCHAR(50),
            Registration_Date DATE,
            Client_Type NVARCHAR(30)
        );
    END
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Payment]') AND type = N'U')
    BEGIN
        CREATE TABLE Dim_Payment (
            Payment_ID INT PRIMARY KEY,
            Payment_Mode NVARCHAR(50)
        );
    END
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Product]') AND type = N'U')
    BEGIN
        CREATE TABLE Dim_Product (
            Product_ID INT PRIMARY KEY,
            Product_Name NVARCHAR(50),
            Category NVARCHAR(50),
            Subcategory NVARCHAR(50)
        );
    END
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Time]') AND type = N'U')
    BEGIN
        CREATE TABLE Dim_Time (
            FullDate DATE PRIMARY KEY,
            Year INT,
            Month INT,
            Day INT,
            MonthName NVARCHAR(20),
            DayOfWeek NVARCHAR(20),
            Trimester VARCHAR(5),
            YearMonth VARCHAR(10),
            IsWeekend BIT,
            IsHoliday BIT
        );
    END
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Promotion]') AND type = N'U')
    BEGIN
        CREATE TABLE Dim_Promotion (
            PromotionID INT PRIMARY KEY,
            CodePromotion VARCHAR(50)
        );
    END
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Fact_Sale]') AND type = N'U')
    BEGIN
        CREATE TABLE Fact_Sale (
            TransactionID VARCHAR(20) PRIMARY KEY,
            channel_ID INT,
            Client_ID VARCHAR(50),
            Payment_ID INT,
            Product_ID INT,
            FullDate DATE,
            PromotionID INT,
            CampagneID INT,
            Montant DECIMAL(12, 2),
            Quantite INT,
            Remise DECIMAL(5, 2),
            MontantRemise DECIMAL(12, 2),
            MontantFinal DECIMAL(12, 2),
            CoutAcquisition DECIMAL(12, 2),
            Marge DECIMAL(12, 2),
            Satisfaction NVARCHAR(30),
            NPS INT,
            PointsFidelite INT
        );
    END
    """,
        """
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_Fact_Sale_Channel')
        ALTER TABLE Fact_Sale ADD CONSTRAINT FK_Fact_Sale_Channel
            FOREIGN KEY (channel_ID) REFERENCES Dim_Channel(channel_ID);
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_Fact_Sale_Client')
        ALTER TABLE Fact_Sale ADD CONSTRAINT FK_Fact_Sale_Client
            FOREIGN KEY (Client_ID) REFERENCES Dim_Client(Client_ID);
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_Fact_Sale_Payment')
        ALTER TABLE Fact_Sale ADD CONSTRAINT FK_Fact_Sale_Payment
            FOREIGN KEY (Payment_ID) REFERENCES Dim_Payment(Payment_ID);
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_Fact_Sale_Product')
        ALTER TABLE Fact_Sale ADD CONSTRAINT FK_Fact_Sale_Product
            FOREIGN KEY (Product_ID) REFERENCES Dim_Product(Product_ID);
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_Fact_Sale_Time')
        ALTER TABLE Fact_Sale ADD CONSTRAINT FK_Fact_Sale_Time
            FOREIGN KEY (FullDate) REFERENCES Dim_Time(FullDate);
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_Fact_Sale_Promotion')
        ALTER TABLE Fact_Sale ADD CONSTRAINT FK_Fact_Sale_Promotion
            FOREIGN KEY (PromotionID) REFERENCES Dim_Promotion(PromotionID);
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_Fact_Sale_Campagne')
        ALTER TABLE Fact_Sale ADD CONSTRAINT FK_Fact_Sale_Campagne
            FOREIGN KEY (CampagneID) REFERENCES Dim_Campagne(Campaign_ID);
    """,
    """
    -- Migrate a table created by an earlier version of this script (Client_ID as PK)
    -- to the new surrogate-key schema. Safe because this table is fully
    -- truncated and reloaded every run -- there's no history to lose.
    IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Client_Segment]') AND type = N'U')
       AND NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Client_Segment]') AND name = 'Segment_ID')
    BEGIN
        DROP TABLE Dim_Client_Segment;
    END
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Client_Segment]') AND type = N'U')
    BEGIN
        CREATE TABLE Dim_Client_Segment (
            Segment_ID INT PRIMARY KEY,
            Client_ID VARCHAR(50) NOT NULL UNIQUE,
            Recency INT,
            Frequency INT,
            Monetary DECIMAL(12, 2),
            R_Score INT,
            F_Score INT,
            M_Score INT,
            RFM_Score INT,
            Cluster_ID INT,
            Segment_Label NVARCHAR(50),
            SegmentDetail NVARCHAR(50),
            Last_Updated DATE,
            FOREIGN KEY (Client_ID) REFERENCES Dim_Client(Client_ID)
        );
    END
    """,
]

for stmt in create_statements:
    dwh_cursor.execute(stmt)
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 3. Dimension objects
#    lookupatts = the natural/business key used to FIND an existing row
#    key        = the surrogate primary key pygrametl fills in on insert
# ---------------------------------------------------------------------------
Dim_Channel = pygrametl.tables.Dimension(
    name='Dim_Channel',
    key='channel_ID',
    attributes=['channel_name'],
    lookupatts=['channel_name']
)

Dim_Campagne = pygrametl.tables.Dimension(
    name='Dim_Campagne',
    key='Campaign_ID',
    attributes=['Campaign_Name'],
    lookupatts=['Campaign_Name']
)

Dim_Client = pygrametl.tables.Dimension(
    name='Dim_Client',
    key='Client_ID',
    attributes=['Full_Name', 'Gender', 'Age', 'Age_Group', 'Ville', 'Region',
                'Registration_Date', 'Client_Type'],
    lookupatts=['Client_ID']
)

Dim_Client_Segment = pygrametl.tables.Dimension(
    name='Dim_Client_Segment',
    key='Segment_ID',
    attributes=['Client_ID', 'Recency', 'Frequency', 'Monetary', 'R_Score', 'F_Score',
                'M_Score', 'RFM_Score', 'Cluster_ID', 'Segment_Label',
                'SegmentDetail', 'Last_Updated'],
    lookupatts=['Client_ID']
)

Dim_Payment = pygrametl.tables.Dimension(
    name='Dim_Payment',
    key='Payment_ID',
    attributes=['Payment_Mode'],
    lookupatts=['Payment_Mode']
)

Dim_Product = pygrametl.tables.Dimension(
    name='Dim_Product',
    key='Product_ID',
    attributes=['Product_Name', 'Category', 'Subcategory'],
    lookupatts=['Product_Name']
)

Dim_Time = pygrametl.tables.Dimension(
    name='Dim_Time',
    key='FullDate',
    attributes=['Year', 'Month', 'Day', 'MonthName', 'DayOfWeek', 'Trimester',
                'YearMonth', 'IsWeekend', 'IsHoliday'],
    lookupatts=['FullDate']
)

Dim_Promotion = pygrametl.tables.Dimension(
    name='Dim_Promotion',
    key='PromotionID',
    attributes=['CodePromotion'],
    lookupatts=['CodePromotion']
)

fact_sale = pygrametl.tables.FactTable(
    name='Fact_Sale',
    keyrefs=['TransactionID', 'channel_ID', 'Client_ID', 'Payment_ID', 'Product_ID',
             'FullDate', 'PromotionID', 'CampagneID'],
    measures=['Montant', 'Quantite', 'Remise', 'MontantRemise', 'MontantFinal',
              'CoutAcquisition', 'Marge', 'Satisfaction', 'NPS', 'PointsFidelite']
)

# ---------------------------------------------------------------------------
# 4. Load Dim_Channel
# ---------------------------------------------------------------------------
channel_source = source_cursor.execute("SELECT DISTINCT CanalVente FROM source")
counter = 0
for row in channel_source:
    channel_data = {"channel_name": row.CanalVente}
    counter += 1
    Dim_Channel.ensure(channel_data)
print(f"Inserted {counter} rows into Dim_Channel.")
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 5. Load Dim_Campagne
#    NULL Campagne -> sentinel 'Aucune' so it maps to one consistent row
# ---------------------------------------------------------------------------
campaign_source = source_cursor.execute("SELECT DISTINCT Campagne FROM source")
counter = 0
for row in campaign_source:
    campaign_data = {"Campaign_Name": row.Campagne if row.Campagne else 'Aucune'}
    counter += 1
    Dim_Campagne.ensure(campaign_data)
print(f"Inserted {counter} rows into Dim_Campagne.")
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 6. Load Dim_Client
# ---------------------------------------------------------------------------
client_source = source_cursor.execute(
    "SELECT DISTINCT ClientID, NomClient, Sexe, Age, TrancheAge, Ville, Region, "
    "DateInscription, ClientType FROM source"
)
counter = 0
for row in client_source:
    client_data = {
        "Client_ID": row.ClientID,
        "Full_Name": row.NomClient,
        "Gender": row.Sexe,
        "Age": row.Age,
        "Age_Group": row.TrancheAge,
        "Ville": row.Ville,
        "Region": row.Region,
        "Registration_Date": row.DateInscription,
        "Client_Type": row.ClientType
    }
    counter += 1
    Dim_Client.ensure(client_data)
print(f"Inserted {counter} rows into Dim_Client.")
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 7. Load Dim_Payment
# ---------------------------------------------------------------------------
payment_source = source_cursor.execute("SELECT DISTINCT ModePaiement FROM source")
counter = 0
for row in payment_source:
    payment_data = {"Payment_Mode": row.ModePaiement}
    counter += 1
    
    Dim_Payment.ensure(payment_data)
print(f"Inserted {counter} rows into Dim_Payment.")
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 8. Load Dim_Product
# ---------------------------------------------------------------------------
product_source = source_cursor.execute(
    "SELECT DISTINCT Produit, CategorieProduit, SousCategorie FROM source"
)
counter = 0
for row in product_source:
    product_data = {
        "Product_Name": row.Produit,
        "Category": row.CategorieProduit,
        "Subcategory": row.SousCategorie
    }
    counter += 1
    Dim_Product.ensure(product_data)
print(f"Inserted {counter} rows into Dim_Product.")
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 9. Load Dim_Time
# ---------------------------------------------------------------------------
date_source = source_cursor.execute(
    "SELECT DISTINCT DateVente, Annee, Mois, MoisNum, Trimestre, YearMonth, "
    "JourSemaine, EstWeekend, EstJourFerie FROM source"
)
counter = 0
for row in date_source:
    full_date = row.DateVente
    if isinstance(full_date, str):
        full_date = datetime.strptime(full_date, "%Y-%m-%d").date()
    elif isinstance(full_date, datetime):
        full_date = full_date.date()

    date_data = {
        "FullDate": full_date,
        "Year": row.Annee,
        "Month": row.MoisNum,
        "Day": full_date.day,
        "MonthName": row.Mois,
        "DayOfWeek": row.JourSemaine,
        "Trimester": row.Trimestre,
        "YearMonth": row.YearMonth,
        "IsWeekend": 1 if row.EstWeekend == "Oui" else 0,
        "IsHoliday": 1 if row.EstJourFerie == "Oui" else 0
    }
    counter += 1
    Dim_Time.ensure(date_data)
print(f"Inserted {counter} rows into Dim_Time.")
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 10. Load Dim_Promotion
#     NULL CodePromo -> sentinel 'Aucune' so it maps to one consistent row
# ---------------------------------------------------------------------------
promotion_source = source_cursor.execute("SELECT DISTINCT CodePromo FROM source")
counter = 0
for row in promotion_source:
    promotion_data = {"CodePromotion": row.CodePromo if row.CodePromo else 'Aucune'}
    counter += 1
    Dim_Promotion.ensure(promotion_data)
print(f"Inserted {counter} rows into Dim_Promotion.")
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 11. Load Fact_Sale
#     Skips any TransactionID already present, so re-running the script
#     doesn't duplicate fact rows.
# ---------------------------------------------------------------------------
sale_source = source_cursor.execute(
    "SELECT TransactionID, CanalVente, ClientID, ModePaiement, Produit, DateVente, "
    "CodePromo, Campagne, Montant, Quantite, Remise, MontantRemise, MontantFinal, "
    "CoutAcquisition, Marge, Satisfaction, NPS, PointsFidelite FROM source"
)
counter = 0
for row in sale_source:
    existing = dwh_cursor.execute(
        "SELECT 1 FROM Fact_Sale WHERE TransactionID = ?", row.TransactionID
    ).fetchone()
    if existing:
        continue

    full_date = row.DateVente
    if isinstance(full_date, str):
        full_date = datetime.strptime(full_date, "%Y-%m-%d").date()
    elif isinstance(full_date, datetime):
        full_date = full_date.date()

    # Remise arrives as text like "0%" / "10%" -- parse to a plain number
    remise_raw = row.Remise
    if isinstance(remise_raw, str):
        remise_raw = remise_raw.strip().replace('%', '').replace(',', '.')
        remise_value = float(remise_raw) if remise_raw else 0.0
    else:
        remise_value = float(remise_raw) if remise_raw is not None else 0.0

    channel_id = Dim_Channel.ensure({"channel_name": row.CanalVente})
    client_id = Dim_Client.ensure({"Client_ID": row.ClientID})
    payment_id = Dim_Payment.ensure({"Payment_Mode": row.ModePaiement})
    product_id = Dim_Product.ensure({"Product_Name": row.Produit})
    Dim_Time.ensure({"FullDate": full_date})
    promotion_id = Dim_Promotion.ensure(
        {"CodePromotion": row.CodePromo if row.CodePromo else 'Aucune'}
    )
    campagne_id = Dim_Campagne.ensure(
        {"Campaign_Name": row.Campagne if row.Campagne else 'Aucune'}
    )
    fact_row = {
        "TransactionID": row.TransactionID,
        "channel_ID": channel_id,
        "Client_ID": client_id,
        "Payment_ID": payment_id,
        "Product_ID": product_id,
        "FullDate": full_date,
        "PromotionID": promotion_id,
        "CampagneID": campagne_id,
        "Montant": row.Montant,
        "Quantite": row.Quantite,
        "Remise": remise_value,
        "MontantRemise": row.MontantRemise,
        "MontantFinal": row.MontantFinal,
        "CoutAcquisition": row.CoutAcquisition,
        "Marge": row.Marge,
        "Satisfaction": row.Satisfaction,
        "NPS": row.NPS,
        "PointsFidelite": row.PointsFidelite
    }
    counter += 1
    fact_sale.insert(fact_row)
print(f"Inserted {counter} rows into Fact_Sale.")
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 11.5 Compute RFM and assign client segments with the pretrained K-means model
#      Full overwrite every run: no history, just today's snapshot.
# ---------------------------------------------------------------------------
with open(MODELS_DIR / "scaler.pkl", "rb") as f:
    rfm_scaler = pickle.load(f)
with open(MODELS_DIR / "kmeans_model.pkl", "rb") as f:
    rfm_kmeans = pickle.load(f)

# Cluster -> business label, derived once from inspecting kmeans.cluster_centers_
# (scaled order is [recency, frequency, monetary]):
#   cluster 0: recency slightly below avg, frequency/monetary slightly below avg -> Reguliers
#   cluster 1: recency low (recent), frequency & monetary high                   -> Champions
#   cluster 2: recency high (long time since last purchase), frequency/monetary low -> A_Risque
CLUSTER_LABELS = {
    0: "Clients Réguliers",
    1: "Champions",
    2: "Clients à Risque / Perdus",
}

# Reference point for Recency: this is a static historical dataset, not a live feed,
# so "today" = the latest sale date actually present in Fact_Sale, not datetime.now().
reference_date = dwh_cursor.execute("SELECT MAX(FullDate) FROM Fact_Sale").fetchone()[0]

rfm_rows = dwh_cursor.execute(
    """
    SELECT Client_ID,
           DATEDIFF(day, MAX(FullDate), ?) AS Recency,
           COUNT(TransactionID)            AS Frequency,
           SUM(MontantFinal)               AS Monetary
    FROM Fact_Sale
    GROUP BY Client_ID
    """,
    reference_date
).fetchall()

rfm_df = pd.DataFrame.from_records(
    rfm_rows, columns=["Client_ID", "Recency", "Frequency", "Monetary"]
)

# Same column order the scaler/model were fit on: recency, frequency, monetary.
# Pass a plain numpy array (not a DataFrame) so sklearn doesn't check column
# names -- the scaler/model were fit on lowercase names ('recency', etc.)
# from the original notebook, while this DataFrame uses capitalized names.
X_scaled = rfm_scaler.transform(
    rfm_df[["Recency", "Frequency", "Monetary"]].to_numpy()
)
rfm_df["Cluster_ID"] = rfm_kmeans.predict(X_scaled)
rfm_df["Segment_Label"] = rfm_df["Cluster_ID"].map(CLUSTER_LABELS)

# ---- R/F/M quintile scores (1-5, recomputed fresh against this run's population) ----
# rank(method='first') breaks ties so qcut always gets 5 clean, equal-sized bins,
# same trick your original notebook used to avoid duplicate-bin-edge errors.
rfm_df["R_Score"] = pd.qcut(
    rfm_df["Recency"].rank(method="first", ascending=True), 5, labels=[5, 4, 3, 2, 1]
).astype(int)
rfm_df["F_Score"] = pd.qcut(
    rfm_df["Frequency"].rank(method="first", ascending=False), 5, labels=[5, 4, 3, 2, 1]
).astype(int)
rfm_df["M_Score"] = pd.qcut(
    rfm_df["Monetary"].rank(method="first", ascending=False), 5, labels=[5, 4, 3, 2, 1]
).astype(int)
rfm_df["RFM_Score"] = (rfm_df["R_Score"] * 100 + rfm_df["F_Score"] * 10 + rfm_df["M_Score"])

# ---- Split "Clients à Risque / Perdus" into Nouveaux / À Surveiller / Perdus ----
# The model only has 3 clusters, so this split isn't something k-means gives us --
# it's a business rule layered on top of that one cluster.
AT_RISK_LABEL = "Clients à Risque / Perdus"
NEW_CLIENT_WINDOW_DAYS = 90  # tune this to your business's definition of "new"

client_reg_rows = dwh_cursor.execute(
    "SELECT Client_ID, Registration_Date FROM Dim_Client"
).fetchall()
reg_df = pd.DataFrame.from_records(
    client_reg_rows, columns=["Client_ID", "Registration_Date"]
)
rfm_df = rfm_df.merge(reg_df, on="Client_ID", how="left")
rfm_df["Days_Since_Registration"] = rfm_df["Registration_Date"].apply(
    lambda d: (reference_date - d).days if pd.notna(d) else None
)

# Default: everyone outside the at-risk cluster keeps their top-level label as detail
rfm_df["SegmentDetail"] = rfm_df["Segment_Label"]

at_risk_mask = rfm_df["Segment_Label"] == AT_RISK_LABEL
new_mask = at_risk_mask & (rfm_df["Days_Since_Registration"] <= NEW_CLIENT_WINDOW_DAYS)
rfm_df.loc[new_mask, "SegmentDetail"] = "Nouveaux Clients"

# Whatever's left in the at-risk cluster (not "new") gets split by how stale they
# are: the most-stale third are "Perdus", the rest are "À Surveiller".
remaining_mask = at_risk_mask & ~new_mask
if remaining_mask.any():
    recency_p66 = rfm_df.loc[remaining_mask, "Recency"].quantile(0.66)
    stale_mask = remaining_mask & (rfm_df["Recency"] > recency_p66)
    watch_mask = remaining_mask & ~stale_mask
    rfm_df.loc[stale_mask, "SegmentDetail"] = "Perdus"
    rfm_df.loc[watch_mask, "SegmentDetail"] = "À Surveiller"

# Full overwrite: truncate then reinsert every run via the pygrametl Dimension object
dwh_cursor.execute("TRUNCATE TABLE Dim_Client_Segment")

counter = 0
for r in rfm_df.itertuples(index=False):
    segment_data = {
        "Client_ID": str(r.Client_ID),
        "Recency": int(r.Recency),      # cast off numpy/pandas dtypes so pyodbc accepts them
        "Frequency": int(r.Frequency),
        "Monetary": float(r.Monetary),
        "R_Score": int(r.R_Score),
        "F_Score": int(r.F_Score),
        "M_Score": int(r.M_Score),
        "RFM_Score": int(r.RFM_Score),
        "Cluster_ID": int(r.Cluster_ID),
        "Segment_Label": r.Segment_Label,
        "SegmentDetail": r.SegmentDetail,
        "Last_Updated": reference_date
    }
    Dim_Client_Segment.insert(segment_data)
    counter += 1
print(f"Inserted {counter} rows into Dim_Client_Segment.")
dwh_connection.commit()

# ---------------------------------------------------------------------------
# 12. Clean up
# ---------------------------------------------------------------------------
dwh_cursor.close()
dwh_connection.close()
source_cursor.close()
source_connection.close()