-- Operational KPI views over the OLTP schema. For heavy analytics use the star schema (04_*), not these.

-- Maintenance cost rolled up the asset hierarchy using ltree: everything at or below each asset.
CREATE VIEW v_asset_cost_rollup AS
SELECT a.asset_num,
       a.path,
       COALESCE(SUM(l.line_cost), 0) AS labor_cost,
       COALESCE(SUM(m.line_cost), 0) AS material_cost
  FROM assets a
  LEFT JOIN assets d ON d.path <@ a.path
  LEFT JOIN work_orders w ON w.asset_id = d.id
  LEFT JOIN LATERAL (SELECT SUM(line_cost) AS line_cost FROM labor_transactions WHERE wo_id = w.id) l ON true
  LEFT JOIN LATERAL (SELECT SUM(line_cost) AS line_cost FROM material_transactions WHERE wo_id = w.id) m ON true
 GROUP BY a.asset_num, a.path;

-- Reliability per asset for a period: unplanned downtime → MTTR, MTBF, availability.
CREATE FUNCTION asset_reliability(p_from timestamptz, p_to timestamptz)
RETURNS TABLE (asset_num text, failures bigint, downtime_hours numeric, mttr_hours numeric, mtbf_hours numeric,
               availability numeric)
LANGUAGE sql STABLE AS $$
  WITH period AS (SELECT EXTRACT(EPOCH FROM (p_to - p_from)) / 3600 AS hours),
  d AS (
    SELECT asset_id, COUNT(*) AS failures,
           SUM(EXTRACT(EPOCH FROM (LEAST(ended_at, p_to) - GREATEST(started_at, p_from))) / 3600) AS downtime_hours
      FROM downtime_events
     WHERE NOT planned AND started_at < p_to AND ended_at > p_from
     GROUP BY asset_id
  )
  SELECT a.asset_num,
         COALESCE(d.failures, 0),
         ROUND(COALESCE(d.downtime_hours, 0)::numeric, 2),
         ROUND((d.downtime_hours / NULLIF(d.failures, 0))::numeric, 2),
         ROUND(((period.hours - d.downtime_hours) / NULLIF(d.failures, 0))::numeric, 2),
         ROUND(((period.hours - COALESCE(d.downtime_hours, 0)) / period.hours)::numeric, 4)
    FROM assets a CROSS JOIN period LEFT JOIN d ON d.asset_id = a.id
$$;

-- PM compliance: PM work orders due in a month that were completed within lead tolerance of their due date.
CREATE VIEW v_pm_compliance_monthly AS
SELECT date_trunc('month', w.target_start)::date AS month,
       COUNT(*) AS pm_due,
       COUNT(*) FILTER (WHERE w.actual_finish IS NOT NULL
                          AND w.actual_finish::date <= w.target_start + p.lead_days) AS pm_on_time,
       ROUND(COUNT(*) FILTER (WHERE w.actual_finish IS NOT NULL
                                AND w.actual_finish::date <= w.target_start + p.lead_days)::numeric / COUNT(*), 2)
         AS compliance
  FROM work_orders w JOIN pm_schedules p ON p.id = w.pm_id
 WHERE w.work_type = 'PM' AND w.status <> 'CANCELLED'
 GROUP BY 1;

-- Backlog: open, approved work in estimated hours per craft.
CREATE VIEW v_backlog AS
SELECT COALESCE(jp.craft_code, 'UNPLANNED') AS craft,
       COUNT(*) AS open_work_orders,
       SUM(COALESCE(w.estimated_hours, jp.estimated_hours, 0)) AS estimated_hours
  FROM work_orders w LEFT JOIN job_plans jp ON jp.id = w.job_plan_id
 WHERE w.status IN ('APPROVED', 'PLANNED', 'WAITING_MATERIAL', 'SCHEDULED', 'ON_HOLD')
 GROUP BY 1;

-- Items at or below their reorder point (available = on hand − reserved).
CREATE VIEW v_reorder_required AS
SELECT b.item_num, s.code AS storeroom, b.on_hand - b.reserved AS available, b.reorder_point, b.reorder_qty
  FROM inventory_balances b JOIN storerooms s ON s.id = b.storeroom_id
 WHERE b.on_hand - b.reserved <= b.reorder_point;
