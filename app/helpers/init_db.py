"""Таблицы, которые необходимо создать в базе данных. Фиксируем изменения, чтобы иметь отправную точку."""

from db_helpers import connect_to_db

#todo здесь
def init_db():
    connection = connect_to_db()
    cursor = connection.cursor()

    # cursor.execute(
    #     """
    #     CREATE TABLE df_delta_sharing_orders (
    #         id SERIAL PRIMARY KEY,
    #         delta_sharing_id TEXT,
    #         starting_version INTEGER,
    #         ending_version INTEGER,
    #         firstDateTimeUtc TIMESTAMP,
    #         price REAL,
    #         priceWithDiscounts REAL,
    #         unmergedCustomerId INTEGER,
    #         firstBrandInternalId TEXT,
    #         pointOfContactInternalId TEXT,
    #         firstPointOfContactInternalId TEXT,
    #         deliveryPrice REAL,
    #         deliveryPriceWithDiscounts REAL,
    #         paidAmount REAL,
    #         _isDeleted TEXT,
    #         _rowversion_ts TIMESTAMP,
    #         _tenant TEXT,
    #         _change_type TEXT,
    #         _commit_version INTEGER,
    #         _commit_timestamp TIMESTAMP
    #     )
    #     """
    # )

    # cursor.execute(
    #     """
    #     CREATE TABLE df_delta_sharing_purchases (
    #         id SERIAL PRIMARY KEY,
    #         starting_version INTEGER,
    #         ending_version INTEGER,
    #         quantity INTEGER,
    #         productInternalId INTEGER
    #     )
    #     """
    # )
    #
    # cursor.execute(
    #     """
    #     CREATE TABLE df_delta_sharing_negative_customer_balance_change (
    #         id SERIAL PRIMARY KEY,
    #         starting_version INTEGER,
    #         ending_version INTEGER,
    #         spentAmount REAL
    #     )
    #     """
    # )
    #
    # cursor.execute(
    #     """
    #     CREATE TABLE df_delta_sharing_points_of_contact (
    #         id SERIAL PRIMARY KEY,
    #         starting_version INTEGER,
    #         ending_version INTEGER,
    #         name TEXT
    #     )
    #     """
    # )
    #
    # cursor.execute(
    #     """
    #     CREATE TABLE df_delta_sharing_purchase_statuses (
    #         id SERIAL PRIMARY KEY,
    #         starting_version INTEGER,
    #         ending_version INTEGER,
    #         name TEXT
    #     )
    #     """
    # )
    #
    # cursor.execute(
    #     """
    #     CREATE TABLE df_php_orders (
    #         id SERIAL PRIMARY KEY,
    #         php_id INTEGER,
    #         status_id TEXT,
    #         price INTEGER,
    #         created_on TIMESTAMP,
    #         canceled TEXT,
    #         user_id TEXT,
    #         delivery_id TEXT,
    #         pay TEXT,
    #         type_id TEXT,
    #         upload_date TIMESTAMP
    #     )
    #     """
    # )

    # cursor.execute(
    #     """
    #     CREATE TABLE df_yandex_visits (
    #         id SERIAL PRIMARY KEY,
    #         purchase_id TEXT,
    #         visit_id TEXT,
    #         purchase_revenue TEXT,
    #         date_time TIMESTAMP,
    #         client_id TEXT,
    #         traffic_source TEXT,
    #         last_search_engine TEXT,
    #         utm_source TEXT,
    #         utm_medium TEXT,
    #         utm_campaign TEXT,
    #         utm_content TEXT,
    #         utm_term TEXT,
    #         device_category TEXT,
    #         referal_source TEXT,
    #         first_dim_upload_date TIMESTAMP,
    #         second_dim_upload_date TIMESTAMP,
    #         third_dim_upload_date TIMESTAMP,
    #         UNIQUE (purchase_id, visit_id) -- Спасибо, яндекс.
    #     )
    #     """
    # )

    cursor.execute(
        """
        CREATE TABLE df_yandex_goals (
            id SERIAL PRIMARY KEY,
            yandex_visit_id INTEGER REFERENCES df_yandex_visits(id),
            goal TEXT,
            date_time TiMESTAMP,
            upload_date TIMESTAMP,
            UNIQUE (yandex_visit_id, goal)
        )
        """
    )

    # cursor.execute(
    #     """
    #     CREATE TABLE df_stenatnn_customers (
    #         id SERIAL PRIMARY KEY,
    #         sex TEXT,
    #         first_Name TEXT, -- new
    #         middle_Name TEXT, -- new
    #         last_Name TEXT, -- new
    #         iana_Time_Zone TEXT, -- new
    #         time_Zone_Source TEXT, -- new
    #         is_Email_Invalid BOOLEAN, -- new
    #         is_Mobile_Phone_Invalid BOOLEAN, -- new
    #         change_Date_Time_Utc TIMESTAMP, -- new
    #         is_Mobile_Phone_Confirmed BOOLEAN, -- new
    #         email TEXT, -- new
    #         mobile_Phone TEXT, -- new
    #         website_id TEXT,
    #         mindbox_id INTEGER,
    #         birth_date TIMESTAMP,
    #         upload_date TIMESTAMP
    #     )
    #     """
    # )
    #
    # cursor.execute(
    #     """
    #     CREATE TABLE df_stenatnn_customers_actions (
    #         id SERIAL PRIMARY KEY,
    #         mindbox_id INTEGER,
    #         date_time_utc TIMESTAMP,
    #         action_template_name TEXT,
    #         channel_name TEXT,
    #         customer_id INTEGER REFERENCES df_stenatnn_customers(id),
    #         upload_date TIMESTAMP
    #     )
    #     """
    # )
    #
    # cursor.execute(
    #     """
    #         CREATE TABLE df_stenatnn_orders (
    #         id SERIAL PRIMARY KEY,  -- Уникальный идентификатор записи
    #         mindbox_id BIGINT,       -- Уникальный идентификатор заказа в системе Mindbox
    #         offline_id TEXT,         -- Уникальный идентификатор заказа в офлайн-системе
    #         order_transaction_id TEXT,  -- Автоматически сгенерированный идентификатор транзакции заказа
    #         first_action_mindbox_id BIGINT,  -- Уникальный идентификатор первого действия
    #         first_action_datetime_utc TIMESTAMP,  -- Дата и время первого действия в формате UTC
    #         channel_mindbox_id BIGINT,  -- Уникальный идентификатор канала
    #         channel_external_id TEXT,   -- Внешний идентификатор канала
    #         channel_name TEXT,          -- Название канала
    #         transaction_external_id TEXT,  -- Внешний идентификатор транзакции
    #         total_price NUMERIC(15, 2),  -- Общая стоимость заказа
    #         customer_id INTEGER REFERENCES df_stenatnn_customers(id), -- Уникальный идентификатор клиента в системе Mindbox
    #         upload_date TIMESTAMP
    #     );
    # """
    # )
    #
    # cursor.execute(
    #     """
    #         CREATE TABLE df_stenatnn_order_lines (
    #         id SERIAL PRIMARY KEY,  -- Уникальный идентификатор записи
    #         order_id INT REFERENCES df_stenatnn_orders(id) ON DELETE CASCADE,  -- Ссылка на заказ
    #         product_riteil1c_id TEXT,  -- Уникальный идентификатор продукта
    #         product_name TEXT,      -- Название продукта
    #         quantity NUMERIC(10, 6),  -- Количество товара
    #         base_price_per_item NUMERIC(15, 2),  -- Базовая цена за единицу товара
    #         price_of_line NUMERIC(15, 2),  -- Общая стоимость строки заказа
    #         status_external_id TEXT,  -- Статус заказа (например, 'Paid')
    #         upload_date TIMESTAMP
    #     );
    # """
    # )
    #
    # cursor.execute(
    #     """
    #     CREATE TABLE df_stenattn_applied_promotions (
    #             id SERIAL PRIMARY KEY,  -- Уникальный идентификатор записи
    #             order_id INT REFERENCES df_stenatnn_orders(id) ON DELETE CASCADE,  -- Ссылка на строку заказа
    #             promotion_type TEXT,    -- Тип акции (например, 'discount', 'earnedBonusPoints')
    #             promotion_mindbox_id BIGINT,  -- Уникальный идентификатор промоакции
    #             promotion_external_id TEXT,  -- Внешний идентификатор промоакции
    #             promotion_name TEXT,    -- Название промоакции
    #             promotion_type_name TEXT,  -- Тип промоакции
    #             grouping_key TEXT,      -- Ключ группировки
    #             amount NUMERIC(15, 2),  -- Сумма скидки или начисленных бонусов
    #             balance_type_system_name TEXT,  -- Тип баланса для бонусных баллов
    #             balance_type_name TEXT,  -- Название типа баланса
    #             expiration_datetime_utc TIMESTAMP,  -- Дата и время истечения срока действия бонусных баллов
    #             upload_date TIMESTAMP
    #         );
    #     """
    # )
    #
    # cursor.execute(
    #     """
    #         CREATE TABLE df_stenattn_bonus_points_info (
    #             id SERIAL PRIMARY KEY,  -- Уникальный идентификатор записи
    #             order_id INT REFERENCES df_stenatnn_orders(id) ON DELETE CASCADE,  -- Ссылка на заказ
    #             balance_type_system_name TEXT,  -- Тип баланса (например, 'Счет программы лояльности')
    #             balance_type_name TEXT,  -- Название типа баланса
    #             earned_amount NUMERIC(15, 2),  -- Количество начисленных бонусных баллов
    #             spent_amount NUMERIC(15, 2),   -- Количество потраченных бонусных баллов
    #             upload_date TIMESTAMP
    #         );
    #     """
    # )

    

    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_db()
