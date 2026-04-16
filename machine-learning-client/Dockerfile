FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY Pipfile Pipfile.lock ./

RUN python -m pip install --no-cache-dir pipenv
RUN pipenv install --system --deploy
RUN python -m pip install --no-cache-dir "setuptools<82"
RUN python -c "import pkg_resources; print('pkg_resources OK at build time')"

COPY . .

CMD ["python", "main.py"]