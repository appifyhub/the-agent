## Docker Compose support

This project can run in the Docker Compose framework. 

The basic `Dockerfile` is available in the project's root directory. To run the service using Docker Compose, you need a `docker-compose.yml` file, which is provided here.

The basic command to run the configured image is:

```console
$ docker-compose up
```

When you don't need the service anymore, you can just tear it down:

```console
$ docker-compose down
```

### How does the local Docker build work?

The build copies over the necessary files into the image, then runs the run script from within. Depending on how your storage is configured, this may pull the necessary dependencies before running.

Docker is not a development environment, therefore no tests will be executed during Docker builds. It's assumed that you're running Docker as the last step of your development process.

The latest image is available in Docker Hub and will be tagged with `appifyhub/the-agent:latest`.

### How do I reconfigure the project properties?

The directory here contains a `.env` file containing configurable build properties. There are sensible defaults that you can change by simply editing the `.env` file. If running the project from your machine directly, normal environment variables will be used.

### Word of caution

It goes without saying, but let's say it anyway:

**DO NOT** deploy any of this directly to production or production-like environments. All of the files provided here are for testing only and should not be used when deploying to real environments and real users.
