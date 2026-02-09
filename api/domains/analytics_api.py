from datetime import date
from typing import Any, Optional

from fastapi import Depends, HTTPException

from .analytics_models import (
    AuditAnalyticsOut,
    AuditItemOut,
    RepeatCustomersOut,
    SalesAnalyticsByType,
    SalesAnalyticsOut,
    SalesAnalyticsPoint,
    SalesAnalyticsTotals,
    SourceAnalyticsItem,
    SourcesAnalyticsOut,
)


def mount_analytics_routes(app, *, DB_DSN, get_current_user, q1, qall, psycopg):
    @app.get("/analytics/sales", response_model=SalesAnalyticsOut)
    def analytics_sales(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        deal_type_code: Optional[str] = None,
        region_code: Optional[str] = None,
        source_id: Optional[int] = None,
        user=Depends(get_current_user),
    ):
        params: list[Any] = []
        filters = ["activity_at IS NOT NULL", "status_code = 'confirmed'"]

        if deal_type_code:
            filters.append("deal_type_code = %s")
            params.append(deal_type_code)
        if region_code:
            filters.append("region_code = %s")
            params.append(region_code)
        if source_id:
            filters.append("source_id = %s")
            params.append(source_id)
        if date_from:
            filters.append("activity_at::date >= %s")
            params.append(date_from)
        if date_to:
            filters.append("activity_at::date <= %s")
            params.append(date_to)

        where_sql = " AND ".join(filters)

        with psycopg.connect(DB_DSN) as conn:
            totals_row = q1(conn, f"""
                WITH base AS (
                    SELECT
                      d.deal_type_code,
                      d.status_code,
                      COALESCE(rd.code, ra.code) AS region_code,
                      COALESCE(rd.purchase_cost_rate, ra.purchase_cost_rate, 1.0) AS rate,
                      c.source_id,
                      di.price,
                      di.purchase_cost,
                      di.qty,
                      CASE
                        WHEN d.deal_type_code = 'sale' THEN d.completed_at
                        ELSE COALESCE(di.purchase_at, d.created_at)
                      END AS activity_at
                    FROM app.deal_items di
                    JOIN app.deals d ON d.deal_id = di.deal_id
                    LEFT JOIN app.accounts a ON a.account_id = di.account_id
                    LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                    LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                    LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                )
                SELECT
                  COALESCE(SUM(price * qty), 0) AS revenue,
                  COALESCE(SUM(purchase_cost * qty * rate), 0) AS purchase_cost,
                  COUNT(*) AS count
                FROM base
                WHERE {where_sql}
            """, params)

            revenue = float(totals_row[0] or 0) if totals_row else 0.0
            purchase_cost = float(totals_row[1] or 0) if totals_row else 0.0
            count = int(totals_row[2] or 0) if totals_row else 0
            margin = revenue - purchase_cost
            avg_check = (revenue / count) if count else 0.0

            by_day_rows = qall(conn, f"""
                WITH base AS (
                    SELECT
                      d.deal_type_code,
                      d.status_code,
                      COALESCE(rd.code, ra.code) AS region_code,
                      COALESCE(rd.purchase_cost_rate, ra.purchase_cost_rate, 1.0) AS rate,
                      c.source_id,
                      di.price,
                      di.purchase_cost,
                      di.qty,
                      CASE
                        WHEN d.deal_type_code = 'sale' THEN d.completed_at
                        ELSE COALESCE(di.purchase_at, d.created_at)
                      END AS activity_at
                    FROM app.deal_items di
                    JOIN app.deals d ON d.deal_id = di.deal_id
                    LEFT JOIN app.accounts a ON a.account_id = di.account_id
                    LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                    LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                    LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                )
                SELECT
                  activity_at::date AS day,
                  COALESCE(SUM(price * qty), 0) AS revenue,
                  COALESCE(SUM(purchase_cost * qty * rate), 0) AS purchase_cost,
                  COUNT(*) AS count
                FROM base
                WHERE {where_sql}
                GROUP BY day
                ORDER BY day
            """, params)

            by_type_rows = qall(conn, f"""
                WITH base AS (
                    SELECT
                      d.deal_type_code,
                      d.status_code,
                      COALESCE(rd.code, ra.code) AS region_code,
                      COALESCE(rd.purchase_cost_rate, ra.purchase_cost_rate, 1.0) AS rate,
                      c.source_id,
                      di.price,
                      di.purchase_cost,
                      di.qty,
                      CASE
                        WHEN d.deal_type_code = 'sale' THEN d.completed_at
                        ELSE COALESCE(di.purchase_at, d.created_at)
                      END AS activity_at
                    FROM app.deal_items di
                    JOIN app.deals d ON d.deal_id = di.deal_id
                    LEFT JOIN app.accounts a ON a.account_id = di.account_id
                    LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                    LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                    LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                )
                SELECT
                  deal_type_code,
                  COALESCE(SUM(price * qty), 0) AS revenue,
                  COALESCE(SUM(purchase_cost * qty * rate), 0) AS purchase_cost,
                  COUNT(*) AS count
                FROM base
                WHERE {where_sql}
                GROUP BY deal_type_code
                ORDER BY deal_type_code
            """, params)

        by_day = []
        for r in by_day_rows:
            rev = float(r[1] or 0)
            pc = float(r[2] or 0)
            by_day.append(
                SalesAnalyticsPoint(
                    date=r[0],
                    revenue=rev,
                    purchase_cost=pc,
                    margin=rev - pc,
                    count=int(r[3] or 0),
                )
            )

        by_type = []
        for r in by_type_rows:
            rev = float(r[1] or 0)
            pc = float(r[2] or 0)
            by_type.append(
                SalesAnalyticsByType(
                    deal_type_code=r[0],
                    revenue=rev,
                    purchase_cost=pc,
                    margin=rev - pc,
                    count=int(r[3] or 0),
                )
            )

        return SalesAnalyticsOut(
            totals=SalesAnalyticsTotals(
                revenue=revenue,
                purchase_cost=purchase_cost,
                margin=margin,
                count=count,
                avg_check=avg_check,
            ),
            by_day=by_day,
            by_type=by_type,
        )

    @app.get("/analytics/sources", response_model=SourcesAnalyticsOut)
    def analytics_sources(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        deal_type_code: Optional[str] = None,
        region_code: Optional[str] = None,
        source_id: Optional[int] = None,
        user=Depends(get_current_user),
    ):
        params: list[Any] = []
        filters = ["activity_at IS NOT NULL", "status_code = 'confirmed'"]

        if deal_type_code:
            filters.append("deal_type_code = %s")
            params.append(deal_type_code)
        if region_code:
            filters.append("region_code = %s")
            params.append(region_code)
        if source_id:
            filters.append("source_id = %s")
            params.append(source_id)
        if date_from:
            filters.append("activity_at::date >= %s")
            params.append(date_from)
        if date_to:
            filters.append("activity_at::date <= %s")
            params.append(date_to)

        where_sql = " AND ".join(filters)

        with psycopg.connect(DB_DSN) as conn:
            top_count_rows = qall(conn, f"""
                WITH base AS (
                    SELECT
                      d.deal_type_code,
                      d.status_code,
                      COALESCE(rd.code, ra.code) AS region_code,
                      c.source_id,
                      src.code as source_code,
                      src.name as source_name,
                      di.price,
                      di.qty,
                      CASE
                        WHEN d.deal_type_code = 'sale' THEN d.completed_at
                        ELSE COALESCE(di.purchase_at, d.created_at)
                      END AS activity_at
                    FROM app.deal_items di
                    JOIN app.deals d ON d.deal_id = di.deal_id
                    LEFT JOIN app.accounts a ON a.account_id = di.account_id
                    LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                    LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                    LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                    LEFT JOIN app.sources src ON src.source_id = c.source_id
                )
                SELECT
                  source_id,
                  source_code,
                  source_name,
                  COUNT(*) AS deals_count,
                  COALESCE(SUM(price * qty), 0) AS revenue
                FROM base
                WHERE {where_sql}
                GROUP BY source_id, source_code, source_name
                ORDER BY deals_count DESC
                LIMIT 10
            """, params)

            top_revenue_rows = qall(conn, f"""
                WITH base AS (
                    SELECT
                      d.deal_type_code,
                      d.status_code,
                      COALESCE(rd.code, ra.code) AS region_code,
                      c.source_id,
                      src.code as source_code,
                      src.name as source_name,
                      di.price,
                      di.qty,
                      CASE
                        WHEN d.deal_type_code = 'sale' THEN d.completed_at
                        ELSE COALESCE(di.purchase_at, d.created_at)
                      END AS activity_at
                    FROM app.deal_items di
                    JOIN app.deals d ON d.deal_id = di.deal_id
                    LEFT JOIN app.accounts a ON a.account_id = di.account_id
                    LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                    LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                    LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                    LEFT JOIN app.sources src ON src.source_id = c.source_id
                )
                SELECT
                  source_id,
                  source_code,
                  source_name,
                  COUNT(*) AS deals_count,
                  COALESCE(SUM(price * qty), 0) AS revenue
                FROM base
                WHERE {where_sql}
                GROUP BY source_id, source_code, source_name
                ORDER BY revenue DESC
                LIMIT 10
            """, params)

            repeat_row = q1(conn, f"""
                WITH base AS (
                    SELECT
                      d.deal_id,
                      d.status_code,
                      d.deal_type_code,
                      COALESCE(rd.code, ra.code) AS region_code,
                      c.source_id,
                      d.customer_id,
                      CASE
                        WHEN d.deal_type_code = 'sale' THEN d.completed_at
                        ELSE COALESCE(di.purchase_at, d.created_at)
                      END AS activity_at
                    FROM app.deal_items di
                    JOIN app.deals d ON d.deal_id = di.deal_id
                    LEFT JOIN app.accounts a ON a.account_id = di.account_id
                    LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                    LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                    LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                ),
                filtered AS (
                    SELECT DISTINCT deal_id, customer_id
                    FROM base
                    WHERE {where_sql}
                ),
                by_customer AS (
                    SELECT customer_id, COUNT(*) AS deals_count
                    FROM filtered
                    WHERE customer_id IS NOT NULL
                    GROUP BY customer_id
                )
                SELECT
                  COALESCE(SUM(CASE WHEN deals_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_count,
                  COALESCE(COUNT(*), 0) AS total_customers
                FROM by_customer
            """, params)

        top_by_count = [
            SourceAnalyticsItem(
                source_id=r[0],
                source_code=r[1],
                source_name=r[2],
                deals_count=int(r[3] or 0),
                revenue=float(r[4] or 0),
            )
            for r in top_count_rows
        ]
        top_by_revenue = [
            SourceAnalyticsItem(
                source_id=r[0],
                source_code=r[1],
                source_name=r[2],
                deals_count=int(r[3] or 0),
                revenue=float(r[4] or 0),
            )
            for r in top_revenue_rows
        ]
        repeat_count = int(repeat_row[0] or 0) if repeat_row else 0
        total_customers = int(repeat_row[1] or 0) if repeat_row else 0
        repeat_share = (repeat_count / total_customers) if total_customers else 0.0

        return SourcesAnalyticsOut(
            top_by_count=top_by_count,
            top_by_revenue=top_by_revenue,
            repeat_customers=RepeatCustomersOut(
                repeat_count=repeat_count,
                total_customers=total_customers,
                repeat_share=repeat_share,
            ),
        )

    @app.get("/analytics/audit", response_model=AuditAnalyticsOut)
    def analytics_audit(
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        deal_type_code: Optional[str] = None,
        region_code: Optional[str] = None,
        source_id: Optional[int] = None,
        limit: int = 200,
        user=Depends(get_current_user),
    ):
        if limit < 1 or limit > 500:
            raise HTTPException(400, "limit must be between 1 and 500")

        params: list[Any] = []
        filters = ["da.changed_at IS NOT NULL"]

        if deal_type_code:
            filters.append("d.deal_type_code = %s")
            params.append(deal_type_code)
        if region_code:
            filters.append("COALESCE(rd.code, ra.code) = %s")
            params.append(region_code)
        if source_id:
            filters.append("c.source_id = %s")
            params.append(source_id)
        if date_from:
            filters.append("da.changed_at::date >= %s")
            params.append(date_from)
        if date_to:
            filters.append("da.changed_at::date <= %s")
            params.append(date_to)

        where_sql = " AND ".join(filters)

        with psycopg.connect(DB_DSN) as conn:
            total_row = q1(conn, f"""
                SELECT COUNT(*)
                FROM app.deal_audit da
                LEFT JOIN app.deals d ON d.deal_id = da.deal_id
                LEFT JOIN LATERAL (
                  SELECT account_id
                  FROM app.deal_items
                  WHERE deal_id = d.deal_id
                  ORDER BY deal_item_id ASC
                  LIMIT 1
                ) di ON true
                LEFT JOIN app.accounts a ON a.account_id = di.account_id
                LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                WHERE {where_sql}
            """, params)
            total = int(total_row[0]) if total_row else 0

            rows = qall(conn, f"""
                SELECT
                  da.deal_id,
                  da.table_name,
                  da.action,
                  da.changed_at,
                  da.changed_by
                FROM app.deal_audit da
                LEFT JOIN app.deals d ON d.deal_id = da.deal_id
                LEFT JOIN LATERAL (
                  SELECT account_id
                  FROM app.deal_items
                  WHERE deal_id = d.deal_id
                  ORDER BY deal_item_id ASC
                  LIMIT 1
                ) di ON true
                LEFT JOIN app.accounts a ON a.account_id = di.account_id
                LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                WHERE {where_sql}
                ORDER BY da.changed_at DESC
                LIMIT %s
            """, params + [limit])

        items = [
            AuditItemOut(
                deal_id=r[0],
                table_name=r[1],
                action=r[2],
                changed_at=r[3],
                changed_by=r[4],
            )
            for r in rows
        ]

        return AuditAnalyticsOut(total=total, items=items)
