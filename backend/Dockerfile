FROM python:3.10-slim

WORKDIR /app

# Installiere Django
RUN pip install django

# Kopiere den Backend-Code
COPY . .

# Port freigeben
EXPOSE 8000

# Server starten
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]