@echo off
echo ========================================
echo BOOKSTORE MICROSERVICE SYSTEM
echo ========================================
echo.
echo Dang khoi dong cac microservices...
echo.

REM Customer Service - Port 8001
start "Customer Service" cmd /k "cd customer_service && python manage.py migrate && python manage.py runserver 8001"
timeout /t 2

REM Product Service (DDD) - Port 8002
start "Product Service" cmd /k "cd product_service && python manage.py migrate --settings=config.settings.dev && python manage.py runserver 8002 --settings=config.settings.dev"
timeout /t 2

REM Cart Service - Port 8003
start "Cart Service" cmd /k "cd cart_service && python manage.py migrate && python manage.py runserver 8003"
timeout /t 2

REM Order Service - Port 8004
start "Order Service" cmd /k "cd order_service && python manage.py migrate && python manage.py runserver 8004"
timeout /t 2

REM Payment Service - Port 8005
start "Payment Service" cmd /k "cd payment_service && python manage.py migrate && python manage.py runserver 8005"
timeout /t 2

REM Shipping Service - Port 8006
start "Shipping Service" cmd /k "cd shipping_service && python manage.py migrate && python manage.py runserver 8006"
timeout /t 2

REM Comment and Rating Service - Port 8007
start "Rating Service" cmd /k "cd comment_and_rating_service && python manage.py migrate && python manage.py runserver 8007"
timeout /t 2

REM API Gateway - Port 8000
start "API Gateway" cmd /k "cd api_gateway && python manage.py migrate && python manage.py runserver 8000"

echo.
echo ========================================
echo TAT CA CAC SERVICES DA DUOC KHOI DONG!
echo ========================================
echo.
echo API Gateway:      http://localhost:8000
echo Customer Service: http://localhost:8001
echo Product Service:  http://localhost:8002  (DDD Architecture)
echo Cart Service:     http://localhost:8003
echo Order Service:    http://localhost:8004
echo Payment Service:  http://localhost:8005
echo Shipping Service: http://localhost:8006
echo Rating Service:   http://localhost:8007
echo.
pause
