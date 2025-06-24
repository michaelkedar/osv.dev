FROM python:3.12.8-slim@sha256:8859bd6ca943079262c27e38b7119cdacede77c463139a15651dd340087a6cc9

# Generation 1 of cloud run overrides the HOME environment variable, causing
# poetry to run in the incorrect environment, as it defaults to using $HOME/.cache/virtualenvs/...
# 
# This forces it to create the virtualenv in the same directory as the project, avoiding this issue.
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_HOME "/opt/poetry"
COPY docker/poetry/requirements.txt ./poetry-requirements.txt
RUN python3 -m venv $POETRY_HOME && \
    $POETRY_HOME/bin/pip install --require-hashes -r ./poetry-requirements.txt && \
    ln -s $POETRY_HOME/bin/poetry /usr/local/bin/poetry

COPY pyproject.toml poetry.lock README.md /osv/
COPY osv /osv/osv
COPY tools/datafix/reput_all.py tools/datafix/pyproject.toml tools/datafix/poetry.lock /osv/tools/datafix/

WORKDIR /osv/tools/datafix/
RUN poetry install

ENTRYPOINT ["poetry", "run", "python", "/osv/tools/datafix/reput_all.py"]
