import pyodbc
import pygrametl
from pygrametl.tables import Dimension, FactTable

# ============================================
# DATABASE CONNECTION CONFIGURATION
# ============================================

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
    "Database=DWH2;"
    "UID=sa;"
    "PWD=ghom3220;"
)

# ============================================
# CONNECT TO DATABASES
# ============================================

print("Connecting to staging database...")
source_conn = pyodbc.connect(STAGING_CONNECTION_STRING)
source_connection = pygrametl.ConnectionWrapper(source_conn)
source_cursor = source_connection.cursor()
source_cursor.execute("SELECT @@version;")
result = source_cursor.fetchone()
print(f"Connected to staging: {result[0]}")

print("Connecting to data warehouse...")
dwh_conn = pyodbc.connect(DWH_CONNECTION_STRING)
dwh_connection = pygrametl.ConnectionWrapper(dwh_conn)
dwh_cursor = dwh_connection.cursor()
dwh_cursor.execute("SELECT @@version;")
result = dwh_cursor.fetchone()
print(f"Connected to data warehouse: {result[0]}")
dwh_connection.setasdefault()

# ============================================
# CREATE DIMENSION TABLES
# ============================================

print("\nCreating dimension tables...")

# 1. Dim_Temps (Time Dimension)
create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Temps]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Temps (
        DateComplete DATE PRIMARY KEY,
        Jour INT,
        NomJour VARCHAR(20),
        Semaine INT,
        Mois INT,
        NomMois VARCHAR(20),
        Trimestre varchar(10),
        Annee INT,
        EstWeekend BIT,
        EstJourFerie BIT
    );
END
"""
dwh_cursor.execute(create_table_sql)
print("  - Dim_Temps created/verified")

# 2. Dim_Client
create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Client]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Client (
        ClientID VARCHAR(50) PRIMARY KEY,
        NomClient VARCHAR(100),
        Sexe VARCHAR(10),
        Age INT,
        TrancheAge VARCHAR(20),
        Ville VARCHAR(50),
        Region VARCHAR(50),
        DateInscription DATE,
        TypeClient VARCHAR(50)
    );
END
"""
dwh_cursor.execute(create_table_sql)
print("  - Dim_Client created/verified")

# 3. Dim_Produit
create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Produit]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Produit (
        ProduitID INT PRIMARY KEY,
        NomProduit VARCHAR(50),
        SousCategorie VARCHAR(50),
        Categorie VARCHAR(50)
    );
END
"""
dwh_cursor.execute(create_table_sql)
print("  - Dim_Produit created/verified")

# 4. Dim_Canal
create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Canal]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Canal (
        CanalID INT PRIMARY KEY,
        CanalVente VARCHAR(100)
    );
END
"""
dwh_cursor.execute(create_table_sql)
print("  - Dim_Canal created/verified")

# 5. Dim_Paiment
create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Paiment]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Paiment (
        PaimentID INT PRIMARY KEY,
        ModePaiment VARCHAR(50)
    );
END
"""
dwh_cursor.execute(create_table_sql)
print("  - Dim_Paiment created/verified")

# 6. Dim_Campagne
create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Campagne]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Campagne (
        CampagneID INT PRIMARY KEY,
        NomCampagne VARCHAR(100)
    );
END
"""
dwh_cursor.execute(create_table_sql)
print("  - Dim_Campagne created/verified")

# 7. Dim_Promotion
create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Dim_Promotion]') AND type in (N'U'))
BEGIN
    CREATE TABLE Dim_Promotion (
        PromotionID INT PRIMARY KEY,
        CodePromo VARCHAR(50),
        Remise DECIMAL(10,2)
    );
END
"""
dwh_cursor.execute(create_table_sql)
print("  - Dim_Promotion created/verified")

# 8. Fact_Vente
create_table_sql = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Fact_Vente]') AND type in (N'U'))
BEGIN
    CREATE TABLE Fact_Vente (
        VenteID INT PRIMARY KEY,
        DateComplete DATE,
        ClientID VARCHAR(50),
        ProduitID INT,
        CanalID INT,
        PaimentID INT,
        CampagneID INT,
        PromotionID INT,
        Montant DECIMAL(18,2),
        MontantFinal DECIMAL(18,2),
        Marge DECIMAL(18,2),
        Quantite INT,
        Remise DECIMAL(10,2),
        CoutAcquisition DECIMAL(18,2),
        PointsFidelite INT,
        NPS INT,
        FOREIGN KEY (DateComplete) REFERENCES Dim_Temps(DateComplete),
        FOREIGN KEY (ClientID) REFERENCES Dim_Client(ClientID),
        FOREIGN KEY (ProduitID) REFERENCES Dim_Produit(ProduitID),
        FOREIGN KEY (CanalID) REFERENCES Dim_Canal(CanalID),
        FOREIGN KEY (PaimentID) REFERENCES Dim_Paiment(PaimentID),
        FOREIGN KEY (CampagneID) REFERENCES Dim_Campagne(CampagneID),
        FOREIGN KEY (PromotionID) REFERENCES Dim_Promotion(PromotionID)
    );
END
"""
dwh_cursor.execute(create_table_sql)
print("  - Fact_Vente created/verified")

