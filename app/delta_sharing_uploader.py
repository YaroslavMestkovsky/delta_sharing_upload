import delta_sharing
from helpers import enums

from uploader import (
    BaseUploader
)
from requests.exceptions import (
    HTTPError,
)

PROFILE = 'configs/Profile.json'


class DeltaSharingUploader(BaseUploader):
    """Загрузка из delta_sharing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._prepare_tables()

    def _prepare_constants(self, *args, **kwargs):
        """Подготовка всех необходимых для загрузки данных."""

        super()._prepare_constants()

        self.orders_table = 'Orders'
        self.orders_db = 'df_delta_sharing_orders'
        self.orders_cols = enums.ORDERS_COLUMNS

        self.purchase_table = 'Purchases'
        self.purchase_db = 'df_delta_sharing_purchases'
        self.purchase_cols = enums.PURCHASE_COLUMNS

        self.deduction_amounts_table = 'NegativeCustomerBalanceChangeDetails'
        self.deduction_amounts_db = 'df_delta_sharing_negative_customer_balance_change'
        self.deduction_amounts_cols = enums.DEDUCTION_AMOUNTS_COLUMNS

        self.purchase_points_table = 'PointsOfContact'
        self.purchase_points_db = 'df_delta_sharing_points_of_contact'
        self.purchase_points_cols = enums.PURCHASE_POINTS_COLUMNS

        self.purchase_statuses_table = 'PurchaseStatuses'
        self.purchase_statuses_db = 'df_delta_sharing_purchase_statuses'
        self.purchase_statuses_cols = enums.PURCHASE_STATUSES_COLUMNS

    def _prepare_tables(self):
        """Инициализация доступных для загрузки таблиц."""

        client = delta_sharing.SharingClient(PROFILE)
        self.tables = client.list_all_tables()

    def run(self):
        """Старт загрузки."""

        self._message('==DELTA_SHARING==')

        # Заказы
        self._upload(
            table_name=self.orders_table,
            db_table_name=self.orders_db,
            columns=self.orders_cols,
        )
        # Покупки
        self._upload(
            table_name=self.purchase_table,
            db_table_name=self.purchase_db,
            columns=self.purchase_cols,
        )
        # Суммы списания
        self._upload(
            table_name=self.deduction_amounts_table,
            db_table_name=self.deduction_amounts_db,
            columns=self.deduction_amounts_cols,
        )
        # Точки совершения покупок
        self._upload(
            table_name=self.purchase_points_table,
            db_table_name=self.purchase_points_db,
            columns=self.purchase_points_cols,
        )
        # Статусы покупок
        self._upload(
            table_name=self.purchase_statuses_table,
            db_table_name=self.purchase_statuses_db,
            columns=self.purchase_statuses_cols,
        )

        self._message('==DELTA_SHARING==')

    def _upload(self, table_name, db_table_name, columns, *args, **kwargs):
        step = 10
        upload_count = 0
        end = False
        last_version = self._get_last_version(db_table_name) or 0

        table = next((item for item in self.tables if item.name == table_name))
        url = f'{PROFILE}#{table.share}.{table.schema}.{table.name}'

        self._message(f'Starting uploading {table_name} from version: {last_version}')

        while True:
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
            upload_count += uploaded

            self._flush(
                filtered_df,
                db_table_name,
                unique_field='delta_sharing_id',
                numeric_unique=False,
                renames={'id': 'delta_sharing_id'},
            )
            self._message(f'\t\tuploaded {uploaded} rows from version{starting_version} to version{ending_version}')

        self._message(f'Ended uploading {table_name} on version {ending_version}, uploaded {upload_count} rows.\n')

    def _get_last_version(self, db_table_name):
        """Получаем последнюю загруженную версию."""

        self.cursor.execute(f"SELECT ending_version FROM {db_table_name} ORDER BY ending_version DESC LIMIT 1")
        fetch = self.cursor.fetchone()

        return fetch[0] if fetch else None
