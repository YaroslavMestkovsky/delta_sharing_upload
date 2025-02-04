import pandas as pd
import requests
import datetime

from helpers.enums import (
    COMMERCE_PURCHASE_DIMENSIONS_PART_ONE,
    COMMERCE_PURCHASE_DIMENSIONS_PART_TWO,
    COMMERCE_PURCHASE_DIMENSIONS_PART_THREE,
    COMMERCE_PURCHASE_DIMENSIONS_PART_FOUR,
)
from uploader import BaseUploader
import configparser


YANDEX_CONFIG_PATH = 'configs/yandex.conf'
YANDEX_CONFIG = configparser.ConfigParser()
YANDEX_CONFIG.read(YANDEX_CONFIG_PATH)


class YandexUploader(BaseUploader):
    """Загрузка с yandex. Здесь всё очень плохо, но времени написать нормально не было."""

    def __init__(self):
        super().__init__()

        self._init_maps()

    def _prepare_constants(self):
        super()._prepare_constants()

        self.dimensions = [
            COMMERCE_PURCHASE_DIMENSIONS_PART_ONE,
            COMMERCE_PURCHASE_DIMENSIONS_PART_TWO,
            COMMERCE_PURCHASE_DIMENSIONS_PART_THREE,
            COMMERCE_PURCHASE_DIMENSIONS_PART_FOUR,
        ]
        self.yandex_commerce_purchase_bd = 'df_yandex_commerce_purchase'

    def run(self):
        self._message('==YANDEX==')

        self._upload(
            yandex_id=YANDEX_CONFIG.get('yandex', 'yandex_id'),
            sort="ym:s:visitID",
            token=YANDEX_CONFIG.get('yandex', 'token'),
            db_table_name=self.yandex_commerce_purchase_bd
        )

        self._message('==YANDEX==')

    def _upload(self, yandex_id, sort, token, db_table_name):
        """Загрузка коммерческих покупок.

        В связи с особенностями источника, грузим частями, которые затем объединяем.
        """

        today = datetime.datetime.now()
        chunk = 10
        end = False

        # На первой итерации возвращаемся на 10 дней назад, чтобы ничего не упустить.
        starting_date = self._get_yandex_upload_starting_time(db_table_name) - datetime.timedelta(days=10)
        self._message(f'Started uploading from yandex metrics, starting date: {starting_date}')

        url = "https://api-metrika.yandex.net/stat/v1/data"

        headers = {
            "Authorization": token
        }
        params = {
            "metrics": "ym:s:visits",
            "id": yandex_id,
            "lang": "ru",
            "accuracy": 1,
            "sort": sort,
        }

        while True:
            ending_date = starting_date + datetime.timedelta(days=chunk)

            if ending_date > today:
                end = True
                chunk = (today - starting_date).days
                ending_date = starting_date + datetime.timedelta(days=chunk + 1)

            self._message(f'Processing yandex_metrics from {starting_date} to {ending_date}')
            date_filter = (
                f"ym:s:dateTime>='{starting_date.strftime('%Y-%m-%d')}' AND "
                f"ym:s:dateTime<='{ending_date.strftime('%Y-%m-%d')}'"
            )
            params.update({'filters': date_filter})

            parts = []

            for dimension in self.dimensions:
                params.update({'dimensions': dimension})

                request_params = {
                    'url': url,
                    'headers': headers,
                    'params': params,
                }
                response = requests.get(**request_params)

                if response.status_code == 200:
                    parts.append(response.json()['data'])

            result = []

            if all(parts):
                data = zip(*parts)

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
                df['upload_date'] = ending_date

                for key, value in self.yandex_metrics_fields_to_db_fields_map.items():
                    if key in df:
                        df.rename(columns={key: value}, inplace=True)

                types = {
                    'visit_id': str,
                    'client_id': str,
                }

                self._flush(df, self.yandex_commerce_purchase_bd, unique_field='visit_id', types=types)
            else:
                self._message(f'\tno data from {starting_date} to {ending_date}.')
            if end:
                break

            starting_date = ending_date + datetime.timedelta(days=chunk)

        self._message(f'Ended uploading from yandex_metrics.')

    def _init_maps(self):
        """Инициализация вспомогательных мап."""

        self.yandex_metrics_commerce_purchase_first_part_map = {key: '' for key in COMMERCE_PURCHASE_DIMENSIONS_PART_ONE.split(',')}
        self.yandex_metrics_commerce_purchase_second_part_map = {key: '' for key in COMMERCE_PURCHASE_DIMENSIONS_PART_TWO.split(',')}
        self.yandex_metrics_commerce_purchase_third_part_map = {key: '' for key in COMMERCE_PURCHASE_DIMENSIONS_PART_THREE.split(',')}
        self.yandex_metrics_commerce_purchase_fourth_part_map = {key: '' for key in COMMERCE_PURCHASE_DIMENSIONS_PART_FOUR.split(',')}

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

    def _manage_data(self, *args, **kwargs):
        """"""

    def _get_yandex_upload_starting_time(self, table_name):
        """Получаем дату последней загрузки данных в БД. Если ничего не грузилось, начинаем с 02.05.2024."""

        self.cursor.execute(f"SELECT upload_date FROM {table_name} ORDER BY upload_date DESC LIMIT 1")
        fetch = self.cursor.fetchone()

        return fetch[0] if fetch else datetime.datetime(2024, 5, 2)
