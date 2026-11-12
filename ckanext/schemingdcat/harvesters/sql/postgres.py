import logging
import time
import uuid

import pandas as pd
import psycopg2

from ckanext.schemingdcat.utils import (
    normalize_temporal_dates,
    normalize_reference_system,
    normalize_resources,
    sql_clauses
)
from ckanext.schemingdcat.harvesters.sql.base import SchemingDCATSQLHarvester, DatabaseManager

log = logging.getLogger(__name__)


class PostgresDatabaseManager(DatabaseManager):
    connection = None

    def connect(self, conn_url):
        try:
            self.connection = psycopg2.connect(conn_url)
        except psycopg2.Error as e:
            raise ValueError('Error connecting to the database: %s', e)

    def check_connection(self, conn_url, retry=None):
        if retry is None:
            retry = self._retry
        elif retry == 0:
            log.info('Giving up after 5 tries...')
            raise ValueError('Unable to connect to the database after %s retries.', retry)

        try:
            connection = psycopg2.connect(conn_url)
        except psycopg2.Error as e:
            log.debug(str(e))
            log.info('Unable to connect to the database, waiting...')
            time.sleep(10)
            self.check_connection(conn_url, retry=retry - 1)
        else:
            connection.close()
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute_query(self, query):
        if not self.connection:
            try:
                self.connect()
            except psycopg2.Error as e: 
                raise ValueError('Database connection is not established: %s' % e)
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Always select queries, only fetchall is required.
            results = cursor.fetchall()
            
            # Obtener los nombres de las columnas de la consulta
            column_names = [desc[0] for desc in cursor.description]
            
            cursor.close()
            
            # Retornar tanto los resultados como los nombres de las columnas
            return results, column_names
        except psycopg2.Error as e:
            raise ValueError('Error executing query: %s' % e)

