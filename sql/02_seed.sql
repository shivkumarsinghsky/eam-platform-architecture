-- Small illustrative data set: one site, a boiler feedwater system and an HVAC unit.
INSERT INTO organizations (code, name) VALUES ('ORG1', 'Example Utilities');
INSERT INTO sites (org_id, code, name, timezone) VALUES (1, 'SITE01', 'North Plant', 'Europe/Berlin');

INSERT INTO locations (site_id, code, name, path) VALUES
  (1, 'SITE01', 'North Plant', 'SITE01'),
  (1, 'BOILER', 'Boiler House', 'SITE01.BOILER'),
  (1, 'FW', 'Feedwater System', 'SITE01.BOILER.FW'),
  (1, 'HVAC', 'HVAC', 'SITE01.HVAC');

INSERT INTO vendors (code, name) VALUES ('ACME-PUMPS', 'Acme Pumps'), ('COOLAIR', 'CoolAir Services');
INSERT INTO asset_classes (code, description) VALUES
  ('PUMP', 'Centrifugal pump'), ('MOTOR', 'Electric motor'), ('AHU', 'Air handling unit');

INSERT INTO assets (site_id, asset_num, description, class_code, location_id, parent_asset_id, path, criticality,
                    manufacturer, model, install_date, purchase_cost, vendor_id) VALUES
  (1, 'P101', 'Boiler feed pump 101', 'PUMP', 3, NULL, 'SITE01.BOILER.FW.P101', 'A', 'Acme', 'BFP-400', '2019-05-01', 85000, 1),
  (1, 'M101', 'Motor for P101', 'MOTOR', 3, 1, 'SITE01.BOILER.FW.P101.M101', 'A', 'Acme', 'M-250kW', '2019-05-01', 32000, 1),
  (1, 'P102', 'Boiler feed pump 102 (standby)', 'PUMP', 3, NULL, 'SITE01.BOILER.FW.P102', 'B', 'Acme', 'BFP-400', '2019-05-01', 85000, 1),
  (1, 'AHU1', 'Air handling unit 1', 'AHU', 4, NULL, 'SITE01.HVAC.AHU1', 'C', 'CoolAir', 'AH-20', '2021-03-15', 41000, 2);

INSERT INTO meters (asset_id, name, unit, meter_type) VALUES (1, 'RUNHOURS', 'h', 'CONTINUOUS'), (1, 'VIBRATION', 'mm/s', 'GAUGE');

INSERT INTO failure_codes (code, code_type, parent_code, description) VALUES
  ('PUMPS', 'CLASS', NULL, 'Pump failures'),
  ('LEAK', 'PROBLEM', 'PUMPS', 'External leakage'),
  ('VIB', 'PROBLEM', 'PUMPS', 'Excessive vibration'),
  ('SEAL-WEAR', 'CAUSE', 'LEAK', 'Mechanical seal wear'),
  ('BRG-WEAR', 'CAUSE', 'VIB', 'Bearing wear'),
  ('REPLACE', 'REMEDY', NULL, 'Replace component');

INSERT INTO crafts (code, hourly_rate) VALUES ('MECH', 60), ('ELEC', 70);
INSERT INTO labor (site_id, code, name, craft_code) VALUES (1, 'T07', 'Technician 7', 'MECH'), (1, 'T11', 'Technician 11', 'ELEC');

INSERT INTO items (item_num, description, unit) VALUES ('SEAL-KIT-40', 'Mechanical seal kit 40mm', 'EA'), ('BRG-6310', 'Bearing 6310', 'EA'), ('FLT-AHU', 'AHU filter set', 'SET');
INSERT INTO storerooms (site_id, code) VALUES (1, 'MAIN');
INSERT INTO inventory_balances (item_num, storeroom_id, on_hand, reorder_point, reorder_qty, avg_unit_cost) VALUES
  ('SEAL-KIT-40', 1, 2, 2, 4, 120), ('BRG-6310', 1, 6, 2, 6, 45), ('FLT-AHU', 1, 1, 3, 6, 80);

INSERT INTO job_plans (code, description, estimated_hours, craft_code) VALUES
  ('JP-PUMP-90D', 'Pump quarterly inspection', 2, 'MECH'), ('JP-AHU-FILTER', 'Replace AHU filters', 1, 'MECH');
INSERT INTO job_plan_materials VALUES (2, 'FLT-AHU', 1);

