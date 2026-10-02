-- Enterprise Asset Management — operational (OLTP) reference schema for PostgreSQL 14+.
-- Organised by bounded context; in a service-based deployment each section is owned by one service.
-- See docs/07-database-design.md for the reasoning behind the main choices.

CREATE EXTENSION IF NOT EXISTS ltree;

-- ============================================================================ Organisation & sites
CREATE TABLE organizations (
  id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL
);

CREATE TABLE sites (
  id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  org_id   bigint NOT NULL REFERENCES organizations (id),
  code     text   NOT NULL UNIQUE,
  name     text   NOT NULL,
  timezone text   NOT NULL DEFAULT 'UTC'
);

-- ============================================================================ Asset registry
-- Functional locations: where something is installed (a position in the process), independent of the
-- physical asset currently fulfilling it. Swapping a pump keeps the location's history intact.
CREATE TABLE locations (
  id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  site_id bigint NOT NULL REFERENCES sites (id),
  code    text   NOT NULL,
  name    text   NOT NULL,
  path    ltree  NOT NULL,              -- e.g. SITE01.BOILER.FW
  UNIQUE (site_id, code)
);
CREATE INDEX locations_path_gist ON locations USING gist (path);

CREATE TABLE vendors (
  id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL
);

CREATE TABLE asset_classes (
  code        text PRIMARY KEY,           -- PUMP, MOTOR, HVAC-AHU ...
  description text NOT NULL
);

CREATE TABLE assets (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  site_id         bigint NOT NULL REFERENCES sites (id),
  asset_num       text   NOT NULL,
  description     text   NOT NULL,
  class_code      text   NOT NULL REFERENCES asset_classes (code),
  location_id     bigint REFERENCES locations (id),
  parent_asset_id bigint REFERENCES assets (id),
  path            ltree  NOT NULL,        -- asset hierarchy, e.g. SITE01.BOILER.FW.P101.M101
  criticality     char(1) NOT NULL DEFAULT 'C' CHECK (criticality IN ('A', 'B', 'C')),
  lifecycle_status text  NOT NULL DEFAULT 'OPERATING'
                  CHECK (lifecycle_status IN ('PLANNED', 'COMMISSIONING', 'OPERATING', 'NOT_READY', 'DECOMMISSIONED', 'DISPOSED')),
  manufacturer    text,
  model           text,
  serial_number   text,
  install_date    date,
  purchase_cost   numeric(14, 2),
  vendor_id       bigint REFERENCES vendors (id),
  UNIQUE (site_id, asset_num)
);
CREATE INDEX assets_path_gist ON assets USING gist (path);
CREATE INDEX assets_location ON assets (location_id);

-- Meters: running hours, cycles (continuous, ever-increasing) or gauges (temperature, vibration).
CREATE TABLE meters (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  asset_id   bigint NOT NULL REFERENCES assets (id),
  name       text   NOT NULL,
  unit       text   NOT NULL,
  meter_type text   NOT NULL CHECK (meter_type IN ('CONTINUOUS', 'GAUGE')),
  UNIQUE (asset_id, name)
);

-- High-volume readings are usually summarised here from the monitoring platform (raw telemetry stays in a
-- time-series store). Partition by month in production.
CREATE TABLE meter_readings (
  meter_id   bigint      NOT NULL REFERENCES meters (id),
  reading_at timestamptz NOT NULL,
  value      double precision NOT NULL,
  source     text        NOT NULL DEFAULT 'MANUAL',   -- MANUAL | IOT
  PRIMARY KEY (meter_id, reading_at)
);

-- ============================================================================ Failure analysis
-- Hierarchical failure codes: class → problem → cause → remedy.
CREATE TABLE failure_codes (
  code        text PRIMARY KEY,
  code_type   text NOT NULL CHECK (code_type IN ('CLASS', 'PROBLEM', 'CAUSE', 'REMEDY')),
  parent_code text REFERENCES failure_codes (code),
  description text NOT NULL
);

