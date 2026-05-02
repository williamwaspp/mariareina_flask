import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', '@X6K%%dH^P!xFi6&%7$!5&t^Nc%6AGEHtgtSE@gk$Gb#XVa2ee%4')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Detectar si estamos en Windows o Linux (producción)
    if os.name == 'nt':  # Windows
        SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://sistema_user:Machado01@192.168.103.96/sistema_gestion?charset=utf8mb4'
    else:  # Linux (Debian)
        SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://sistema_user:Machado01@192.168.103.96/sistema_gestion?charset=utf8mb4'
        # También podrías usar: 'mysql://sistema_user:ClaveSegura123!@localhost/sistema_gestion'
    
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', 'YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODk=')
    
    # Configuración específica para desarrollo
    DEBUG = True
    TESTING = False