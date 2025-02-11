import configparser
import datetime

import pandas as pd
import requests
import time

from helpers.maps import CUSTOMERS_MAP, ACTIONS_MAP, ORDERS_MAP, LINES_MAP, BONUS_POINTS_MAP, PROMOTIONS_MAP
from uploader import BaseUploader


MINDBOX_CONFIG_PATH = 'configs/mindbox.conf'
MINDBOX_CONFIG = configparser.ConfigParser()
MINDBOX_CONFIG.read(MINDBOX_CONFIG_PATH)


class MindboxUploader(BaseUploader):
    """Загрузка из mindbox."""

    def _prepare_constants(self):
        super()._prepare_constants()

        self.stenatnn_analytics_bi = 'Senatnn.Analytics.BI'
        self.stenatnn_analytics = 'Senatnn.Analytics'

        self.customers_operation = 'Analytics.ExportCustomersBI'
        self.customers_bd = 'df_stenatnn_customers'

        self.customers_actions_operation = 'Analytics.ExportCustomerActions'
        self.customers_actions_bd = 'df_stenatnn_customers_actions'

        self.orders_operation = 'Analytics.ExportOrderJson'
        self.orders_bd = 'df_stenatnn_orders'
        self.order_lines_bd = 'df_stenatnn_order_lines'
        self.applied_promotions_bd = 'df_stenattn_applied_promotions'
        self.bonus_points_info_bd = 'df_stenattn_bonus_points_info'

    def run(self):
        self._message('==MINDBOX==')

        self._upload(
            endpoint_id=self.stenatnn_analytics_bi,
            operation=self.customers_operation,
            secret_key=MINDBOX_CONFIG.get("mindbox", "customers_secret_key"),
            db_table_name = self.customers_bd,
            unique_field = 'mindbox_id',
        )

        self._upload(
            endpoint_id=self.stenatnn_analytics,
            operation=self.customers_actions_operation,
            secret_key=MINDBOX_CONFIG.get("mindbox", "actions_secret_key"),
            db_table_name=self.customers_actions_bd,
            unique_field='mindbox_id',
        )

        self._upload(
            endpoint_id=self.stenatnn_analytics,
            operation=self.orders_operation,
            secret_key=MINDBOX_CONFIG.get("mindbox", "orders_secret_key"),
            db_table_name=self.orders_bd,
            unique_field='mindbox_id',
        )

        self._message('==MINDBOX==')

    def _upload(self, endpoint_id, operation, db_table_name, secret_key, unique_field=None):
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
        self._message(f'Started uploading from {operation}, starting date: {starting_date}')

        while True:
            ending_date = starting_date + datetime.timedelta(days=chunk)

            if ending_date > today:
                end = True
                chunk = (today - starting_date).days
                ending_date = starting_date + datetime.timedelta(days=chunk + 1)

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
                        self._message(f'Processing {operation}, from {starting_date} to {ending_date}:')

                        no_data = self._manage_data(
                            response,
                            operation,
                            ending_date,
                            db_table_name,
                            unique_field,
                            period,
                        )

                        if no_data:
                            self._message(f'\tNo data from {operation} from {starting_date} to {ending_date}')

                            if ending_date > today:
                                end = True

                            break

            # Данных больше нет, завершаем цикл.
            if end:
                break

            starting_date += datetime.timedelta(days=chunk)

        self._message(f'Ended uploading {operation}.')

    def _manage_data(self, response, operation, ending_date, db_table_name, unique_field, period):
        no_data = False

        if operation == self.customers_operation:
            customers = response.json()['customers']
            db_info = [
                {
                    db_key: self.dict_getattr(customer, api_key)
                    for db_key, api_key in CUSTOMERS_MAP.items()
                }
                for customer in customers
            ]

            no_data = self._flush_df(db_info, db_table_name, unique_field, ending_date)

        elif operation == self.customers_actions_operation:
            actions = response.json()['customerActions']
            self._process_nonexistent_customers(actions, period, ending_date)

            db_info = [
                {
                    db_key: self.dict_getattr(action, api_key)
                    for db_key, api_key in ACTIONS_MAP.items()
                }
                for action in actions
            ]

            self._rebind_related_ids(db_info, 'customer_id', self.customers_bd)
            no_data = self._flush_df(db_info, db_table_name, unique_field, ending_date)

        elif operation == self.orders_operation:
            orders = response.json()['orders']
            self._process_nonexistent_customers(orders, period, ending_date)

            db_info = [
                {
                    db_key: self.dict_getattr(order, api_key)
                    for db_key, api_key in ORDERS_MAP.items()
                }
                for order in orders
            ]

            self._rebind_related_ids(db_info, 'customer_id', self.customers_bd)
            no_data = self._flush_df(db_info, db_table_name, unique_field, ending_date)

            if not no_data:
                self._process_lines(orders, ending_date)
                self._process_applied_promotions(orders, ending_date)
                self._process_bonus_points_info(orders, ending_date)

        return no_data

    def _process_nonexistent_customers(self, data, period, ending_date):
        """Проверка наличия полученных клиентов в БД. Если не нашли - создаем."""

        customers = [
            {
                db_key: self.dict_getattr(customer, api_key)
                for db_key, api_key in CUSTOMERS_MAP.items()
            } for customer in [info['customer'] for info in data]
        ]

        customers_ids = set((customer.get('mindbox_id') for customer in customers))

        if customers_ids:
            self.cursor.execute(f"SELECT mindbox_id FROM {self.customers_bd} WHERE mindbox_id IN {tuple(customers_ids)};")
            existed_ids = set(map(lambda row: row[0], self.cursor.fetchall()))
            nonexistent_ids = customers_ids - existed_ids

            if nonexistent_ids:
                self._message(f'\t\tfind {len(customers)} nonexistent customers.')

                df = pd.DataFrame(customers)
                df['upload_date'] = ending_date

                self._flush(df, self.customers_bd, unique_field='mindbox_id')

    def _process_lines(self, data, ending_date):
        """Сохранение позиций заказа."""

        lines = [
            {
                **line,
                'order_id': self.dict_getattr(order, 'ids.mindboxId')
            }
            for order in data
            if 'lines' in order
            for line in order['lines']
        ]
        db_info = [
            {
                db_key: self.dict_getattr(line, api_key)
                for db_key, api_key in LINES_MAP.items()
            }
            for line in lines
        ]

        self._rebind_related_ids(db_info, 'order_id', self.orders_bd)
        self._flush_df(db_info, self.order_lines_bd, unique_field=None, ending_date=ending_date)

    def _process_applied_promotions(self, data, ending_date):
        """Сохранение акций. Реализована только связь с order, как лепить к line - без понятия..."""

        promotions = [
            {
                **promotion,
                'order_id': self.dict_getattr(order, 'ids.mindboxId')
            }
            for order in data
            if 'appliedPromotions' in order
            for promotion in order['appliedPromotions']
        ]
        db_info = [
            {
                db_key: self.dict_getattr(promotion, api_key)
                for db_key, api_key in PROMOTIONS_MAP.items()
            }
            for promotion in promotions
        ]

        self._rebind_related_ids(db_info, 'order_id', self.orders_bd)
        self._flush_df(db_info, self.applied_promotions_bd, unique_field=None, ending_date=ending_date)

    def _process_bonus_points_info(self, data, ending_date):
        """Сохранение бонусных баллов."""

        bonuses = [
            {
                **bonus,
                'order_id': self.dict_getattr(order, 'ids.mindboxId')
            }
            for order in data
            if 'bonusPointsInfoPerBalanceTypes' in order
            for bonus in order['bonusPointsInfoPerBalanceTypes']
        ]
        db_info = [
            {
                db_key: self.dict_getattr(bonus, api_key)
                for db_key, api_key in BONUS_POINTS_MAP.items()
            }
            for bonus in bonuses
        ]

        self._rebind_related_ids(db_info, 'order_id', self.orders_bd)
        self._flush_df(db_info, self.bonus_points_info_bd, unique_field=None, ending_date=ending_date)

    def _get_mindbox_upload_starting_date(self, table_name):
        """Получаем дату последней загрузки данных в БД. Если ничего не грузилось, начинаем с начала 2024 года."""

        self.cursor.execute(f"SELECT upload_date FROM {table_name} ORDER BY upload_date DESC LIMIT 1")
        fetch = self.cursor.fetchone()

        return fetch[0] if fetch else datetime.datetime(2023, 1, 1)

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
            self._error(f"\t\tError {response.status_code} while getting export_id: {response.text}")

        return result

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

    def _rebind_customers_ids(self, data):
        """Привязываем id-шники заказчиков вместо mindboxId."""

        mindbox_ids = [info['customer_id'] for info in data]

        self.cursor.execute(f"SELECT id, mindbox_id FROM {self.customers_bd} WHERE mindbox_id IN {tuple(mindbox_ids)};")
        customers_ids_map = {data[1]: data[0] for data in self.cursor.fetchall()}

        for info in data:
            info['customer_id'] = customers_ids_map[info['customer_id']]
