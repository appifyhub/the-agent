## The Agent

This is the complete source code of The Agent, our intelligent virtual assistant.

### How to run?

This project uses `pipenv`.

Using `pipenv`, you can run `pipenv install` in the root directory to set up your dependencies correctly.

For running the production server:

```console
$ pipenv install
```

For running on development systems, e.g. for testing purposes:

```console
$ pipenv install --dev
```

After the dependencies have been installed, you can run `pipenv shell` to get a new shell fork in which the environment will be set up to easily run everything.

Once the environment has been configured, you can run the main code.

#### Scripts

You can use the pre-built scripts located in the `tools` directory – those are easy-to-use single-shot Shell executables that require no developer setup.

Production server:

```console
$ ./tools/run_main.sh
```

Development server:

```console
$ ./tools/run_dev.sh
```

All tests:

```console
$ ./tools/run_tests.sh
```

There are more tools in the same directory (especially useful around database migrations); feel free to explore those at your own pace when needed.

To emulate this behavior on Windows, you would need to inspect the scripts individually and mimic their behavior in the DOS environment.

### License

Check out the license [here](LICENSE).
