FROM quay.io/giantswarm/app-build-suite:latest

ARG ABS_DIR="/abs"

RUN pip install --no-cache-dir pipenv==2020.8.13
WORKDIR $ABS_DIR
COPY .bandit .
COPY .coveragerc .
COPY .flake8 .
COPY .mypy.ini .
COPY .pre-commit-config.yaml .
COPY pyproject.toml .
COPY run-tests-in-docker.sh .
COPY Pipfile .
COPY Pipfile.lock .
COPY tests/ tests/
COPY .git/ ./.git/
#RUN ln -s /.venv ${ABS_DIR}/.venv
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --clear --dev
RUN pipenv run pre-commit install-hooks
ENTRYPOINT ["./run-tests-in-docker.sh"]
CMD ["--cov", "app_build_suite", "--log-cli-level", "info", "tests/"]
