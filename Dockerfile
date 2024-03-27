FROM python:3.11

WORKDIR /app
ADD . /app/

ENV FLIT_ROOT_INSTALL=1
RUN pip install flit
RUN flit install -s

CMD [ "python", "main.py" ]