-- ============================================================================ Workforce
CREATE TABLE crafts (
  code        text PRIMARY KEY,           -- MECH, ELEC, INST ...
  hourly_rate numeric(10, 2) NOT NULL
);

CREATE TABLE labor (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  site_id    bigint NOT NULL REFERENCES sites (id),
  code       text   NOT NULL UNIQUE,
  name       text   NOT NULL,
  craft_code text   NOT NULL REFERENCES crafts (code)
);

-- ============================================================================ Inventory
CREATE TABLE items (
  item_num    text PRIMARY KEY,
  description text NOT NULL,
  unit        text NOT NULL
);

CREATE TABLE storerooms (
  id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  site_id bigint NOT NULL REFERENCES sites (id),
  code    text   NOT NULL,
  UNIQUE (site_id, code)
);

CREATE TABLE inventory_balances (
  item_num      text    NOT NULL REFERENCES items (item_num),
  storeroom_id  bigint  NOT NULL REFERENCES storerooms (id),
  on_hand       numeric(12, 2) NOT NULL DEFAULT 0 CHECK (on_hand >= 0),
  reserved      numeric(12, 2) NOT NULL DEFAULT 0 CHECK (reserved >= 0),
  reorder_point numeric(12, 2) NOT NULL DEFAULT 0,
  reorder_qty   numeric(12, 2) NOT NULL DEFAULT 0,
  avg_unit_cost numeric(12, 4) NOT NULL DEFAULT 0,
  PRIMARY KEY (item_num, storeroom_id)
);

-- ============================================================================ Maintenance planning
CREATE TABLE job_plans (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code            text   NOT NULL UNIQUE,
  description     text   NOT NULL,
  estimated_hours numeric(8, 2) NOT NULL,
  craft_code      text   NOT NULL REFERENCES crafts (code)
);

CREATE TABLE job_plan_materials (
  job_plan_id bigint NOT NULL REFERENCES job_plans (id),
  item_num    text   NOT NULL REFERENCES items (item_num),
  quantity    numeric(12, 2) NOT NULL,
  PRIMARY KEY (job_plan_id, item_num)
);

CREATE TABLE pm_schedules (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code           text   NOT NULL UNIQUE,
  asset_id       bigint NOT NULL REFERENCES assets (id),
  job_plan_id    bigint NOT NULL REFERENCES job_plans (id),
  schedule_type  text   NOT NULL CHECK (schedule_type IN ('FIXED', 'FLOATING')),
  frequency_days integer CHECK (frequency_days > 0),
  meter_id       bigint REFERENCES meters (id),
  meter_interval double precision CHECK (meter_interval > 0),
  lead_days      integer NOT NULL DEFAULT 7,
  start_date     date    NOT NULL,
  last_due       date,
  last_completed date,
  last_completed_meter double precision,
  active         boolean NOT NULL DEFAULT true,
  CHECK (frequency_days IS NOT NULL OR (meter_id IS NOT NULL AND meter_interval IS NOT NULL))
);

