"""Таблицы, которые необходимо создать в базе данных. Фиксируем изменения, чтобы иметь отправную точку."""

from db_helpers import connect_to_db


def init_db():
    connection = connect_to_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE df_delta_sharing_orders (
            id SERIAL PRIMARY KEY,
            starting_version INTEGER,
            ending_version INTEGER,
            firstDateTimeUtc TIMESTAMP,
            price REAL,
            priceWithDiscounts REAL,
            unmergedCustomerId INTEGER
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE df_delta_sharing_purchases (
            id SERIAL PRIMARY KEY,
            starting_version INTEGER,
            ending_version INTEGER,
            quantity INTEGER,
            productInternalId INTEGER
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE df_delta_sharing_negative_customer_balance_change (
            id SERIAL PRIMARY KEY,
            starting_version INTEGER,
            ending_version INTEGER,
            spentAmount REAL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE df_delta_sharing_points_of_contact (
            id SERIAL PRIMARY KEY,
            starting_version INTEGER,
            ending_version INTEGER,
            name TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE df_delta_sharing_purchase_statuses (
            id SERIAL PRIMARY KEY,
            starting_version INTEGER,
            ending_version INTEGER,
            name TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE df_stenatnn_customers (
            id SERIAL PRIMARY KEY,
            sex TEXT,
            website_id TEXT,
            mindbox_id INTEGER,
            birth_date TIMESTAMP,
            upload_date TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE df_stenatnn_customers_actions (
            id SERIAL PRIMARY KEY,
            mindbox_id INTEGER,
            date_time_utc TIMESTAMP,
            action_template_name TEXT,
            channel_name TEXT,
            customer_id INTEGER REFERENCES df_stenatnn_customers(id),
            upload_date TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE df_php_orders (
            id SERIAL PRIMARY KEY,
            php_id INTEGER,
            status_id TEXT,
            price INTEGER,
            created_on TIMESTAMP,
            canceled TEXT,
            user_id TEXT,
            delivery_id TEXT,
            pay TEXT,
            type_id TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE df_yandex_commerce_purchase (
            id SERIAL PRIMARY KEY,
            visit_id TEXT,
            purchase_id TEXT,
            purchase_revenue TEXT,
            date_time TIMESTAMP,
            client_id TEXT,
            traffic_source TEXT,
            last_search_engine TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_content TEXT,
            utm_term TEXT,
            device_category TEXT,
            referal_source TEXT,
            goal TEXT
        )
        """
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_db()
