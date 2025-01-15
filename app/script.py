import configparser
import datetime
import time
import pandas as pd
import requests
import delta_sharing
import logging

from requests.exceptions import (
    HTTPError,
)

from enums import (
    ORDERS_COLUMNS,
    PURCHASE_COLUMNS,
    NEGATIVE_CUSTOMER_BALANCE_CHANGE_DETAILS_COLUMNS,
    POINTS_OF_CONTRACT_COLUMNS,
    PURCHASE_STATUSES_COLUMNS,
    COMMERCE_PURCHASE_DIMENSIONS_PART_ONE,
    COMMERCE_PURCHASE_DIMENSIONS_PART_TWO,
    COMMERCE_PURCHASE_DIMENSIONS_PART_THREE,
    COMMERCE_PURCHASE_DIMENSIONS_PART_FOUR,
)
from db_helpers import (
    connect_to_db,
    create_alchemy_engine,
)


PROFILE = 'Profile.json'

MINDBOX_CONFIG_PATH = 'mindbox.conf'
MINDBOX_CONFIG = configparser.ConfigParser()
MINDBOX_CONFIG.read(MINDBOX_CONFIG_PATH)

PHP_CONFIG_PATH = 'php.conf'
PHP_CONFIG = configparser.ConfigParser()
PHP_CONFIG.read(PHP_CONFIG_PATH)

YANDEX_CONFIG_PATH = 'yandex.conf'
YANDEX_CONFIG = configparser.ConfigParser()
YANDEX_CONFIG.read(YANDEX_CONFIG_PATH)


