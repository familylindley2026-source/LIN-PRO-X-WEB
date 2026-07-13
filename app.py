import streamlit as st
import altair as alt
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
import plotly.express as px
import extra_streamlit_components as stx  # <-- LIBRERÍA DE COOKIES

# 1. CONFIGURACIÓN DE PÁGINA (Debe ir antes de cualquier otro comando de Streamlit)
st.set_page_config(page_title="LIN-PRO X WEB", page_icon="🏭", layout="wide")

# 2. IMPORTACIONES DE TU ARQUITECTURA
from database import SessionLocal
from controllers import SistemaController

# 3. INICIALIZAR EL CONTROLADOR CON LA BASE DE DATOS
if "controller" not in st.session_state:
    st.session_state.controller = SistemaController(SessionLocal)
controller = st.session_state.controller


# ---------------------------------------------------------
# 4. INICIALIZACIÓN DE LA MEMORIA DE SESIÓN
# ---------------------------------------------------------
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# ---------------------------------------------------------
# 5. PANTALLA DE INICIO DE SESIÓN (LOGIN)
# ---------------------------------------------------------
if not st.session_state["autenticado"]:
    st.markdown(
        "<h1 style='text-align: center; color: #00b4d8;'>LIN-PRO X WEB</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h3 style='text-align: center;'>Acceso Empresarial</h3>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("formulario_login"):
            usuario_input = st.text_input(
                "👤 Usuario", placeholder="Ej: IVONNE BERNATE"
            )
            clave_input = st.text_input("🔑 Contraseña", type="password")

            submit_login = st.form_submit_button(
                "Ingresar al Sistema", use_container_width=True, type="primary"
            )

            if submit_login:
                if not usuario_input or not clave_input:
                    st.warning("Por favor, llena ambos campos.")
                else:
                    exito, datos_usuario = controller.verificar_acceso(
                        usuario_input, clave_input
                    )

                    if exito:
                        st.session_state["autenticado"] = True
                        st.session_state["usuario"] = datos_usuario["usuario"]
                        st.session_state["empresa_id"] = datos_usuario["empresa_id"]

                        st.success("¡Acceso exitoso! Cargando panel...")
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos.")

    # 🛑 MURO DE CONTENCIÓN: Si no está autenticado, la lectura muere aquí.
    st.stop()

# =====================================================================
# SISTEMA PRINCIPAL (Solo se ejecuta si pasó el login)
# =====================================================================

# ==========================================
# ⚙️ CONFIGURACIÓN GLOBAL Y ESTILOS
# ==========================================
NOMBRE_NEGOCIO = "IVONNE BERNATE PRODUCTOS CAPILARES"
NUMERO_WHATSAPP = "573016884590"

st.markdown(
    """
    <style>
    .titulo-sidebar { color: #2ecc71; text-align: center; font-size: 2.2em; font-weight: 800; margin-bottom: 5px; }
    .subtitulo-sidebar { text-align: center; color: #ecf0f1; font-size: 0.9em; margin-bottom: 25px; }
    </style>
""",
    unsafe_allow_html=True,
)


# --- FUNCIÓN MAESTRA PARA TABLAS FULL-WIDTH Y ALINEACIÓN PERFECTA ---
def renderizar_tabla_estilizada(datos, col_izquierda):
    if not datos:
        st.info("No hay registros para mostrar en esta sección.")
        return

    df = pd.DataFrame(datos)
    cols_centro = [c for c in df.columns if c != col_izquierda]

    try:
        styler = (
            df.style.set_properties(subset=[col_izquierda], **{"text-align": "left"})
            .set_properties(subset=cols_centro, **{"text-align": "center"})
            .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
        )
        st.dataframe(styler, use_container_width=True, hide_index=True)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True)


# ==========================================
# 🗂️ BARRA DE NAVEGACIÓN LATERAL
# ==========================================
usuario_logeado = st.session_state.get("usuario", "Usuario")
st.sidebar.markdown(f"### 👤 Bienvenido: {usuario_logeado}")
st.sidebar.markdown("⭐ **Plan Activo:** Plan Mensual (Distribuidores)")
st.sidebar.success("⏳ **Tiempo restante: 13 días**")

with st.sidebar.expander("🚀 PLANES DE SUSCRIPCIÓN LIN-PRO X WEB"):
    st.markdown("""
    🥇 **1. Plan Personal** • 25.000 COP / mes
    🥈 **2. Plan Trimestral** • 65.000 COP / trim
    🥉 **3. Plan Semestral** • 120.000 COP / sem
    💎 **4. Plan Anual** • 199.000 COP / año
    """)
    st.markdown(f"[🟢 Renovar vía WhatsApp](https://wa.me/{NUMERO_WHATSAPP})")

st.sidebar.markdown("---")

# CERRAR SESIÓN
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True, type="primary"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")

st.sidebar.markdown(
    "<div class='titulo-sidebar'>LIN - PRO X WEB</div>", unsafe_allow_html=True
)
st.sidebar.markdown(
    f"<div class='subtitulo-sidebar'>{usuario_logeado} | Costos & Planta</div>",
    unsafe_allow_html=True,
)

menu_opciones = [
    "📊 Dashboard",
    "--- DPTO DE COMPRAS Y VENTAS ---",
    "🛒 Punto de Venta",
    "📦 Entradas (Compras)",
    "--- DPTO DE PRODUCCION ---",
    "🧪 Producción y Fórmulas",
    "--- DPTO DE LOGISTICA ---",
    "🏭 Inventario Maestro",
    "🔄 Kardex/Ajustes",
    "🗃️ Auditoría",
    "--- GESTION ADMINISTRATIVA ---",
    "👥 CRM y Clientes",
    "💼 Directorio Asesores",
    "🧴 Catálogo Productos",
    "--- DPTO DE CARTERA ---",
    "💸 Gastos Operativos",
    "💰 Cartera y Abonos",
    "🔒 Seguridad y Cuenta",
]

menu_seleccionado = st.sidebar.radio("Módulos del Sistema:", menu_opciones)

# ==========================================
# 📊 LÓGICA DE PANTALLAS
# ==========================================

