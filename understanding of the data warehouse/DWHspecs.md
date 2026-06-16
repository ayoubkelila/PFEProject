# Data Warehouse — Technical Specification (Final v2.0)
## PFE — Kimball Dimensional Modeling | TunisShop Retail DWH

---

## 1. Business Scenario & Client Needs

### Company Profile
**TunisShop** is a Tunisian multi-channel retail company selling products across 8 categories
(Alimentation, Beauté, Électronique, Jouets, Livres, Maison, Sport, Vêtements) through
both a physical store and digital channels (website, mobile app, social media, phone).
The company operates across all four Tunisian regions (Grand Tunis, Nord, Centre, Sud)
and accepts 6 payment methods including modern fintech options (Flouci, D17).

### Analytical Needs (BI Reporting Goals)
| # | Need | Key Question |
|---|------|-------------|
| 1 | Sales Performance | What is the revenue and margin by period, region, and category? |
| 2 | Customer Behavior | Which loyalty segments buy most, and through which channels? |
| 3 | Promotion Effectiveness | Which campaigns/codes generate the most sales lift? |
| 4 | Customer Satisfaction | How does post-purchase satisfaction correlate with product, channel, and promotion? |
| 5 | Payment Trends | Which payment methods dominate by region and age group? |

---

## 2. Business Rules (Confirmed & Refined)

| # | Rule |
|---|------|
| BR-01 | **Grain**: One transaction line = one product purchased by one client on one date. There is no basket concept. |
| BR-02 | **ETL Strategy**: The staging table is a **full reload** — the ETL truncates the DWH target and reloads from the latest export file. |
| BR-03 | **Loyalty Segment**: Manually assigned by business users based on real-life CRM interaction. It is not system-calculated. The value captured at transaction time is the authoritative truth. No SCD Type 2 is needed. |
| BR-04 | **Promotion & Promo Code are independent**: A transaction can have (a) no promotion and no code, (b) a campaign name only, (c) a promo code only, or (d) both. They map to two separate nullable foreign keys in the fact table. |
| BR-05 | **is_holiday** is a valid boolean flag derived from the Tunisian public holiday calendar. It is populated at ETL time for every transaction date. |
| BR-06 | **Satisfaction & NPS** are post-purchase survey responses captured immediately after the transaction. They are fact-table measures, not client attributes. |
| BR-07 | Revenue TTC = (unit_price × quantity) − discount_amount. TVA and margin are pre-calculated in the source and stored as additive measures. |
| BR-08 | A discount_amount > 0 always implies either a promotion_name, a promo_code, or both. A 0% discount means neither was applied. |
| BR-09 | `acquisition_channel` describes how the client was originally acquired (a client-level attribute), not the channel through which this specific order was placed. |
| BR-10 | `feedback_comment` is free-text and optional. It does not belong in any dimension — it is a degenerate textual measure on the fact table. |

---

## 3. Core Dimensional Modeling

### 3.1 Business Process
> **Retail Sales Transactions** — a customer purchases one product unit (or more) in a single
> transaction, through a given acquisition channel, at a given date, potentially under a
> promotion campaign and/or promo code.

### 3.2 Grain
> **One row = one product transaction line**
> (one client · one product · one date · one payment method)

### 3.3 Confirmed Dimension List

| ID | Dimension | Entity | Notes |
|----|-----------|--------|-------|
| D1 | DIM_CLIENT | Customer | Includes loyalty segment (manual, snapshot at load time) |
| D2 | DIM_PRODUIT | Product | 3-level hierarchy: Catégorie > Sous-catégorie > Produit |
| D3 | DIM_TEMPS | Date | Full calendar hierarchy + is_holiday flag |
| D4 | DIM_GEOGRAPHIE | Geography | Région > Ville |
| D5 | DIM_CANAL | Acquisition Channel | Where the client was recruited |
| D6 | DIM_CAMPAGNE | Promotion Campaign | Nullable — campaign name (e.g., Ramadan, Black_Friday) |
| D7 | DIM_CODE_PROMO | Promo Code | Nullable — specific code (e.g., PROMO38) — independent of campaign |
| D8 | DIM_PAIEMENT | Payment Method | Flouci, D17, Carte Bancaire, Espèces, Virement, Paiement à la livraison |

### 3.4 Axes of Analysis

