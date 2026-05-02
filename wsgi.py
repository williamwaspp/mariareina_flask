#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WSGI entry point for Gunicorn
Producción - Sistema de Gestión
"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# Configurar logging antes de importar la app
log_formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
)

# Log para WSGI
wsgi_log = RotatingFileHandler(
    '/var/log/sistema_gestion/wsgi.log',
    maxBytes=1024 * 1024 * 10,  # 10MB
    backupCount=10
)
wsgi_log.setFormatter(log_formatter)
wsgi_log.setLevel(logging.INFO)

# Agregar handler para stdout también (para systemd)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Configurar logger raíz
root_logger = logging.getLogger()
root_logger.addHandler(wsgi_log)
root_logger.addHandler(console_handler)
root_logger.setLevel(logging.INFO)

# Agregar directorio del proyecto al path
project_dir = '/srv/sistema_gestion'
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Variables de entorno para producción
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('FLASK_DEBUG', '0')

try:
    # Importar la aplicación
    from app import app as application
    
    # Para compatibilidad
    app = application
    
    logging.info(f"✅ WSGI cargado correctamente desde {project_dir}")
    logging.info(f"🔧 Modo: {os.environ.get('FLASK_ENV', 'production')}")
    
except Exception as e:
    logging.error(f"❌ Error al cargar la aplicación WSGI: {str(e)}")
    logging.exception(e)
    raise

# Opcional: Asegurar que las tablas existan (solo en desarrollo)
# En producción usar migraciones con Flask-Migrate
if os.environ.get('FLASK_ENV') == 'development':
    with app.app_context():
        from app import db
        db.create_all()
        logging.info("📊 Verificación de tablas completada")