-- ============================================================================ Work management
CREATE TABLE work_orders (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  wo_num         text   NOT NULL UNIQUE,
  site_id        bigint NOT NULL REFERENCES sites (id),
  asset_id       bigint REFERENCES assets (id),
  location_id    bigint REFERENCES locations (id),
  work_type      text   NOT NULL CHECK (work_type IN ('CM', 'PM', 'PdM', 'INSP', 'EM')),
  status         text   NOT NULL CHECK (status IN ('REQUESTED', 'APPROVED', 'PLANNED', 'WAITING_MATERIAL', 'SCHEDULED',
                                                    'IN_PROGRESS', 'ON_HOLD', 'COMPLETED', 'CLOSED', 'CANCELLED')),
  priority       smallint NOT NULL CHECK (priority BETWEEN 1 AND 5),
  description    text   NOT NULL,
  pm_id          bigint REFERENCES pm_schedules (id),
  job_plan_id    bigint REFERENCES job_plans (id),
  parent_wo_id   bigint REFERENCES work_orders (id),
  reported_at    timestamptz NOT NULL DEFAULT now(),
  target_start   date,
  target_finish  date,
  actual_start   timestamptz,
  actual_finish  timestamptz,
  assigned_labor_id bigint REFERENCES labor (id),
  problem_code   text REFERENCES failure_codes (code),
  cause_code     text REFERENCES failure_codes (code),
  remedy_code    text REFERENCES failure_codes (code),
  estimated_hours numeric(8, 2),
  CHECK (work_type NOT IN ('CM', 'EM') OR status NOT IN ('COMPLETED', 'CLOSED') OR problem_code IS NOT NULL),
  CHECK (asset_id IS NOT NULL OR location_id IS NOT NULL)
);
-- PM generation is idempotent: one work order per PM occurrence.
CREATE UNIQUE INDEX work_orders_pm_occurrence ON work_orders (pm_id, target_start) WHERE pm_id IS NOT NULL;
CREATE INDEX work_orders_open ON work_orders (site_id, status) WHERE status NOT IN ('CLOSED', 'CANCELLED');
CREATE INDEX work_orders_asset ON work_orders (asset_id, reported_at);

CREATE TABLE work_order_status_history (
  wo_id      bigint      NOT NULL REFERENCES work_orders (id),
  status     text        NOT NULL,
  changed_at timestamptz NOT NULL DEFAULT now(),
  changed_by text        NOT NULL,
  note       text
);
CREATE INDEX wo_status_history_wo ON work_order_status_history (wo_id, changed_at);

CREATE TABLE labor_transactions (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  wo_id      bigint NOT NULL REFERENCES work_orders (id),
  labor_id   bigint NOT NULL REFERENCES labor (id),
  craft_code text   NOT NULL REFERENCES crafts (code),
  work_date  date   NOT NULL,
  hours      numeric(6, 2) NOT NULL CHECK (hours > 0),
  rate       numeric(10, 2) NOT NULL,
  line_cost  numeric(12, 2) GENERATED ALWAYS AS (hours * rate) STORED
);

CREATE TABLE material_transactions (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  wo_id        bigint NOT NULL REFERENCES work_orders (id),
  item_num     text   NOT NULL REFERENCES items (item_num),
  storeroom_id bigint NOT NULL REFERENCES storerooms (id),
  issued_at    timestamptz NOT NULL DEFAULT now(),
  quantity     numeric(12, 2) NOT NULL,          -- negative = return to store
  unit_cost    numeric(12, 4) NOT NULL,
  line_cost    numeric(14, 2) GENERATED ALWAYS AS (quantity * unit_cost) STORED
);

-- Downtime is recorded separately from work orders: one outage may span several work orders and vice versa.
CREATE TABLE downtime_events (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  asset_id   bigint      NOT NULL REFERENCES assets (id),
  started_at timestamptz NOT NULL,
  ended_at   timestamptz,
  planned    boolean     NOT NULL,
  wo_id      bigint REFERENCES work_orders (id),
  CHECK (ended_at IS NULL OR ended_at > started_at)
);

-- ============================================================================ Contracts & vendors
CREATE TABLE contracts (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  contract_num  text   NOT NULL UNIQUE,
  vendor_id     bigint NOT NULL REFERENCES vendors (id),
  contract_type text   NOT NULL CHECK (contract_type IN ('SERVICE', 'WARRANTY', 'LEASE', 'PURCHASE')),
  starts_on     date   NOT NULL,
  ends_on       date   NOT NULL,
  CHECK (ends_on >= starts_on)
);

CREATE TABLE contract_assets (
  contract_id bigint NOT NULL REFERENCES contracts (id),
  asset_id    bigint NOT NULL REFERENCES assets (id),
  PRIMARY KEY (contract_id, asset_id)
);