| Axis | Dimension | Granularity Levels |
|------|-----------|-------------------|
| Temporel | DIM_TEMPS | Année → Trimestre → Mois → Semaine → Date → Jour |
| Client | DIM_CLIENT | Segment → Groupe d'âge → Genre → Client |
| Géographique | DIM_GEOGRAPHIE | Région → Ville |
| Produit | DIM_PRODUIT | Catégorie → Sous-catégorie → Produit |
| Canal | DIM_CANAL | Canal d'acquisition |
| Campagne | DIM_CAMPAGNE | Nom de campagne |
| Code Promo | DIM_CODE_PROMO | Code promotionnel |
| Paiement | DIM_PAIEMENT | Moyen de paiement |

---

## 4. Bus Matrix (Matrice des Besoins)

| Business Process | D1 Client | D2 Produit | D3 Temps | D4 Géo | D5 Canal | D6 Campagne | D7 Code Promo | D8 Paiement |
|-----------------|:---------:|:----------:|:--------:|:------:|:--------:|:-----------:|:-------------:|:-----------:|
| **Ventes (Transactions)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Satisfaction Post-Achat** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Performance Promotions** | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Analyse Paiements** | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |

*(✅ = dimension is relevant to this process | ❌ = not applicable)*

---

## 5. Hierarchies, Attributes & Measures

### 5.1 Dimension Hierarchies

```
DIM_TEMPS
└── Année (2022 … 2025)
    └── Trimestre (Q1, Q2, Q3, Q4)
        └── Mois_Num (1 … 12) / Mois_Nom (Janvier … Décembre)
            └── Semaine_ISO (numéro de semaine)
                └── Date_Complète (YYYY-MM-DD)
                    ├── Jour_Semaine (Lundi … Dimanche)
                    ├── is_weekend (BOOLEAN)
                    └── is_holiday (BOOLEAN)

DIM_GEOGRAPHIE
└── Région (Grand Tunis | Nord | Centre | Sud)
    └── Ville / Gouvernorat (Ariana, Sfax, Tunis, Tozeur, …)

DIM_PRODUIT
└── Catégorie (Alimentation | Électronique | Sport | Jouets | Beauté | Maison | Vêtements | Livres)
    └── Sous-catégorie (Smartphone | Fitness | Légumes | Poupées | …)
        └── Nom_Produit (Smartphone 1 | Fitness 35 | Poupées 60 | …)

DIM_CLIENT
└── Segment_Fidélité (VIP | Fidèle | Régulier | Occasionnel)
    └── Groupe_Age (18-25 | 25-35 | 35-45 | 45-55 | 55-65 | 65+)
        └── Genre (M | F)
            └── Client (client_id)
```

---

### 5.2 Dimension Table Definitions

#### DIM_CLIENT
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| client_sk | INT (PK surrogate) | 1001 | Warehouse-generated key |
| client_id | VARCHAR (BK) | CLT01848 | Source business key |
| client_name | VARCHAR | Chokri Chaabane | |
| gender | CHAR(1) | M / F | |
| age | INT | 44 | Age at time of export |
| age_group | VARCHAR | 35-45 | Pre-banded in source |
| loyalty_segment | VARCHAR | Fidèle | Manual input by user; VIP / Fidèle / Régulier / Occasionnel |
| registration_date | DATE | 2023-10-27 | |
| days_since_registration | INT | 50 | Computed as of export date |
| acquisition_channel | VARCHAR | Site web | Where the client was originally recruited |

> **Design Note**: Because the ETL is a full reload and `loyalty_segment` is manually assigned,
> no SCD Type 2 is required. The segment value in the fact row is always the value at load time.

---

#### DIM_PRODUIT
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| produit_sk | INT (PK) | 2001 | |
| product_name | VARCHAR | Poupées 60 | Finest grain of product |
| subcategory | VARCHAR | Poupées | |
| category | VARCHAR | Jouets | |
| unit_price | DECIMAL(10,2) | 12905.00 | Snapshot price at time of load |

---

#### DIM_TEMPS
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| temps_sk | INT (PK) | 20231216 | Format YYYYMMDD |
| full_date | DATE | 2023-12-16 | |
| year | INT | 2023 | |
| quarter | CHAR(2) | Q4 | |
| month_num | INT | 12 | |
| month_name | VARCHAR | Décembre | |
| year_month | CHAR(7) | 2023-12 | |
| week_iso | INT | 50 | ISO week number |
| day_of_week | VARCHAR | Samedi | |
| is_weekend | BOOLEAN | TRUE | |
| is_holiday | BOOLEAN | FALSE | Derived from Tunisian public holiday calendar at ETL time |

---

#### DIM_GEOGRAPHIE
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| geo_sk | INT (PK) | 3001 | |
| city | VARCHAR | Tozeur | |
| region | VARCHAR | Sud | Grand Tunis / Nord / Centre / Sud |

---

