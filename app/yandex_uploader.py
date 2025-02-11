import pandas as pd
import requests
import datetime
from collections import defaultdict
from psycopg2.extras import execute_values
from helpers.maps import (
    YANDEX_DIMENSIONS_ONE_MAP,
    YANDEX_DIMENSIONS_TWO_MAP,
    YANDEX_DIMENSIONS_THREE_MAP,
    YANDEX_DIMENSIONS_FOUR_MAP,
    YANDEX_GOALS_TO_VISITS_FIELDS_MAP,
)
from helpers.enums import YANDEX_UPLOAD_TIME_PARTS
from uploader import BaseUploader
import configparser


YANDEX_CONFIG_PATH = 'configs/yandex.conf'
YANDEX_CONFIG = configparser.ConfigParser()
YANDEX_CONFIG.read(YANDEX_CONFIG_PATH)


class YandexUploader(BaseUploader):
    """Загрузка с яндекса."""

    def _prepare_constants(self):
        super()._prepare_constants()

        self.yandex_visits_bd = 'df_yandex_visits'
        self.yandex_goals_bd = 'df_yandex_goals'

    def run(self):
        self._message('==YANDEX==')

        self._upload_dimensions(
            dimensions=YANDEX_DIMENSIONS_ONE_MAP,
            db_table_name=self.yandex_visits_bd,
            db_date_field=YANDEX_UPLOAD_TIME_PARTS['ONE'],
            metrics='ym:s:ecommercePurchases',
            unique_selection='purchase_id, visit_id',
        )
        self._upload_dimensions(
            dimensions=YANDEX_DIMENSIONS_TWO_MAP,
            db_table_name=self.yandex_visits_bd,
            db_date_field=YANDEX_UPLOAD_TIME_PARTS['TWO'],
            unique_selection='purchase_id, visit_id',
        )
        self._upload_dimensions(
            dimensions=YANDEX_DIMENSIONS_THREE_MAP,
            db_table_name=self.yandex_visits_bd,
            db_date_field=YANDEX_UPLOAD_TIME_PARTS['THREE'],
            unique_selection='purchase_id, visit_id',
        )
        self._upload_dimensions(
            dimensions=YANDEX_DIMENSIONS_FOUR_MAP,
            db_table_name=self.yandex_goals_bd,
            db_date_field=YANDEX_UPLOAD_TIME_PARTS['FOUR'],
            fields_map=YANDEX_GOALS_TO_VISITS_FIELDS_MAP,
            unique_selection='yandex_visit_id, goal',
            need_indexing=False,
        )

        self._message('==YANDEX==')

    def _upload_dimensions(
            self,
            dimensions,
            db_table_name,
            db_date_field,
            metrics='ym:s:visits',
            fields_map=None,
            unique_selection=None,
            need_indexing=True,
    ):
        dims = ', '.join(dimensions.keys())
        self._message(f"Processing dimensions: {dims}")
        self._upload(
            yandex_id=YANDEX_CONFIG.get('yandex', 'yandex_id'),
            sort="ym:s:visitID",
            metrics=metrics,
            token=YANDEX_CONFIG.get('yandex', 'token'),
            dimensions=dimensions,
            db_table_name=db_table_name,
            db_date_field=db_date_field,
            fields_map=fields_map,
            unique_selection=unique_selection,
            need_indexing=need_indexing,
        )
        self._message(f'Done processing dimensions: {dims}')

    def _upload(
            self,
            yandex_id,
            sort,
            token,
            dimensions,
            metrics,
            db_table_name,
            db_date_field,
            fields_map,
            unique_selection,
            need_indexing,
    ):
        """В связи с особенностями источника, грузим частями, которые затем объединяем."""

        today = datetime.datetime.now()
        chunk = 10
        end = False
        # На первой итерации возвращаемся на 10 дней назад, чтобы ничего не упустить.
        starting_date = self._get_yandex_upload_starting_time(db_table_name, db_date_field) - datetime.timedelta(days=10)
        self._message(f'\tUploading from yandex metrics, starting date: {starting_date}')

        url = "https://api-metrika.yandex.net/stat/v1/data"

        headers = {
            "Authorization": token
        }
        params = {
            "metrics": metrics,
            "dimensions": ','.join(dimensions.keys()),
            "id": yandex_id,
            "lang": "ru",
            "accuracy": 1,
            "sort": sort,
            "limit": 100000,
        }

        while True:
            ending_date = starting_date + datetime.timedelta(days=chunk)

            if ending_date > today:
                end = True
                chunk = (today - starting_date).days
                ending_date = starting_date + datetime.timedelta(days=chunk + 1)

            self._message(f'\tProcessing data from {starting_date} to {ending_date}')

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

                if data:
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
                    self._smart_flush(df, db_table_name, ending_date, db_date_field, unique_selection, need_indexing)
                else:
                    self._message('\t\tNo data found')
            if end:
                break

            starting_date = ending_date + datetime.timedelta(days=chunk)

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

    def _smart_flush(self, df, table, ending_date, db_date_field, unique_selection, need_indexing=True):
        """Обновляем существующие/создаем новые."""

        for date_field in self.date_fields:
            if date_field in df:
                df.loc[:, date_field] = pd.to_datetime(df[date_field], format='mixed', dayfirst=True)

        unique_selection_split = unique_selection.split(', ')
        columns_to_flush = (
            [col for col in df.columns if col not in unique_selection_split]
            if need_indexing
            else df.columns.to_list()
        )

        query = self._get_old_records_query(table, df, unique_selection)
        db_df = pd.read_sql(query, self.engine)
        db_df.drop(
            columns=[
                'id',
                *[col for col in YANDEX_UPLOAD_TIME_PARTS.values() if col != db_date_field and col in db_df],
            ],
            axis=1,
            inplace=True,
        )

        # Устанавливаем unique_id как индекс для обоих df - если требуется
        if need_indexing:
            df.set_index(unique_selection_split, inplace=True)
            db_df.set_index(unique_selection_split, inplace=True)

        rows_from_db = set(tuple(row) for row in db_df[columns_to_flush].iloc)
        rows_from_api = set(tuple(row) for row in df[columns_to_flush].iloc)
        rows_to_update = len(rows_from_db - rows_from_api)

        if rows_to_update > 0:
            # Обновляем то, что есть
            db_df.update(df)

        # И создаем новые
        new_rows = df.loc[~df.index.isin(db_df.index)].reindex(columns=db_df.columns, fill_value=None)
        rows_to_create = len(new_rows)

        if not new_rows.empty:
            db_df = pd.concat([db_df, new_rows]) if not db_df.empty else new_rows

        if rows_to_create or rows_to_update:
            db_df.reset_index(inplace=True)
            db_df[db_date_field] = ending_date
            db_df = db_df.where(pd.notnull(db_df), None)

            if 'index' in db_df:
                db_df.drop(['index'], axis=1, inplace=True)

            data = [tuple(row) for row in db_df.to_numpy()]
            # Cобираем колонки для апдейтов
            columns = [col for col in db_df.columns.tolist()]
            update_clause = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns])
            columns = ', '.join(columns)

            # SQL-запрос для UPSERT
            upsert_query = self._get_upsert_query(table, columns, update_clause, unique_selection)

            execute_values(self.cursor, upsert_query, data)
            self.connection.commit()

        self._message(f'{len(df)} records proceeded. {rows_to_create} created, {rows_to_update} updated.')

    @staticmethod
    def _get_old_records_query(table, df, unique_selection):
        keys = unique_selection.split(', ')
        selections = tuple(zip(*(df[key].fillna("") for key in keys)))

        return f"""
            SELECT *
            FROM {table}
            WHERE ({unique_selection}) IN {selections}
        """

    @staticmethod
    def _get_upsert_query(table, columns, update_clause, unique_selection):
        return f"""
            INSERT INTO {table} ({columns})
            VALUES %s
            ON CONFLICT ({unique_selection})
            DO UPDATE SET
                {update_clause};
        """

    def _get_fields_map_values(self, field_to, values_to_map, table):
        self.cursor.execute(f"""
            SELECT id, {field_to}
            FROM {table}
            WHERE {field_to} IN {values_to_map}
        """)
        fetch = self.cursor.fetchall()

        return fetch
