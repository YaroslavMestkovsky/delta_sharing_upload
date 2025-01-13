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

    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_db()