INSERT INTO pm_schedules (code, asset_id, job_plan_id, schedule_type, frequency_days, lead_days, start_date, last_due, last_completed) VALUES
  ('PM-P101-90D', 1, 1, 'FLOATING', 90, 7, '2026-01-05', '2026-04-05', '2026-04-08'),
  ('PM-AHU1-30D', 4, 2, 'FIXED', 30, 3, '2026-01-01', '2026-08-29', '2026-08-30');

-- Work history (2026): three pump failures and PM work.
INSERT INTO work_orders (wo_num, site_id, asset_id, work_type, status, priority, description, reported_at, actual_start,
                         actual_finish, assigned_labor_id, problem_code, cause_code, remedy_code, target_start, pm_id) VALUES
  ('WO-1001', 1, 1, 'CM', 'CLOSED', 1, 'Seal leak on P101', '2026-02-10 06:00+00', '2026-02-10 07:00+00', '2026-02-10 11:00+00', 1, 'LEAK', 'SEAL-WEAR', 'REPLACE', NULL, NULL),
  ('WO-1002', 1, 1, 'CM', 'CLOSED', 2, 'High vibration P101', '2026-05-20 09:00+00', '2026-05-20 10:00+00', '2026-05-20 16:00+00', 1, 'VIB', 'BRG-WEAR', 'REPLACE', NULL, NULL),
  ('WO-1003', 1, 1, 'EM', 'CLOSED', 1, 'Seal failure P101', '2026-08-01 02:00+00', '2026-08-01 02:30+00', '2026-08-01 04:30+00', 1, 'LEAK', 'SEAL-WEAR', 'REPLACE', NULL, NULL),
  ('WO-1004', 1, 1, 'PM', 'CLOSED', 3, 'P101 quarterly inspection', '2026-03-29 00:00+00', '2026-04-08 08:00+00', '2026-04-08 10:00+00', 1, NULL, NULL, NULL, '2026-04-05', 1),
  ('WO-1005', 1, 4, 'PM', 'CLOSED', 4, 'AHU1 filters', '2026-08-26 00:00+00', '2026-08-30 08:00+00', '2026-08-30 09:00+00', 1, NULL, NULL, NULL, '2026-08-29', 2),
  ('WO-1006', 1, 1, 'PM', 'SCHEDULED', 3, 'P101 quarterly inspection', '2026-06-30 00:00+00', NULL, NULL, 1, NULL, NULL, NULL, '2026-07-07', 1),
  ('WO-1007', 1, 4, 'CM', 'WAITING_MATERIAL', 3, 'AHU1 fan belt noise', '2026-09-20 10:00+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
UPDATE work_orders SET estimated_hours = 4 WHERE wo_num IN ('WO-1006', 'WO-1007');

INSERT INTO labor_transactions (wo_id, labor_id, craft_code, work_date, hours, rate) VALUES
  (1, 1, 'MECH', '2026-02-10', 4, 60), (2, 1, 'MECH', '2026-05-20', 6, 60), (2, 2, 'ELEC', '2026-05-20', 1, 70),
  (3, 1, 'MECH', '2026-08-01', 2, 60), (4, 1, 'MECH', '2026-04-08', 2, 60), (5, 1, 'MECH', '2026-08-30', 1, 60);

INSERT INTO material_transactions (wo_id, item_num, storeroom_id, issued_at, quantity, unit_cost) VALUES
  (1, 'SEAL-KIT-40', 1, '2026-02-10 07:30+00', 1, 120), (2, 'BRG-6310', 1, '2026-05-20 11:00+00', 2, 45),
  (3, 'SEAL-KIT-40', 1, '2026-08-01 03:00+00', 1, 120), (5, 'FLT-AHU', 1, '2026-08-30 08:10+00', 1, 80);

INSERT INTO downtime_events (asset_id, started_at, ended_at, planned, wo_id) VALUES
  (1, '2026-02-10 06:00+00', '2026-02-10 11:00+00', false, 1),
  (1, '2026-05-20 09:00+00', '2026-05-20 16:00+00', false, 2),
  (1, '2026-08-01 02:00+00', '2026-08-01 04:30+00', false, 3),
  (1, '2026-04-08 08:00+00', '2026-04-08 10:00+00', true, 4);

INSERT INTO contracts (contract_num, vendor_id, contract_type, starts_on, ends_on) VALUES
  ('W-ACME-2019', 1, 'WARRANTY', '2019-05-01', '2024-04-30'), ('S-COOLAIR-26', 2, 'SERVICE', '2026-01-01', '2026-12-31');
INSERT INTO contract_assets VALUES (1, 1), (1, 2), (2, 4);
