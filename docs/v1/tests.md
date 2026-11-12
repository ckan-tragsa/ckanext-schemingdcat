## Running the Tests
To run the tests:

    pytest --ckan-ini=test.ini ckanext/schemingdcat/tests


### Run tests quickly with Docker Compose
This repository includes a Docker Compose configuration to simplify running tests. The CKAN image is built using the Dockerfile located in the `docker/` directory.

To test against the CKAN version you want to use, proceed as follows

1. Build the necessary Docker images. This step ensures that all dependencies and configurations are correctly set up.

```sh
docker compose build
```

3. After building the images, you can run the tests. The Docker Compose configuration mounts the root of the repository into the CKAN container as a volume. This means that any changes you make to the code will be reflected inside the container without needing to rebuild the image, unless you modify the extension's dependencies.

```sh
docker compose up
```
