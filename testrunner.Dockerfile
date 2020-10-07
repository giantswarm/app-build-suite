FROM app_build_suite:latest

ARG ABS_DIR="/abs"

RUN pip install --no-cache-dir pipenv==2020.8.13
WORKDIR $ABS_DIR
COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --clear --dev
COPY tests/ tests/
ENTRYPOINT ["pipenv", "run", "pytest"]
CMD ["--cov", "app_build_suite", "--log-cli-level", "info", "tests/"]
