FROM ghcr.io/mjanez/ckan-spatial-test:2.10.5

ENV CKAN_VERSION_MAYOR=ckan-2.10
ENV APP_DIR=/srv/app
ENV CKAN_DIR=${APP_DIR}/src/ckan
ENV TZ=UTC

WORKDIR ${APP_DIR}/src/ckanext-schemingdcat

# Conditionally install pytest-rerunfailures if CKAN version is 2.9
RUN if [ "$CKAN_VERSION_MAYOR" = "2.9" ]; then \
        pip3  install -U pytest-rerunfailures; \
    fi

# Copy extension files to the container
COPY . .

# ## Override test_ckan.sh
# - Make sure to put the docker/setup/test_ckan.sh.override path because of the COPY context 
# COPY docker/setup/test_ckan.sh.override ${APP_DIR}/test_ckan.sh
# RUN chmod +x ${APP_DIR}/test_ckan.sh

# Install the base + test dependencies
RUN pip3  install --no-cache-dir -r ${APP_DIR}/src/ckanext-schemingdcat/requirements.txt && \
    # ignore installed packaging required version (fixed pyshacl issues)
    pip3  install --no-cache-dir -r ${APP_DIR}/src/ckanext-schemingdcat/dev-requirements.txt && \
    pip3  install -e ${APP_DIR}/src/ckanext-schemingdcat && \
    # Replace default path to CKAN core config file with the one on the container
    sed -i -e 's/use = config:.*/use = config:\/srv\/app\/src\/ckan\/test-core.ini/' test.ini

WORKDIR ${APP_DIR}

# Setup other extensions
RUN echo "ckan/ckanext-dcat" && \
    pip3  install --no-cache-dir -e git+https://github.com/ckan/ckanext-dcat.git#egg=ckanext-dcat && \
    pip3  install --no-cache-dir -r ${APP_DIR}/src/ckanext-dcat/requirements.txt && \
    echo "ckan/ckanext-harvest" && \
    pip3  install --no-cache-dir -e git+https://github.com/ckan/ckanext-harvest.git#egg=ckanext-harvest && \
    pip3  install --no-cache-dir -r ${APP_DIR}/src/ckanext-harvest/requirements.txt && \
    echo "ckan/ckanext-scheming" && \
    pip3  install --no-cache-dir -e git+https://github.com/ckan/ckanext-scheming.git#egg=ckanext-scheming && \
    echo "mjanez/ckanext-fluent" && \
    pip3  install --no-cache-dir -e git+https://github.com/mjanez/ckanext-fluent.git#egg=ckanext-fluent

WORKDIR ${APP_DIR}/src/ckanext-schemingdcat

# Running the tests with coverage output
CMD ["/bin/sh", "-c", "$APP_DIR/test_ckan.sh -d ckanext/schemingdcat/tests ckanext.schemingdcat"]