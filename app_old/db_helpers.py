import psycopg2
import configparser
from sqlalchemy import create_engine


CONFIG = 'postgres.conf'


def prepare_db_params():
    config = configparser.ConfigParser()
    config.read(CONFIG)

    db_params = {
        "host": config.get("postgresql", "host"),
        "port": config.get("postgresql", "port"),
        "dbname": config.get("postgresql", "dbname"),
        "user": config.get("postgresql", "user"),
        "password": config.get("postgresql", "password")
    }

    return db_params

def connect_to_db():
    return psycopg2.connect(**prepare_db_params())


def create_alchemy_engine():
    db_params = prepare_db_params()
    connection_url = (
        f"postgresql+psycopg2://{db_params['user']}:{db_params['password']}"
        f"@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
    )
    engine = create_engine(connection_url)

    return engine
