<<<<<<< HEAD
<<<<<<< HEAD
FROM python:3.11

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE="chapp.settings"

RUN mkdir /code
WORKDIR /code
COPY . /code/

RUN pip install --upgrade pip

# Install requirements
RUN pip install --upgrade pip
ADD requirements.txt /code/
RUN pip install -r requirements.txt
RUN pip install whitenoise


# Install debugpy for python debugging in VS code
RUN pip install debugpy -t /tmp

ADD . /code/

# create unprivileged user
RUN adduser --disabled-password --gecos '' myuser

# Configurar variable de entorno de Django
ENV DJANGO_SETTINGS_MODULE=chapp.settings

# Exponer el puerto de Django
EXPOSE 8000

# Comando para ejecutar el servidor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
=======
=======
>>>>>>> feature/02-dashboard-occupancy
FROM python:latest

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE="chapp.settings"

RUN mkdir /code
WORKDIR /code

RUN pip install --upgrade pip

# Install requirements
ADD requirements.txt /code/
RUN pip install -r requirements.txt

# Install debugpy for python debugging in VS code
RUN pip install debugpy -t /tmp

ADD . /code/

# create unprivileged user
RUN adduser --disabled-password --gecos '' myuser
<<<<<<< HEAD
>>>>>>> 34e21f3b96c1e22ee961526b94d87b9c837e3591
=======
>>>>>>> feature/02-dashboard-occupancy
