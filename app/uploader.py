import datetime
import logging

import pandas as pd
from helpers.db_helpers import (
    connect_to_db,
    create_alchemy_engine,
)


class BaseUploader:
    """Базовый класс-загрузчик."""

    def __init__(self, *args, **kwargs):
        logging.basicConfig(
            filename='../upload.log',
            level=logging.INFO,
            format='%(levelname)s - %(message)s'
        )

        self._prepare_db()
        self._prepare_constants()

    def run(self):
        """Агла!"""
        raise NotImplementedError

    def _prepare_db(self):
        """Подготовка подключений к БД."""

        self.connection = connect_to_db()
        self.cursor = self.connection.cursor()
        self.engine = create_alchemy_engine()

    def _prepare_constants(self, *args, **kwargs):
        """Подготовка всех необходимых для загрузки данных."""

        self.date_fields = [
            'birth_date',
            'date_time_utc',
            'created_on',
            'date_time',
            'change_date_time_utc',
            'first_action_datetime_utc',
            'upload_date',
            'expiration_datetime_utc',
            'first_dim_upload_date',
            'second_dim_upload_date',
            'third_dim_upload_date',
        ]

    def _upload(self, *args, **kwargs):
        """Загрузка данных из источника."""
        raise NotImplementedError

    def _manage_data(self, *args, **kwargs):
        """Обработка полученных данных."""
        raise NotImplementedError

    def _flush_df(self, db_info, db_table_name, unique_field, ending_date, renames=None, from_dict=False, types=None):
        """Проверка и запись информации в БД."""

        no_data = False

        df = pd.DataFrame.from_dict(db_info) if from_dict else pd.DataFrame(db_info)

        if df is None or df.empty:
            no_data = True
        else:
            df['upload_date'] = ending_date
            self._flush(df, db_table_name, renames=renames, unique_field=unique_field, types=types)

        return no_data

    def _flush(
            self,
            df,
            table_name,
            unique_field=None,
            numeric_unique=True,
            types=None,
            renames=None,
            *args,
            **kwargs,
    ):
        """Запись полученных данных в базу."""

        types = types or {}

        if renames:
            df.rename(columns=renames, inplace=True)

        if unique_field:
            if numeric_unique:
                df[unique_field] = pd.to_numeric(df[unique_field], errors='coerce')

            existing_ids = pd.read_sql_query(f"SELECT {unique_field} FROM {table_name}", self.engine)
            existing_ids[unique_field] = pd.to_numeric(existing_ids[unique_field], errors='coerce')
            existing_ids = existing_ids[unique_field].tolist() if not existing_ids.empty else []

            df = df[~df[unique_field].isin(existing_ids)]

        for date_field in self.date_fields:
            if date_field in df:
                df.loc[:, date_field] = pd.to_datetime(df[date_field], format='mixed', dayfirst=True)

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

        self._message(
            f'\tuploaded {len(df)} rows to {table_name}'
            if not df.empty
            else f'\tNo new data available for {table_name}'
        )

    def _rebind_related_ids(self, data, id_field, bd):
        """Сверяем mindbox_id с записями в БД и перепривязываем настоящие id-шники."""

        mindbox_ids = [info[id_field] for info in data]

        if mindbox_ids:
            self.cursor.execute(f"SELECT id, mindbox_id FROM {bd} WHERE mindbox_id IN {tuple(mindbox_ids)};")
            ids_map = {data[1]: data[0] for data in self.cursor.fetchall()}

            for info in data:
                info[id_field] = ids_map[info[id_field]]

    def close_connections(self):
        """Закрытие соединений с БД."""

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
        """Ркурсивно получает значение из вложенного словаря, используя указанный путь."""

        keys = path.split('.')

        def _recursive_get(current_data, current_keys):
            result = None

            if not current_keys:
                result = current_data
            else:
                key = current_keys[0]

                if isinstance(current_data, dict) and key in current_data:
                    result = _recursive_get(current_data[key], current_keys[1:])

            return result if result is not None else default

        return _recursive_get(data, keys)