dwh_connection.commit()

# ============================================
# DEFINE DIMENSION OBJECTS
# ============================================

print("\nInitializing dimension objects...")

Dim_Temps = Dimension(
    name='Dim_Temps',
    key='DateComplete',
    attributes=['Jour', 'NomJour', 'Semaine', 'Mois', 'NomMois', 'Trimestre', 'Annee', 'EstWeekend', 'EstJourFerie']
)

Dim_Client = Dimension(
    name='Dim_Client',
    key='ClientID',
    attributes=['NomClient', 'Sexe', 'Age', 'TrancheAge', 'Ville', 'Region', 'DateInscription', 'TypeClient']
)

Dim_Produit = Dimension(
    name='Dim_Produit',
    key='ProduitID',
    attributes=['NomProduit', 'SousCategorie', 'Categorie']
)

Dim_Canal = Dimension(
    name='Dim_Canal',
    key='CanalID',
    attributes=['CanalVente']
)

Dim_Paiment = Dimension(
    name='Dim_Paiment',
    key='PaimentID',
    attributes=['ModePaiment']
)

Dim_Campagne = Dimension(
    name='Dim_Campagne',
    key='CampagneID',
    attributes=['NomCampagne']
)

Dim_Promotion = Dimension(
    name='Dim_Promotion',
    key='PromotionID',
    attributes=['CodePromo', 'Remise']
)

print("  - All dimension objects initialized")

# ============================================
# LOAD DIMENSION TABLES
# ============================================

print("\nLoading dimension tables...")

# --------------------------------------------
# 1. Load Dim_Temps
# --------------------------------------------
print("  - Loading Dim_Temps...")
temp_source = source_cursor.execute("""
    SELECT DISTINCT 
        DateVente,
        DAY(DateVente) as Jour,
        DATENAME(weekday, DateVente) as NomJour,
        DATEPART(week, DateVente) as Semaine,
        MONTH(DateVente) as Mois,
        DATENAME(month, DateVente) as NomMois,
        Trimestre,
        YEAR(DateVente) as Annee,
        EstWeekend,
        EstJourFerie
    FROM source
""")
temp_count = 0
for row in temp_source:
    est_weekend = 1 if row.EstWeekend == 'Oui' else 0
    est_jour_ferie = 1 if row.EstJourFerie == 'Oui' else 0
    temp_data = {
        "DateComplete": row.DateVente,
        "Jour": row.Jour,
        "NomJour": row.NomJour,
        "Semaine": row.Semaine,
        "Mois": row.Mois,
        "NomMois": row.NomMois,
        "Trimestre": row.Trimestre,
        "Annee": row.Annee,
        "EstWeekend": est_weekend,
        "EstJourFerie": est_jour_ferie
    }
    Dim_Temps.insert(temp_data)
    temp_count += 1
print(f"    Loaded {temp_count} time records")

# --------------------------------------------
# 2. Load Dim_Client
# --------------------------------------------
print("  - Loading Dim_Client...")
client_source = source_cursor.execute("""
    SELECT DISTINCT 
        ClientID, NomClient, Sexe, Age, TrancheAge, 
        Ville, Region, DateInscription, ClientType
    FROM source
""")
client_count = 0
for row in client_source:
    client_data = {
        "ClientID": row.ClientID,
        "NomClient": row.NomClient,
        "Sexe": row.Sexe,
        "Age": row.Age,
        "TrancheAge": row.TrancheAge,
        "Ville": row.Ville,
        "Region": row.Region,
        "DateInscription": row.DateInscription,
        "TypeClient": row.ClientType
    }
    Dim_Client.insert(client_data)
    client_count += 1
    if client_count % 100 == 0:
        print(f"    Processed {client_count} clients")
print(f"    Loaded {client_count} clients")

# --------------------------------------------
# 3. Load Dim_Produit
# --------------------------------------------
print("  - Loading Dim_Produit...")
produit_source = source_cursor.execute("SELECT DISTINCT Produit, SousCategorie, CategorieProduit FROM source")
produit_count = 0
for row in produit_source:
    produit_data = {
        "NomProduit": row.Produit,
        "SousCategorie": row.SousCategorie,
        "Categorie": row.CategorieProduit
    }
    Dim_Produit.insert(produit_data)
    produit_count += 1
    if produit_count % 100 == 0:
        print(f"    Processed {produit_count} products")
print(f"    Loaded {produit_count} products")

# --------------------------------------------
# 4. Load Dim_Canal
# --------------------------------------------
print("  - Loading Dim_Canal...")
canal_source = source_cursor.execute("SELECT DISTINCT CanalVente FROM source")
canal_count = 0
for row in canal_source:
    canal_data = {
        "CanalVente": row.CanalVente
    }
    Dim_Canal.insert(canal_data)
    canal_count += 1
