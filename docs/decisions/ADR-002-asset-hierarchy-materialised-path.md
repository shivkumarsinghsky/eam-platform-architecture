# ADR-002: Asset Hierarchy as Materialised Path (`ltree`)

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

Most EAM questions are hierarchical: cost of everything in the feedwater system, open work below a boiler,
criticality inherited from a parent system. Hierarchies are 4–8 levels deep and change rarely compared to how
often they are queried.

## Decision

Store `parent_asset_id` as the authoritative relationship and a derived `path ltree` column with a GiST index on
assets and locations. Subtree queries use `path <@ 'SITE01.BOILER'`; moves update the paths of the moved subtree
in one transaction and emit `asset.moved`.

## Alternatives Considered

- **Adjacency list only** — recursive CTEs on every roll-up; fine for small sites, slow for dashboards.
- **Closure table** — fast reads, but moves rewrite O(subtree × depth) rows and the table grows quadratically
  with depth.
- **Nested sets** — fast reads, expensive inserts and moves.

## Trade-offs

`ltree` is PostgreSQL-specific (other databases: a `varchar` path with prefix `LIKE` and a b-tree index). Path
labels must be valid `ltree` labels (asset numbers sanitised).

## Consequences

The Python model (`eam.hierarchy`) mirrors the same materialised-path approach for roll-ups and criticality
inheritance, and the SQL view `v_asset_cost_rollup` uses `<@`.
