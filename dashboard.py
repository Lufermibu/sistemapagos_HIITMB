import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta

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
    
    telefono_input = st.text_input("Número de teléfono", placeholder="Ej: 555-1234")
    
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
# --- PANTALLA 2: LO QUE VE TU HERMANA ---
elif vista == "Panel Administrador":
    st.title("⚙️ Panel de Control")
    
    clave = st.text_input("Ingresa la clave de acceso", type="password")
    
    if clave == "Mibu070996":
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
                        vencimiento_base = fecha_pago + timedelta(days=30)
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
            st.write("Aquí puedes ver a todos los clientes registrados en la base de datos.")
            
            # Botón para recargar los datos
            if st.button("🔄 Actualizar lista"):
                pass 
            
            # Descargamos todos los datos de Supabase
            respuesta_todos = supabase.table('clientes').select('*').order('id', desc=True).execute()
            datos_todos = respuesta_todos.data
            
            if len(datos_todos) > 0:
                # Convertimos los datos a un formato de tabla
                df_todos = pd.DataFrame(datos_todos)
                
                # Seleccionamos y renombramos las columnas para que se vean presentables
                df_mostrar = df_todos[['nombre', 'telefono', 'monto_pagado', 'fecha_pago', 'fecha_vencimiento']]
                df_mostrar.columns = ['Nombre', 'Teléfono', 'Monto ($)', 'Fecha de Pago', 'Vencimiento']
                
                # Mostramos la tabla interactiva
                st.dataframe(df_mostrar, use_container_width=True)
            else:
                st.info("Aún no hay clientes registrados en la nube.")
                
    elif clave != "":
        st.error("Clave incorrecta. Acceso denegado.")