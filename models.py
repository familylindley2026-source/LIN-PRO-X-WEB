from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Date,  # <--- ¡AQUÍ ESTÁ LA CLAVE!
    func,
)
from sqlalchemy.orm import relationship
from database import Base  # Importamos la base desde nuestro nuevo archivo


def get_local_time():
    return datetime.now()


class Proveedor(Base):
    __tablename__ = "proveedores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nit = Column(String(20), default="S/N", nullable=False)
    nombre = Column(String(100), unique=True, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    insumos = relationship("Insumo", back_populates="proveedor")
    empresa_id = Column(String, index=True)


class Insumo(Base):
    __tablename__ = "insumos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(30), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    categoria = Column(String(50), nullable=False)
    unidad_medida = Column(String(20), nullable=False)
    stock_actual = Column(Float, default=0.0)
    costo_promedio = Column(Float, default=0.0)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    proveedor = relationship("Proveedor", back_populates="insumos")
    empresa_id = Column(String, index=True)


class CatalogoProducto(Base):
    __tablename__ = "catalogo_productos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    presentacion = Column(String(100))
    precio_publico = Column(Float, default=0.0)
    dias_cobertura = Column(Integer, default=30)
    puntos_pv = Column(Integer, default=0)
    empresa_id = Column(String, index=True)


class ProductoTerminado(Base):
    __tablename__ = "productos_terminados"
    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(30), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    linea = Column(String(50), default="Capilar")
    presentacion = Column(String(50), default="Genérico")
    es_souvenir = Column(Boolean, default=False, nullable=False)
    costo_unitario = Column(Float, default=0.0)
    precio_venta = Column(Float, default=0.0)
    stock_actual = Column(Integer, default=0)
    dias_consumo = Column(Integer, default=30)
    puntos_pv = Column(Integer, default=0)
    activo = Column(Boolean, default=True, nullable=False)
    empresa_id = Column(String, index=True)

class Receta(Base):
    __tablename__ = "recetas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(String, index=True)
    nombre = Column(String(100), nullable=False)
    volumen_lote_base = Column(Float, default=1000.0)
    producto_id = Column(Integer, ForeignKey("productos_terminados.id"), nullable=False)
    producto = relationship("ProductoTerminado")
    detalles = relationship(
        "RecetaDetalle", back_populates="receta", cascade="all, delete-orphan"
    )


class RecetaDetalle(Base):
    __tablename__ = "receta_detalles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    receta_id = Column(Integer, ForeignKey("recetas.id"), nullable=False)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    empresa_id = Column(String, index=True)
    cantidad_requerida = Column(Float, nullable=False, default=0.0)
    cantidad_necesaria = Column(Float, nullable=False, default=0.0)
    receta = relationship("Receta", back_populates="detalles")
    insumo = relationship("Insumo")


class ControlCaja(Base):
    __tablename__ = "control_caja"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_apertura = Column(DateTime, default=get_local_time, nullable=False)
    monto_apertura = Column(Float, default=0.0, nullable=False)
    ingresos = Column(Float, default=0.0)
    egresos = Column(Float, default=0.0)
    usuario_cajero = Column(String(50), nullable=False)
    empresa_id = Column(String, index=True)

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20))
    whatsapp = Column(String(20), default="", nullable=True)
    email = Column(String(100))
    ciudad = Column(String(100), default="Cartagena")
    tipo_cliente = Column(String(50), default="General")
    empresa_id = Column(String, index=True)
    activo = Column(Boolean, default=True)


class Asesor(Base):
    __tablename__ = "asesores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20))
    empresa_id = Column(String, index=True)
    activo = Column(Boolean, default=True)


class GastoOperativo(Base):
    __tablename__ = "gastos_operativos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, default=get_local_time)
    descripcion = Column(String(200), nullable=False)
    monto = Column(Float, nullable=False)
    empresa_id = Column(String, index=True)


class VentaDetalle(Base):
    __tablename__ = "venta_detalles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos_terminados.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("ProductoTerminado")
    empresa_id = Column(String, index=True)


class Venta(Base):
    __tablename__ = "ventas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    factura_nro = Column(String(20), unique=True, nullable=False)
    fecha = Column(DateTime, default=get_local_time)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    vendedor = Column(String(50))
    tipo_destinatario = Column(String(50))
    medio_pago = Column(String(50))
    total_bruto = Column(Float, default=0.0)
    descuento_total = Column(Float, default=0.0)
    total_neto = Column(Float, default=0.0)
    saldo_pendiente = Column(Float, default=0.0)
    estado_financiero = Column(String(20), default="Pagado")
    cliente = relationship("Cliente")
    detalles = relationship(
        "VentaDetalle", back_populates="venta", cascade="all, delete-orphan"
    )
    empresa_id = Column(String, index=True)

class Abono(Base):
    __tablename__ = "abonos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    fecha = Column(DateTime, default=get_local_time)
    monto = Column(Float, nullable=False)
    venta = relationship("Venta")
    empresa_id = Column(String, index=True)


class KardexMovimiento(Base):
    __tablename__ = "kardex_movimientos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, default=get_local_time)
    producto_id = Column(Integer, ForeignKey("productos_terminados.id"), nullable=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=True)
    operacion = Column(String(50))
    cantidad = Column(Float)
    motivo = Column(String(100))
    involucrado = Column(String(100), nullable=True)
    producto = relationship("ProductoTerminado")
    insumo = relationship("Insumo")
    empresa_id = Column(String, index=True)


# Asegúrate de que Date esté importado al principio de models.py:
# from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Date, func


class Suscriptor(Base):
    __tablename__ = "suscriptores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String(100), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    plan = Column(String(100))
    empresa_id = Column(String(100))