print(f"    Loaded {canal_count} channels")

# --------------------------------------------
# 5. Load Dim_Paiment
# --------------------------------------------
print("  - Loading Dim_Paiment...")
paiment_source = source_cursor.execute("SELECT DISTINCT ModePaiement FROM source")
paiment_count = 0
for row in paiment_source:
    paiment_data = {
        "ModePaiment": row.ModePaiement
    }
    Dim_Paiment.insert(paiment_data)
    paiment_count += 1
print(f"    Loaded {paiment_count} payment modes")

# --------------------------------------------
# 6. Load Dim_Campagne
# --------------------------------------------
print("  - Loading Dim_Campagne...")
campagne_source = source_cursor.execute("SELECT DISTINCT Campagne FROM source WHERE Campagne IS NOT NULL")
campagne_count = 0
for row in campagne_source:
    campagne_data = {
        "NomCampagne": row.Campagne
    }
    Dim_Campagne.insert(campagne_data)
    campagne_count += 1
print(f"    Loaded {campagne_count} campaigns")

# --------------------------------------------
# 7. Load Dim_Promotion
# --------------------------------------------
print("  - Loading Dim_Promotion...")
promotion_source = source_cursor.execute("SELECT DISTINCT CodePromo, Remise FROM source WHERE CodePromo IS NOT NULL")
promotion_count = 0
for row in promotion_source:
    number = int(row.Remise.replace("%",""))
    promotion_data = {
        "CodePromo": row.CodePromo,
        "Remise": number
    }
    Dim_Promotion.insert(promotion_data)
    promotion_count += 1
print(f"    Loaded {promotion_count} promotions")

# ============================================
# LOAD FACT TABLE
# ============================================

print("\nLoading Fact_Vente...")

# Create FactTable object
Fact_Vente = FactTable(
    name='Fact_Vente',
    keyrefs=['DateComplete', 'ClientID', 'ProduitID', 'CanalID', 'PaimentID', 'CampagneID', 'PromotionID'],
    measures=['Montant', 'MontantFinal', 'Marge', 'Quantite', 'Remise', 'CoutAcquisition', 'PointsFidelite', 'NPS']
)

# Query to load fact table with all dimension keys
fact_source = source_cursor.execute("""
    SELECT 
        s.DateVente,
        s.ClientID,
        p.ProduitID,
        c.CanalID,
        pm.PaimentID,
        cam.CampagneID,
        prom.PromotionID,
        s.Montant,
        s.MontantFinal,
        s.Marge,
        s.Quantite,
        s.Remise,
        s.CoutAcquisition,
        s.PointsFidelite,
        s.NPS
    FROM source s
    LEFT JOIN dbo.Dim_Produit p ON p.NomProduit = s.Produit
    LEFT JOIN dbo.Dim_Canal c ON c.CanalVente = s.CanalVente
    LEFT JOIN dbo.Dim_Paiment pm ON pm.ModePaiment = s.ModePaiement
    LEFT JOIN dbo.Dim_Campagne cam ON cam.NomCampagne = s.Campagne
    LEFT JOIN dbo.Dim_Promotion prom ON prom.CodePromo = s.CodePromo
""")

fact_count = 0
for row in fact_source:
    fact_data = {
        "DateComplete": row.DateVente,
        "ClientID": row.ClientID,
        "ProduitID": row.ProduitID,
        "CanalID": row.CanalID,
        "PaimentID": row.PaimentID,
        "CampagneID": row.CampagneID,
        "PromotionID": row.PromotionID,
        "Montant": row.Montant,
        "MontantFinal": row.MontantFinal,
        "Marge": row.Marge,
        "Quantite": row.Quantite,
        "Remise": row.Remise,
        "CoutAcquisition": row.CoutAcquisition,
        "PointsFidelite": row.PointsFidelite,
        "NPS": row.NPS
    }
    Fact_Vente.insert(fact_data)
    fact_count += 1
    if fact_count % 1000 == 0:
        print(f"    Processed {fact_count} fact records")

print(f"    Loaded {fact_count} fact records")

# ============================================
# COMMIT AND CLEANUP
# ============================================

print("\nCommitting changes and closing connections...")
dwh_connection.commit()

dwh_cursor.close()
dwh_connection.close()
source_cursor.close()
source_connection.close()

print("\n" + "="*60)
print("DATA WAREHOUSE LOADED SUCCESSFULLY!")
print("="*60)
print(f"  - Dim_Temps:        {temp_count} records")
print(f"  - Dim_Client:       {client_count} records")
print(f"  - Dim_Produit:      {produit_count} records")
print(f"  - Dim_Canal:        {canal_count} records")
print(f"  - Dim_Paiment:      {paiment_count} records")
print(f"  - Dim_Campagne:     {campagne_count} records")
print(f"  - Dim_Promotion:    {promotion_count} records")
print(f"  - Fact_Vente:       {fact_count} records")
print("="*60)