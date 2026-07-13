from datetime import datetime
import re
from sqlalchemy import func
from sqlalchemy.orm import joinedload

# Asegúrate que esta línea en controllers.py sea así:
from models import (
    Insumo,
    Proveedor,
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

    def generar_nro_orden_compra(self):
        with self.SessionFactory() as db:
            ultimo = (
                db.query(KardexMovimiento)
                .filter(KardexMovimiento.motivo.like("%#IB-%"))
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
                .filter(Insumo.activo == True)
                .order_by(Insumo.categoria, Insumo.nombre)
                .all()
            )

    def obtener_proveedores(self):
        with self.SessionFactory() as db:
            return (
                db.query(Proveedor)
                .filter(Proveedor.activo == True)
                .order_by(Proveedor.nombre)
                .all()
            )

    def guardar_o_actualizar_insumo(
        self, id_insumo, nombre, categoria, unidad, costo, stock, nombre_prov
    ):
        db = self.SessionFactory()
        try:
            nombre_prov_limpio = str(nombre_prov).strip()
            prov = db.query(Proveedor).filter_by(nombre=nombre_prov_limpio).first()
            if not prov and nombre_prov_limpio != "S/N":
                prov = Proveedor(
                    nombre=nombre_prov_limpio,
                    nit=f"SN-{datetime.now().strftime('%H%M%S')}",
                )
                db.add(prov)
                db.flush()
            prov_id = prov.id if prov else None

            insumo = (
                db.query(Insumo).filter_by(id=id_insumo).first()
                if id_insumo
                else db.query(Insumo).filter_by(nombre=nombre.strip()).first()
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
            insumo = db.query(Insumo).filter_by(id=id_insumo).first()
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
            for item in carrito:
                if item["tipo"] == "Insumos":
                    insumo = db.query(Insumo).filter_by(id=item["id"]).first()
                    if insumo:
                        if insumo.stock_actual > 0:
                            costo_total_actual = (
                                insumo.stock_actual * insumo.costo_promedio
                            )
                            costo_nueva_compra = item["precio"]
                            insumo.costo_promedio = (
                                costo_total_actual + costo_nueva_compra
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
                                involucrado=proveedor_nombre,
                            )
                        )

                elif item["tipo"] == "Productos Terminados":
                    prod = db.query(ProductoTerminado).filter_by(id=item["id"]).first()
                    if prod:
                        if prod.stock_actual > 0:
                            costo_total_actual = prod.stock_actual * prod.costo_unitario
                            costo_nueva_compra = item["precio"]
                            prod.costo_unitario = (
                                costo_total_actual + costo_nueva_compra
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
                                involucrado=proveedor_nombre,
                            )
                        )
            db.commit()

            total = sum(i["precio"] for i in carrito)
            ticket = f"🏢 *LINDLEY CLOUD OS*\n📦 *COMPROBANTE DE INGRESO*\n----------------------------------------\n"
            ticket += f"🧾 *Orden N°:* {nro_orden}\n📅 *Fecha:* {datetime.now().strftime('%Y-%m-%d %H:%M')}\n🏭 *Proveedor:* {proveedor_nombre}\n👤 *Comprador/Recibe:* {comprador}\n----------------------------------------\n"
            for item in carrito:
                ticket += f"▪ {item['cant']:,.0f}x {item['nombre']}\n   Subtotal: $ {item['precio']:,.0f}\n"
            ticket += f"----------------------------------------\n💰 *TOTAL INVERSIÓN: $ {total:,.0f}*\n"

            return True, "Compra registrada con éxito.", ticket
        except Exception as e:
            db.rollback()
            return False, f"Error: {str(e)}", ""
        finally:
            db.close()

    def obtener_catalogo_productos(self):
        with self.SessionFactory() as db:
            return db.query(ProductoTerminado).order_by(ProductoTerminado.nombre).all()

    def obtener_productos_terminados(self):
        with self.SessionFactory() as db:
            return (
                db.query(ProductoTerminado)
                .filter(ProductoTerminado.activo == True)
                .order_by(ProductoTerminado.nombre)
                .all()
            )

    def guardar_producto_catalogo(self, nombre, presentacion, precio, dias, puntos):
        db = self.SessionFactory()
        try:
            nombre_limpio = nombre.strip().upper()

            existe_pt = (
                db.query(ProductoTerminado)
                .filter_by(nombre=nombre_limpio, presentacion=presentacion)
                .first()
            )
            if not existe_pt:
                codigo_nuevo = f"PT-{datetime.now().strftime('%S%f')[:5]}"
                db.add(
                    ProductoTerminado(
                        codigo=codigo_nuevo,
                        nombre=nombre_limpio,
                        presentacion=presentacion,
                        precio_venta=precio,
                        dias_consumo=dias,
                        puntos_pv=puntos,
                        stock_actual=0,
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
            prod_pt = db.query(ProductoTerminado).filter_by(id=producto_id).first()
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
            prod_pt = db.query(ProductoTerminado).filter_by(id=producto_id).first()
            if not prod_pt:
                return False, "Producto no encontrado."
            db.delete(prod_pt)
            db.commit()
            return True, "Producto eliminado completamente de Supabase."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def obtener_recetas_disponibles(self):
        with self.SessionFactory() as db:
            return db.query(Receta).order_by(Receta.nombre).all()

    def guardar_nueva_formula(self, nombre, volumen, lista_ingredientes):
        db = self.SessionFactory()
        try:
            prod = db.query(ProductoTerminado).filter_by(nombre=nombre).first()
            if not prod:
                prod = ProductoTerminado(
                    codigo=f"PT-{datetime.now().strftime('%H%M%S')}",
                    nombre=nombre,
                    linea="Capilar",
                    presentacion="Base Granel",
                )
                db.add(prod)
                db.flush()
            receta = db.query(Receta).filter_by(nombre=nombre).first()
            if receta:
                db.query(RecetaDetalle).filter_by(receta_id=receta.id).delete()
            else:
                receta = Receta(nombre=nombre, producto_id=prod.id)
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
                .filter(func.upper(Receta.nombre) == receta_nombre.upper().strip())
                .first()
            )
            if not receta:
                return (
                    False,
                    f"La fórmula '{receta_nombre}' no existe en la base de datos.",
                )
            if receta.volumen_lote_base <= 0:
                return False, "El volumen base de la fórmula es inválido."
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
                        tam_num = tam_key.replace("ml", "")
                        if re.search(rf"\b{tam_num}\b", det.insumo.nombre):
                            consumo_und += cant_val
                            is_specific = True
                    consumo = consumo_und if is_specific else total_botellas
                else:
                    consumo = det.cantidad_requerida * factor

                consumos_calculados[det.id] = consumo
                if det.insumo.stock_actual < consumo:
                    falta = consumo - det.insumo.stock_actual
                    faltantes.append(
                        f"- {det.insumo.nombre}: Faltan {int(falta)} UND"
                        if det.insumo.unidad_medida.upper() in ["UND", "UNIDAD"]
                        else f"- {det.insumo.nombre}: Faltan {falta:.2f} {det.insumo.unidad_medida}"
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
                        )
                    )
            db.commit()
            return True, "¡Éxito! Lote procesado y stock actualizado."
        except Exception as e:
            db.rollback()
            return False, f"Error interno: {str(e)}"
        finally:
            db.close()

    def registrar_movimiento_kardex(self, producto_id, motivo, cantidad, involucrado):
        db = self.SessionFactory()
        try:
            prod = db.query(ProductoTerminado).filter_by(id=producto_id).first()
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
                )
            )
            db.commit()
            return (
                True,
                "Movimiento registrado.",
                self._generar_ticket(
                    involucrado,
                    motivo,
                    cantidad,
                    f"{prod.nombre} ({prod.presentacion})",
                ),
            )
        except Exception as e:
            db.rollback()
            return False, str(e), ""
        finally:
            db.close()

    def _generar_ticket(self, involucrado, operacion, cant, producto):
        return f"\n📦 LINDLEY CLOUD OS\nSOPORTE: {datetime.now().strftime('%Y-%m-%d %H:%M')}\nOPERACIÓN: {operacion}\nCANT: {cant} | PROD: {producto}\n"

    def obtener_auditoria_kardex(self):
        with self.SessionFactory() as db:
            return (
                db.query(KardexMovimiento)
                .options(
                    joinedload(KardexMovimiento.producto),
                    joinedload(KardexMovimiento.insumo),
                )
                .order_by(KardexMovimiento.fecha.desc())
                .limit(100)
                .all()
            )

    def obtener_kardex_matematico(self):
        with self.SessionFactory() as db:
            productos = db.query(ProductoTerminado).all()
            resultados = []
            for p in productos:
                sumas = (
                    db.query(func.sum(KardexMovimiento.cantidad))
                    .filter(
                        KardexMovimiento.producto_id == p.id,
                        KardexMovimiento.operacion == "Entrada",
                    )
                    .scalar()
                    or 0
                )
                restas = (
                    db.query(func.sum(KardexMovimiento.cantidad))
                    .filter(
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
                .filter(Cliente.activo == True)
                .order_by(Cliente.nombre)
                .all()
            )

    def guardar_cliente(self, id_cliente, nombre, telefono, ciudad, email):
        db = self.SessionFactory()
        try:
            wa = telefono if telefono else "N/A"
            if id_cliente:
                cliente = db.query(Cliente).filter_by(id=id_cliente).first()
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
            cli = db.query(Cliente).filter_by(id=id_cliente).first()
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
                .filter(Asesor.activo == True)
                .order_by(Asesor.nombre)
                .all()
            )

    def guardar_asesor(self, id_asesor, nombre, telefono):
        db = self.SessionFactory()
        try:
            if id_asesor:
                asesor = db.query(Asesor).filter_by(id=id_asesor).first()
                if asesor:
                    asesor.nombre = nombre.strip().upper()
                    asesor.telefono = telefono
            else:
                db.add(Asesor(nombre=nombre.strip().upper(), telefono=telefono))
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
            ase = db.query(Asesor).filter_by(id=id_asesor).first()
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
            return db.query(GastoOperativo).order_by(GastoOperativo.fecha.desc()).all()

    def guardar_gasto(self, descripcion, monto):
        db = self.SessionFactory()
        try:
            db.add(
                GastoOperativo(
                    descripcion=descripcion.strip().capitalize(), monto=monto
                )
            )
            caja = db.query(ControlCaja).order_by(ControlCaja.id.desc()).first()
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
            ultima = db.query(Venta).order_by(Venta.id.desc()).first()
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
            )
            db.add(venta)
            db.flush()

            cliente = db.query(Cliente).filter_by(id=cliente_id).first()
            nombre_cliente = cliente.nombre if cliente else "Consumidor Final"

            for item in carrito:
                db.add(
                    VentaDetalle(
                        venta_id=venta.id,
                        producto_id=item["producto_id"],
                        cantidad=item["cant"],
                        precio_unitario=item["precio"],
                        subtotal=item["subtotal"],
                    )
                )
                prod = (
                    db.query(ProductoTerminado)
                    .filter_by(id=item["producto_id"])
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
                        )
                    )

            if saldo == 0:
                caja = db.query(ControlCaja).order_by(ControlCaja.id.desc()).first()
                if caja:
                    caja.ingresos += total_neto
            db.commit()

            # Construcción del ticket con formato profesional
            ticket = f"✨ *IVONNE BERNATE PRODUCTOS CAPILARES*\n🧾 *FACTURA N°:* {nro}\n📅 *Fecha:* {datetime.now().strftime('%Y-%m-%d %H:%M')}\n👤 *Cliente:* {nombre_cliente}\n💼 *Atiende:* {vendedor}\n💳 *Medio de Pago:* {medio_pago}\n----------------------------------------\n"
            for item in carrito:
                cant = int(item["cant"])
                prec = int(item["precio"])
                subt = int(item["subtotal"])
                ticket += f"▪ {cant}x *{item['nombre']}*\n   $ {prec:,.0f}  =>  $ {subt:,.0f}\n"

            total_formateado = int(total_neto)
            ticket += f"----------------------------------------\n💰 *TOTAL A PAGAR: $ {total_formateado:,.0f}*\n🙏 *¡Gracias por su compra!*\n"

            return True, f"Venta {nro} procesada.", ticket
        except Exception as e:
            db.rollback()
            return False, str(e), ""
        finally:
            db.close()

    def obtener_cartera_por_cliente(self, cliente_id):
        with self.SessionFactory() as db:
            return (
                db.query(Venta)
                .filter(
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
                .filter(Venta.saldo_pendiente > 0, Venta.medio_pago == "Crédito")
                .order_by(Venta.fecha.desc())
                .all()
            )

    def registrar_abono_fifo(self, cliente_id, monto):
        db = self.SessionFactory()
        try:
            ventas = (
                db.query(Venta)
                .filter(
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
                db.add(Abono(venta_id=v.id, monto=abono_aplicado))
                v.saldo_pendiente -= abono_aplicado
                if v.saldo_pendiente <= 0:
                    v.estado_financiero = "Pagado"
                monto_restante -= abono_aplicado
                mensajes_abono.append(f"#{v.factura_nro}")
            caja = db.query(ControlCaja).order_by(ControlCaja.id.desc()).first()
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
            caja = db.query(ControlCaja).order_by(ControlCaja.id.desc()).first()
            ventas_hoy = (
                db.query(func.sum(Venta.total_neto))
                .filter(func.date(Venta.fecha) == hoy)
                .scalar()
                or 0.0
            )
            total_clientes = db.query(func.count(Cliente.id)).scalar() or 0
            return {
                "caja_actual": (caja.monto_apertura + caja.ingresos - caja.egresos)
                if caja
                else 0.0,
                "ventas_hoy": ventas_hoy,  # <--- EL ERROR ESTABA AQUÍ (Decía values_hoy)
                "total_clientes": total_clientes,
            }

    def obtener_datos_suscriptor(self, usuario):
        with self.SessionFactory() as db:
            # Trae la información del usuario desde la base de datos
            return db.query(Suscriptor).filter(Suscriptor.usuario == usuario).first()

    def cambiar_password_suscriptor(self, usuario, password_actual, nueva_password):
        db = self.SessionFactory()
        try:
            sub = db.query(Suscriptor).filter(Suscriptor.usuario == usuario).first()

            if not sub:
                return False, "Usuario no encontrado en la base de datos."

            # Validar que la contraseña actual ingresada coincida con la de la BD
            if sub.password != password_actual:
                return False, "La contraseña actual es incorrecta."

            # Actualizar a la nueva contraseña
            sub.password = nueva_password
            db.commit()
            return True, "¡Contraseña actualizada exitosamente!"
        except Exception as e:
            db.rollback()
            return False, f"Error en la base de datos: {str(e)}"
        finally:
            db.close()

    def verificar_acceso(self, usuario_ingresado, clave_ingresada):
        """
        Verifica las credenciales del usuario usando SQLAlchemy.
        Retorna (True, datos_del_usuario) si es correcto, o (False, None) si falla.
        """
        db = self.SessionFactory()
        try:
            # Busca en el modelo Suscriptor donde coincidan usuario y password
            usuario_db = (
                db.query(Suscriptor)
                .filter(
                    Suscriptor.usuario == usuario_ingresado,
                    Suscriptor.password == clave_ingresada,
                )
                .first()
            )

            # Si encuentra al usuario, extrae sus datos
            if usuario_db:
                datos_usuario = {
                    "usuario": usuario_db.usuario,
                    "empresa_id": usuario_db.empresa_id,
                    "plan": usuario_db.plan,
                }
                return True, datos_usuario
            else:
                return False, None

        except Exception as e:
            print(f"Error en el login: {e}")
            return False, None
        finally:
            db.close()

    def eliminar_pedido_erroneo(self, numero_orden, empresa_id):
        """
        Elimina por completo una venta y sus detalles de la base de datos.
        """
        db = self.SessionFactory()
        try:
            # 1. Buscar la factura en la base de datos de esa empresa
            venta = (
                db.query(Venta)
                .filter(
                    Venta.numero_orden == numero_orden, Venta.empresa_id == empresa_id
                )
                .first()
            )

            if not venta:
                return False, "❌ El pedido no existe o pertenece a otra empresa."

            # 2. Eliminar primero los detalles (los productos de esa factura)
            db.query(VentaDetalle).filter(VentaDetalle.venta_id == venta.id).delete()

            # 3. Eliminar la factura principal
            db.delete(venta)

            db.commit()
            return True, f"✅ Pedido {numero_orden} eliminado permanentemente."
        except Exception as e:
            db.rollback()
            return False, f"Error al eliminar: {str(e)}"
        finally:
            db.close()

    def obtener_lista_compras(self):
        """Devuelve una lista de todos los motivos de compras registrados en el Kardex."""
        db = self.SessionFactory()
        try:
            # Busca todos los movimientos que empiecen con la palabra "Compra"
            movimientos = (
                db.query(KardexMovimiento.motivo)
                .filter(KardexMovimiento.motivo.like("Compra%"))
                .distinct()
                .all()
            )

            # Devuelve una lista limpia de textos
            return [m[0] for m in movimientos]
        finally:
            db.close()

    def eliminar_pedido_erroneo(self, numero_orden, empresa_id):
        """
        Elimina por completo una venta y sus detalles de la base de datos.
        """
        db = self.SessionFactory()
        try:
            # CORRECCIÓN: Se usa 'factura_nro' que es el nombre real de tu columna
            venta = db.query(Venta).filter(Venta.factura_nro == numero_orden).first()

            if not venta:
                return False, "❌ El pedido no existe o ya fue eliminado."

            # 1. Recuperar el stock de los productos vendidos antes de borrar el detalle
            detalles = (
                db.query(VentaDetalle).filter(VentaDetalle.venta_id == venta.id).all()
            )
            for det in detalles:
                prod = db.query(ProductoTerminado).filter_by(id=det.producto_id).first()
                if prod:
                    prod.stock_actual += (
                        det.cantidad
                    )  # Devolvemos el producto al inventario
                db.delete(det)  # Borramos el detalle

            # 2. Eliminar la factura principal
            db.delete(venta)

            db.commit()
            return (
                True,
                f"✅ Pedido {numero_orden} eliminado permanentemente y stock recuperado.",
            )
        except Exception as e:
            db.rollback()
            return False, f"Error al eliminar: {str(e)}"
        finally:
            db.close()
