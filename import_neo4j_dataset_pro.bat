@echo off
setlocal

REM Chuyen ve thu muc goc cua project (noi chua file .bat)
cd /d "%~dp0"

set "CSV_PATH=ai_recommendation_service\dataset\dataset.csv"
set "CYPHER_PATH=scripts\neo4j\import_dataset_pro.cypher"
set "NEO4J_USER=neo4j"
set "NEO4J_PASSWORD=password"
set "CONTAINER_IMPORT_DIR=/var/lib/neo4j/import"
set "CONTAINER_CSV_PATH=/var/lib/neo4j/import/dataset.csv"

echo [1/5] Kiem tra file dataset...
if not exist "%CSV_PATH%" (
  echo [ERROR] Khong tim thay file: %CSV_PATH%
  pause
  exit /b 1
)

echo [2/5] Khoi dong service neo4j...
docker compose up -d neo4j
if errorlevel 1 (
  echo [ERROR] Khong the khoi dong neo4j.
  pause
  exit /b 1
)

echo [3/5] Tao thu muc import trong container...
docker compose exec -T neo4j sh -lc "mkdir -p %CONTAINER_IMPORT_DIR%"
if errorlevel 1 (
  echo [ERROR] Khong tao duoc thu muc import trong container.
  pause
  exit /b 1
)

echo [4/5] Copy dataset vao container...
docker compose cp "%CSV_PATH%" neo4j:%CONTAINER_CSV_PATH%
if errorlevel 1 (
  echo [ERROR] Copy dataset vao container that bai.
  pause
  exit /b 1
)

echo [5/5] Chay import vao Neo4j...
type "%CYPHER_PATH%" | docker compose exec -T neo4j cypher-shell -u %NEO4J_USER% -p %NEO4J_PASSWORD%
if errorlevel 1 (
  echo [ERROR] Import that bai.
  pause
  exit /b 1
)

echo.
echo Import thanh cong. Kiem tra nhanh:
docker compose exec -T neo4j cypher-shell -u %NEO4J_USER% -p %NEO4J_PASSWORD% "MATCH (u:User) RETURN count(u) AS users;"
docker compose exec -T neo4j cypher-shell -u %NEO4J_USER% -p %NEO4J_PASSWORD% "MATCH (p:Product) RETURN count(p) AS products;"
docker compose exec -T neo4j cypher-shell -u %NEO4J_USER% -p %NEO4J_PASSWORD% "MATCH ()-[r:INTERACTED]->() RETURN count(r) AS interactions;"

echo.
echo Hoan tat. Nhan phim bat ky de dong.
pause >nul
exit /b 0