class DeltaSharingUpload:
    """Загрузка данных из таблиц."""

    def __init__(self):
        logging.basicConfig(
            filename='../upload.log',
            level=logging.INFO,
            format='%(levelname)s - %(message)s'
        )

        self._init_names()
        self._init_columns_rules()
        self._init_connections()
        self._init_tables()
        self._init_helpers()
        self._init_maps()

    def run(self):
        """Получение и загрузка данных."""

        # Пока не известно, какие могут быть ошибки, так что логируем всё подряд - на всякий случай.
        try:
            self._upload_dsh_orders()
            self._upload_purchase()
            self._upload_negative_customer_balance_change_details()
            self._upload_point_od_contract()
            self._upload_purchase_statuses()
            self._upload_customer()
            self._upload_customer_actions()
            self._upload_php_orders()
            self._upload_commerce_purchase()

        except Exception as e:
            self._error(e)

    def delta_sharing_upload(self, table_name, db_table_name, columns):
        """Получение и загрузка сущностей из delta sharing."""

        step = 10
        upload_count = 0
        end = False
        last_version = self._get_last_version(db_table_name) or 0

        table = next((item for item in self.tables if item.name == table_name))
        url = f'{PROFILE}#{table.share}.{table.schema}.{table.name}'

        self._message(f'Started uploading from delta sharing {table_name}, from version: {last_version}')

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
            self._message(f'uploaded {uploaded} rows from {starting_version}-{ending_version} versions.')
            upload_count += uploaded
            self._flush_df_to_db(filtered_df, db_table_name)

        self._message(f'Ended uploading {table_name} on version {ending_version}, uploaded {upload_count} rows.')

    def mindbox_upload(self, endpoint_id, operation, db_table_name, secret_key, unique_field=None):
        """Получение и загрузка сущностей из mindbox api."""

        today = datetime.datetime.now()
        chunk = 10
        end = False
        url = f"https://api.mindbox.ru/v3/operations/sync?endpointId={endpoint_id}&operation={operation}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"SecretKey {secret_key}"
        }

        # На первой итерации возвращаемся на 10 дней назад, чтобы ничего не упустить.
        starting_date = self._get_mindbox_upload_starting_date(db_table_name) - datetime.timedelta(days=10)
        self._message(f'Started uploading from mindbox {operation}, starting date: {starting_date}')

        while True:
            ending_date = starting_date + datetime.timedelta(days=chunk)

            if ending_date > today:
                end = True
                chunk = (today - starting_date).days
                ending_date = starting_date + datetime.timedelta(days=chunk)

            export_id = self._get_export_id(url, headers, starting_date, ending_date)

            if export_id:
                request_body = {"exportId": export_id}

                params = {
                    'url': url,
                    'headers': headers,
                    'json': request_body,
                }
                response_urls = self._recursive_get_urls(requests.post, params)

                for response_url in response_urls:
                    response = requests.get(response_url)

                    if response.status_code == 200:
                        period = {'start': starting_date, 'end': ending_date}
                        df = self._process_mindbox_info(response, operation, ending_date, period)

                        if df is None or df.empty:
                            self._message(f'No data from {operation} from {starting_date} to {ending_date}')

                            if ending_date > today:
                                end = True

                            break
                        else:
                            self._flush_df_to_db(df, db_table_name, unique_field=unique_field, period=period)
            # Данных больше нет, завершаем цикл.
            if end:
                break

            starting_date += datetime.timedelta(days=chunk)

        self._message(f'Ended uploading {operation}.')

    def php_upload(self, endpoint, key):
        self._message(f'Starting uploading from {endpoint}.')

        url = f"https://senatnn.ru/local/api/analytic/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Key": key,
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            orders = response.json().get('orders')

            df = pd.DataFrame.from_dict(orders)
            df.rename(columns={'id': 'php_id', 'createdOn': 'created_on'}, inplace=True)

            self._flush_df_to_db(df, self.php_orders_db, unique_field='php_id')

    @staticmethod
    def yandex_upload(dimensions, yandex_id, sort, token):
        result = None
        url = "https://api-metrika.yandex.net/stat/v1/data"

        params = {
            "metrics": "ym:s:visits",
            "dimensions": dimensions,
            "id": yandex_id,
            "lang": "ru",
            "accuracy": 1,
            "sort": sort,
        }

        headers = {
            "Authorization": token
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            result = response.json()

        return result

    def _process_mindbox_info(self, response, operation, ending_date, period):
        df = None
        db_info = None

        if operation == self.customers_operation:
            customers = response.json()['customers']
            db_info = [
                {
                    'sex': customer.get('sex'),
                    'website_id': self.dict_getattr(customer, 'ids.websiteID'),
                    'mindbox_id': self.dict_getattr(customer, 'ids.mindboxId'),
                    'birth_date': customer.get('birthDate'),
                    'upload_date': ending_date,
                } for customer in customers
            ]
        elif operation == self.customers_actions_operation:
            actions = response.json()['customerActions']
            db_info = [
                {
                    'mindbox_id': self.dict_getattr(action, 'ids.mindboxId'),
                    'date_time_utc': action.get('dateTimeUtc'),
                    'action_template_name': self.dict_getattr(action, 'actionTemplate.name'),
                    'channel_name': self.dict_getattr(action, 'channel.name'),
                    'customer_id': self.dict_getattr(action, 'customer.ids.mindboxId'),
                    'upload_date': ending_date,
                    '_action': action,
                } for action in actions
            ]

            db_info = self._check_customers_ids(db_info, period)

        if db_info:
            df = pd.DataFrame(db_info)

        return df

    def _get_export_id(self, url, headers, starting_date, ending_date):
        """Получение export_id сформированных в mindbox данных."""

        result = None
        request_body = {
            "sinceDateTimeUtc": starting_date.strftime("%Y-%m-%d"),
            "tillDateTimeUtc": ending_date.strftime("%Y-%m-%d"),
        }

        response = requests.post(url, headers=headers, json=request_body)

        if response.status_code == 200:
            result = response.json().get('exportId')
        else:
            self._error(f"Error {response.status_code} while getting export_id: {response.text}")

        return result

    def _upload_dsh_orders(self):
        """Загрузка заказов с delta_sharing."""
        self.delta_sharing_upload(
            table_name=self.orders,
            db_table_name=self.dsh_orders_db,
            columns=self.orders_cols,
        )

    def _upload_purchase(self):
        """Загрузка покупок."""
        self.delta_sharing_upload(
            table_name=self.purchase,
            db_table_name=self.purchase_db,
            columns=self.purchase_cols,
        )

    def _upload_negative_customer_balance_change_details(self):
        """Загрузка сумм списания."""
        self.delta_sharing_upload(
            table_name=self.negative_customer_balance_change_details,
            db_table_name=self.negative_customer_balance_change_details_db,
            columns=self.negative_customer_balance_change_details_cols,
        )

    def _upload_point_od_contract(self):
        """Загрузка точек совершения покупок."""
        self.delta_sharing_upload(
            table_name=self.points_of_contract,
            db_table_name=self.points_of_contract_db,
            columns=self.points_of_contract_cols,
        )

    def _upload_purchase_statuses(self):
        """Загрузка точек совершения покупок."""
        self.delta_sharing_upload(
            table_name=self.purchase_statuses,
            db_table_name=self.purchase_statuses_db,
            columns=self.purchase_statuses_cols,
        )

    def _upload_customer(self):
        """Загрузка клиентов."""
        self.mindbox_upload(
            endpoint_id=self.stenatnn_analytics_bi,
            operation=self.customers_operation,
            secret_key=MINDBOX_CONFIG.get("mindbox", "customers_secret_key"),
            db_table_name=self.customers_bd,
            unique_field='mindbox_id',
        )

    def _upload_customer_actions(self):
        """Загрузка действий клиентов."""
        self.mindbox_upload(
            endpoint_id=self.stenatnn_analytics,
            operation=self.customers_actions_operation,
            secret_key=MINDBOX_CONFIG.get("mindbox", "actions_secret_key"),
            db_table_name=self.customers_actions_bd,
            unique_field='mindbox_id',
        )

    def _upload_php_orders(self):
        """Загрузка заказов с PHP."""
        self.php_upload(
            endpoint=PHP_CONFIG.get("php", "endpoint"),
            key=PHP_CONFIG.get("php", "key"),
        )

    def _upload_commerce_purchase(self):
        """Загрузка коммерческих покупок."""

        self._message(f'Starting uploading from yandex metrics.')
        same_params = dict(
            yandex_id=YANDEX_CONFIG.get('yandex', 'yandex_id'),
            sort="ym:s:visitID",
            token=YANDEX_CONFIG.get('yandex', 'token'),
        )

        first_part = self.yandex_upload(
            dimensions=self.commerce_purchase_dimensions_part_one,
            **same_params,
        )
        second_part = self.yandex_upload(
            dimensions=self.commerce_purchase_dimensions_part_two,
            **same_params,
        )
        third_part = self.yandex_upload(
            dimensions=self.commerce_purchase_dimensions_part_three,
            **same_params,
        )
        fourth_part = self.yandex_upload(
            dimensions=self.commerce_purchase_dimensions_part_four,
            **same_params,
        )

        result = []
        data = zip(first_part['data'], second_part['data'], third_part['data'], fourth_part['data'])

        # ¯\_(ツ)_/¯
        for first_dim, second_dim, third_dim, fourth_dim in data:
            first_dims_mapped = {
                key: value
                for num, key in enumerate(self.yandex_metrics_commerce_purchase_first_part_map)
                for value in first_dim['dimensions'][num].values()
            }
            second_dims_mapped = {
                key: value
                for num, key in enumerate(self.yandex_metrics_commerce_purchase_second_part_map)
                for value in second_dim['dimensions'][num].values()
            }
            third_dims_mapped = {
                key: value
                for num, key in enumerate(self.yandex_metrics_commerce_purchase_third_part_map)
                for value in third_dim['dimensions'][num].values()
            }
            fourth_dims_mapped = {
                key: value
                for num, key in enumerate(self.yandex_metrics_commerce_purchase_fourth_part_map)
                for value in fourth_dim['dimensions'][num].values()
            }

            first_dims_mapped.update(second_dims_mapped)
            first_dims_mapped.update(third_dims_mapped)
            first_dims_mapped.update(fourth_dims_mapped)

            result.append(first_dims_mapped)

        if result:
            df = pd.DataFrame(result)

            for key, value in self.yandex_metrics_fields_to_db_fields_map.items():
                if key in df:
                    df.rename(columns={key: value}, inplace=True)

            types = {
                'visit_id': str,
                'client_id': str,
            }

            self._flush_df_to_db(df, self.yandex_commerce_purchase_bd, unique_field='visit_id', types=types)

    def _check_customers_ids(self, db_info, period):
        """Проверка наличия полученных клиентов в БД. Если не нашли - создаем."""

        customers_ids = set((action.get('customer_id') for action in db_info))
        self.cursor.execute(f"SELECT mindbox_id FROM {self.customers_bd} WHERE mindbox_id IN {tuple(customers_ids)};")
        existed_ids = set(map(lambda row: row[0], self.cursor.fetchall()))
        nonexistent_ids = customers_ids - existed_ids

        if nonexistent_ids:
            actions = [(info['_action'], info['upload_date']) for info in db_info if info['customer_id'] in nonexistent_ids]
            self._message(f'Find {len(actions)} nonexistent customers.')
            customers_to_create = [
                {
                    'sex': self.dict_getattr(action[0], 'customer.sex'),
                    'website_id': self.dict_getattr(action[0], 'customer.ids.websiteID'),
                    'mindbox_id': self.dict_getattr(action[0], 'customer.ids.mindboxId'),
                    'birth_date': self.dict_getattr(action[0], 'customer.birthDate'),
                    'upload_date': action[1],
                } for action in actions
            ]

            df = pd.DataFrame(customers_to_create)
            self._flush_df_to_db(df, self.customers_bd, unique_field='mindbox_id', period=period)

        # К сожалению, я не придумал, как сделать лучше. Но хотя бы запрос в БД один.
        processed_info = []
        self.cursor.execute(f"SELECT id, mindbox_id FROM {self.customers_bd} WHERE mindbox_id IN {tuple(customers_ids)};")
        customers_ids_map = {data[1]: data[0] for data in self.cursor.fetchall()}

        for info in db_info:
            new_info = {}

            for key, value in info.items():
                if key == '_action':
                    continue
                elif key == 'customer_id':
                    new_info['customer_id'] = customers_ids_map[value]
                else:
                    new_info[key] = value
            processed_info.append(new_info)

        return processed_info

    def _get_mindbox_upload_starting_date(self, table_name):
        """Получаем дату последней загрузки данных в БД. Если ничего не грузилось, начинаем с начала 2024 года."""

        self.cursor.execute(f"SELECT upload_date FROM {table_name} ORDER BY upload_date DESC LIMIT 1")
        fetch = self.cursor.fetchone()

        return fetch[0] if fetch else datetime.datetime(2024, 1, 1)

    def _recursive_get_urls(self, func, params, attempt_num=0):
        """Попытки получить сформированные данные."""

        result = []
        attempts = 30
        timeout = 10

        if attempt_num < attempts:
            response = func(**params)

            if response.status_code == 200:
                response_json = response.json()

                if self.dict_getattr(response_json, 'exportResult.processingStatus') == 'Ready':
                    result = self.dict_getattr(response_json, 'exportResult.urls', [])
                else:
                    time.sleep(timeout)
                    result = self._recursive_get_urls(func, params, attempt_num + 1)
            else:
                time.sleep(timeout)
                result = self._recursive_get_urls(func, params, attempt_num + 1)

        return result

    def _init_names(self):
        """Инициализация названий таблиц."""

        self.orders = 'Orders'
        self.dsh_orders_db = 'df_delta_sharing_orders'

        self.purchase = 'Purchases'
        self.purchase_db = 'df_delta_sharing_purchases'

        self.negative_customer_balance_change_details = 'NegativeCustomerBalanceChangeDetails'
        self.negative_customer_balance_change_details_db = 'df_delta_sharing_negative_customer_balance_change'

        self.points_of_contract = 'PointsOfContact'
        self.points_of_contract_db = 'df_delta_sharing_points_of_contact'

        self.purchase_statuses = 'PurchaseStatuses'
        self.purchase_statuses_db = 'df_delta_sharing_purchase_statuses'

        self.stenatnn_analytics_bi = 'Senatnn.Analytics.BI'
        self.stenatnn_analytics = 'Senatnn.Analytics'

        self.customers_operation = 'Analytics.ExportCustomersBI'
        self.customers_bd = 'df_stenatnn_customers'

        self.customers_actions_operation = 'Analytics.ExportCustomerActions'
        self.customers_actions_bd = 'df_stenatnn_customers_actions'

        self.php_orders_db = 'df_php_orders'

        self.yandex_commerce_purchase_bd = 'df_yandex_commerce_purchase'

    def _init_columns_rules(self):
        """Инициализация столбцов, которые мы хотим получить и сохранить."""
        self.orders_cols = ORDERS_COLUMNS
        self.purchase_cols = PURCHASE_COLUMNS
        self.negative_customer_balance_change_details_cols = NEGATIVE_CUSTOMER_BALANCE_CHANGE_DETAILS_COLUMNS
        self.points_of_contract_cols = POINTS_OF_CONTRACT_COLUMNS
        self.purchase_statuses_cols = PURCHASE_STATUSES_COLUMNS

        self.commerce_purchase_dimensions_part_one = COMMERCE_PURCHASE_DIMENSIONS_PART_ONE
        self.commerce_purchase_dimensions_part_two = COMMERCE_PURCHASE_DIMENSIONS_PART_TWO
        self.commerce_purchase_dimensions_part_three = COMMERCE_PURCHASE_DIMENSIONS_PART_THREE
        self.commerce_purchase_dimensions_part_four = COMMERCE_PURCHASE_DIMENSIONS_PART_FOUR

    def _init_connections(self):
        """Инициализация подключений к базе."""

        self.connection = connect_to_db()
        self.cursor = self.connection.cursor()
        self.engine = create_alchemy_engine()

    def _init_tables(self):
        """Инициализация доступных для загрузки таблиц."""

        client = delta_sharing.SharingClient(PROFILE)
        self.tables = client.list_all_tables()

    def _init_helpers(self):
        """Инициализация вспомогательных переменных."""

        self.date_fields = [
            'birth_date',
            'date_time_utc',
            'created_on',
            'date_time',
        ]

    def _init_maps(self):
        """Инициализация вспомогательных мап."""

        self.yandex_metrics_commerce_purchase_first_part_map = {key: '' for key in self.commerce_purchase_dimensions_part_one.split(',')}
        self.yandex_metrics_commerce_purchase_second_part_map = {key: '' for key in self.commerce_purchase_dimensions_part_two.split(',')}
        self.yandex_metrics_commerce_purchase_third_part_map = {key: '' for key in self.commerce_purchase_dimensions_part_three.split(',')}
        self.yandex_metrics_commerce_purchase_fourth_part_map = {key: '' for key in self.commerce_purchase_dimensions_part_four.split(',')}

        self.yandex_metrics_fields_to_db_fields_map = {
            "ym:s:visitID": 'visit_id',
            "ym:s:purchaseID": 'purchase_id',
            "ym:s:purchaseRevenue": 'purchase_revenue',
            "ym:s:dateTime": 'date_time',
            "ym:s:clientID": 'client_id',
            "ym:s:TrafficSource": 'traffic_source',
            "ym:s:lastSearchEngine": 'last_search_engine',
            "ym:s:UTMSource": 'utm_source',
            "ym:s:UTMMedium": 'utm_medium',
            "ym:s:UTMCampaign": 'utm_campaign',
            "ym:s:UTMContent": 'utm_content',
            "ym:s:UTMTerm": 'utm_term',
            "ym:s:deviceCategory": 'device_category',
            "ym:s:ReferalSource": 'referal_source',
            "ym:s:goal": 'goal',
        }

    def _get_last_version(self, table_name):
        """Получаем последнюю загруженную версию."""

        self.cursor.execute(f"SELECT ending_version FROM {table_name} ORDER BY ending_version DESC LIMIT 1")
        fetch = self.cursor.fetchone()
        result = fetch[0] if fetch else None

        return result

    def _flush_df_to_db(self, df, table_name, unique_field=None, types=None, period=None):
        """Запись полученных данных в базу. Значением unique_field в df непременно должен быть INTEGER."""

        types = types or {}

        for date_field in self.date_fields:
            if date_field in df:
                df[date_field] = pd.to_datetime(df[date_field], format='mixed')

        if unique_field:
            df[unique_field] = pd.to_numeric(df[unique_field], errors='coerce')

            existing_ids = pd.read_sql_query(f"SELECT {unique_field} FROM {table_name}", self.engine)
            existing_ids[unique_field] = pd.to_numeric(existing_ids[unique_field], errors='coerce')
            existing_ids = existing_ids[unique_field].tolist() if not existing_ids.empty else []

            df = df[~df[unique_field].isin(existing_ids)]

        for col, _type in types.items():
            if col in df:
                df[col] = df[col].astype(_type)

        df.to_sql(
            name=table_name,
            con=self.engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000,
        )

        period_part =  f' (from {period["start"]} to {period["end"]})' if period else ''
        self._message(f'Uploaded {len(df)} rows to {table_name}{period_part}.')

    def close_connection(self):
        """Закрываем соединения с базой."""

        self.connection.close()
        self.engine.dispose()

    @staticmethod
    def _message(msg):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f'{now}: {msg}')

    @staticmethod
    def _error(msg):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.error(f'{now}: {msg}')

    @staticmethod
    def dict_getattr(data, path, default=None):
        keys = path.split('.')

        def _recursive_get(current_data, current_keys):
            result = None

            if not current_keys:
                result = current_data
            else:
                key = current_keys[0]

                if isinstance(current_data, dict) and key in current_data:
                    result = _recursive_get(current_data[key], current_keys[1:])

            return result or default

        return _recursive_get(data, keys)


if __name__ == '__main__':
    uploader = DeltaSharingUpload()
    uploader.run()
    uploader.close_connection()