-- Example analytical queries against the star schema (used by dashboards).

-- 1. Maintenance cost by asset class and work type for a year.
-- name: cost_by_class_and_work_type
SELECT da.asset_class, f.work_type, SUM(f.labor_cost + f.material_cost) AS total_cost
  FROM dw.fact_work_order f
  JOIN dw.dim_asset da ON da.asset_key = f.asset_key
  JOIN dw.dim_date d ON d.date_key = f.reported_date_key
 WHERE d.year = 2026
 GROUP BY 1, 2
 ORDER BY 1, 2;

-- 2. Planned vs. unplanned labor hours (planned maintenance percentage).
-- name: planned_maintenance_percentage
SELECT ROUND(SUM(fl.hours) FILTER (WHERE wt.is_planned) / SUM(fl.hours), 4) AS planned_pct
  FROM dw.fact_labor fl JOIN dw.dim_work_type wt ON wt.work_type = fl.work_type;

-- 3. Top failure modes (problem/cause) by count and downtime.
-- name: top_failure_modes
SELECT df.problem_code, df.cause_code, COUNT(*) AS failures, SUM(fd.hours) AS downtime_hours
  FROM dw.fact_work_order f
  JOIN dw.dim_failure df ON df.failure_key = f.failure_key
  LEFT JOIN dw.fact_downtime fd ON fd.wo_id = f.wo_id AND NOT fd.planned
 GROUP BY 1, 2
 ORDER BY failures DESC, downtime_hours DESC;

-- 4. MTTR by criticality (unplanned downtime only).
-- name: mttr_by_criticality
SELECT da.criticality, ROUND(AVG(fd.hours), 2) AS mttr_hours, COUNT(*) AS failures
  FROM dw.fact_downtime fd JOIN dw.dim_asset da ON da.asset_key = fd.asset_key
 WHERE NOT fd.planned
 GROUP BY 1
 ORDER BY 1;
