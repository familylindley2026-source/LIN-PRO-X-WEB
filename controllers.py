from datetime import datetime
import re
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from fpdf import FPDF

from models import (
    Insumo,
    Proveedor,
    CatalogoProducto,
    ProductoTerminado,
    Receta,
    RecetaDetalle,
    KardexMovimiento,
    ControlCaja,
    Venta,
    VentaDetalle,
    Abono,
    GastoOperativo,
    Cliente,
    Asesor,
    Suscriptor,
)


class SistemaController:
    def __init__(self, session_factory):
        self.SessionFactory = session_factory
        self.empresa_id = None

    def generar_nro_orden_compra(self):
        with self.SessionFactory() as db:
            ultimo = (
                db.query(KardexMovimiento)
                .filter(
                    KardexMovimiento.empresa_id == self.empresa_id,
                    KardexMovimiento.motivo.like("%#IB-%"),
                )
                .order_by(KardexMovimiento.id.desc())
                .first()
            )
            if ultimo:
                try:
                    motivo = ultimo.motivo
                    parte_num = motivo.split("#IB-")[1].split()[0]
                    num = int("".join(filter(str.isdigit, parte_num)))
                    return f"IB-{num + 1:03d}"
                except:
                    pass
            return "IB-001"

    def obtener_insumos(self):
        with self.SessionFactory() as db:
            return (
                db.query(Insumo)
                .options(joinedload(Insumo.proveedor))
                .filter(Insumo.empresa_id == self.empresa_id, Insumo.activo == True)
                .order_by(Insumo.categoria, Insumo.nombre)
                .all()
            )

    def obtener_proveedores(self):
        with self.SessionFactory() as db:
            return (
                db.query(Proveedor)
                .filter(
                    Proveedor.empresa_id == self.empresa_id, Proveedor.activo == True
                )
                .order_by(Proveedor.nombre)
                .all()
            )

    def guardar_o_actualizar_insumo(
        self, id_insumo, nombre, categoria, unidad, costo, stock, nombre_prov
    ):
        db = self.SessionFactory()
        try:
            nombre_prov_limpio = str(nombre_prov).strip()
            prov = (
                db.query(Proveedor)
                .filter_by(nombre=nombre_prov_limpio, empresa_id=self.empresa_id)
                .first()
            )
            if not prov and nombre_prov_limpio != "S/N":
                prov = Proveedor(
                    nombre=nombre_prov_limpio,
                    nit=f"SN-{datetime.now().strftime('%H%M%S')}",
                    empresa_id=self.empresa_id,
                )
                db.add(prov)
                db.flush()
            prov_id = prov.id if prov else None

            insumo = (
                db.query(Insumo)
                .filter_by(id=id_insumo, empresa_id=self.empresa_id)
                .first()
                if id_insumo
                else db.query(Insumo)
                .filter_by(nombre=nombre.strip(), empresa_id=self.empresa_id)
                .first()
            )
            if insumo:
                insumo.nombre = nombre.strip()
                insumo.categoria = categoria
                insumo.unidad_medida = unidad
                insumo.costo_promedio = costo
                insumo.stock_actual = stock
                insumo.proveedor_id = prov_id
            else:
                db.add(
                    Insumo(
                        codigo=f"INS-{datetime.now().strftime('%S%f')[:4]}",
                        nombre=nombre.strip(),
                        categoria=categoria,
                        unidad_medida=unidad,
                        costo_promedio=costo,
                        proveedor_id=prov_id,
                        stock_actual=stock,
                        empresa_id=self.empresa_id,
                    )
                )
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()

    def eliminar_insumo(self, id_insumo):
        db = self.SessionFactory()
        try:
            insumo = (
                db.query(Insumo)
                .filter_by(id=id_insumo, empresa_id=self.empresa_id)
                .first()
            )
            if insumo:
                db.delete(insumo)
                db.commit()
                return True
            return False
        except:
            db.rollback()
            return False
        finally:
            db.close()

    def procesar_compra_mixta(self, proveedor_nombre, nro_orden, carrito, comprador):
        db = self.SessionFactory()
        try:
            # === NUEVO: REGISTRAR PROVEEDOR SI NO EXISTE ===
            nombre_prov_limpio = str(proveedor_nombre).strip().upper()
            prov = (
                db.query(Proveedor)
                .filter_by(nombre=nombre_prov_limpio, empresa_id=self.empresa_id)
                .first()
            )

            if not prov:
                nuevo_prov = Proveedor(
                    nombre=nombre_prov_limpio,
                    nit=f"SN-{datetime.now().strftime('%H%M%S')}",
                    empresa_id=self.empresa_id,
                )
                db.add(nuevo_prov)
                db.flush()
            # ===============================================

            for item in carrito:
                if item["tipo"] == "Insumos":
                    insumo = (
                        db.query(Insumo)
                        .filter_by(id=item["id"], empresa_id=self.empresa_id)
                        .first()
                    )
                    if insumo:
                        if insumo.stock_actual > 0:
                            insumo.costo_promedio = (
                                (insumo.stock_actual * insumo.costo_promedio)
                                + item["precio"]
                            ) / (insumo.stock_actual + item["cant"])
                        else:
                            insumo.costo_promedio = item["precio"] / item["cant"]
                        insumo.stock_actual += item["cant"]
                        db.add(
                            KardexMovimiento(
                                insumo_id=insumo.id,
                                operacion="Entrada",
                                cantidad=item["cant"],
                                motivo=f"Compra Orden #{nro_orden}",
                                involucrado=nombre_prov_limpio,
                                empresa_id=self.empresa_id,
                            )
                        )
                elif item["tipo"] == "Productos Terminados":
                    prod = (
                        db.query(ProductoTerminado)
                        .filter_by(id=item["id"], empresa_id=self.empresa_id)
                        .first()
                    )
                    if prod:
                        if prod.stock_actual > 0:
                            prod.costo_unitario = (
                                (prod.stock_actual * prod.costo_unitario)
                                + item["precio"]
                            ) / (prod.stock_actual + item["cant"])
                        else:
                            prod.costo_unitario = item["precio"] / item["cant"]
                        prod.stock_actual += item["cant"]
                        db.add(
                            KardexMovimiento(
                                producto_id=prod.id,
                                operacion="Entrada",
                                cantidad=item["cant"],
                                motivo=f"Compra Lab/Terceros #{nro_orden}",
                                involucrado=nombre_prov_limpio,
                                empresa_id=self.empresa_id,
                            )
                        )
            # ... (código anterior de la función procesar_compra_mixta)

            db.commit()
            total = sum(i["precio"] for i in carrito)

            # --- AQUÍ ESTÁ LA CORRECCIÓN: Construcción completa del ticket ---
            ticket = f"🏢 *{self.empresa_id.replace('_', ' ').upper()}*\n"
            ticket += f"📦 *COMPROBANTE DE INGRESO*\n"
            ticket += f"----------------------------------------\n"
            ticket += f"🧾 *Orden N°:* {nro_orden}\n"
            ticket += f"📅 *Fecha:* {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            ticket += f"🏭 *Proveedor:* {nombre_prov_limpio}\n"
            ticket += f"👤 *Comprador/Recibe:* {comprador}\n"
            ticket += f"----------------------------------------\n"

            # Es vital este ciclo para que los productos aparezcan en el mensaje
            for item in carrito:
                ticket += f"▪ {item['cant']}x {item['nombre']}\n   Subtotal: $ {int(item['precio']):,.0f}\n"

            ticket += f"----------------------------------------\n"
            ticket += f"💰 *TOTAL INVERSIÓN: $ {int(total):,.0f}*\n"
            # -----------------------------------------------------------------

            # Generamos el PDF antes de retornar
            pdf_bytes = self.generar_pdf_compra(
                nro_orden, nombre_prov_limpio, comprador, carrito, total
            )

            return True, "Compra registrada con éxito.", ticket, pdf_bytes
        except Exception as e:
            db.rollback()
            return False, f"Error: {str(e)}", "", None
        finally:
            db.close()

    def obtener_catalogo_productos(self):
        with self.SessionFactory() as db:
            return (
                db.query(CatalogoProducto)
                .filter(CatalogoProducto.empresa_id == self.empresa_id)
                .order_by(CatalogoProducto.nombre)
                .all()
            )

    def obtener_productos_terminados(self):
        with self.SessionFactory() as db:
            return (
                db.query(ProductoTerminado)
                .filter(
                    ProductoTerminado.empresa_id == self.empresa_id,
                    ProductoTerminado.activo == True,
                )
                .order_by(ProductoTerminado.nombre)
                .all()
            )

    def guardar_producto_catalogo(self, nombre, presentacion, precio, dias, puntos):
        db = self.SessionFactory()
        try:
            nombre_limpio = nombre.strip().upper()
            existe_pt = (
                db.query(ProductoTerminado)
                .filter_by(
                    nombre=nombre_limpio,
                    presentacion=presentacion,
                    empresa_id=self.empresa_id,
                )
                .first()
            )
            if not existe_pt:
                db.add(
                    ProductoTerminado(
                        codigo=f"PT-{datetime.now().strftime('%S%f')[:5]}",
                        nombre=nombre_limpio,
                        presentacion=presentacion,
                        precio_venta=precio,
                        dias_consumo=dias,
                        puntos_pv=puntos,
                        stock_actual=0,
                        empresa_id=self.empresa_id,
                    )
                )
                db.commit()
                return True, "Producto creado exitosamente."
            return False, "Ese producto ya existe."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def editar_producto_catalogo(self, producto_id, presentacion, precio, dias, puntos):
        db = self.SessionFactory()
        try:
            prod_pt = (
                db.query(ProductoTerminado)
                .filter_by(id=producto_id, empresa_id=self.empresa_id)
                .first()
            )
            if not prod_pt:
                return False, "Producto no encontrado."
            prod_pt.presentacion = presentacion
            prod_pt.precio_venta = precio
            prod_pt.dias_consumo = dias
            prod_pt.puntos_pv = puntos
            db.commit()
            return True, "Catálogo actualizado."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def eliminar_producto_catalogo(self, producto_id):
        db = self.SessionFactory()
        try:
            prod_pt = (
                db.query(ProductoTerminado)
                .filter_by(id=producto_id, empresa_id=self.empresa_id)
                .first()
            )
            if not prod_pt:
                return False, "Producto no encontrado."
            db.delete(prod_pt)
            db.commit()
            return True, "Producto eliminado completamente."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def obtener_recetas_disponibles(self):
        with self.SessionFactory() as db:
            return (
                db.query(Receta)
                .filter(Receta.empresa_id == self.empresa_id)
                .order_by(Receta.nombre)
                .all()
            )

    def guardar_nueva_formula(self, nombre, volumen, lista_ingredientes):
        db = self.SessionFactory()
        try:
            prod = (
                db.query(ProductoTerminado)
                .filter_by(nombre=nombre, empresa_id=self.empresa_id)
                .first()
            )
            if not prod:
                prod = ProductoTerminado(
                    codigo=f"PT-{datetime.now().strftime('%H%M%S')}",
                    nombre=nombre,
                    linea="Capilar",
                    presentacion="Base Granel",
                    empresa_id=self.empresa_id,
                )
                db.add(prod)
                db.flush()
            receta = (
                db.query(Receta)
                .filter_by(nombre=nombre, empresa_id=self.empresa_id)
                .first()
            )
            if receta:
                db.query(RecetaDetalle).filter_by(
                    receta_id=receta.id, empresa_id=self.empresa_id
                ).delete()
            else:
                receta = Receta(
                    nombre=nombre, producto_id=prod.id, empresa_id=self.empresa_id
                )
                db.add(receta)
                db.flush()
            receta.volumen_lote_base = volumen
            for ing in lista_ingredientes:
                db.add(
                    RecetaDetalle(
                        receta_id=receta.id,
                        insumo_id=ing["id"],
                        cantidad_requerida=ing["cant"],
                        cantidad_necesaria=ing["cant"],
                        empresa_id=self.empresa_id,
                    )
                )
            db.commit()
            return True, "Fórmula guardada."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def procesar_fraccionamiento_lote(self, receta_nombre, volumen_preparar, envases):
        db = self.SessionFactory()
        try:
            receta = (
                db.query(Receta)
                .options(joinedload(Receta.detalles).joinedload(RecetaDetalle.insumo))
                .filter(
                    Receta.empresa_id == self.empresa_id,
                    func.upper(Receta.nombre) == receta_nombre.upper().strip(),
                )
                .first()
            )
            if not receta:
                return False, f"La fórmula '{receta_nombre}' no existe."
            factor = float(volumen_preparar) / float(receta.volumen_lote_base)
            total_botellas = sum(envases.values())
            faltantes = []
            consumos_calculados = {}
            for det in receta.detalles:
                if det.insumo.unidad_medida.upper() in [
                    "UND",
                    "UNIDAD",
                    "U",
                    "UNIDADES",
                ]:
                    is_specific = False
                    consumo_und = 0
                    for tam_key, cant_val in envases.items():
                        if re.search(
                            rf"\b{tam_key.replace('ml', '')}\b", det.insumo.nombre
                        ):
                            consumo_und += cant_val
                            is_specific = True
                    consumo = consumo_und if is_specific else total_botellas
                else:
                    consumo = det.cantidad_requerida * factor
                consumos_calculados[det.id] = consumo
                if det.insumo.stock_actual < consumo:
                    faltantes.append(
                        f"- {det.insumo.nombre}: Faltan {consumo - det.insumo.stock_actual:.1f} {det.insumo.unidad_medida}"
                    )
            if faltantes:
                return False, "Stock insuficiente:\n\n" + "\n".join(faltantes)
            for det in receta.detalles:
                det.insumo.stock_actual -= consumos_calculados[det.id]
            nombre_base = (
                receta.nombre.replace("FORMULA: ", "")
                .replace("LOTE BASE - ", "")
                .strip()
            )
            for tam, cant in envases.items():
                if cant > 0:
                    prod = (
                        db.query(ProductoTerminado)
                        .filter(
                            ProductoTerminado.empresa_id == self.empresa_id,
                            ProductoTerminado.nombre.contains(nombre_base),
                            ProductoTerminado.presentacion.contains(tam),
                        )
                        .first()
                    )
                    if prod:
                        prod.stock_actual += cant
                    else:
                        prod = ProductoTerminado(
                            codigo=f"PT-{nombre_base[:3]}-{tam}",
                            nombre=f"{nombre_base} {tam}",
                            presentacion=tam,
                            stock_actual=cant,
                            empresa_id=self.empresa_id,
                        )
                        db.add(prod)
                        db.flush()
                    db.add(
                        KardexMovimiento(
                            producto_id=prod.id,
                            operacion="Entrada",
                            cantidad=cant,
                            motivo="Producción de Lote",
                            involucrado="Planta",
                            empresa_id=self.empresa_id,
                        )
                    )
            db.commit()
            return True, "Lote procesado y stock actualizado."
        except Exception as e:
            db.rollback()
            return False, f"Error interno: {str(e)}"
        finally:
            db.close()

    def registrar_movimiento_kardex(self, producto_id, motivo, cantidad, involucrado):
        db = self.SessionFactory()
        try:
            prod = (
                db.query(ProductoTerminado)
                .filter_by(id=producto_id, empresa_id=self.empresa_id)
                .first()
            )
            if not prod:
                return False, "Producto no encontrado.", ""
            operacion = "Entrada" if "Suma" in motivo else "Salida"
            if operacion == "Salida" and prod.stock_actual < cantidad:
                return False, f"Stock insuficiente.", ""
            if operacion == "Entrada":
                prod.stock_actual += cantidad
            else:
                prod.stock_actual -= cantidad
            db.add(
                KardexMovimiento(
                    producto_id=producto_id,
                    operacion=operacion,
                    cantidad=cantidad,
                    motivo=motivo,
                    involucrado=involucrado,
                    empresa_id=self.empresa_id,
                )
            )
            db.commit()
            return (
                True,
                "Movimiento registrado.",
                f"\n📦 IVONNE BERNATE OS\nSOPORTE: {datetime.now().strftime('%Y-%m-%d %H:%M')}\nOPERACIÓN: {operacion}\nCANT: {cantidad} | PROD: {prod.nombre}\n",
            )
        except Exception as e:
            db.rollback()
            return False, str(e), ""
        finally:
            db.close()

    def obtener_auditoria_kardex(self):
        with self.SessionFactory() as db:
            return (
                db.query(KardexMovimiento)
                .options(
                    joinedload(KardexMovimiento.producto),
                    joinedload(KardexMovimiento.insumo),
                )
                .filter(KardexMovimiento.empresa_id == self.empresa_id)
                .order_by(KardexMovimiento.fecha.desc())
                .limit(100)
                .all()
            )

    def obtener_kardex_matematico(self):
        with self.SessionFactory() as db:
            productos = (
                db.query(ProductoTerminado)
                .filter(ProductoTerminado.empresa_id == self.empresa_id)
                .all()
            )
            resultados = []
            for p in productos:
                sumas = (
                    db.query(func.sum(KardexMovimiento.cantidad))
                    .filter(
                        KardexMovimiento.empresa_id == self.empresa_id,
                        KardexMovimiento.producto_id == p.id,
                        KardexMovimiento.operacion == "Entrada",
                    )
                    .scalar()
                    or 0
                )
                restas = (
                    db.query(func.sum(KardexMovimiento.cantidad))
                    .filter(
                        KardexMovimiento.empresa_id == self.empresa_id,
                        KardexMovimiento.producto_id == p.id,
                        KardexMovimiento.operacion == "Salida",
                    )
                    .scalar()
                    or 0
                )
                resultados.append(
                    {
                        "nombre": f"{p.nombre} - {p.presentacion}",
                        "sumas": sumas,
                        "restas": restas,
                        "stock_real": p.stock_actual,
                    }
                )
            return resultados

    def obtener_clientes(self):
        with self.SessionFactory() as db:
            return (
                db.query(Cliente)
                .filter(Cliente.empresa_id == self.empresa_id, Cliente.activo == True)
                .order_by(Cliente.nombre)
                .all()
            )

    def guardar_cliente(self, id_cliente, nombre, telefono, ciudad, email):
        db = self.SessionFactory()
        try:
            wa = telefono if telefono else "N/A"
            if id_cliente:
                cliente = (
                    db.query(Cliente)
                    .filter_by(id=id_cliente, empresa_id=self.empresa_id)
                    .first()
                )
                if cliente:
                    cliente.nombre = nombre.strip().title()
                    cliente.telefono = telefono
                    cliente.whatsapp = wa
                    cliente.ciudad = ciudad
                    cliente.email = email
            else:
                db.add(
                    Cliente(
                        nombre=nombre.strip().title(),
                        telefono=telefono,
                        whatsapp=wa,
                        email=email,
                        ciudad=ciudad,
                        tipo_cliente="General",
                        empresa_id=self.empresa_id,
                    )
                )
            db.commit()
            return True, "Cliente guardado."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def eliminar_cliente(self, id_cliente):
        db = self.SessionFactory()
        try:
            cli = (
                db.query(Cliente)
                .filter_by(id=id_cliente, empresa_id=self.empresa_id)
                .first()
            )
            if cli:
                cli.activo = False
                db.commit()
                return True
            return False
        except:
            db.rollback()
            return False
        finally:
            db.close()

    def obtener_asesores(self):
        with self.SessionFactory() as db:
            return (
                db.query(Asesor)
                .filter(Asesor.empresa_id == self.empresa_id, Asesor.activo == True)
                .order_by(Asesor.nombre)
                .all()
            )

    def guardar_asesor(self, id_asesor, nombre, telefono):
        db = self.SessionFactory()
        try:
            if id_asesor:
                asesor = (
                    db.query(Asesor)
                    .filter_by(id=id_asesor, empresa_id=self.empresa_id)
                    .first()
                )
                if asesor:
                    asesor.nombre = nombre.strip().upper()
                    asesor.telefono = telefono
            else:
                db.add(
                    Asesor(
                        nombre=nombre.strip().upper(),
                        telefono=telefono,
                        empresa_id=self.empresa_id,
                    )
                )
            db.commit()
            return True, "Asesor guardado."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def eliminar_asesor(self, id_asesor):
        db = self.SessionFactory()
        try:
            ase = (
                db.query(Asesor)
                .filter_by(id=id_asesor, empresa_id=self.empresa_id)
                .first()
            )
            if ase:
                ase.activo = False
                db.commit()
                return True
            return False
        except:
            db.rollback()
            return False
        finally:
            db.close()

    def obtener_gastos(self):
        with self.SessionFactory() as db:
            return (
                db.query(GastoOperativo)
                .filter(GastoOperativo.empresa_id == self.empresa_id)
                .order_by(GastoOperativo.fecha.desc())
                .all()
            )

    def guardar_gasto(self, descripcion, monto):
        db = self.SessionFactory()
        try:
            db.add(
                GastoOperativo(
                    descripcion=descripcion.strip().capitalize(),
                    monto=monto,
                    empresa_id=self.empresa_id,
                )
            )
            caja = (
                db.query(ControlCaja)
                .filter_by(empresa_id=self.empresa_id)
                .order_by(ControlCaja.id.desc())
                .first()
            )
            if caja:
                caja.egresos += monto
            db.commit()
            return True
        except:
            db.rollback()
            return False
        finally:
            db.close()

    def generar_nro_factura(self):
        with self.SessionFactory() as db:
            ultima = (
                db.query(Venta)
                .filter(Venta.empresa_id == self.empresa_id)
                .order_by(Venta.id.desc())
                .first()
            )
            return (
                f"FACT-{(int(ultima.factura_nro.split('-')[1]) + 1):03d}"
                if ultima
                else "FACT-001"
            )

    def procesar_venta(self, cliente_id, vendedor, tipo_dest, medio_pago, carrito):
        db = self.SessionFactory()
        try:
            total_neto = sum([item["subtotal"] for item in carrito])
            nro = self.generar_nro_factura()
            saldo = total_neto if medio_pago in ["Crédito", "Sistecrédito"] else 0.0
            venta = Venta(
                factura_nro=nro,
                cliente_id=cliente_id,
                vendedor=vendedor,
                tipo_destinatario=tipo_dest,
                medio_pago=medio_pago,
                total_neto=total_neto,
                saldo_pendiente=saldo,
                estado_financiero="Debe" if saldo > 0 else "Pagado",
                empresa_id=self.empresa_id,
            )
            db.add(venta)
            db.flush()

            cliente = (
                db.query(Cliente)
                .filter_by(id=cliente_id, empresa_id=self.empresa_id)
                .first()
            )
            nombre_cliente = cliente.nombre if cliente else "Consumidor Final"

            for item in carrito:
                db.add(
                    VentaDetalle(
                        venta_id=venta.id,
                        producto_id=item["producto_id"],
                        cantidad=item["cant"],
                        precio_unitario=item["precio"],
                        subtotal=item["subtotal"],
                        empresa_id=self.empresa_id,
                    )
                )
                prod = (
                    db.query(ProductoTerminado)
                    .filter_by(id=item["producto_id"], empresa_id=self.empresa_id)
                    .first()
                )
                if prod:
                    prod.stock_actual -= item["cant"]
                    db.add(
                        KardexMovimiento(
                            producto_id=prod.id,
                            operacion="Salida",
                            cantidad=item["cant"],
                            motivo=f"Venta {nro}",
                            involucrado=vendedor,
                            empresa_id=self.empresa_id,
                        )
                    )

            if saldo == 0:
                caja = (
                    db.query(ControlCaja)
                    .filter_by(empresa_id=self.empresa_id)
                    .order_by(ControlCaja.id.desc())
                    .first()
                )
                if caja:
                    caja.ingresos += total_neto
            db.commit()

            ticket = f"✨ *IVONNE BERNATE PRODUCTOS CAPILARES*\n🧾 *FACTURA N°:* {nro}\n📅 *Fecha:* {datetime.now().strftime('%Y-%m-%d %H:%M')}\n👤 *Cliente:* {nombre_cliente}\n💼 *Atiende:* {vendedor}\n💳 *Medio de Pago:* {medio_pago}\n----------------------------------------\n"
            for item in carrito:
                ticket += f"▪ {int(item['cant'])}x *{item['nombre']}*\n   $ {int(item['precio']):,.0f}  =>  $ {int(item['subtotal']):,.0f}\n"
            # ... (código dentro de procesar_venta, justo antes del return)
            ticket += f"----------------------------------------\n💰 *TOTAL A PAGAR: $ {int(total_neto):,.0f}*\n"

            # GENERAMOS EL PDF AQUÍ
            pdf_bytes = self.generar_pdf_venta(
                nro, nombre_cliente, vendedor, medio_pago, carrito, total_neto
            )

            return True, f"Venta {nro} procesada.", ticket, pdf_bytes

        except Exception as e:
            db.rollback()
            # Si hay un error, devolvemos 4 valores (el último es None)
            return False, str(e), "", None
        finally:
            db.close()

    def obtener_cartera_por_cliente(self, cliente_id):
        with self.SessionFactory() as db:
            return (
                db.query(Venta)
                .filter(
                    Venta.empresa_id == self.empresa_id,
                    Venta.cliente_id == cliente_id,
                    Venta.saldo_pendiente > 0,
                    Venta.medio_pago == "Crédito",
                )
                .order_by(Venta.fecha.asc())
                .all()
            )

    def obtener_cartera(self):
        with self.SessionFactory() as db:
            return (
                db.query(Venta)
                .options(joinedload(Venta.cliente))
                .filter(
                    Venta.empresa_id == self.empresa_id,
                    Venta.saldo_pendiente > 0,
                    Venta.medio_pago == "Crédito",
                )
                .order_by(Venta.fecha.desc())
                .all()
            )

    def registrar_abono_fifo(self, cliente_id, monto):
        db = self.SessionFactory()
        try:
            ventas = (
                db.query(Venta)
                .filter(
                    Venta.empresa_id == self.empresa_id,
                    Venta.cliente_id == cliente_id,
                    Venta.saldo_pendiente > 0,
                    Venta.medio_pago == "Crédito",
                )
                .order_by(Venta.fecha.asc())
                .all()
            )
            if not ventas:
                return False, "El cliente no tiene facturas a crédito pendientes."
            if monto <= 0:
                return False, "El monto debe ser mayor a 0."
            monto_restante = monto
            mensajes_abono = []
            for v in ventas:
                if monto_restante <= 0:
                    break
                abono_aplicado = min(monto_restante, v.saldo_pendiente)
                db.add(
                    Abono(
                        venta_id=v.id, monto=abono_aplicado, empresa_id=self.empresa_id
                    )
                )
                v.saldo_pendiente -= abono_aplicado
                if v.saldo_pendiente <= 0:
                    v.estado_financiero = "Pagado"
                monto_restante -= abono_aplicado
                mensajes_abono.append(f"#{v.factura_nro}")
            caja = (
                db.query(ControlCaja)
                .filter_by(empresa_id=self.empresa_id)
                .order_by(ControlCaja.id.desc())
                .first()
            )
            if caja:
                caja.ingresos += monto - monto_restante
            db.commit()
            return True, f"Pago aplicado a las facturas: {', '.join(mensajes_abono)}"
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def obtener_metricas_dashboard(self):
        with self.SessionFactory() as db:
            hoy = datetime.now().date()
            caja = (
                db.query(ControlCaja)
                .filter_by(empresa_id=self.empresa_id)
                .order_by(ControlCaja.id.desc())
                .first()
            )
            ventas_hoy = (
                db.query(func.sum(Venta.total_neto))
                .filter(
                    Venta.empresa_id == self.empresa_id, func.date(Venta.fecha) == hoy
                )
                .scalar()
                or 0.0
            )
            total_clientes = (
                db.query(func.count(Cliente.id))
                .filter(Cliente.empresa_id == self.empresa_id)
                .scalar()
                or 0
            )
            return {
                "caja_actual": (caja.monto_apertura + caja.ingresos - caja.egresos)
                if caja
                else 0.0,
                "ventas_hoy": ventas_hoy,
                "total_clientes": total_clientes,
            }

    def obtener_datos_suscriptor(self, usuario):
        with self.SessionFactory() as db:
            return db.query(Suscriptor).filter(Suscriptor.usuario == usuario).first()

    def verificar_acceso(self, usuario_ingresado, clave_ingresada):
        db = self.SessionFactory()
        try:
            usuario_db = (
                db.query(Suscriptor)
                .filter(
                    Suscriptor.usuario == usuario_ingresado,
                    Suscriptor.password == clave_ingresada,
                )
                .first()
            )
            if usuario_db:
                return True, {
                    "usuario": usuario_db.usuario,
                    "empresa_id": usuario_db.empresa_id,
                    "plan": usuario_db.plan,
                }
            return False, None
        finally:
            db.close()

    def eliminar_pedido_erroneo(self, numero_orden):
        db = self.SessionFactory()
        try:
            venta = (
                db.query(Venta)
                .filter(
                    Venta.factura_nro == numero_orden,
                    Venta.empresa_id == self.empresa_id,
                )
                .first()
            )
            if not venta:
                return False, "El pedido no existe."
            detalles = (
                db.query(VentaDetalle)
                .filter(
                    VentaDetalle.venta_id == venta.id,
                    VentaDetalle.empresa_id == self.empresa_id,
                )
                .all()
            )
            for det in detalles:
                prod = (
                    db.query(ProductoTerminado)
                    .filter_by(id=det.producto_id, empresa_id=self.empresa_id)
                    .first()
                )
                if prod:
                    prod.stock_actual += det.cantidad
                db.delete(det)
            db.delete(venta)
            db.commit()
            return (
                True,
                f"Pedido {numero_orden} eliminado permanentemente y stock recuperado.",
            )
        except Exception as e:
            db.rollback()
            return False, f"Error: {str(e)}"
        finally:
            db.close()

    def obtener_lista_compras(self):
        db = self.SessionFactory()
        try:
            movimientos = (
                db.query(KardexMovimiento.motivo)
                .filter(
                    KardexMovimiento.empresa_id == self.empresa_id,
                    KardexMovimiento.motivo.like("Compra%"),
                )
                .distinct()
                .all()
            )
            return [m[0] for m in movimientos]
        finally:
            db.close()

    def eliminar_compra_erronea(self, motivo_compra):
        db = self.SessionFactory()
        try:
            movs = (
                db.query(KardexMovimiento)
                .filter(
                    KardexMovimiento.motivo == motivo_compra,
                    KardexMovimiento.empresa_id == self.empresa_id,
                )
                .all()
            )
            if not movs:
                return False, "No se encontraron registros."
            for m in movs:
                if m.insumo_id:
                    ins = (
                        db.query(Insumo)
                        .filter_by(id=m.insumo_id, empresa_id=self.empresa_id)
                        .first()
                    )
                    if ins:
                        ins.stock_actual -= m.cantidad
                elif m.producto_id:
                    prod = (
                        db.query(ProductoTerminado)
                        .filter_by(id=m.producto_id, empresa_id=self.empresa_id)
                        .first()
                    )
                    if prod:
                        prod.stock_actual -= m.cantidad
                db.delete(m)
            db.commit()
            return True, f"Compra '{motivo_compra}' eliminada."
        except Exception as e:
            db.rollback()
            return False, f"Error: {str(e)}"
        finally:
            db.close()

    def obtener_todas_las_ventas(self):
        db = self.SessionFactory()
        try:
            return (
                db.query(Venta)
                .filter(Venta.empresa_id == self.empresa_id)
                .order_by(Venta.fecha.asc())
                .all()
            )
        finally:
            db.close()

    def registrar_nueva_empresa_vacia(
        self, usuario, password, plan, fecha_vencimiento, empresa_id
    ):
        """Crea un nuevo cliente (SaaS) con base de datos limpia."""
        db = self.SessionFactory()
        try:
            # 1. Verificar si el usuario ya existe
            existe_usuario = (
                db.query(Suscriptor).filter_by(usuario=usuario.strip()).first()
            )
            if existe_usuario:
                return (
                    False,
                    "❌ El nombre de usuario ya está registrado en el sistema.",
                )

            # 2. Verificar si el ID de empresa ya existe (NUEVO SEGURO)
            existe_empresa = (
                db.query(Suscriptor).filter_by(empresa_id=empresa_id.strip()).first()
            )
            if existe_empresa:
                return (
                    False,
                    f"❌ El ID de empresa '{empresa_id}' ya está en uso. Usa uno diferente.",
                )

            # 3. Crear el perfil de Suscriptor
            nuevo_suscriptor = Suscriptor(
                usuario=usuario.strip(),
                password=password.strip(),
                fecha_vencimiento=fecha_vencimiento,
                plan=plan,
                empresa_id=empresa_id.strip(),
            )
            db.add(nuevo_suscriptor)

            # 4. Registrar "Consumidor Final" por defecto
            cliente_defecto = Cliente(
                nombre="Consumidor Final",
                telefono="0000000000",
                whatsapp="N/A",
                email="consumidor@final.com",
                ciudad="General",
                tipo_cliente="General",
                activo=True,
                empresa_id=empresa_id.strip(),
            )
            db.add(cliente_defecto)

            # 5. Registrar un Asesor/Vendedor inicial por defecto
            asesor_defecto = Asesor(
                nombre="ADMINISTRADOR",
                telefono="0000000000",
                activo=True,
                empresa_id=empresa_id.strip(),
            )
            db.add(asesor_defecto)

            # 6. Crear apertura de caja inicial en $0
            caja_defecto = ControlCaja(
                monto_apertura=0.0,
                ingresos=0.0,
                egresos=0.0,
                usuario_cajero=usuario.strip(),
                empresa_id=empresa_id.strip(),
            )
            db.add(caja_defecto)

            db.commit()
            return (
                True,
                f"🚀 ¡Empresa '{empresa_id}' registrada con éxito en el sistema multi-tenant!",
            )

        except Exception as e:
            db.rollback()
            return False, f"Error al aprovisionar la nueva empresa: {str(e)}"
        finally:
            db.close()

    def cambiar_password_suscriptor(self, usuario, password_actual, nueva_password):
        db = self.SessionFactory()
        try:
            sub = db.query(Suscriptor).filter(Suscriptor.usuario == usuario).first()
            if not sub:
                return False, "Usuario no encontrado en la base de datos."
            if sub.password != password_actual:
                return False, "La contraseña actual es incorrecta."
            sub.password = nueva_password
            db.commit()
            return True, "¡Contraseña actualizada exitosamente!"
        except Exception as e:
            db.rollback()
            return False, f"Error en la base de datos: {str(e)}"
        finally:
            db.close()

    def procesar_cambio_kardex(
        self, involucrado, id_entra, cant_entra, id_sale, cant_sale
    ):
        """Procesa un trueque o cambio de mercancía entre compañeros."""
        db = self.SessionFactory()
        try:
            prod_entra = (
                db.query(ProductoTerminado)
                .filter_by(id=id_entra, empresa_id=self.empresa_id)
                .first()
            )
            prod_sale = (
                db.query(ProductoTerminado)
                .filter_by(id=id_sale, empresa_id=self.empresa_id)
                .first()
            )

            if not prod_entra or not prod_sale:
                return False, "Uno de los productos no fue encontrado.", ""

            if prod_sale.stock_actual < cant_sale:
                return (
                    False,
                    f"Stock insuficiente del producto que entregas ({prod_sale.nombre}).",
                    "",
                )

            # 1. Restar el producto que sale (el que entrego)
            prod_sale.stock_actual -= cant_sale
            db.add(
                KardexMovimiento(
                    producto_id=prod_sale.id,
                    operacion="Salida",
                    cantidad=cant_sale,
                    motivo=f"Cambio por {prod_entra.nombre}",
                    involucrado=involucrado,
                    empresa_id=self.empresa_id,
                )
            )

            # 2. Sumar el producto que entra (el que recibo)
            prod_entra.stock_actual += cant_entra
            db.add(
                KardexMovimiento(
                    producto_id=prod_entra.id,
                    operacion="Entrada",
                    cantidad=cant_entra,
                    motivo=f"Cambio entregando {prod_sale.nombre}",
                    involucrado=involucrado,
                    empresa_id=self.empresa_id,
                )
            )

            db.commit()
            ticket = f"Cambio procesado: Entregó {cant_sale} {prod_sale.nombre} / Recibió {cant_entra} {prod_entra.nombre}"
            return (
                True,
                "Cambio de producto registrado correctamente en Kardex.",
                ticket,
            )

        except Exception as e:
            db.rollback()
            return False, f"Error interno: {str(e)}", ""
        finally:
            db.close()

    def generar_pdf_venta(
        self, nro_factura, nombre_cliente, vendedor, medio_pago, carrito, total_neto
    ):
        """Genera un archivo PDF profesional en memoria para descargarlo."""
        try:
            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.add_page()

            # 1. ENCABEZADO DE LA EMPRESA
            pdf.set_font("helvetica", "B", 18)
            # Usamos el ID de la empresa como título (puedes mejorarlo luego)
            nombre_negocio = str(self.empresa_id).replace("_", " ").upper()
            pdf.cell(0, 10, txt=nombre_negocio, ln=True, align="C")

            pdf.set_font("helvetica", "", 10)
            pdf.cell(0, 6, txt="Documento Electrónico de Venta", ln=True, align="C")
            pdf.ln(8)

            # 2. DATOS DE LA FACTURA
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(35, 6, txt="Factura Nro:", border=0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(65, 6, txt=nro_factura, ln=True)

            pdf.set_font("helvetica", "B", 10)
            pdf.cell(35, 6, txt="Fecha:", border=0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(65, 6, txt=datetime.now().strftime("%Y-%m-%d %H:%M"), ln=True)

            pdf.set_font("helvetica", "B", 10)
            pdf.cell(35, 6, txt="Cliente:", border=0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(65, 6, txt=nombre_cliente, ln=True)

            pdf.set_font("helvetica", "B", 10)
            pdf.cell(35, 6, txt="Medio Pago:", border=0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(65, 6, txt=medio_pago, ln=True)

            pdf.ln(10)

            # 3. TABLA DE PRODUCTOS (Cabecera)
            pdf.set_fill_color(220, 220, 220)
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(15, 8, txt="Cant", border=1, align="C", fill=True)
            pdf.cell(
                95, 8, txt="Descripción del Producto", border=1, align="C", fill=True
            )
            pdf.cell(40, 8, txt="V. Unitario", border=1, align="C", fill=True)
            pdf.cell(40, 8, txt="Subtotal", border=1, align="C", fill=True)
            pdf.ln()

            # 4. FILAS DEL CARRITO
            pdf.set_font("helvetica", "", 10)
            for item in carrito:
                pdf.cell(15, 8, txt=str(int(item["cant"])), border=1, align="C")
                pdf.cell(95, 8, txt=item["nombre"][:45], border=1, align="L")
                pdf.cell(
                    40, 8, txt=f"$ {int(item['precio']):,.0f}", border=1, align="C"
                )
                pdf.cell(
                    40, 8, txt=f"$ {int(item['subtotal']):,.0f}", border=1, align="C"
                )
                pdf.ln()

            # 5. TOTAL A PAGAR
            pdf.ln(5)
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(150, 10, txt="TOTAL A PAGAR:", align="R")
            pdf.cell(40, 10, txt=f"$ {int(total_neto):,.0f}", border=1, align="C")

            # 6. PIE DE PÁGINA
            pdf.ln(20)
            pdf.set_font("helvetica", "I", 9)
            pdf.cell(
                0, 5, txt="Gracias por su compra. ¡Vuelva pronto!", align="C", ln=True
            )

            # Retornar el archivo en formato de bytes (listo para descargar)
            return bytes(pdf.output())

        except Exception as e:
            print(f"Error generando PDF: {e}")
            return None

    def generar_pdf_compra(
        self, nro_orden, proveedor_nombre, comprador, carrito, total
    ):
        """Genera un archivo PDF profesional para los comprobantes de ingreso."""
        try:
            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.add_page()

            # 1. ENCABEZADO DE LA EMPRESA
            pdf.set_font("helvetica", "B", 18)
            nombre_negocio = str(self.empresa_id).replace("_", " ").upper()
            pdf.cell(0, 10, txt=nombre_negocio, ln=True, align="C")

            pdf.set_font("helvetica", "", 10)
            pdf.cell(0, 6, txt="Comprobante de Ingreso / Compra", ln=True, align="C")
            pdf.ln(8)

            # 2. DATOS DEL INGRESO
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(35, 6, txt="Orden Nro:", border=0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(65, 6, txt=nro_orden, ln=True)

            pdf.set_font("helvetica", "B", 10)
            pdf.cell(35, 6, txt="Fecha:", border=0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(65, 6, txt=datetime.now().strftime("%Y-%m-%d %H:%M"), ln=True)

            pdf.set_font("helvetica", "B", 10)
            pdf.cell(35, 6, txt="Proveedor:", border=0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(65, 6, txt=proveedor_nombre, ln=True)

            pdf.set_font("helvetica", "B", 10)
            pdf.cell(35, 6, txt="Recibe:", border=0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(65, 6, txt=comprador, ln=True)

            pdf.ln(10)

            # 3. TABLA DE PRODUCTOS
            pdf.set_fill_color(220, 220, 220)
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(15, 8, txt="Cant", border=1, align="C", fill=True)
            pdf.cell(105, 8, txt="Item Ingresado", border=1, align="C", fill=True)
            pdf.cell(70, 8, txt="Valor Total", border=1, align="C", fill=True)
            pdf.ln()

            # 4. FILAS DEL CARRITO
            pdf.set_font("helvetica", "", 10)
            for item in carrito:
                pdf.cell(15, 8, txt=str(item["cant"]), border=1, align="C")
                pdf.cell(105, 8, txt=item["nombre"][:50], border=1, align="L")
                pdf.cell(
                    70, 8, txt=f"$ {int(item['precio']):,.0f}", border=1, align="C"
                )
                pdf.ln()

            # 5. TOTAL
            pdf.ln(5)
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(120, 10, txt="TOTAL INVERSIÓN:", align="R")
            pdf.cell(70, 10, txt=f"$ {int(total):,.0f}", border=1, align="C")

            return bytes(pdf.output())

        except Exception as e:
            print(f"Error generando PDF compra: {e}")
            return None

    def importar_excel_onboarding(self, archivo_excel):
        """Lee la plantilla de Excel y carga Insumos, Productos y Fórmulas."""
        import pandas as pd  # Importación local para esta función

        db = self.SessionFactory()
        try:
            # 1. Leer todas las hojas del Excel
            xls = pd.read_excel(archivo_excel, sheet_name=None)

            if not all(hoja in xls for hoja in ["Insumos", "Productos", "Formulas"]):
                return (
                    False,
                    "❌ El Excel no tiene las 3 hojas requeridas: Insumos, Productos, Formulas.",
                )

            df_insumos = xls["Insumos"]
            df_productos = xls["Productos"]
            df_formulas = xls["Formulas"]

            # Diccionarios de memoria para vincular las fórmulas luego
            mapa_insumos = {}
            mapa_productos = {}

            # 2. Guardar Insumos
            for _, row in df_insumos.iterrows():
                nombre = str(row["Nombre"]).strip().upper()
                insumo = Insumo(
                    codigo=f"INS-{datetime.now().strftime('%S%f')[:5]}",
                    nombre=nombre,
                    categoria=str(row["Categoria"]).strip(),
                    unidad_medida=str(row["Unidad"]).strip(),
                    costo_promedio=float(row["Costo"]),
                    stock_actual=float(row["Stock"]),
                    empresa_id=self.empresa_id,
                )
                db.add(insumo)
                db.flush()  # Guardamos para obtener el ID real
                mapa_insumos[nombre] = insumo.id

            # 3. Guardar Productos
            for _, row in df_productos.iterrows():
                nombre = str(row["Nombre"]).strip().upper()
                producto = ProductoTerminado(
                    codigo=f"PT-{datetime.now().strftime('%S%f')[:5]}",
                    nombre=nombre,
                    presentacion=str(row["Presentacion"]).strip(),
                    precio_venta=float(row["Precio"]),
                    stock_actual=0,  # Inician en cero por defecto
                    empresa_id=self.empresa_id,
                )
                db.add(producto)
                db.flush()
                mapa_productos[nombre] = producto.id

            # 4. Guardar Fórmulas (Recetas)
            # Agrupamos por Producto_Base para crear la receta maestra
            for prod_nombre, grupo in df_formulas.groupby("Producto_Base"):
                prod_nombre_limpio = str(prod_nombre).strip().upper()

                # Validar que el producto exista en la hoja Productos
                if prod_nombre_limpio not in mapa_productos:
                    continue

                volumen_lote = float(grupo["Volumen_Lote"].iloc[0])

                receta = Receta(
                    nombre=f"FORMULA: {prod_nombre_limpio}",
                    volumen_lote_base=volumen_lote,
                    producto_id=mapa_productos[prod_nombre_limpio],
                    empresa_id=self.empresa_id,
                )
                db.add(receta)
                db.flush()

                # Guardar los detalles (ingredientes) de esa receta
                for _, row in grupo.iterrows():
                    ins_nombre = str(row["Insumo_Requerido"]).strip().upper()
                    if ins_nombre in mapa_insumos:
                        detalle = RecetaDetalle(
                            receta_id=receta.id,
                            insumo_id=mapa_insumos[ins_nombre],
                            cantidad_requerida=float(row["Cantidad"]),
                            cantidad_necesaria=float(row["Cantidad"]),
                            empresa_id=self.empresa_id,
                        )
                        db.add(detalle)

            db.commit()
            return (
                True,
                "✅ ¡Carga Masiva Exitosa! Tu sistema está configurado y listo para operar.",
            )

        except Exception as e:
            db.rollback()
            return (
                False,
                f"⚠️ Error procesando el Excel. Revisa el formato. Detalle: {str(e)}",
            )
        finally:
            db.close()

    def resetear_empresa_completa(self):
        """Borra todos los datos operativos de una empresa, dejándola como nueva."""
        db = self.SessionFactory()
        try:
            # El orden de borrado es vital por las llaves foráneas (Foreign Keys)
            # 1. Borramos auditorías, movimientos y detalles primero
            db.query(KardexMovimiento).filter_by(empresa_id=self.empresa_id).delete()
            db.query(VentaDetalle).filter_by(empresa_id=self.empresa_id).delete()
            db.query(Abono).filter_by(empresa_id=self.empresa_id).delete()
            db.query(RecetaDetalle).filter_by(empresa_id=self.empresa_id).delete()
            db.query(GastoOperativo).filter_by(empresa_id=self.empresa_id).delete()

            # 2. Borramos las cabeceras (Ventas, Recetas)
            db.query(Venta).filter_by(empresa_id=self.empresa_id).delete()
            db.query(Receta).filter_by(empresa_id=self.empresa_id).delete()

            # 3. Borramos los catálogos y clientes
            db.query(ProductoTerminado).filter_by(empresa_id=self.empresa_id).delete()
            db.query(Insumo).filter_by(empresa_id=self.empresa_id).delete()
            db.query(Proveedor).filter_by(empresa_id=self.empresa_id).delete()
            # Ojo: No borramos Suscriptor, Asesores, ni la Caja para no romper el Login del usuario.

            db.commit()
            return True, "✅ Base de datos reseteada con éxito. El sistema está limpio."

        except Exception as e:
            db.rollback()
            return False, f"Error al resetear la base de datos: {str(e)}"
        finally:
            db.close()

    def obtener_todas_las_empresas(self):
        """Obtiene la lista de todos los suscriptores SaaS registrados."""
        with self.SessionFactory() as db:
            return db.query(Suscriptor).order_by(Suscriptor.empresa_id).all()

    def eliminar_empresa_definitivamente(self, empresa_id_a_borrar):
        """Borra absolutamente todo rastro de una empresa, incluyendo su inicio de sesión."""
        db = self.SessionFactory()
        try:
            # 1. Borrar tablas de transacciones y detalles (Las ramas)
            db.query(KardexMovimiento).filter_by(
                empresa_id=empresa_id_a_borrar
            ).delete()
            db.query(VentaDetalle).filter_by(empresa_id=empresa_id_a_borrar).delete()
            db.query(Abono).filter_by(empresa_id=empresa_id_a_borrar).delete()
            db.query(RecetaDetalle).filter_by(empresa_id=empresa_id_a_borrar).delete()
            db.query(GastoOperativo).filter_by(empresa_id=empresa_id_a_borrar).delete()

            # 2. Borrar cabeceras operativas (El tronco)
            db.query(Venta).filter_by(empresa_id=empresa_id_a_borrar).delete()
            db.query(Receta).filter_by(empresa_id=empresa_id_a_borrar).delete()

            # 3. Borrar Catálogos e Inventarios
            db.query(ProductoTerminado).filter_by(
                empresa_id=empresa_id_a_borrar
            ).delete()
            db.query(CatalogoProducto).filter_by(
                empresa_id=empresa_id_a_borrar
            ).delete()
            db.query(Insumo).filter_by(empresa_id=empresa_id_a_borrar).delete()
            db.query(Proveedor).filter_by(empresa_id=empresa_id_a_borrar).delete()

            # 4. Borrar Entidades Base
            db.query(Cliente).filter_by(empresa_id=empresa_id_a_borrar).delete()
            db.query(Asesor).filter_by(empresa_id=empresa_id_a_borrar).delete()
            db.query(ControlCaja).filter_by(empresa_id=empresa_id_a_borrar).delete()

            # 5. EL GOLPE FINAL: Borrar el acceso del cliente al sistema
            db.query(Suscriptor).filter_by(empresa_id=empresa_id_a_borrar).delete()

            db.commit()
            return (
                True,
                f"✅ La empresa '{empresa_id_a_borrar}' y todos sus datos fueron eliminados de los servidores.",
            )
        except Exception as e:
            db.rollback()
            return False, f"Error al eliminar la empresa: {str(e)}"
        finally:
            db.close()