# TODO: PostgreSQL Harvester
class SchemingDCATPostgresHarvester(SchemingDCATSQLHarvester):
    '''
    A custom harvester for harvesting PostgreSQL databases using the schemingdcat extension.

    It extends the base `SchemingDCATSQLHarvester` class.
    '''

    def info(self):
        return {
            'name': 'schemingdcat_postgres_harvester',
            'title': 'PostgreSQL Database Harvester',
            'description': 'A PostgreSQL database harvester for CKAN'
        }
    
    db_manager = PostgresDatabaseManager()
    harvester_type = 'postgres'
        
    def _generate_conn_url(self):
        '''
        Generates a database connection url using the class's internal configuration attributes.

        Returns:
            str: The database URL.

        Raises:
            ValueError: If the database type is not supported.
        '''
        user = self._credentials['user']
        password = self._credentials['password']
        host = self._credentials['host']
        port = self._credentials['port']
        db = self._credentials['db']

        if self._database_type == self.harvester_type:
            return f'postgresql://{user}:{password}@{host}:{port}/{db}'
        else:
            raise ValueError('Database type not supported.')
                         
    def _read_remote_database(self, field_mappings, conn_url):
        """
        Reads data from a remote database and maps it according to the provided field mappings.

        Establishes a connection to a remote database using conn_url. Generates and executes queries based on field_mappings to fetch data. Organizes fetched data into a dictionary categorized by mapping keys.

        Args:
            field_mappings (dict): Dictionary defining database fields mapping to desired structure.
            conn_url (str): Connection URL for the remote database.

        Returns:
            dict: Dictionary containing lists of data categorized by keys in field_mappings, with data as pd.DataFrames or None.

        Raises:
            ValueError: If database connection cannot be established.
        """
                
        if not self.db_manager.connection:
            try:
                self.db_manager.connect(conn_url)
            except psycopg2.Error as e:
                raise ValueError(f"Database connection is not established: {e}") from e
        
        # Create queries
        self._save_queries(field_mappings)
        log.debug('Field mappings queries: %s', self._queries)
        
        # Mapping for content categories
        content_category_mapping = {
            "dataset_field_mapping": "datasets",
            "distribution_field_mapping": "distributions",
            "datadictionary_field_mapping": "datadictionaries"
        }
        
        content_dicts = {value: [] for value in content_category_mapping.values()}
        for mapping, query in self._queries.items():
            results, column_names = self.db_manager.execute_query(query)
            results_df = pd.DataFrame(results, columns=column_names, dtype=str).fillna('')

            # # Exporting the DataFrame to a CSV file
            # log.debug('export to output.csv')
            # filename = f'output_{mapping}.csv'
            # results_df.to_csv(filename, index=False)
            
            # Map the result to the correct category in the results dictionary
            # Only add results_df if it is not empty
            if mapping in content_category_mapping and not results_df.empty:
                content_dicts[content_category_mapping[mapping]].append(results_df)
                            
        self.db_manager.disconnect()
        
        # Convert lists of DataFrames to single DataFrames for each category
        for key in content_dicts:
            if content_dicts[key]:
                concatenated_df = pd.concat(content_dicts[key], ignore_index=True)
                # Assign None if the concatenated DataFrame is empty
                content_dicts[key] = concatenated_df if not concatenated_df.empty else None
            else:
                content_dicts[key] = None
        
        return content_dicts

    def _process_content(self, content_dicts, conn_url, field_mapping):
        """
        Processes the SQL query content_dicts based on the field_mapping, handling multilingual fields by appending -lang to the original field name for each available language.
        """
        
        log.debug('In SchemingDCATPostgresHarvester process_content: %s', self.obfuscate_credentials_in_url(conn_url))
        
        # Clean datasets
        table_datasets = self._clean_table_datasets(content_dicts['datasets'])
        
        # Clean distributions
        dataset_id_colname = self._field_mapping_info['distribution_field_mapping'].get('parent_resource_id')
        if content_dicts.get('distributions') is not None and not content_dicts['distributions'].empty:
            table_distributions_grouped = self._clean_table_distributions(content_dicts['distributions'], dataset_id_colname)
        else:
            log.debug('No distributions loaded. Check "distribution.%s" fields', dataset_id_colname)
            table_distributions_grouped = None
        
        # Clean datadictionaries
        distribution_id_colname = self._field_mapping_info['datadictionary_field_mapping'].get('parent_resource_id')
        if content_dicts.get('datadictionaries') is not None and not content_dicts['datadictionaries'].empty:
            table_datadictionaries_grouped = self._clean_table_datadictionaries(content_dicts['datadictionaries'], distribution_id_colname)
        else:
            table_datadictionaries_grouped = None

        return self._add_distributions_and_datadictionaries_to_datasets(table_datasets, table_distributions_grouped, table_datadictionaries_grouped)

    def modify_package_dict(self, package_dict, harvest_object):
      '''
      Allows custom harvesters to modify the package dict before
      creating or updating the actual package.
      ''' 
      
      # Simplified check for 'temporal_start' and 'temporal_end'
      if all(key in package_dict for key in ['temporal_start', 'temporal_end']):
        package_dict = normalize_temporal_dates(package_dict)
      
      # Simplified check for 'reference_system'
      if package_dict.get('reference_system'):
        package_dict = normalize_reference_system(package_dict)
        
      # Check resources
      if package_dict.get("resources"):
        package_dict = normalize_resources(package_dict)
    
      return package_dict

    def get_package_dict(self, harvest_object, context, package_dict=None):
        """
        Returns a dictionary representing the CKAN package to be created or updated.

        Args:
            harvest_object (HarvestObject): The harvest object being processed.
            context (dict): The context of the harvest process.
            package_dict (dict, optional): The initial package dictionary (dataset). Defaults to None.

        Returns:
            dict: The package dictionary with translated fields and default values set.
        """
        # Add default values: tags, groups, etc.
        package_dict = self._set_package_dict_default_values(package_dict, harvest_object, context)

        # Update unique ids
        for resource in package_dict['resources']:
            resource['url'] = resource.get('url', "")
            resource['alternate_identifier'] = resource.get('id', None)
            resource['id'] = str(uuid.uuid4())
            resource.pop('dataset_id', None)

        return package_dict
    
    # PostgreSQL-Postgis DB
    def _save_queries(self, field_mappings):
        """
        Saves queries from field mappings into a dictionary.

        Iterates over field_mappings, checking if each is required or can be skipped if None. Constructs SQL queries for non-None mappings and stores them in self._queries. Raises ValueError for required but None mappings, and RuntimeError for errors during query construction.

        Args:
            field_mappings (dict): Dictionary with query types as keys and field mappings as values.

        Raises:
            ValueError: For required but None field mappings.
            RuntimeError: For errors in query construction.
        """
        try:
            for query_type, field_mapping in field_mappings.items():
                # Retrieve the mapping info for the current query type
                mapping_info = self._field_mapping_info.get(query_type)
                if mapping_info is None:
                    continue  # Skip if the query_type is not recognized

                # Check if the field mapping is required and if it is None
                if mapping_info["required"] and field_mapping is None:
                    raise ValueError(f"{query_type} is required and cannot be None.")
                # Skip if the field mapping is not required and is None
                elif not mapping_info["required"] and field_mapping is None:
                    continue

                query = self._build_query(field_mapping)
                # Ensure that self._queries[query_type] is a dictionary
                if query_type not in self._queries:
                    self._queries[query_type] = {}
                self._queries[query_type] = query

        except Exception as e:
            raise RuntimeError("Error generating queries") from e

    def _build_query(self, field_mapping):
      """
      Constructs a SQL query based on the provided field mapping, considering both direct field names
      and nested field names within language-specific dictionaries.

      Args:
        field_mapping (dict): A dictionary mapping field aliases to their details, including
          the database schema, table, and column names, as well as foreign key references
          and whether the field is a primary key. Field names can be direct strings or nested
          within language-specific dictionaries under a 'languages' key.

      Returns:
        str: A SQL query string constructed based on the field mapping.

      Raises:
        RuntimeError: If an error occurs during the construction of the SQL query.
      """
      try:
        query_components = {'selects': [], 'joins': [], 'schemas': set()}
        for field, details in field_mapping.items():
          # Handle direct field_name cases
          if 'field_name' in details:
            schema, table, column = details['field_name'].split('.')
            query_components['schemas'].add(schema)
            alias = field
            query_components['selects'].append(self._build_select_clause(schema, table, column, alias))

            for f_key_ref_str in details.get('f_key_references', []):
              ref_schema, ref_table, ref_column = f_key_ref_str.split('.')
              query_components['schemas'].add(ref_schema)
              query_components['joins'].append(self._build_join_clause(schema, table, column, ref_schema, ref_table, ref_column))
          # Handle nested field_name cases within 'languages'
          elif 'languages' in details:
            for lang, lang_details in details['languages'].items():
              if 'field_name' in lang_details:
                schema, table, column = lang_details['field_name'].split('.')
                query_components['schemas'].add(schema)
                # Use double quotes to include hyphens in the alias
                alias = f'"{field}-{lang}"'
                query_components['selects'].append(self._build_select_clause(schema, table, column, alias))

        search_path = self._set_search_path(query_components['schemas'])
        # Assuming schema and table are defined; this might need adjustment based on actual use case
        base_query = f"SELECT {', '.join(query_components['selects'])} FROM {schema}.{table}"
        full_query = ' '.join([search_path, base_query] + query_components['joins'])

        log.debug('full_query:%s', full_query)

        return full_query

      except Exception as e:
        raise RuntimeError("Error generating SQL query") from e
    
    def _build_select_clause(self, schema, table, column, alias):
        """
        Builds a SELECT clause for a SQL query.

        Args:
            schema (str): The database schema name.
            table (str): The table name.
            column (str): The column name.
            alias (str): The alias to use for the selected column in the query results.

        Returns:
            str: A SELECT clause string.
        """
        return sql_clauses(schema, table, column, alias)

    def _build_join_clause(self, schema, table, column, ref_schema, ref_table, ref_column, join_type="LEFT JOIN"):
        """
        Constructs a JOIN clause for a SQL query.

        Args:
            schema (str): The schema of the primary table.
            table (str): The primary table name.
            column (str): The column name in the primary table to join on.
            ref_schema (str): The schema of the reference table.
            ref_table (str): The reference table name.
            ref_column (str): The column name in the reference table to join on.
            join_type (str, optional): The type of join to perform. Defaults to "LEFT JOIN".

        Returns:
            str: A JOIN clause string.
        """
        join_on = f"{schema}.{table}.{column} = {ref_schema}.{ref_table}.{ref_column}"
        return f"{join_type} {ref_schema}.{ref_table} ON {join_on}"

    def _set_search_path(self, schemas):
        """
        Sets the search path for the SQL query.

        Args:
            schemas (set): A set of schema names to include in the search path.

        Returns:
            str: A SQL command to set the search path.
        """
        schemas_str = ', '.join(schemas)
        return f"SET search_path TO {schemas_str}, public;"    
