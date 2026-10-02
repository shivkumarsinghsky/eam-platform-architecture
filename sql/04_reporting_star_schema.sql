-- Reporting warehouse (star schema) for maintenance analytics, in a separate `dw` schema.
-- In production this lives in a warehouse (PostgreSQL replica, Snowflake, BigQuery, Synapse ...) fed by CDC;
-- the shapes are the same. See docs/09-reporting-architecture.md.

CREATE SCHEMA dw;

CREATE TABLE dw.dim_date (
  date_key    integer PRIMARY KEY,            -- yyyymmdd
  full_date   date    NOT NULL UNIQUE,
  year        smallint NOT NULL,
  quarter     smallint NOT NULL,
  month       smallint NOT NULL,
  iso_week    smallint NOT NULL,
  day_of_week smallint NOT NULL,
  is_weekend  boolean  NOT NULL
);

-- Slowly changing dimension type 2: an asset's criticality or location changes are kept as history, so
-- last year's costs are reported against last year's criticality.
CREATE TABLE dw.dim_asset (
  asset_key     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  asset_id      bigint  NOT NULL,              -- business key from OLTP
  asset_num     text    NOT NULL,
  description   text    NOT NULL,
  asset_class   text    NOT NULL,
  criticality   char(1) NOT NULL,
  site_code     text    NOT NULL,
  location_path text,
  hierarchy_path text   NOT NULL,
  valid_from    date    NOT NULL,
  valid_to      date    NOT NULL DEFAULT '9999-12-31',
  is_current    boolean NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX dim_asset_current ON dw.dim_asset (asset_id) WHERE is_current;

CREATE TABLE dw.dim_failure (
  failure_key  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  problem_code text NOT NULL,
  cause_code   text NOT NULL,
  remedy_code  text NOT NULL,
  UNIQUE (problem_code, cause_code, remedy_code)
);

CREATE TABLE dw.dim_work_type (
  work_type   text PRIMARY KEY,
  description text NOT NULL,
  is_planned  boolean NOT NULL
);

CREATE TABLE dw.dim_craft (
  craft_code text PRIMARY KEY
);

-- Fact: one row per work order (accumulating snapshot: milestones are filled in as the WO progresses).
CREATE TABLE dw.fact_work_order (
  wo_id              bigint PRIMARY KEY,
  wo_num             text   NOT NULL,
  asset_key          bigint NOT NULL REFERENCES dw.dim_asset (asset_key),
  work_type          text   NOT NULL REFERENCES dw.dim_work_type (work_type),
  failure_key        integer REFERENCES dw.dim_failure (failure_key),
  reported_date_key  integer NOT NULL REFERENCES dw.dim_date (date_key),
  completed_date_key integer REFERENCES dw.dim_date (date_key),
  status             text   NOT NULL,
  priority           smallint NOT NULL,
  labor_hours        numeric(10, 2) NOT NULL DEFAULT 0,
  labor_cost         numeric(14, 2) NOT NULL DEFAULT 0,
  material_cost      numeric(14, 2) NOT NULL DEFAULT 0,
  response_hours     numeric(10, 2),          -- reported → actual start
  repair_hours       numeric(10, 2)           -- actual start → actual finish
);

-- Fact: labor transactions (transaction grain) for craft utilisation and planned-vs-unplanned analysis.
CREATE TABLE dw.fact_labor (
  labor_txn_id bigint PRIMARY KEY,
  wo_id        bigint NOT NULL,
  asset_key    bigint NOT NULL REFERENCES dw.dim_asset (asset_key),
  date_key     integer NOT NULL REFERENCES dw.dim_date (date_key),
  craft_code   text   NOT NULL REFERENCES dw.dim_craft (craft_code),
  work_type    text   NOT NULL REFERENCES dw.dim_work_type (work_type),
  hours        numeric(8, 2) NOT NULL,
  cost         numeric(12, 2) NOT NULL
);

-- Fact: downtime events, for availability, MTTR and MTBF by any dimension.
CREATE TABLE dw.fact_downtime (
  downtime_id    bigint PRIMARY KEY,
  asset_key      bigint  NOT NULL REFERENCES dw.dim_asset (asset_key),
  start_date_key integer NOT NULL REFERENCES dw.dim_date (date_key),
  planned        boolean NOT NULL,
  hours          numeric(10, 2) NOT NULL,
  wo_id          bigint
);
