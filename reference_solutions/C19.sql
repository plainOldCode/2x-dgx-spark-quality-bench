SELECT a.id,b.id FROM reservations a JOIN reservations b ON a.id<b.id AND a.resource=b.resource
WHERE a.start_ms<a.end_ms AND b.start_ms<b.end_ms AND a.start_ms<b.end_ms AND b.start_ms<a.end_ms ORDER BY a.id,b.id
