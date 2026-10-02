WITH ranked AS (SELECT *,ROW_NUMBER() OVER (PARTITION BY entity ORDER BY version DESC,seq DESC) rn FROM events)
SELECT entity,value FROM ranked WHERE rn=1 AND deleted=0 ORDER BY entity
