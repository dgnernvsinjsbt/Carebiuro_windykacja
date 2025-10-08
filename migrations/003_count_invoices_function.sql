-- Function to count unique invoices per client
-- Returns: client_id, invoice_count
-- This is more efficient than fetching all invoices and counting in JavaScript

CREATE OR REPLACE FUNCTION count_invoices_per_client()
RETURNS TABLE (
  client_id bigint,
  invoice_count bigint
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    i.client_id,
    COUNT(DISTINCT i.id)::bigint as invoice_count
  FROM invoices i
  WHERE i.client_id IS NOT NULL
  GROUP BY i.client_id;
END;
$$ LANGUAGE plpgsql;
