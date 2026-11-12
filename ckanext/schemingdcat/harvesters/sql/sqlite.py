import logging
import sqlite3

from ckanext.schemingdcat.harvesters.sql.base import SchemingDCATSQLHarvester, DatabaseManager

log = logging.getLogger(__name__)


class SqliteDatabaseManager(DatabaseManager):
    def connect(self):
        self._connection = sqlite3.connect(self.db_path)

    def disconnect(self):
        if self._connection:
            self._connection.close()

    def execute_query(self, query):
        pass

# TODO: SQLite Harvester using interfaces
class SchemingDCATSQLiteHarvester(SchemingDCATSQLHarvester):
    """
    A custom harvester for harvesting SQLite databases using the schemingdcat extension.

    It extends the base `SchemingDCATSQLHarvester` class.
    """

    def info(self):
        return {
            'name': 'schemingdcat_sqlite_harvester',
            'title': 'SQLite Database Harvester',
            'description': 'An SQLite database harvester for CKAN'
        }
    
    db_manager = SqliteDatabaseManager()
    _db_path = None
    _connection = None