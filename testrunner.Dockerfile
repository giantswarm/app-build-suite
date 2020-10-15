FROM quay.io/giantswarm/app-build-suite:latest

ARG ABS_DIR="/abs"

RUN pip install --no-cache-dir pipenv==2020.8.13
WORKDIR $ABS_DIR
COPY .bandit .
COPY .coveragerc .
COPY .flake8 .
COPY .mypy.ini .
COPY .pre-commit-config.yaml .
COPY run-tests-in-docker.sh .
COPY Pipfile .
COPY Pipfile.lock .
COPY tests/ tests/
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --clear --dev
ENTRYPOINT ["./run-tests-in-docker.sh"]
CMD ["--cov", "app_build_suite", "--log-cli-level", "info", "tests/"]
