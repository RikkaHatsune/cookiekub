-- Нормализуем номера платежей старых заказов: SIM-xxxx -> PAY-xxxx.
-- Новые заказы сразу получают префикс PAY- (backend/orders.py).
UPDATE orders
SET payment_ref = 'PAY-' || substr(payment_ref, 5)
WHERE payment_ref LIKE 'SIM-%';
