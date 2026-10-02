-- Illustrative batch load from OLTP to the star schema. A production pipeline would be incremental (CDC or
-- updated_at watermarks) and handle SCD2 changes; this full load shows the transformations.

INSERT INTO dw.dim_date
SELECT to_char(d, 'YYYYMMDD')::int, d::date, EXTRACT(YEAR FROM d), EXTRACT(QUARTER FROM d), EXTRACT(MONTH FROM d),
       EXTRACT(WEEK FROM d), EXTRACT(ISODOW FROM d), EXTRACT(ISODOW FROM d) IN (6, 7)
  FROM generate_series('2025-01-01'::date, '2027-12-31'::date, interval '1 day') AS d;

INSERT INTO dw.dim_work_type VALUES
  ('CM', 'Corrective', false), ('EM', 'Emergency', false), ('PM', 'Preventive', true),
  ('PdM', 'Predictive', true), ('INSP', 'Inspection', true);

INSERT INTO dw.dim_craft SELECT code FROM crafts;

INSERT INTO dw.dim_failure (problem_code, cause_code, remedy_code)
SELECT DISTINCT problem_code, cause_code, remedy_code FROM work_orders
 WHERE problem_code IS NOT NULL AND cause_code IS NOT NULL AND remedy_code IS NOT NULL;

INSERT INTO dw.dim_asset (asset_id, asset_num, description, asset_class, criticality, site_code, location_path,
                          hierarchy_path, valid_from)
SELECT a.id, a.asset_num, a.description, a.class_code, a.criticality, s.code, l.path::text, a.path::text,
       COALESCE(a.install_date, '2000-01-01')
  FROM assets a JOIN sites s ON s.id = a.site_id LEFT JOIN locations l ON l.id = a.location_id;

INSERT INTO dw.fact_work_order
SELECT w.id, w.wo_num, da.asset_key, w.work_type, df.failure_key,
       to_char(w.reported_at, 'YYYYMMDD')::int,
       to_char(w.actual_finish, 'YYYYMMDD')::int,
       w.status, w.priority,
       COALESCE(l.hours, 0), COALESCE(l.cost, 0), COALESCE(m.cost, 0),
       ROUND((EXTRACT(EPOCH FROM (w.actual_start - w.reported_at)) / 3600)::numeric, 2),
       ROUND((EXTRACT(EPOCH FROM (w.actual_finish - w.actual_start)) / 3600)::numeric, 2)
  FROM work_orders w
  JOIN dw.dim_asset da ON da.asset_id = w.asset_id AND da.is_current
  LEFT JOIN dw.dim_failure df ON (df.problem_code, df.cause_code, df.remedy_code) = (w.problem_code, w.cause_code, w.remedy_code)
  LEFT JOIN (SELECT wo_id, SUM(hours) AS hours, SUM(line_cost) AS cost FROM labor_transactions GROUP BY wo_id) l ON l.wo_id = w.id
  LEFT JOIN (SELECT wo_id, SUM(line_cost) AS cost FROM material_transactions GROUP BY wo_id) m ON m.wo_id = w.id;

INSERT INTO dw.fact_labor
SELECT t.id, t.wo_id, da.asset_key, to_char(t.work_date, 'YYYYMMDD')::int, t.craft_code, w.work_type, t.hours, t.line_cost
  FROM labor_transactions t
  JOIN work_orders w ON w.id = t.wo_id
  JOIN dw.dim_asset da ON da.asset_id = w.asset_id AND da.is_current;

INSERT INTO dw.fact_downtime
SELECT e.id, da.asset_key, to_char(e.started_at, 'YYYYMMDD')::int, e.planned,
       ROUND((EXTRACT(EPOCH FROM (e.ended_at - e.started_at)) / 3600)::numeric, 2), e.wo_id
  FROM downtime_events e JOIN dw.dim_asset da ON da.asset_id = e.asset_id AND da.is_current
 WHERE e.ended_at IS NOT NULL;
