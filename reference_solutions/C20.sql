WITH p AS (SELECT order_id,SUM(cents) v FROM payments GROUP BY order_id),
r AS (SELECT order_id,SUM(cents) v FROM refunds GROUP BY order_id)
SELECT o.day,SUM(COALESCE(p.v,0)),SUM(COALESCE(r.v,0)),SUM(COALESCE(p.v,0)-COALESCE(r.v,0))
FROM orders o LEFT JOIN p ON p.order_id=o.id LEFT JOIN r ON r.order_id=o.id GROUP BY o.day ORDER BY o.day
