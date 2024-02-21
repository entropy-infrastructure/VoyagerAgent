
FROM python:3.10-bookworm

WORKDIR /Maxwell

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONPATH .
CMD ["sh","setup.sh"]

