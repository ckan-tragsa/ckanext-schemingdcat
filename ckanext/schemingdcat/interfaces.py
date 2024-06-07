from ckan.plugins.interfaces import Interface


class ISchemingDCATHarvester(Interface):
    """
    This is a common harvesting interface for SchemingDCATHarvester that provides a set of methods to be implemented by a harvester. 
    The methods are designed to be called at different stages of the harvesting process, allowing for 
    customization and extension of the default behavior. 

    The methods include hooks before and after the download of the remote sheet file, before and after the 
    cleaning process, after the parsing of the sheet file, and before and after the creation and update of 
    the dataset. 

    Additionally, there are methods to modify the dataset dict that will be created or updated, and to 
    update the package schema for the creation and update actions.

    Each method is documented with its purpose, parameters, and return values.
    """

    def before_download(self, url, harvest_job):
        """
        Called just before the remote file is downloaded

        Args:
            url (str): The harvest source URL, ie the remote file location
            harvest_job (object): A ``HarvestJob`` domain object which contains a
                                  reference to the harvest source (``harvest_job.source``).

        Returns:
            tuple: A tuple with two items:
                    * The url. If this is False the gather stage will stop.
                    * A list of error messages. These will get stored as gather
                      errors by the harvester
        """
        return url, []

    def update_session(self, session):
        """
        Called before making the HTTP request to the remote site to download
        the file.

        Args:
            session (object): The requests session object

        Returns:
            object: The updated requests session object
        """
        return session

    def after_download(self, content_dicts, harvest_job):
        """
        Called just after the remote file has been downloaded

        Args:
            content_dicts (dict): A dict of dataframes containing the content of the harvested dataset (datasets, distributions and datadictionaries).
            harvest_job (object): A ``HarvestJob`` domain object which contains a
                                  reference to the harvest source (``harvest_job.source``).

        Returns:
            tuple: A tuple with two items:
                    * The file content_dicts. If this is False the gather stage will
                      stop.
                    * A list of error messages. These will get stored as gather
                      errors by the harvester
        """
        return content_dicts, []

    def before_cleaning(self, content_dicts):
        """
        This method is called before the cleaning process starts.

        Args:
            content_dicts (dict): A dict of dataframes containing the content of the harvested dataset (datasets, distributions and datadictionaries).

        Returns:
            tuple: A tuple with two items:
                    * The remote sheet content_dicts with all datasets, distributions and datadictionaries dicts.
                    * A list of error messages. These will get stored as gather errors by the harvester.
        """
        return content_dicts, []

    def after_cleaning(self, clean_datasets):
        """
        This method is called after the cleaning process ends.

        Args:
            clean_datasets (list): The cleaned datasets.

        Returns:
            tuple: A tuple with two items:
                    * The cleaned datasets list of dictionaries.
                    * A list of error messages. These will get stored as gather errors by the harvester.
        """
        return clean_datasets, []

    def after_parsing(self, schemingdcat_parser, harvest_job):
        """
        Called just after the content_dicts from the remote file has been parsed

        Args:
            schemingdcat_parser (ckanext.schemingdcat.processors.SchemingDCATParser): The parser.
            harvest_job (object): A ``HarvestJob`` domain object which contains a
                                  reference to the harvest source (``harvest_job.source``).

        Returns:
            tuple: A tuple with two items:
                    * The schemingdcat parser. If this is False the gather stage will
                      stop.
                    * A list of error messages. These will get stored as gather
                      errors by the harvester
        """
        return schemingdcat_parser, []

    def get_package_dict(self, context, data_dict):
        """
        Allows to modify the dataset dict that will be created or updated

        Args:
            context (dict): Contains a reference to the model, eg to
                            perform DB queries, and the user name used for
                            authorization.
            data_dict (dict): Available data. Contains four keys:
                * `package_dict`
                   The default package_dict generated by the harvester. Modify this
                   or create a brand new one.
                * `xls_values`
                   The parsed XLS dataset values. These contain more fields
                   that are not added by default to the ``package_dict``.
                * `harvest_object`
                   A ``HarvestObject`` domain object which contains a reference
                   to the original metadata document (``harvest_object.content_dicts``)
                   and the harvest source (``harvest_object.source``).

        Returns:
            dict: A dataset dict ready to be used by ``package_create`` or
                  ``package_update``
        """
        return data_dict['package_dict']

    def before_update(self, harvest_object, package_dict, harvester_tmp_dict):
        """
        Called just before the ``package_update`` action.

        Args:
            harvest_object (object): A ``HarvestObject`` domain object.
            package_dict (dict): The dataset dict already parsed by the parser
                                 (and related plugins).
            harvester_tmp_dict (dict): A dictionary, shared among all plugins, for storing
                              temp data. Such dict will be passed back in the
                              ``after_update`` call.
        """
        pass

    def after_update(self, harvest_object, package_dict, harvester_tmp_dict):
        """
        Called just after a successful ``package_update`` action has been
        performed.

        Args:
            harvest_object (object): A ``HarvestObject`` domain object.
            package_dict (dict): The dataset dict that has just been stored into
                                 the DB.
            harvester_tmp_dict (dict): A dictionary, shared among all plugins, for storing
                              temp data. 

        Returns:
            string: A string containing an error message, or None. If the error
                    string is not None, it will be saved as an import error,
                    and dataset importing will be rolled back,
        """
        return None

    def before_create(self, harvest_object, package_dict, schema, harvester_tmp_dict):
        """
        Called just before the ``package_create`` action.
        It may be used to preprocess the dataset dict.

        If the content_dicts of the dataset dict is emptied (i.e. set to ``None``), 
        the dataset will not be created in CKAN, but simply ignored.

        Implementations may store some temp values in harvester_tmp_dict, that will be
        then passed back in the ``after_create`` call.

        Args:
            harvest_object (object): A ``HarvestObject`` domain object.
            package_dict (dict): The dataset dict already parsed by the parser
                                 (and related plugins).
            harvester_tmp_dict (dict): A dictionary, shared among all plugins, for storing
                              temp data. Such dict will be passed back in the
                              ``after_create`` call.
        Returns:
            string: A string containing an error message, or None. If the error
                    string is not None, it will be saved as an import error,
                    and dataset importing will be rolled back.
        """
        return None

    def after_create(self, harvest_object, package_dict, harvester_tmp_dict):
        """
        Called just after a successful ``package_create`` action has been
        performed.

        Args:
            harvest_object (object): A ``HarvestObject`` domain object.
            package_dict (dict): The dataset dict that has just been stored into
                                 the DB.
            harvester_tmp_dict (dict): A dictionary, shared among all plugins, for storing
                              temp data.

        Returns:
            string: A string containing an error message, or None. If the error
                    string is not None, it will be saved as an import error,
                    and dataset importing will be rolled back.
        """
        return None

    def update_package_schema_for_create(self, package_schema):
        """
        Called just before the ``package_create`` action.

        Args:
            package_schema (dict): The default create package schema dict.

        Returns:
            object: The updated package_schema object
        """
        return package_schema

    def update_package_schema_for_update(self, package_schema):
        """
        Called just before the ``package_update`` action.

        Args:
            package_schema (dict): The default update package schema dict.

        Returns:
            object: The updated package_schema object
        """
        return package_schema