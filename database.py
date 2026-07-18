import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, declared_attr
from sqlalchemy.pool import NullPool

load_dotenv()

# Obtener URL de la base de datos (Supabase)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///lin_pro_x.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configurar el motor de la base de datos
# 💡 NOTA: Se usa NullPool para cerrar la conexión tras cada uso y evitar el error de max clients
engine = create_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool if "postgresql" in DATABASE_URL else None,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Crear la fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base para que los modelos construyan las tablas
class ConfiguracionBase:
    @declared_attr
    def __table_args__(cls):
        return {"extend_existing": True}


Base = declarative_base(cls=ConfiguracionBase)
