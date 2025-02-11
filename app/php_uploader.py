import requests
import datetime
from uploader import BaseUploader
import configparser


PHP_CONFIG_PATH = 'configs/php.conf'
PHP_CONFIG = configparser.ConfigParser()
PHP_CONFIG.read(PHP_CONFIG_PATH)


class PHPUploader(BaseUploader):
    """Загрузка с PHP."""

    def _prepare_constants(self):
        super()._prepare_constants()

        self.php_orders_db = 'df_php_orders'

    def run(self):
        self._message('==PHP==')

        self._upload(
            endpoint=PHP_CONFIG.get("php", "endpoint"),
            key=PHP_CONFIG.get("php", "key"),
            db_table_name=self.php_orders_db,
        )

        self._message('==PHP==')

    def _upload(self, endpoint, key, db_table_name):
        today = datetime.datetime.now()
        chunk = 10
        end = False
        self._message(f'Starting uploading from {endpoint}.')

        url = f"https://senatnn.ru/local/api/analytic/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Key": key,
        }

        # На первой итерации возвращаемся на 10 дней назад, чтобы ничего не упустить.
        starting_date = self._get_php_upload_starting_time(db_table_name) - datetime.timedelta(days=10)
        self._message(f'Started uploading from {endpoint}, starting date: {starting_date}')

        while True:
            ending_date = starting_date + datetime.timedelta(days=chunk)
            self._message(f'Processing {endpoint}, from {starting_date} to {ending_date}:')

            if ending_date > today:
                end = True
                chunk = (today - starting_date).days
                ending_date = starting_date + datetime.timedelta(days=chunk + 1)

            request_body = {
                "dateFrom": starting_date.strftime("%Y-%m-%d"),
                "dateTo": ending_date.strftime("%Y-%m-%d"),
            }
            params = {
                'url': url,
                'headers': headers,
                'json': request_body,
            }

            response = requests.get(**params)

            if response.status_code == 200:
                orders = response.json().get('orders')

                no_data = self._flush_df(
                    orders,
                    self.php_orders_db,
                    ending_date=ending_date,
                    renames={'id': 'php_id', 'createdOn': 'created_on'},
                    unique_field='php_id',
                )

                if no_data:
                    self._message(f'\tNo data from {endpoint} from {starting_date} to {ending_date}')
            else:
                self._error(f'code {response.status_code}: {response.text}')

            if end:
                break

            starting_date = ending_date + datetime.timedelta(days=chunk)

        self._message(f'Ended uploading {endpoint}.')

    def _get_php_upload_starting_time(self, table_name):
        """Получаем дату последней загрузки данных в БД. Если ничего не грузилось, начинаем с 02.05.2024."""

        self.cursor.execute(f"SELECT upload_date FROM {table_name} ORDER BY upload_date DESC LIMIT 1")
        fetch = self.cursor.fetchone()

        return fetch[0] if fetch else datetime.datetime(2023, 1, 1)
