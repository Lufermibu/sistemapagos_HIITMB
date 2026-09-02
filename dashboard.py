import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import calendar
import urllib.parse

# --- FUNCIÓN AUXILIAR PARA CÁLCULO DE MESES EXACTOS ---
def calcular_proximo_mes(fecha_inicial):
    nuevo_mes = fecha_inicial.month + 1
    nuevo_anio = fecha_inicial.year
    
    # Si pasamos de diciembre, reiniciamos a enero y sumamos un año
    if nuevo_mes > 12:
        nuevo_mes = 1
        nuevo_anio += 1
    
    # Averiguamos cuántos días tiene el nuevo mes (para evitar el error del "31 de febrero")
    ultimo_dia_nuevo_mes = calendar.monthrange(nuevo_anio, nuevo_mes)[1]
    
    # Mantenemos el mismo día de pago, a menos que el nuevo mes sea más corto
    nuevo_dia = min(fecha_inicial.day, ultimo_dia_nuevo_mes)
    
    return fecha_inicial.replace(year=nuevo_anio, month=nuevo_mes, day=nuevo_dia)


# Configuración de la página
st.set_page_config(page_title="HIIT MB", page_icon="💪", layout="wide")

# --- CONEXIÓN A SUPABASE ---
# Pega aquí las credenciales que copiaste (entre las comillas)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Creamos el "cliente" para conectarnos
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MENÚ LATERAL ---
st.sidebar.title("Navegación")
vista = st.sidebar.radio("Ir a:", ["Vista Cliente", "Panel Administrador"])

# --- PANTALLA 1: LO QUE VEN LOS CLIENTES ---
if vista == "Vista Cliente":
    st.title("Consulta tu Perfil")
    st.write("Ingresa tu número de teléfono para ver tu estatus:")
    
    telefono_input = st.text_input("Número de teléfono", placeholder="Ej: 9211961723")
    
    if st.button("Entrar"):
        if telefono_input:
            # Buscamos en Supabase en lugar de SQLite
            respuesta = supabase.table('clientes').select('*').eq('telefono', telefono_input).order('id', desc=True).execute()
            datos = respuesta.data
            
            if len(datos) > 0:
                st.success("¡Perfil encontrado!")
                cliente = datos[0] # Tomamos el registro más reciente
                
                nombre = cliente['nombre']
                monto = cliente['monto_pagado']
                fecha_vence_db = cliente['fecha_vencimiento']
                
                st.subheader(f"Hola, {nombre} 👋")
                col1, col2 = st.columns(2)
                
                fecha_vence = datetime.strptime(fecha_vence_db, "%Y-%m-%d")
                dias_restantes = (fecha_vence - datetime.now()).days
                fecha_vence_pantalla = fecha_vence.strftime("%d/%m/%Y")
                
                col1.metric(label="Monto Último Pago", value=f"${monto}")
                col2.metric(label="Días para corte", value=f"{dias_restantes} días", delta_color="inverse")
                
                st.info(f"📅 Tu mensualidad vence el: **{fecha_vence_pantalla}**")
            else:
                st.error("No se encontró ningún usuario con ese número.")
        else:
            st.warning("Por favor ingresa un número de teléfono.")

