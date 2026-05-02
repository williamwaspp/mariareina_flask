from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://sistema_user:Machado01@192.168.103.96/sistema_gestion')
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("✅ Conexión exitosa:", result.fetchone())