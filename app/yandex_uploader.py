import pandas as pd
import requests
import datetime
import calendar
import configparser
from uploader import BaseUploader
from sqlalchemy import (
    MetaData,
    Table,
)
from sqlalchemy.dialects.postgresql import insert
from collections import defaultdict
from helpers.maps import (
    YANDEX_VISITS_DIMENSIONS_FIRST_MAP,
    YANDEX_VISITS_DIMENSIONS_SECOND_MAP,
    YANDEX_PURCHASE_DIMENSIONS_MAP,
    YANDEX_GOALS_DIMENSIONS_MAP,
    YANDEX_GOALS_TO_VISITS_FIELDS_MAP,
    YANDEX_PURCHASES_TO_VISITS_FIELDS_MAP,
)


YANDEX_CONFIG_PATH = 'configs/yandex.conf'
YANDEX_CONFIG = configparser.ConfigParser()
YANDEX_CONFIG.read(YANDEX_CONFIG_PATH)


pd.set_option('future.no_silent_downcasting', True)


class YandexUploader(BaseUploader):
    """Загрузка с яндекса."""

    def _prepare_constants(self):
        super()._prepare_constants()

        self.yandex_visits_bd = 'df_yandex_visits'
        self.yandex_purchases_bd = 'df_yandex_purchases'
        self.yandex_goals_bd = 'df_yandex_goals'

    def run(self):
        self._message('==YANDEX==')

        self._upload_visits(
            dimensions_parts=[
                YANDEX_VISITS_DIMENSIONS_FIRST_MAP,
                YANDEX_VISITS_DIMENSIONS_SECOND_MAP,
            ],
            db_table_name=self.yandex_visits_bd,
            metrics='ym:s:visits',
        )
        self._upload_purchases(
            dimensions_parts=[
                YANDEX_PURCHASE_DIMENSIONS_MAP,
            ],
            db_table_name=self.yandex_purchases_bd,
            metrics='ym:s:ecommercePurchases',
            fields_map=YANDEX_PURCHASES_TO_VISITS_FIELDS_MAP,
        )
        self._upload_goals(
            dimensions_parts=[
                YANDEX_GOALS_DIMENSIONS_MAP,
            ],
            db_table_name=self.yandex_goals_bd,
            metrics='ym:s:visits',
            fields_map=YANDEX_GOALS_TO_VISITS_FIELDS_MAP,
        )

        self._message('==YANDEX==')

    def _upload_visits( self, dimensions_parts,  db_table_name, metrics):
        today = datetime.datetime.now()
        end = False

        # Грузим сразу за месяц.
        starting_date = self._get_yandex_upload_starting_time(db_table_name, 'upload_date')
        starting_date = datetime.datetime(year=starting_date.year, month=starting_date.month, day=1)

        self._message(f'\n\tUploading from yandex metrics, starting date: {starting_date}')

        url = "https://api-metrika.yandex.net/stat/v1/data"

        headers = {"Authorization": YANDEX_CONFIG.get('yandex', 'token')}

        while True:
            dfs = []
            _, last_day = calendar.monthrange(starting_date.year, starting_date.month)
            ending_date = datetime.datetime(year=starting_date.year, month=starting_date.month, day=last_day)

            if ending_date > today:
                end = True

            self._message(f'\tProcessing data from {starting_date} to {ending_date}')

            for dimensions in dimensions_parts:
                params = {
                    "metrics": metrics,
                    "dimensions": ','.join(dimensions.keys()),
                    "id": YANDEX_CONFIG.get('yandex', 'yandex_id'),
                    "lang": "ru",
                    "accuracy": 1,
                    "sort": "ym:s:visitID",
                    "limit": 100000,
                }

                params.update({
                    'date1': starting_date.strftime('%Y-%m-%d'),
                    'date2': ending_date.strftime('%Y-%m-%d'),
                })

                request_params = {
                    'url': url,
                    'headers': headers,
                    'params': params,
                }

                response = requests.get(**request_params)

                if response.status_code == 200:
                    data = response.json()['data']

                    db_info = [
                        {
                            db_name: dims[num]['name']
                            for num, db_name in enumerate(list(dimensions.values()))
                        }
                        for info in data
                        for dims in [info['dimensions']]
                    ]

                    df = pd.DataFrame(db_info)

                    if not df.empty:
                        dfs.append(df)
                    else:
                        self._message('\t\tNo data')
                        break
                else:
                    self._error(f'ERROR while getting data, code {response.status_code}: {response.text}')
                    break

            if dfs:
                combined_df = dfs[0]

                for df in dfs[1:]:
                    combined_df = pd.merge(combined_df, df, on='visit_id', how='inner')

                combined_df['upload_date'] = ending_date

                if not combined_df.empty:
                    self._smart_flush(combined_df, db_table_name, ['visit_id'])

            if end:
                break

            starting_date = ending_date + datetime.timedelta(days=1)

    def _upload_purchases(self, dimensions_parts, db_table_name, metrics, fields_map):
        today = datetime.datetime.now()
        end = False

        # Грузим сразу за месяц.
        starting_date = self._get_yandex_upload_starting_time(db_table_name, 'upload_date')
        starting_date = datetime.datetime(year=starting_date.year, month=starting_date.month, day=1)

        self._message(f'\n\tUploading from yandex metrics, starting date: {starting_date}')

        url = "https://api-metrika.yandex.net/stat/v1/data"

        headers = {"Authorization": YANDEX_CONFIG.get('yandex', 'token')}

        while True:
            dfs = []
            _, last_day = calendar.monthrange(starting_date.year, starting_date.month)
            ending_date = datetime.datetime(year=starting_date.year, month=starting_date.month, day=last_day)

            if ending_date > today:
                end = True

            self._message(f'\tProcessing data from {starting_date} to {ending_date}')

            for dimensions in dimensions_parts:
                params = {
                    "metrics": metrics,
                    "dimensions": ','.join(dimensions.keys()),
                    "id": YANDEX_CONFIG.get('yandex', 'yandex_id'),
                    "lang": "ru",
                    "accuracy": 1,
                    "sort": "ym:s:visitID",
                    "limit": 100000,
                }

                params.update({
                    'date1': starting_date.strftime('%Y-%m-%d'),
                    'date2': ending_date.strftime('%Y-%m-%d'),
                })

                request_params = {
                    'url': url,
                    'headers': headers,
                    'params': params,
                }

                response = requests.get(**request_params)

                if response.status_code == 200:
                    data = response.json()['data']

                    db_info = [
                        {
                            db_name: dims[num]['name']
                            for num, db_name in enumerate(list(dimensions.values()))
                        }
                        for info in data
                        for dims in [info['dimensions']]
                    ]

                    if fields_map:
                        db_info = self._manage_data(db_info, fields_map)

                    df = pd.DataFrame(db_info)

                    if not df.empty:
                        dfs.append(df)
                    else:
                        self._message('\t\tNo data')
                        break
                else:
                    self._error(f'ERROR while getting data, code {response.status_code}: {response.text}')
                    break

            if dfs:
                combined_df = dfs[0]

                for df in dfs[1:]:
                    combined_df = pd.merge(combined_df, df, on='visit_id', how='inner')

                combined_df['upload_date'] = ending_date

                if not combined_df.empty:
                    self._smart_flush(combined_df, db_table_name, ['yandex_visit_id', 'purchase_id'])

            if end:
                break

            starting_date = ending_date + datetime.timedelta(days=1)

    def _upload_goals(self, dimensions_parts, db_table_name, metrics, fields_map):
        today = datetime.datetime.now()
        end = False

        # Грузим сразу за месяц, но начиная со следующего дня от последней загруженной даты, тк именно цели не можем проверить на уникальность.
        starting_date = self._get_yandex_upload_starting_time(db_table_name, 'upload_date') + datetime.timedelta(days=1)

        if starting_date > today:
            self._message(f'All ready uploaded newest data for date: {starting_date - datetime.timedelta(days=1)}')
            return

        self._message(f'\n\tUploading from yandex metrics, starting date: {starting_date}')

        url = "https://api-metrika.yandex.net/stat/v1/data"

        headers = {"Authorization": YANDEX_CONFIG.get('yandex', 'token')}

        while True:
            dfs = []
            _, last_day = calendar.monthrange(starting_date.year, starting_date.month)
            ending_date = datetime.datetime(year=starting_date.year, month=starting_date.month, day=last_day)

            if ending_date > today:
                end = True

            self._message(f'\tProcessing data from {starting_date} to {ending_date}')

            for dimensions in dimensions_parts:
                params = {
                    "metrics": metrics,
                    "dimensions": ','.join(dimensions.keys()),
                    "id": YANDEX_CONFIG.get('yandex', 'yandex_id'),
                    "lang": "ru",
                    "accuracy": 1,
                    "sort": "ym:s:visitID",
                    "limit": 100000,
                }

                params.update({
                    'date1': starting_date.strftime('%Y-%m-%d'),
                    'date2': ending_date.strftime('%Y-%m-%d'),
                })

                request_params = {
                    'url': url,
                    'headers': headers,
                    'params': params,
                }

                response = requests.get(**request_params)

                if response.status_code == 200:
                    data = response.json()['data']

                    db_info = [
                        {
                            db_name: dims[num]['name']
                            for num, db_name in enumerate(list(dimensions.values()))
                        }
                        for info in data
                        for dims in [info['dimensions']]
                    ]

                    if fields_map:
                        db_info = self._manage_data(db_info, fields_map)

                    df = pd.DataFrame(db_info)

                    if not df.empty:
                        dfs.append(df)
                    else:
                        self._message('\t\tNo data')
                        break
                else:
                    self._error(f'ERROR while getting data, code {response.status_code}: {response.text}')
                    break

            if dfs:
                combined_df = dfs[0]

                for df in dfs[1:]:
                    combined_df = pd.merge(combined_df, df, on='visit_id', how='inner')

                combined_df['upload_date'] = ending_date
                combined_df.dropna(inplace=True)

                if not combined_df.empty:
                    self._smart_flush(combined_df, db_table_name)

            if end:
                break

            starting_date = ending_date + datetime.timedelta(days=1)

    def _smart_flush(self, df, db_table_name, unique_rows=None):
        metadata = MetaData()
        table = Table(db_table_name, metadata, autoload_with=self.engine)

        batch_size = 5000
        batches = [df[i:i + batch_size] for i in range(0, len(df), batch_size)]

        updated_count = created_count = 0

        for batch in batches:
            records = tuple([row.to_dict() for _, row in batch.iterrows()])
            updated_count = 0
            created_count = 0
            statement = insert(table).values(records)

            if unique_rows:
                unique_values = tuple((tuple(row[key] for key in unique_rows) for row in records))

                if len(unique_rows) == 1:
                    unique_values = tuple(zip(*unique_values))[0]

                rows_to_update = self._get_count_query(db_table_name, ', '.join(unique_rows), unique_values)
                updated_count += rows_to_update
                created_count += len(records) - rows_to_update

                upsert_statement = statement.on_conflict_do_update(
                    index_elements=unique_rows,
                    set_={
                        col: getattr(statement.excluded, col)
                        for col in table.columns.keys()
                        if col not in ['id']
                    },
                )
            else:
                created_count += len(records)
                upsert_statement = statement.on_conflict_do_update(
                    index_elements=['id'],
                    set_={
                        col: getattr(statement.excluded, col)
                        for col in table.columns.keys()
                        if col not in ['id']
                    },
                )

            compiled_statement = upsert_statement.compile(compile_kwargs={"literal_binds": False})
            sql_query = str(compiled_statement)  # SQL-запрос
            params = compiled_statement.params  # Параметры

            self.cursor.execute(sql_query, params)
            self.connection.commit()

        self._message(f'\t\tproceeded {len(df)} rows:')
        self._message(
            f'\t\t existing rows: {updated_count} (updated, if needed); '
            f'created: {created_count}, in table {db_table_name}'
        )

    def _manage_data(self, db_info, fields_map):
        """Ищем записи, на которые ссылаются полученные данные. Если нашли несколько записей, клонируем данные так, чтобы связать с каждой."""

        parent_db = fields_map['parent_db']
        field_from = fields_map['from']
        field_to = fields_map['to']

        values_to_map = tuple(info[field_from] for info in db_info)
        db_values = self._get_fields_map_values(field_to, values_to_map, parent_db)
        db_map = {key: value for key, value in db_values}
        reversed_db_map = defaultdict(list)

        for key, value in db_map.items():
            reversed_db_map[value].append(key)

        map = dict(reversed_db_map)
        result = []

        for info in db_info:
            key = info[field_from]
            ids_to_map = map.get(key)

            if ids_to_map:
                for _id in ids_to_map:
                    result.append({
                        field_from: _id,
                        **{key: value for key, value in info.items() if key != field_from},
                    })

        return result

    def _get_yandex_upload_starting_time(self, table_name, db_date_field):
        """Получаем дату последней загрузки данных в БД. Если ничего не грузилось, начинаем с 02.05.2024."""

        result = None
        self.cursor.execute(f"SELECT {db_date_field} FROM {table_name} WHERE {db_date_field} IS NOT NULL ORDER BY {db_date_field} DESC LIMIT 1")
        fetch = self.cursor.fetchone()

        if fetch:
            result = fetch[0]

        return result if result else datetime.datetime(2023, 1, 1)

    def _get_count_query(self, table, field, records):
        self.cursor.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE ({field}) in {records}
        """)
        fetch = self.cursor.fetchone()

        return fetch[0]

    def _get_fields_map_values(self, field_to, values_to_map, table):
        self.cursor.execute(f"""
            SELECT id, {field_to}
            FROM {table}
            WHERE {field_to} IN {values_to_map}
        """)
        fetch = self.cursor.fetchall()

        return fetch
