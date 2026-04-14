#!/bin/sh
set -e

create_db() {
  db_name="$1"
  echo "Creating database '$db_name' (if missing)"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    SELECT 'CREATE DATABASE $db_name'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db_name')\gexec
EOSQL
}

create_db customer_db
create_db product_db
create_db cart_db
create_db order_db
create_db payment_db
create_db shipping_db
create_db rating_db
create_db ai_recommendation_db
create_db gateway_db
create_db manager_db
create_db staff_db