# 1. DASHBOARD GRÁFICO (REDISEÑADO)
if menu_seleccionado == "📊 Dashboard":
    st.title("📊 Panel de Control y Analítica Avanzada")

    # ---------------------------------------------------------
    # EXTRACCIÓN DE DATOS Y PREPARACIÓN (ETL)
    # ---------------------------------------------------------
    ventas_crudas = controller.obtener_todas_las_ventas()
    insumos = controller.obtener_insumos()
    productos = controller.obtener_productos_terminados()

    if not ventas_crudas:
        st.info(
            "No hay datos históricos de ventas suficientes para proyectar analíticas."
        )
    else:
        # Convertir ventas a un DataFrame de Pandas (AÑADIMOS EL MEDIO DE PAGO)
        df_ventas = pd.DataFrame(
            [
                {
                    "Fecha": v.fecha,
                    "Año": v.fecha.year,
                    "Mes": v.fecha.month,
                    "Día": v.fecha.date(),
                    "Vendedor": v.vendedor,
                    "Canal": v.tipo_destinatario,
                    "Medio_Pago": v.medio_pago,  # <--- Nuevo campo para el gráfico 5
                    "Total": v.total_neto,
                    "Factura": v.factura_nro,
                }
                for v in ventas_crudas
            ]
        )

        # ---------------------------------------------------------
        # ZONA DE FILTROS ADAPTATIVOS
        # ---------------------------------------------------------
        st.markdown("### 🎛️ Filtros de Análisis")
        f_col1, f_col2, f_col3 = st.columns(3)

        # Diccionario para mapear números a nombres legibles de meses
        MESES_TRADUCCION = {
            1: "Enero",
            2: "Febrero",
            3: "Marzo",
            4: "Abril",
            5: "Mayo",
            6: "Junio",
            7: "Julio",
            8: "Agosto",
            9: "Septiembre",
            10: "Octubre",
            11: "Noviembre",
            12: "Diciembre",
        }

        df_ventas["Nombre_Mes"] = df_ventas["Mes"].map(MESES_TRADUCCION)

        lista_anios = ["Todos"] + sorted(list(df_ventas["Año"].unique()), reverse=True)
        meses_existentes_num = sorted(list(df_ventas["Mes"].unique()))
        lista_meses = ["Todos"] + [MESES_TRADUCCION[m] for m in meses_existentes_num]
        lista_vendedores = ["Todos"] + sorted(list(df_ventas["Vendedor"].unique()))

        with f_col1:
            anio_sel = st.selectbox("📅 Año", lista_anios)
        with f_col2:
            mes_sel = st.selectbox("📆 Mes", lista_meses)
        with f_col3:
            vend_sel = st.selectbox("💼 Vendedor", lista_vendedores)

        # Aplicar filtros lógicos
        df_filtrado = df_ventas.copy()
        if anio_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Año"] == anio_sel]
        if mes_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Nombre_Mes"] == mes_sel]
        if vend_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Vendedor"] == vend_sel]

        # ---------------------------------------------------------
        # CÁLCULO DE KPIs ESTRATÉGICOS
        # ---------------------------------------------------------
        ventas_totales = df_filtrado["Total"].sum()
        num_operaciones = df_filtrado["Factura"].nunique()
        ticket_promedio = ventas_totales / num_operaciones if num_operaciones > 0 else 0

        capital_insumos = sum(
            i.stock_actual * i.costo_promedio for i in insumos if i.stock_actual > 0
        )
        capital_pt = sum(
            p.stock_actual * p.precio_venta for p in productos if p.stock_actual > 0
        )
        capital_total_bodega = capital_insumos + capital_pt

        st.markdown("---")

        # 🎨 INYECCIÓN CSS: Forzar letras y flechas blancas en los KPIs nativos
        st.markdown(
            """
        <style>
        [data-testid="stMetricDelta"] {
            color: #ffffff !important;
        }
        [data-testid="stMetricDelta"] > div {
            color: #ffffff !important;
            font-weight: 600 !important;
        }
        [data-testid="stMetricDelta"] svg {
            fill: #ffffff !important; /* Flecha blanca */
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "💰 Ventas (Periodo)",
            f"$ {int(ventas_totales):,.0f}",
            f"{num_operaciones} Cierres",
        )
        m2.metric(
            "🎯 Ticket Promedio",
            f"$ {int(ticket_promedio):,.0f}",
            "Eficiencia de venta",
        )

        # Formateamos los números con puntos (formato latino)
        str_bodega = f"$ {int(capital_total_bodega):,.0f}".replace(",", ".")
        str_insumos = f"$ {int(capital_insumos):,.0f}".replace(",", ".")
        str_pt = f"$ {int(capital_pt):,.0f}".replace(",", ".")

        # Métrica principal sin el delta por defecto
        m3.metric("📦 Valor en Bodega", str_bodega)

        # Etiqueta HTML con texto blanco y fondo verde resaltado
        m3.markdown(
            f"""
        <div style="
            color: #ffffff; 
            background-color: rgba(9, 171, 59, 0.35); 
            padding: 4px 10px; 
            border-radius: 6px; 
            font-size: 0.85rem; 
            margin-top: -15px; 
            display: inline-block; 
            font-weight: 600;
            line-height: 1.4;
        ">
            ↑ Insumo = {str_insumos} <br>
            ↑ Producto Terminado = {str_pt}
        </div>
        """,
            unsafe_allow_html=True,
        )

        m4.metric(
            "🚨 Alertas de Stock",
            f"{len([p for p in insumos if p.stock_actual <= 10])}",
            "Insumos Críticos",
        )
        st.markdown("---")

        # =========================================================
        # 1. GRÁFICO SUPERIOR: FULL-WIDTH (Comportamiento de Ventas)
        # =========================================================
        st.markdown("#### 📈 Comportamiento de Ventas en el Tiempo")
        if not df_filtrado.empty:
            df_tiempo = df_filtrado.groupby("Día")["Total"].sum().reset_index()
            # Convertimos a texto
            df_tiempo["Día"] = df_tiempo["Día"].astype(str)

            # Usamos px.area para que se vea lleno por debajo como tu referencia
            fig_line = px.area(
                df_tiempo,
                x="Día",
                y="Total",
                template="plotly_dark",
                markers=True,
                color_discrete_sequence=["#00b4d8"],
            )

            # 🛑 LA MAGIA ESTÁ AQUÍ: Obligamos a Plotly a tratar el eje X como texto puro (categoría)
            fig_line.update_xaxes(type="category")

            # Agregamos las etiquetas de precio a cada punto
            fig_line.update_traces(
                mode="lines+markers+text",
                texttemplate="$ %{y:,.0f}",
                textposition="top center",
            )
            fig_line.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                height=350,
                yaxis_title="Ingresos ($)",
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("No hay ventas en los filtros seleccionados.")

        st.markdown("---")

        # =========================================================
        # GRÁFICOS INFERIORES: CUADRÍCULA 2x2 (4 Gráficos)
        # =========================================================
        graf_col1, graf_col2 = st.columns(2)

        with graf_col1:
            # GRÁFICO 2: RENDIMIENTO POR VENDEDOR
            st.markdown("#### 🏆 Desempeño Comercial por Vendedor")
            if not df_filtrado.empty:
                df_vend = (
                    df_filtrado.groupby("Vendedor")["Total"]
                    .sum()
                    .reset_index()
                    .sort_values(by="Total", ascending=True)
                )
                fig_bar_v = px.bar(
                    df_vend,
                    x="Total",
                    y="Vendedor",
                    orientation="h",
                    text="Total",
                    template="plotly_dark",
                    color_discrete_sequence=["#2FA572"],
                )
                fig_bar_v.update_traces(
                    texttemplate="$ %{text:,.0f}", textposition="outside"
                )
                fig_bar_v.update_layout(
                    margin=dict(l=20, r=20, t=30, b=20),
                    height=350,
                    xaxis_title="Ingresos Generados",
                )
                st.plotly_chart(fig_bar_v, use_container_width=True)

            # GRÁFICO 3: NUEVO GRÁFICO TIPO DE PAGO (Dona + Tabla)
            st.markdown("#### 💳 Ingresos por Medio de Pago")
            if not df_filtrado.empty:
                # Agrupar y ordenar datos de mayor a menor
                df_pago = (
                    df_filtrado.groupby("Medio_Pago")["Total"]
                    .sum()
                    .reset_index()
                    .sort_values(by="Total", ascending=False)
                )

                # Calcular el porcentaje que representa cada medio de pago
                total_ingresos = df_pago["Total"].sum()
                df_pago["%"] = (df_pago["Total"] / total_ingresos) * 100

                # 1. Crear el Gráfico de Dona
                fig_pago = px.pie(
                    df_pago,
                    values="Total",
                    names="Medio_Pago",
                    hole=0.45,  # Esto crea el "hueco" en el centro para que sea dona
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                # Mostrar solo el porcentaje por fuera de la dona, sin leyenda lateral (como en tu imagen)
                fig_pago.update_traces(textposition="outside", textinfo="percent")
                fig_pago.update_layout(
                    margin=dict(l=20, r=20, t=10, b=10), height=280, showlegend=False
                )

                # Renderizar Gráfico
                st.plotly_chart(fig_pago, use_container_width=True)

                # 2. Preparar y Mostrar la Tabla de Resumen
                df_tabla = df_pago.copy()
                df_tabla = df_tabla.rename(
                    columns={"Medio_Pago": "Medio", "Total": "Monto"}
                )

                # Formatear el dinero y el porcentaje para que se vean elegantes
                df_tabla["Monto"] = df_tabla["Monto"].apply(
                    lambda x: f"$ {int(x):,.0f}"
                )
                df_tabla["%"] = df_tabla["%"].apply(lambda x: f"{x:.1f} %")

                # Mostrar la tabla ajustada al ancho de la columna sin el índice numérico
                st.dataframe(df_tabla, use_container_width=True, hide_index=True)
            else:
                st.info("No hay ingresos registrados para mostrar.")

        with graf_col2:
            # GRÁFICO 4: VENTAS POR CANAL/DESTINATARIO
            st.markdown("#### 🎯 Ingresos por Canal Comercial")
            if not df_filtrado.empty:
                df_canal = df_filtrado.groupby("Canal")["Total"].sum().reset_index()
                fig_pie = px.pie(
                    df_canal,
                    values="Total",
                    names="Canal",
                    hole=0.4,
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig_pie.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=350)
                st.plotly_chart(fig_pie, use_container_width=True)

            # GRÁFICO 5: RENDIMIENTO DEUDA VS ABONOS
            st.markdown("#### ⚖️ Rendimiento: Deuda vs Abonos")

            # Consultamos la cartera real en la base de datos
            deudas = controller.obtener_cartera()
            datos_cartera = []

            if deudas:
                for d in deudas:
                    datos_cartera.append(
                        {
                            "Cliente": d.cliente.nombre,
                            "Factura": d.factura_nro,
                            "Deuda Original": float(d.total_neto),
                            "Abono Aplicado": float(d.total_neto - d.saldo_pendiente),
                            "Saldo Pendiente": float(d.saldo_pendiente),
                            "Etiqueta": f"{d.cliente.nombre[:15]}... ({d.factura_nro})",
                        }
                    )

            df_cartera_facturas = pd.DataFrame(datos_cartera)

            if not df_cartera_facturas.empty:
                data_plot = df_cartera_facturas.melt(
                    id_vars=["Etiqueta", "Saldo Pendiente", "Cliente", "Factura"],
                    value_vars=["Deuda Original", "Abono Aplicado"],
                    var_name="Tipo",
                    value_name="Monto",
                )
                chart = (
                    alt.Chart(data_plot)
                    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                    .encode(
                        x=alt.X(
                            "Etiqueta:N",
                            title="Facturas Activas por Cliente",
                            axis=alt.Axis(labelAngle=-45),
                        ),
                        y=alt.Y("Monto:Q", stack=None, title="Monto ($)"),
                        color=alt.Color(
                            "Tipo:N",
                            scale=alt.Scale(
                                domain=["Deuda Original", "Abono Aplicado"],
                                range=["#ff4d4d", "#00ADEF"],
                            ),
                        ),
                        order=alt.Order("Tipo:N", sort="descending"),
                        tooltip=[
                            "Cliente",
                            "Factura",
                            "Tipo",
                            alt.Tooltip("Monto:Q", format="$,.0f"),
                            alt.Tooltip("Saldo Pendiente:Q", format="$,.0f"),
                        ],
                    )
                )
                st.altair_chart(chart, use_container_width=True)

                # Tabla de resumen debajo del gráfico
                st.dataframe(
                    df_cartera_facturas[
                        [
                            "Cliente",
                            "Factura",
                            "Deuda Original",
                            "Abono Aplicado",
                            "Saldo Pendiente",
                        ]
                    ].style.format(
                        {
                            "Deuda Original": "${:,.0f}",
                            "Abono Aplicado": "${:,.0f}",
                            "Saldo Pendiente": "${:,.0f}",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                # Gráfico vacío decorativo si no hay deudas
                data_vacia = pd.DataFrame(
                    [{"Etiqueta": "-", "Monto": 0.0, "Tipo": "Deuda Original"}]
                )
                chart_vacio = (
                    alt.Chart(data_vacia)
                    .mark_bar()
                    .encode(
                        x=alt.X(
                            "Etiqueta:N",
                            title="Facturas Pendientes",
                            axis=alt.Axis(labelAngle=0),
                        ),
                        y=alt.Y(
                            "Monto:Q",
                            title="Monto ($)",
                            scale=alt.Scale(domain=[0, 100000]),
                        ),
                        color=alt.Color(
                            "Tipo:N",
                            title="Tipo",
                            scale=alt.Scale(
                                domain=["Deuda Original", "Abono Aplicado"],
                                range=["#ff4d4d", "#00ADEF"],
                            ),
                        ),
                    )
                )
                st.altair_chart(chart_vacio, use_container_width=True)
                st.success(
                    "🎉 ¡Excelente! Todas las facturas a crédito están pagadas. Cartera en cero."
                )


# 2. PUNTO DE VENTA
elif menu_seleccionado == "🛒 Punto de Venta":
    st.title("🛒 Terminal de Ventas POS")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        vendedor = st.selectbox(
            "Vendedor / Asesor",
            [a.nombre for a in controller.obtener_asesores()] + ["ADMIN"],
        )
    with col2:
        cliente = st.selectbox(
            "Cliente Final",
            [c.nombre for c in controller.obtener_clientes()] + ["Consumidor Final"],
        )
    with col3:
        tipo_dest = st.selectbox(
            "Tipo Destinatario", ["Cliente Real", "Vendedora", "Página Web"]
        )
    with col4:
        medio_pago = st.selectbox(
            "Medio de Pago",
            ["Efectivo", "Crédito", "Sistecrédito", "Addi", "Llave", "Bolt", "Otros"],
        )

    st.markdown("---")
    productos_con_stock = [
        p for p in controller.obtener_productos_terminados() if p.stock_actual > 0
    ]

    if not productos_con_stock:
        st.warning("⚠️ No hay productos con stock disponible.")
    else:
        col_sel, col_cant, col_precio, col_desc_p, col_desc_f, col_btn = st.columns(
            [4, 1, 1.5, 1, 1, 1.5]
        )
        with col_sel:
            prod_options = [
                f"{p.nombre} ({p.presentacion}) - Stock: {p.stock_actual}"
                for p in productos_con_stock
            ]
            producto_seleccionado = st.selectbox("Seleccionar Producto", prod_options)
            prod_obj = next(
                p
                for p in productos_con_stock
                if f"{p.nombre} ({p.presentacion}) - Stock: {p.stock_actual}"
                == producto_seleccionado
            )
        with col_cant:
            cantidad = st.number_input(
                "Cant", min_value=1, max_value=int(prod_obj.stock_actual), value=1
            )
        with col_precio:
            precio_unit = st.number_input(
                "Precio U. ($)", value=float(prod_obj.precio_venta), step=1000.0
            )
        with col_desc_p:
            desc_porcentaje = st.number_input(
                "Dcto (%)", min_value=0.0, max_value=100.0, value=0.0
            )
        with col_desc_f:
            desc_fijo = st.number_input("Dcto Extra ($)", min_value=0.0, value=0.0)

        with col_btn:
            st.write("##")
            if st.button("➕ Añadir", use_container_width=True):
                precio_bruto = cantidad * precio_unit
                val_dcto_pct = precio_bruto * (desc_porcentaje / 100)
                subtotal_final = max(0, precio_bruto - val_dcto_pct - desc_fijo)

                if "carrito" not in st.session_state:
                    st.session_state.carrito = []
                st.session_state.carrito.append(
                    {
                        "producto_id": prod_obj.id,
                        "nombre": f"{prod_obj.nombre} ({prod_obj.presentacion})",
                        "cant": cantidad,
                        "precio": precio_unit,
                        "descuentos": val_dcto_pct + desc_fijo,
                        "subtotal": subtotal_final,
                    }
                )
                st.rerun()

    if "carrito" in st.session_state and st.session_state.carrito:
        st.markdown("### 🛒 Detalle de Facturación")
        total_neto = sum(i["subtotal"] for i in st.session_state.carrito)

        for idx, item in enumerate(st.session_state.carrito):
            c1, c2, c3, c4, c5 = st.columns([4, 1, 1.5, 1.5, 0.5])
            c1.write(item["nombre"])
            c2.write(f"{item['cant']} und")
            c3.write(f"$ {int(item['precio']):,.0f}")
            c4.write(f"$ {int(item['subtotal']):,.0f}")
            with c5:
                if st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()

        st.markdown("---")
        col_tot, col_proc = st.columns([3, 1])
        col_tot.markdown(f"### 💰 Total Neto: $ {int(total_neto):,.0f}")

        if col_proc.button("Procesar Pago", type="primary", use_container_width=True):
            cliente_obj = next(
                (c for c in controller.obtener_clientes() if c.nombre == cliente), None
            )
            c_id = cliente_obj.id if cliente_obj else 1
            exito, msg, ticket = controller.procesar_venta(
                c_id, vendedor, tipo_dest, medio_pago, st.session_state.carrito
            )
            if exito:
                st.success(msg)
                st.session_state.carrito = []
                url_wa = (
                    f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(ticket)}"
                )
                st.link_button("📲 Compartir por WhatsApp", url_wa)
            else:
                st.error(msg)

    # ==========================================
    # 🗑️ ZONA DE ELIMINACIÓN DE VENTAS
    # ==========================================
    st.write("---")
    st.markdown("### 🗑️ Zona de Seguridad: Eliminar Pedido")
    st.info(
        "Si registraste una venta por error, selecciona la factura de la lista. "
        "Se borrará del sistema y los productos regresarán automáticamente a tu stock."
    )

    lista_ventas = controller.obtener_todas_las_ventas()

    with st.form("form_eliminar_pedido"):
        if lista_ventas:
            # Formateamos la lista para mostrar la factura, cliente y total
            opciones_ventas = [
                f"{v.factura_nro} - {v.cliente.nombre if v.cliente else 'Consumidor'} ($ {v.total_neto:,.0f})"
                for v in reversed(lista_ventas)
            ]
            pedido_a_eliminar = st.selectbox(
                "Selecciona la Factura / Orden de Venta",
                options=["Seleccione un pedido..."] + opciones_ventas,
            )
        else:
            pedido_a_eliminar = "Seleccione un pedido..."
            st.warning("No hay ventas registradas en el sistema.")

        # Botón rojo para acciones destructivas
        submit_eliminar = st.form_submit_button(
            "Eliminar Pedido Permanentemente", type="primary"
        )

        if submit_eliminar:
            if pedido_a_eliminar != "Seleccione un pedido...":
                # Extraemos solo el "FACT-XXX" que está antes del primer guion
                nro_factura = pedido_a_eliminar.split(" - ")[0]
                exito, msg = controller.eliminar_pedido_erroneo(nro_factura)
                if exito:
                    st.success(msg)
                    st.rerun()  # Recarga para actualizar la lista y el inventario visualmente
                else:
                    st.error(msg)
            else:
                st.warning("Por favor, selecciona un pedido válido de la lista.")

# 3. ENTRADAS COMPRAS
elif menu_seleccionado == "📦 Entradas (Compras)":
    st.title("📦 Registro de Pedidos y Entradas")

    # --- AUTO-NUMERACIÓN ---
    # Llamamos a tu función original para obtener el próximo número IB-XXX
    try:
        nro_sugerido = controller.generar_nro_orden_compra()
    except:
        nro_sugerido = "IB-001"
    # -----------------------

    col_prov, col_doc, col_comp = st.columns(3)
    proveedores = controller.obtener_proveedores()

    with col_prov:
        proveedor_sel = st.selectbox(
            "Proveedor", [p.nombre for p in proveedores] if proveedores else ["S/N"]
        )
    with col_doc:
        # Aquí inyectamos el número sugerido por defecto
        nro_factura = st.text_input("N° Factura / Orden", value=nro_sugerido)
    with col_comp:
        comprador_sel = st.selectbox("Comprador", ["Ivonne Bernate", "Admin", "Otro"])

    tipo_compra = st.radio(
        "Tipo de Catálogo:", ["Insumos", "Productos Terminados"], horizontal=True
    )

    col_ins, col_c, col_p, col_btn = st.columns([4, 1.5, 1.5, 1.5])
    with col_ins:
        if tipo_compra == "Insumos":
            opc = [
                f"{i.id} - {i.nombre} ({i.unidad_medida})"
                for i in controller.obtener_insumos()
            ]
        else:
            opc = [
                f"{p.id} - {p.nombre} ({p.presentacion})"
                for p in controller.obtener_productos_terminados()
            ]
        item_sel = st.selectbox("Buscar Item", opc if opc else ["Sin registros"])

    with col_c:
        cant_compra = st.number_input("Cantidad", min_value=0.1, value=1.0)
    with col_p:
        costo_total = st.number_input("Total Factura ($)", min_value=0.0, step=1000.0)
    with col_btn:
        st.write("##")
        if st.button("➕ Añadir"):
            if "Sin registros" not in item_sel and costo_total > 0:
                id_item = int(item_sel.split(" - ")[0])
                nombre_item = item_sel.split(" - ")[1]
                if "carrito_compras" not in st.session_state:
                    st.session_state.carrito_compras = []
                st.session_state.carrito_compras.append(
                    {
                        "id": id_item,
                        "tipo": tipo_compra,
                        "nombre": nombre_item,
                        "cant": cant_compra,
                        "precio": costo_total,
                    }
                )
                st.rerun()

    if "carrito_compras" in st.session_state and st.session_state.carrito_compras:
        st.markdown("---")
        tot = sum(i["precio"] for i in st.session_state.carrito_compras)
        for idx, i in enumerate(st.session_state.carrito_compras):
            c1, c2, c3, c4 = st.columns([4, 1.5, 1.5, 0.5])
            c1.write(f"[{i['tipo'][:3]}] {i['nombre']}")
            c2.write(f"{i['cant']}")
            c3.write(f"$ {int(i['precio']):,.0f}")
            if c4.button("🗑️", key=f"del_c_{idx}"):
                st.session_state.carrito_compras.pop(idx)
                st.rerun()

        st.markdown(f"### 💰 Total: $ {int(tot):,.0f}")
        if st.button("💾 Registrar Entrada", type="primary"):
            if not nro_factura:
                st.error("Falta N° Factura")
            else:
                exito, msg, ticket = controller.procesar_compra_mixta(
                    proveedor_sel,
                    nro_factura,
                    st.session_state.carrito_compras,
                    comprador_sel,
                )
                if exito:
                    st.success(msg)
                    st.session_state.carrito_compras = []
                else:
                    st.error(msg)

    # ==========================================
    # 🗑️ ZONA DE ELIMINACIÓN DE COMPRAS (Desplegable)
    # ==========================================
    st.write("---")
    st.markdown("### 🗑️ Zona de Seguridad: Eliminar Compra")
    st.info(
        "Si registraste una compra por error, selecciónala de la lista. Se descontará el stock y se borrará del sistema."
    )

    # Obtenemos la lista de compras registradas
    lista_compras_db = controller.obtener_lista_compras()

    with st.form("form_eliminar_compra"):
        if lista_compras_db:
            compra_a_eliminar = st.selectbox(
                "Selecciona la Orden / Factura de Compra",
                options=["Seleccione una compra..."] + lista_compras_db,
            )
        else:
            compra_a_eliminar = "Seleccione una compra..."
            st.warning("No hay compras registradas en el sistema todavía.")

        submit_eliminar = st.form_submit_button(
            "Eliminar Compra Permanentemente", type="primary"
        )
        # Zona de Seguridad: Eliminar Compra
        if submit_eliminar:
            if compra_a_eliminar != "Seleccione una compra...":
                exito, msg = controller.eliminar_compra_erronea(compra_a_eliminar)
                if exito:
                    st.success(msg)
                    st.rerun()  # Refresca para limpiar la lista
                else:
                    st.error(msg)
            else:
                st.warning("Por favor, selecciona una compra válida de la lista.")

    
# 4. PRODUCCIÓN
elif menu_seleccionado == "🧪 Producción y Fórmulas":
    st.title("🧪 Planta y Laboratorio")
    tab1, tab2 = st.tabs(["⚙️ Fraccionar Lote", "🔬 Diseñador de Fórmulas"])

    with tab1:
        recetas = controller.obtener_recetas_disponibles()
        receta_sel = st.selectbox(
            "Fórmula a Preparar",
            [r.nombre for r in recetas] if recetas else ["No hay fórmulas"],
        )
        volumen_total = st.number_input(
            "Volumen Preparado (ml/gr)", min_value=100, value=4000
        )

        st.markdown("### Asignación a Envases")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            c1000 = st.number_input("1000ml", min_value=0, value=0)
        with col2:
            c500 = st.number_input("500ml", min_value=0, value=0)
        with col3:
            c250 = st.number_input("250ml", min_value=0, value=0)
        with col4:
            c120 = st.number_input("120ml", min_value=0, value=0)
        with col5:
            c60 = st.number_input("60ml", min_value=0, value=0)

        volumen_usado = (
            (c1000 * 1000) + (c500 * 500) + (c250 * 250) + (c120 * 120) + (c60 * 60)
        )
        if volumen_usado > volumen_total:
            st.error(
                f"¡Exceso! Has asignado {volumen_usado} ml pero el lote es de {volumen_total} ml."
            )
        else:
            st.success(f"Asignado: {volumen_usado} ml / {volumen_total} ml")
            if st.button("🚀 Procesar Producción Real", type="primary"):
                envases = {
                    "1000ml": c1000,
                    "500ml": c500,
                    "250ml": c250,
                    "120ml": c120,
                    "60ml": c60,
                }
                exito, msg = controller.procesar_fraccionamiento_lote(
                    receta_sel, volumen_total, envases
                )
                if exito:
                    st.success(msg)
                else:
                    st.error(msg)

    with tab2:
        st.markdown("### Crear Nueva Fórmula Base")
        c1, c2 = st.columns(2)
        nom_receta = c1.text_input("Nombre del Producto / Receta")
        vol_base = c2.number_input(
            "Volumen Lote Base (ml/gr)", min_value=10.0, value=1000.0
        )

        st.markdown("#### Ingredientes")
        c3, c4, c5 = st.columns([3, 1, 1])
        insumos_db = controller.obtener_insumos()
        with c3:
            ing_sel = st.selectbox(
                "Seleccionar Insumo",
                [f"{i.id} - {i.nombre} ({i.unidad_medida})" for i in insumos_db],
            )
        with c4:
            ing_cant = st.number_input("Cant Requerida", min_value=0.1, step=1.0)
        with c5:
            st.write("##")
            if st.button("➕ Añadir Ingrediente"):
                if "receta_temp" not in st.session_state:
                    st.session_state.receta_temp = []
                ins_id = int(ing_sel.split(" - ")[0])
                st.session_state.receta_temp.append(
                    {"id": ins_id, "nombre": ing_sel, "cant": ing_cant}
                )
                st.rerun()

        if "receta_temp" in st.session_state and st.session_state.receta_temp:
            for idx, item in enumerate(st.session_state.receta_temp):
                st.write(f"- {item['nombre']} | Cantidad: {item['cant']}")

            if st.button("💾 Guardar Fórmula en BD", type="primary"):
                if not nom_receta:
                    st.error("Falta nombre de la receta.")
                else:
                    exito, msg = controller.guardar_nueva_formula(
                        nom_receta, vol_base, st.session_state.receta_temp
                    )
                    if exito:
                        st.success(msg)
                        st.session_state.receta_temp = []
                    else:
                        st.error(msg)

# 5. INVENTARIO MAESTRO
elif menu_seleccionado == "🏭 Inventario Maestro":
    st.title("🏭 Gestión de Insumos y Proveedores")
    tab1, tab2 = st.tabs(["📊 Ver Inventario", "➕ Crear / Editar Insumo"])

    insumos = controller.obtener_insumos()
    with tab1:
        data_inv = [
            {
                "ID": i.id,
                "Código": i.codigo,
                "Nombre": i.nombre,
                "Categoría": i.categoria,
                "Und": i.unidad_medida,
                "Stock": i.stock_actual,
                "Costo": f"$ {int(i.costo_promedio):,.0f}",
                "Proveedor": i.proveedor.nombre if i.proveedor else "S/N",
            }
            for i in insumos
        ]
        renderizar_tabla_estilizada(data_inv, "Nombre")

    with tab2:
        with st.form("form_insumo"):
            st.markdown(
                "Deja el campo **ID** vacío para crear uno nuevo, o ingresa el ID de la tabla para editar."
            )
            c1, c2, c3 = st.columns(3)
            id_insumo = c1.text_input("ID Insumo (Opcional)")
            nombre_ins = c2.text_input("Nombre *")
            cat_ins = c3.selectbox(
                "Categoría", ["Materia Prima", "Base Intermedia", "Envases y Empaques"]
            )
            c4, c5, c6, c7 = st.columns(4)
            prov_ins = c4.text_input("Nombre Proveedor (O 'S/N')")
            und_ins = c5.text_input("Unidad (Ej: ml, gr, UND) *")
            stock_ins = c6.number_input("Stock Inicial", value=0.0)
            costo_ins = c7.number_input("Costo Promedio ($)", value=0.0)

            if st.form_submit_button("💾 Guardar Insumo", type="primary"):
                if not nombre_ins or not und_ins:
                    st.error("Nombre y Unidad son obligatorios.")
                else:
                    id_val = int(id_insumo) if id_insumo.isdigit() else None
                    exito = controller.guardar_o_actualizar_insumo(
                        id_val,
                        nombre_ins,
                        cat_ins,
                        und_ins,
                        costo_ins,
                        stock_ins,
                        prov_ins,
                    )
                    if exito:
                        st.success("Insumo guardado correctamente.")
                    else:
                        st.error("Error al guardar en base de datos.")

# 6. KARDEX Y AJUSTES
elif menu_seleccionado == "🔄 Kardex/Ajustes":
    st.title("🔄 Kardex Matemático en Tiempo Real")

    opciones_kardex = [
        "Ajuste (+) Entrada",
        "Préstamo: Me devuelven (+) Suma",
        "Consumo Personal (-) Resta",
        "Préstamo: Yo presto (-) Resta",
        "Obsequio para cliente (-) Resta",
        "Merma/Pérdida (-) Resta",
        "Cambio de producto con compañero",
    ]
    motivo = st.selectbox("Tipo de Operación:", opciones_kardex)

    if motivo == "Cambio de producto con compañero":
        st.markdown("#### Detalle del Cambio")
        c1, c2, c3, c4, c5 = st.columns([3, 1, 3, 1, 2])
        prods = [
            f"{p.id} - {p.nombre} ({p.presentacion})"
            for p in controller.obtener_productos_terminados()
        ]

        with c1:
            p_entra = st.selectbox("Entra (Recibo)", prods if prods else ["Vacio"])
        with c2:
            c_entra = st.number_input("Cant. Entra", min_value=1)
        with c3:
            p_sale = st.selectbox("Sale (Entrego)", prods if prods else ["Vacio"])
        with c4:
            c_sale = st.number_input("Cant. Sale", min_value=1)
        with c5:
            st.write("##")
            if st.button(
                "💾 Procesar Cambio", type="primary", use_container_width=True
            ):
                involucrado = "N/A"
                id_ent = int(p_entra.split(" - ")[0])
                id_sal = int(p_sale.split(" - ")[0])
                exito, msg, tck = controller.procesar_cambio_kardex(
                    involucrado, id_ent, c_entra, id_sal, c_sale
                )
                if exito:
                    st.success(msg)
                else:
                    st.error(msg)
    else:
        c_inv, c_prod, c_cant, c_btn = st.columns([2, 3, 1, 1.5])
        with c_inv:
            involucrado = st.text_input("Involucrado:", "N/A")
        prods = [
            f"{p.id} - {p.nombre} ({p.presentacion})"
            for p in controller.obtener_productos_terminados()
        ]
        with c_prod:
            p_ajuste = st.selectbox("Producto:", prods if prods else ["Vacio"])
        with c_cant:
            c_ajuste = st.number_input("Cant:", min_value=1)
        with c_btn:
            st.write("##")
            if st.button("💾 Registrar", type="primary", use_container_width=True):
                if "Vacio" not in p_ajuste:
                    id_aj = int(p_ajuste.split(" - ")[0])
                    exito, msg, tck = controller.registrar_movimiento_kardex(
                        id_aj, motivo, c_ajuste, involucrado
                    )
                    if exito:
                        st.success(msg)
                    else:
                        st.error(msg)

    st.markdown("---")

    km = controller.obtener_kardex_matematico()
    if km:
        data_km = [
            {
                "Producto Terminado": r["nombre"],
                "Total Entradas (+)": r["sumas"],
                "Total Salidas (-)": r["restas"],
                "Stock Real": r["stock_real"],
            }
            for r in km
        ]
        renderizar_tabla_estilizada(data_km, "Producto Terminado")
    else:
        st.info("No hay registros matemáticos en el Kardex.")

# 7. AUDITORÍA
elif menu_seleccionado == "🗃️ Auditoría":
    st.title("🗃️ Auditoría y Logs del Sistema")
    insumos, productos = (
        controller.obtener_insumos(),
        controller.obtener_productos_terminados(),
    )
    v_insumos = sum(i.stock_actual * i.costo_promedio for i in insumos)
    v_productos = sum(p.stock_actual * p.precio_venta for p in productos)

    c1, c2 = st.columns(2)
    c1.metric("Capital en Materia Prima", f"$ {int(v_insumos):,.0f}")
    c2.metric("Proyección Ventas (PT)", f"$ {int(v_productos):,.0f}")

    st.markdown("### Registro Detallado (Últimos 100 movimientos)")
    logs = controller.obtener_auditoria_kardex()
    if logs:
        data_logs = [
            {
                "Fecha": l.fecha.strftime("%Y-%m-%d %H:%M"),
                "Producto / Insumo": (
                    l.producto.nombre + " (" + l.producto.presentacion + ")"
                )
                if l.producto
                else (l.insumo.nombre if getattr(l, "insumo", None) else "Desconocido"),
                "Operación": l.operacion,
                "Cant": l.cantidad,
                "Motivo": l.motivo,
            }
            for l in logs
        ]
        renderizar_tabla_estilizada(data_logs, "Producto / Insumo")

# 8. CRM Y CLIENTES
elif menu_seleccionado == "👥 CRM y Clientes":
    st.title("🤝 Gestión de Clientes")
    tab1, tab2 = st.tabs(["📋 Lista de Clientes", "➕ / ✏️ Gestionar Cliente"])

    with tab1:
        data_cli = [
            {
                "ID": c.id,
                "Nombre": c.nombre,
                "Teléfono": c.telefono,
                "Email": c.email,
                "Ciudad": c.ciudad,
            }
            for c in controller.obtener_clientes()
        ]
        renderizar_tabla_estilizada(data_cli, "Nombre")

    with tab2:
        with st.form("f_cliente"):
            st.write("Para editar, ingresa el ID. Para crear nuevo, déjalo vacío.")
            c1, c2 = st.columns(2)
            c_id = c1.text_input("ID Cliente")
            c_nom = c2.text_input("Nombre *")
            c_tel = c1.text_input("Teléfono *")
            c_ciu = c2.text_input("Ciudad")
            c_email = c1.text_input("Correo Electrónico")
            if st.form_submit_button("Guardar", type="primary"):
                id_val = int(c_id) if c_id.isdigit() else None
                if controller.guardar_cliente(id_val, c_nom, c_tel, c_ciu, c_email)[0]:
                    st.success("Guardado.")

# 9. DIRECTORIO ASESORES
elif menu_seleccionado == "💼 Directorio Asesores":
    st.title("💼 Equipo Comercial")
    tab1, tab2 = st.tabs(["📋 Asesores", "➕ / ✏️ Gestionar Asesor"])
    with tab1:
        data_ase = [
            {"ID": a.id, "Nombre": a.nombre, "Teléfono": a.telefono}
            for a in controller.obtener_asesores()
        ]
        renderizar_tabla_estilizada(data_ase, "Nombre")

    with tab2:
        with st.form("f_asesor"):
            c_id = st.text_input("ID Asesor (Vacío para nuevo)")
            c_nom = st.text_input("Nombre *")
            c_tel = st.text_input("Teléfono")
            if st.form_submit_button("Guardar"):
                id_val = int(c_id) if c_id.isdigit() else None
                if controller.guardar_asesor(id_val, c_nom, c_tel)[0]:
                    st.success("Guardado.")

# 10. CATÁLOGO PRODUCTOS
elif menu_seleccionado == "🧴 Catálogo Productos":
    st.title("🧴 Catálogo General (SaaS)")
    tab1, tab2 = st.tabs(["📚 Ver Catálogo", "➕ Crear/Editar Producto"])

    with tab1:
        data_cat = [
            {
                "ID": p.id,
                "Nombre": p.nombre,
                "Presentación": p.presentacion,
                "Precio": f"$ {int(p.precio_venta):,.0f}",
                "Días Cobertura": p.dias_consumo,
                "PV": getattr(p, "puntos_pv", 0),
            }
            for p in controller.obtener_productos_terminados()
        ]
        renderizar_tabla_estilizada(data_cat, "Nombre")

    with tab2:
        with st.form("f_cat"):
            st.info(
                "La creación de producto aquí lo registra automáticamente como Producto Terminado para inventario."
            )
            c1, c2 = st.columns(2)
            c_nom = c1.text_input("Nombre Producto")
            c_pres = c2.text_input("Presentación (Ej: 250ml)")
            c_prec = c1.number_input("Precio Venta ($)", min_value=0.0)
            c_dias = c2.number_input("Días Cobertura", value=30)
            c_puntos = c1.number_input("Puntos PV", value=0)
            if st.form_submit_button("Guardar en Catálogo", type="primary"):
                if controller.guardar_producto_catalogo(
                    c_nom, c_pres, c_prec, c_dias, c_puntos
                )[0]:
                    st.success("Creado.")

# 11. GASTOS OPERATIVOS
elif menu_seleccionado == "💸 Gastos Operativos":
    st.title("📉 Registro de Gastos")
    tab1, tab2 = st.tabs(["📋 Historial de Gastos", "➕ Registrar Salida"])
    with tab1:
        data_gas = [
            {
                "Fecha": g.fecha.strftime("%Y-%m-%d %H:%M"),
                "Descripción": g.descripcion,
                "Monto": f"$ {int(g.monto):,.0f}",
            }
            for g in controller.obtener_gastos()
        ]
        renderizar_tabla_estilizada(data_gas, "Descripción")

    with tab2:
        with st.form("f_gasto"):
            desc = st.text_input("Descripción del Gasto")
            monto = st.number_input("Monto ($)", min_value=0.0)
            if st.form_submit_button("Registrar Gasto", type="primary"):
                if controller.guardar_gasto(desc, monto):
                    st.success("Registrado.")

# 12. CARTERA Y ABONOS
elif menu_seleccionado == "💰 Cartera y Abonos":
    st.title("💰 Gestión de Cartera Inteligente")
    tab1, tab2 = st.tabs(["📑 Estado de Cuenta General", "➕ Aplicar Pago"])

    deudas = controller.obtener_cartera()
    with tab1:
        if deudas:
            data_car = [
                {
                    "Cliente": d.cliente.nombre,
                    "Factura": d.factura_nro,
                    "Saldo": f"$ {int(d.saldo_pendiente):,.0f}",
                    "Estado": d.estado_financiero,
                }
                for d in deudas
            ]
            renderizar_tabla_estilizada(data_car, "Cliente")
        else:
            st.success("¡Excelente! No hay facturas en mora.")

    with tab2:
        clientes_mora = list(set([d.cliente.nombre for d in deudas]))
        if not clientes_mora:
            st.info("No hay clientes con deudas.")
        else:
            cli_sel = st.selectbox("Seleccionar Cliente Deudor", clientes_mora)
            cli_id = next(
                c.id for c in controller.obtener_clientes() if c.nombre == cli_sel
            )
            mora_total = sum(
                d.saldo_pendiente for d in deudas if d.cliente_id == cli_id
            )

            st.error(f"Deuda Total: $ {int(mora_total):,.0f}")
            with st.form("f_abono"):
                abono = st.number_input(
                    "Monto del Abono ($)", min_value=1.0, max_value=float(mora_total)
                )
                if st.form_submit_button("Aplicar Pago (FIFO)", type="primary"):
                    exito, msg = controller.registrar_abono_fifo(cli_id, abono)
                    if exito:
                        st.success(msg)
                    else:
                        st.error(msg)

# 14. PANTALLAS DE BIENVENIDA DE ALTO IMPACTO (HERO BANNERS)
elif menu_seleccionado.startswith("---"):
    # Función de Código Limpio para generar Banners impactantes
    def renderizar_banner_impacto(icono, titulo, descripcion, color_tema):
        html_banner = f"""
        <div style="
            background: linear-gradient(145deg, #152238 0%, #192a40 100%);
            padding: 80px 50px;
            border-radius: 20px;
            border-left: 15px solid {color_tema};
            box-shadow: 0 20px 40px rgba(0,0,0,0.6);
            text-align: center;
            margin-top: 8vh;
            transition: transform 0.3s ease;
        ">
            <h1 style="
                color: {color_tema}; 
                font-size: 4.5em; 
                margin-bottom: 20px; 
                font-weight: 900; 
                letter-spacing: -1px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            ">
                {icono} {titulo}
            </h1>
            <p style="
                color: #e2e8f0; 
                font-size: 1.8em; 
                line-height: 1.6; 
                max-width: 900px; 
                margin: 0 auto;
                font-weight: 300;
            ">
                {descripcion}
            </p>
        </div>
        """
        st.markdown(html_banner, unsafe_allow_html=True)

    # Enrutador inteligente con colores psicológicos por departamento
    if "COMPRAS Y VENTAS" in menu_seleccionado:
        renderizar_banner_impacto(
            "🤝",
            "Compras y Ventas",
            "El núcleo comercial. Gestiona las entradas de inventario mediante compras a proveedores y registra salidas a través del Punto de Venta POS con total fluidez.",
            "#3498db",
        )  # Azul corporativo

    elif "PRODUCCION" in menu_seleccionado:
        renderizar_banner_impacto(
            "🧪",
            "Planta de Producción",
            "El laboratorio creativo. Diseña nuevas fórmulas magistrales, gestiona tus recetas y fracciona lotes de producción para actualizar tu inventario mágicamente.",
            "#9b59b6",
        )  # Morado científico

    elif "LOGISTICA" in menu_seleccionado:
        renderizar_banner_impacto(
            "🏭",
            "Logística y Bodega",
            "El centro de control. Supervisa tu inventario maestro, audita el capital invertido en tiempo real y registra ajustes manuales en el Kardex.",
            "#e67e22",
        )  # Naranja industrial

    elif "GESTION ADMINISTRATIVA" in menu_seleccionado:
        renderizar_banner_impacto(
            "🏢",
            "Gestión Administrativa",
            "El cerebro del negocio. Fideliza la relación con tus clientes en el CRM, mantén tu directorio de asesores y administra el catálogo general.",
            "#e74c3c",
        )  # Rojo ejecutivo

    elif "CARTERA" in menu_seleccionado:
        renderizar_banner_impacto(
            "💼",
            "Cartera y Finanzas",
            "La bóveda financiera. Lleva un control estricto de los gastos operativos y administra las cuentas por cobrar y abonos con el sistema inteligente FIFO.",
            "#2ecc71",
        )  # Verde financiero

    elif "CONFIGURACION" in menu_seleccionado:
        renderizar_banner_impacto(
            "⚙️",
            "Configuración Global",
            "El panel de seguridad. Administra las credenciales de acceso, planes de suscripción y la seguridad encriptada de tu cuenta empresarial.",
            "#f1c40f",
        )  # Amarillo advertencia/ajustes

    else:
        renderizar_banner_impacto(
            "📍",
            "Navegación del Sistema",
            "Has ingresado a una zona segura. Selecciona un módulo específico en el menú lateral izquierdo para comenzar a operar.",
            "#95a5a6",
        )  # Gris neutro

# 13. CONFIGURACIÓN DE SEGURIDAD Y CUENTA
elif menu_seleccionado == "🔒 Seguridad y Cuenta":
    st.title("🔒 Configuración de Seguridad - LIN - PRO X")
    st.markdown("Administra las credenciales de acceso a tu panel empresarial.")
    st.write("---")

    # Tomamos el usuario real de la memoria del sistema
    usuario_actual = st.session_state["usuario"]

    try:
        datos_cuenta = controller.obtener_datos_suscriptor(usuario_actual)
    except:
        datos_cuenta = None

    col1, col2 = st.columns([1, 1.2])

    with col1:
        if datos_cuenta:
            # Cálculo de días restantes
            hoy = datetime.now().date()
            dias_restantes = (datos_cuenta.fecha_vencimiento - hoy).days

            # Tarjeta HTML/CSS idéntica a tu diseño
            tarjeta_html = f"""
                <div style="background: linear-gradient(135deg, #1c2b4a 0%, #152238 100%); 
                            padding: 25px; 
                            border-radius: 12px; 
                            border-left: 6px solid #00b4d8;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <h4 style="color: #00b4d8; margin-top: 0; display: flex; align-items: center;">
                        <span style="font-size: 1.5em; margin-right: 10px;">📋</span> Resumen de la Cuenta
                    </h4>
                    <p style="color: #e2e8f0; font-size: 1.05em; margin: 10px 0;">• <b>Usuario principal:</b> {datos_cuenta.usuario}</p>
                    <p style="color: #e2e8f0; font-size: 1.05em; margin: 10px 0;">• <b>ID Empresarial:</b> {datos_cuenta.empresa_id}</p>
                    <p style="color: #e2e8f0; font-size: 1.05em; margin: 10px 0;">• <b>Licencia Activa:</b> {datos_cuenta.plan}</p>
                    <p style="color: #e2e8f0; font-size: 1.05em; margin: 10px 0;">• <b>Días Restantes:</b> {dias_restantes} días</p>
                </div>
                """
            st.markdown(tarjeta_html, unsafe_allow_html=True)
        else:
            st.warning(
                "⚠️ No se encontraron los datos de suscripción en la base de datos."
            )

    with col2:
        st.markdown("### 🔑 Cambiar Contraseña")
        with st.form("form_cambio_pw"):
            pw_actual = st.text_input("Contraseña Actual", type="password")
            pw_nueva = st.text_input("Nueva Contraseña Personal", type="password")
            pw_conf = st.text_input("Confirmar Nueva Contraseña", type="password")

            st.write("##")  # Espaciado
            if st.form_submit_button(
                "💾 Guardar Nueva Contraseña", use_container_width=True, type="primary"
            ):
                if not pw_actual or not pw_nueva or not pw_conf:
                    st.warning("Todos los campos son obligatorios.")
                elif pw_nueva != pw_conf:
                    st.error("Las nuevas contraseñas no coinciden.")
                elif len(pw_nueva) < 6:
                    st.error("La nueva contraseña debe tener al menos 6 caracteres.")
                else:
                    exito, msg = controller.cambiar_password_suscriptor(
                        usuario_actual, pw_actual, pw_nueva
                    )
                    if exito:
                        st.success(msg)
                    else:
                        st.error(msg)