#### DIM_CANAL
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| canal_sk | INT (PK) | 4001 | |
| channel_name | VARCHAR | Site web | Site web / Application mobile / Magasin physique / Téléphone / Réseaux sociaux |

---

#### DIM_CAMPAGNE
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| campagne_sk | INT (PK) | 5001 | |
| campaign_name | VARCHAR | Ramadan | Soldes_été / Black_Friday / Nouvel_An / Ramadan / Back_to_school / Fête_des_mères |

> **Design Note**: A special "No Campaign" row (campagne_sk = 0, campaign_name = 'Aucune')
> should be inserted to avoid NULL foreign keys in the fact table — a Kimball best practice.

---

#### DIM_CODE_PROMO
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| code_promo_sk | INT (PK) | 6001 | |
| promo_code | VARCHAR | PROMO38 | |

> **Design Note**: Same pattern — insert a "No Code" row (code_promo_sk = 0, promo_code = 'Aucun')
> to replace NULLs in the fact table.

---

#### DIM_PAIEMENT
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| paiement_sk | INT (PK) | 7001 | |
| payment_method | VARCHAR | Flouci | Flouci / D17 / Carte Bancaire / Virement / Espèces / Paiement à la livraison |

---

### 5.3 Fact Table — FAIT_TRANSACTIONS

#### Foreign Keys (constellation links)
| Column | Type | References |
|--------|------|------------|
| temps_sk | INT (FK) | → DIM_TEMPS |
| client_sk | INT (FK) | → DIM_CLIENT |
| produit_sk | INT (FK) | → DIM_PRODUIT |
| geo_sk | INT (FK) | → DIM_GEOGRAPHIE |
| canal_sk | INT (FK) | → DIM_CANAL |
| campagne_sk | INT (FK) | → DIM_CAMPAGNE (0 = Aucune) |
| code_promo_sk | INT (FK) | → DIM_CODE_PROMO (0 = Aucun) |
| paiement_sk | INT (FK) | → DIM_PAIEMENT |

#### Degenerate Dimension
| Column | Type | Notes |
|--------|------|-------|
| transaction_id | VARCHAR | TRX00000001 — kept for traceability; no separate dim table needed |

#### Measures
| Column | Type | Additivity | Description |
|--------|------|-----------|-------------|
| quantity | INT | Fully additive | Number of units purchased |
| unit_price | DECIMAL(10,2) | Non-additive | Price per unit (use AVG, not SUM) |
| discount_amount | DECIMAL(10,2) | Fully additive | Total discount value applied |
| subtotal_HT | DECIMAL(10,2) | Fully additive | Pre-TVA subtotal after discount |
| tva_amount | DECIMAL(10,2) | Fully additive | TVA amount (approx. 15%) |
| revenue_TTC | DECIMAL(10,2) | Fully additive | Final revenue incl. taxes — primary KPI |
| margin_amount | DECIMAL(10,2) | Fully additive | Gross margin |
| discount_pct | DECIMAL(5,2) | Non-additive | Discount rate — use AVG or MAX in reports |
| nps_score | INT (0–10) | Semi-additive | Post-purchase NPS — average is meaningful, sum is not |
| satisfaction_score | INT (1–5) | Semi-additive | Encoded Likert: Très insatisfait=1, Insatisfait=2, Neutre=3, Satisfait=4, Très satisfait=5 |
| feedback_comment | VARCHAR | N/A (textual) | Optional open-text post-purchase comment |

---

## 6. Star Schema — Conceptual Diagram

```
                        DIM_CAMPAGNE
                             │
             DIM_CLIENT      │     DIM_PRODUIT
                  \          │         /
DIM_CANAL ─── FAIT_TRANSACTIONS ─── DIM_TEMPS
                  /          │         \
        DIM_GEOGRAPHIE       │     DIM_PAIEMENT
                             │
                       DIM_CODE_PROMO
```

---

## 7. ETL Notes (Full Reload Pattern)

| Step | Action |
|------|--------|
| 1. Extract | User places export CSV in staging folder |
| 2. Stage | Script reads CSV into staging table |
| 3. Truncate | All DWH dimension and fact tables are truncated |
| 4. Load Dims | Dimensions loaded first (lookup tables populated) |
| 5. Load Fact | FAIT_TRANSACTIONS loaded with surrogate key lookups |
| 6. Validate | Row counts and SUM(revenue_TTC) reconciled against staging |

> **Risk**: Full reload means **no historical comparison** across exports unless the staging
> file always contains the full historical dataset. Clarify with your supervisor whether
> the export is cumulative (all history) or incremental (only new records).