import datetime
import delta_sharing
import logging
from requests.exceptions import HTTPError

from enums import (
    ORDERS_COLUMNS,
    PURCHASE_COLUMNS,
    NEGATIVE_CUSTOMER_BALANCE_CHANGE_DETAILS_COLUMNS,
    POINTS_OF_CONTRACT_COLUMNS,
    PURCHASE_STATUSES_COLUMNS,
)
from db_helpers import (
    connect_to_db, 
    create_alchemy_engine,
)


PROFILE = 'Profile.json'
CONFIG = 'postgres.conf'


class DeltaSharingUpload:
    """Загрузка данных из таблиц."""

    def __init__(self):
        logging.basicConfig(
            filename='upload.log',
            level=logging.INFO,
            format='%(levelname)s - %(message)s'
        )

        self._init_names()
        self._init_columns_rules()
        self._init_connections()
        self._init_tables()

    def run(self):
        """Получение и загрузка данных."""

        # Пока не известно, какие могут быть ошибки, так что логируем всё подряд - на всякий случай.
        try:
            self._upload_orders()
            self._upload_purchase()
            self._upload_negative_customer_balance_change_details()
            self._upload_point_od_contract()
            self._upload_purchase_statuses()

        except Exception as e:
            self._error(e)

    def upload(self, table_name, db_table_name, columns):
        """Получение и загрузка сущностей."""

        step = 10
        upload_count = 0
        end = False
        last_version = self._get_last_version(db_table_name) or 0
        ending_version = None

        table = next((item for item in self.tables if item.name == table_name))
        url = f'{PROFILE}#{table.share}.{table.schema}.{table.name}'

        self._message(f'Started uploading {table_name}, from version: {last_version}')
        c=0
        while True:
            c+=1
            if c== 5:break
            starting_version = last_version
            ending_version = starting_version + step

            try:
                df = delta_sharing.load_table_changes_as_pandas(
                    url,
                    starting_version=starting_version,
                    ending_version=ending_version,
                )
                last_version = ending_version

                if df.empty:
                    continue

            except HTTPError:
                if end:
                    # Дошли до последней доступной версии.
                    break
                else:
                    # Возможно, осталось меньше 10 версий, простучим по одной.
                    end = True
                    step = 1
                    continue

            df['starting_version'] = starting_version
            df['ending_version'] = ending_version

            filtered_df = df.filter(items=columns)
            filtered_df.columns = filtered_df.columns.str.lower()

            uploaded = len(filtered_df)
            self._message(f'uploaded {uploaded} rows from {starting_version}-{ending_version} versions.')
            upload_count += uploaded
            self._flush_to_db(filtered_df, db_table_name)

        self._message(f'Ended uploading {table_name} on version {ending_version}, uploaded {upload_count} rows.')

    def _upload_orders(self):
        """Загрузка заказов."""
        self.upload(
            table_name=self.orders,
            db_table_name=self.orders_db,
            columns=self.orders_cols,
        )

    def _upload_purchase(self):
        """Загрузка покупок."""
        self.upload(
            table_name=self.purchase,
            db_table_name=self.purchase_db,
            columns=self.purchase_cols,
        )

    def _upload_negative_customer_balance_change_details(self):
        """Загрузка сумм списания."""
        self.upload(
            table_name=self.negative_customer_balance_change_details,
            db_table_name=self.negative_customer_balance_change_details_db,
            columns=self.negative_customer_balance_change_details_cols,
        )

    def _upload_point_od_contract(self):
        """Загрузка точек совершения покупок."""
        self.upload(
            table_name=self.points_of_contract,
            db_table_name=self.points_of_contract_db,
            columns=self.points_of_contract_cols,
        )

    def _upload_purchase_statuses(self):
        """Загрузка точек совершения покупок."""
        self.upload(
            table_name=self.purchase_statuses,
            db_table_name=self.purchase_statuses_db,
            columns=self.purchase_statuses_cols,
        )

    def _init_names(self):
        """Инициализация названий таблиц."""

        self.orders = 'Orders'
        self.orders_db = 'df_delta_sharing_orders'

        self.purchase = 'Purchases'
        self.purchase_db = 'df_delta_sharing_purchases'

        self.negative_customer_balance_change_details = 'NegativeCustomerBalanceChangeDetails'
        self.negative_customer_balance_change_details_db = 'df_delta_sharing_negative_customer_balance_change'

        self.points_of_contract = 'PointsOfContact'
        self.points_of_contract_db = 'df_delta_sharing_points_of_contact'

        self.purchase_statuses = 'PurchaseStatuses'
        self.purchase_statuses_db = 'df_delta_sharing_purchase_statuses'

    def _init_columns_rules(self):
        """Инициализация столбцов, которые мы хотим получить и сохранить."""
        self.orders_cols = ORDERS_COLUMNS
        self.purchase_cols = PURCHASE_COLUMNS
        self.negative_customer_balance_change_details_cols = NEGATIVE_CUSTOMER_BALANCE_CHANGE_DETAILS_COLUMNS
        self.points_of_contract_cols = POINTS_OF_CONTRACT_COLUMNS
        self.purchase_statuses_cols = PURCHASE_STATUSES_COLUMNS

    def _init_connections(self):
        """Инициализация подключений к базе."""

        self.connection = connect_to_db()
        self.cursor = self.connection.cursor()
        self.engine = create_alchemy_engine()

    def close_connection(self):
        """Закрываем соединения с базой."""

        self.connection.close()
        self.engine.dispose()

    def _init_tables(self):
        """Инициализация доступных для загрузки таблиц."""

        client = delta_sharing.SharingClient(PROFILE)
        self.tables = client.list_all_tables()

    def _get_last_version(self, table_name):
        """Получаем последнюю загруженную версию."""

        self.cursor.execute(f"SELECT ending_version FROM {table_name} ORDER BY ending_version DESC LIMIT 1")
        fetch = self.cursor.fetchone()
        result = fetch[0] if fetch else None

        return result

    def _flush_to_db(self, df, table_name):
        """Запись полученных данных в базу."""
        df.to_sql(table_name, self.engine, if_exists="append", index=False)

    @staticmethod
    def _message(msg):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f'{now}: {msg}')

    @staticmethod
    def _error(msg):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.error(f'{now}: {msg}')


if __name__ == '__main__':
    uploader = DeltaSharingUpload()
    uploader.run()
    uploader.close_connection()