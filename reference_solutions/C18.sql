SELECT c.id,c.name FROM customers c WHERE c.active=1 AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id=c.id AND o.status='paid') ORDER BY c.id