# --- PANTALLA 2: ADMINISTRADOR---
elif vista == "Panel Administrador":
    st.title("⚙️ Panel de Control")
    
    clave = st.text_input("Ingresa la clave de acceso", type="password")
    
    if clave == "Mibu0796":
        st.success("Acceso concedido.")
        
        # Creamos dos pestañas para organizar la vista
        tab1, tab2 = st.tabs(["📝 Registrar Pago", "📋 Lista de Clientes"])
        
        # --- PESTAÑA 1: EL FORMULARIO ---
        with tab1:
            st.write("Llena los datos para registrar el pago de un cliente.")
            
            with st.form("formulario_pago", clear_on_submit=True):
                nombre = st.text_input("Nombre del cliente")
                telefono = st.text_input("Teléfono del cliente")
                monto = st.number_input("Monto pagado", min_value=0.0, step=50.0)
                fecha_pago = st.date_input("Fecha de pago", datetime.now()) 
                dias_ajuste = st.number_input("Días de ajuste (Ej: 2 para dar extra, -1 para quitar)", value=0, step=1)
                
                submit = st.form_submit_button("Registrar Pago")
                
                if submit:
                    if nombre and telefono:
                        # USAMOS LA NUEVA LÓGICA DE MES EXACTO
                        vencimiento_base = calcular_proximo_mes(fecha_pago)
                        vencimiento_final = vencimiento_base + timedelta(days=dias_ajuste)
                        
                        fecha_pago_db = fecha_pago.strftime("%Y-%m-%d")
                        vencimiento_db = vencimiento_final.strftime("%Y-%m-%d")
                        vencimiento_pantalla = vencimiento_final.strftime("%d/%m/%Y")
                        
                        nuevo_registro = {
                            "nombre": nombre,
                            "telefono": telefono,
                            "monto_pagado": monto,
                            "fecha_pago": fecha_pago_db,
                            "dias_ajuste": dias_ajuste,
                            "fecha_vencimiento": vencimiento_db
                        }
                        supabase.table('clientes').insert(nuevo_registro).execute()
                        
                        st.success(f"✅ ¡Pago de {nombre} registrado exitosamente! Vence el {vencimiento_pantalla}")
                    else:
                        st.error("Por favor llena al menos el nombre y el teléfono.")
        
        # --- PESTAÑA 2: LA TABLA DE CLIENTES ---
        with tab2:
            st.write("Aquí puedes ver a todos los clientes registrados.")
            
            if st.button("🔄 Actualizar lista"):
                pass 
            
            respuesta_todos = supabase.table('clientes').select('*').order('id', desc=True).execute()
            datos_todos = respuesta_todos.data
            
            if len(datos_todos) > 0:
                df_todos = pd.DataFrame(datos_todos)
                
                df_mostrar = df_todos[['nombre', 'telefono', 'monto_pagado', 'fecha_pago', 'fecha_vencimiento']]
                df_mostrar.columns = ['Nombre', 'Teléfono', 'Monto ($)', 'Fecha de Pago', 'Vencimiento']
                
                st.dataframe(df_mostrar, use_container_width=True)
                
                st.divider()
                st.subheader("⚡ Acciones Rápidas")
                
                opciones = {f"{fila['nombre']} - {fila['telefono']}": fila for fila in datos_todos}
                cliente_elegido = st.selectbox("Selecciona un cliente para interactuar:", list(opciones.keys()))
                
                if cliente_elegido:
                    datos_cliente = opciones[cliente_elegido]
                    id_cliente = datos_cliente['id']
                    nom_cliente = datos_cliente['nombre']
                    tel_cliente = datos_cliente['telefono']
                    vence_cliente = datos_cliente['fecha_vencimiento']
                    monto_previo = datos_cliente['monto_pagado']
                    
                    fecha_obj = datetime.strptime(vence_cliente, "%Y-%m-%d")
                    fecha_bonita = fecha_obj.strftime("%d/%m/%Y")
                    
                    # --- FUNCIÓN 1: VENTANA PARA RENOVAR PAGO ---
                    @st.dialog("🔄 Renovar Mensualidad")
                    def renovar_pago(id_renovar, nombre_renovar, monto_sugerido):
                        st.write(f"Registrar nuevo pago para **{nombre_renovar}**")
                        
                        nuevo_monto = st.number_input("Monto pagado", min_value=0.0, value=float(monto_sugerido), step=50.0)
                        nueva_fecha_pago = st.date_input("Fecha de pago", datetime.now())
                        dias_ajuste = st.number_input("Días de ajuste", value=0, step=1)
                        
                        if st.button("Guardar Renovación"):
                            # USAMOS LA NUEVA LÓGICA DE MES EXACTO AQUÍ TAMBIÉN
                            vencimiento_base = calcular_proximo_mes(nueva_fecha_pago)
                            vencimiento_final = vencimiento_base + timedelta(days=dias_ajuste)
                            
                            # Usamos .update() en lugar de .insert() para sobreescribir sus datos
                            supabase.table('clientes').update({
                                "monto_pagado": nuevo_monto,
                                "fecha_pago": nueva_fecha_pago.strftime("%Y-%m-%d"),
                                "dias_ajuste": dias_ajuste,
                                "fecha_vencimiento": vencimiento_final.strftime("%Y-%m-%d")
                            }).eq('id', id_renovar).execute()
                            
                            st.success("¡Pago actualizado!")
                            st.rerun()

                    # --- FUNCIÓN 2: VENTANA EMERGENTE DE BORRADO ---
                    @st.dialog("⚠️ Confirmar Borrado")
                    def confirmar_borrado(id_borrar, nombre_borrar):
                        st.warning(f"¿Estás segura de que quieres eliminar a **{nombre_borrar}**?")
                        st.write("Esta acción no se puede deshacer y borrará su historial de pagos.")
                        
                        if st.button("Sí, eliminar permanentemente"):
                            supabase.table('clientes').delete().eq('id', id_borrar).execute()
                            st.rerun() 

                    # --- FUNCIÓN 3: VENTANA PARA EDITAR DATOS ---
                    @st.dialog("✏️ Editar Datos del Cliente")
                    def editar_cliente(id_editar, nombre_actual, telefono_actual):
                        st.write("Modifica los datos correspondientes:")
                        
                        # Pre-llenamos los campos con los datos actuales
                        nuevo_nombre = st.text_input("Nombre del cliente", value=nombre_actual)
                        nuevo_telefono = st.text_input("Teléfono", value=telefono_actual)
                        
                        if st.button("Guardar Cambios"):
                            # Hacemos el UPDATE en Supabase usando el ID
                            supabase.table('clientes').update({
                                "nombre": nuevo_nombre,
                                "telefono": nuevo_telefono
                            }).eq('id', id_editar).execute()
                            
                            st.success("¡Datos actualizados!")
                            st.rerun()
                    # ------------------------------------------------
                    
                    # Dividimos en 4 columnas para que los botones quepan bien
                    colA, colB, colC, colD = st.columns(4)
                    
                    with colA:
                        numero_limpio = tel_cliente.replace("-", "").replace(" ", "")
                        mensaje = f"¡Hola {nom_cliente}!. Te enviamos esta notificación para recordarte que tu próxima mensualidad se debe renovar el día {fecha_bonita}. ¡Gracias por ser parte del equipo HIIT! ♡"
                        mensaje_codificado = urllib.parse.quote(mensaje)
                        link_wa = f"https://wa.me/52{numero_limpio}?text={mensaje_codificado}"
                        
                        st.link_button("📲 WhatsApp", link_wa)
                        
                    with colB:
                        # Botón que llama a la ventana de renovación
                        if st.button("🔄 Renovar"):
                            renovar_pago(id_cliente, nom_cliente, monto_previo)
                    
                    with colC:
                        # NUEVO BOTÓN: Llama a la ventana de edición
                        if st.button("✏️ Editar"):
                            editar_cliente(id_cliente, nom_cliente, tel_cliente)
                            
                    with colD:
                        # Botón que llama a la ventana de confirmación
                        if st.button("❌ Eliminar"):
                            confirmar_borrado(id_cliente, nom_cliente)
                        else:
                                    st.info("Aún no hay clientes registrados en la nube.")
                        elif clave != "":
                            st.error("Clave incorrecta. Acceso denegado.")
