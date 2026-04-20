CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.user_id IS UNIQUE;

CREATE CONSTRAINT product_id_unique IF NOT EXISTS
FOR (p:Product) REQUIRE p.product_id IS UNIQUE;

LOAD CSV WITH HEADERS FROM "file:///dataset.csv" AS row
CALL {
  WITH row
  WITH
    toInteger(row.user_id) AS user_id,
    toInteger(row.product_id) AS product_id,
    toLower(trim(row.action)) AS action,
    datetime(replace(trim(row.timestamp), " ", "T")) AS ts
  WHERE user_id IS NOT NULL AND product_id IS NOT NULL AND action <> ""
  MERGE (u:User {user_id: user_id})
  MERGE (p:Product {product_id: product_id})
  MERGE (u)-[r:INTERACTED {action: action}]->(p)
  ON CREATE SET
    r.count = 1,
    r.first_ts = ts,
    r.last_ts = ts
  ON MATCH SET
    r.count = coalesce(r.count, 0) + 1,
    r.first_ts = CASE WHEN ts < r.first_ts THEN ts ELSE r.first_ts END,
    r.last_ts = CASE WHEN ts > r.last_ts THEN ts ELSE r.last_ts END
} IN TRANSACTIONS OF 1000 ROWS;
