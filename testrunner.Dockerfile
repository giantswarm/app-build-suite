FROM gsoci.azurecr.io/giantswarm/app-build-suite:latest

ARG ABS_DIR="/abs"

RUN pip install --no-cache-dir pipenv==${PIPENV_VER}
RUN apt-get update && apt-get install -y wget xz-utils git libatomic1 && rm -rf /var/lib/apt/lists/*
RUN wget -qO- "https://github.com/koalaman/shellcheck/releases/download/latest/shellcheck-latest.linux.x86_64.tar.xz" | tar -xJv && cp "shellcheck-latest/shellcheck" /usr/bin/
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
COPY examples/ examples/
COPY .git/ ./.git/
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --clear --dev
RUN git config --global --add safe.directory /abs
RUN pipenv run pre-commit run -a
ENTRYPOINT ["./run-tests-in-docker.sh"]
CMD ["--cov", "app_build_suite", "--log-cli-level", "info", "tests/"]
