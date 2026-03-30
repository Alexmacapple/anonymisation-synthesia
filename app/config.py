"""Configuration de l'application."""

import os


HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8090"))
MODEL_NAME = os.getenv("MODEL_NAME", "fastino/gliner2-base-v1")
NER_THRESHOLD = float(os.getenv("NER_THRESHOLD", "0.4"))
CONFIDENTIEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'confidentiel')
