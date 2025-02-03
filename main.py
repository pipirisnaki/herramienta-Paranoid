import os
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading

import rcon_ftp
import parsing
import server_list

def crear_pestana_ftp(notebook):
    # Cargar configuración desde herramienta.ini
    parametros = rcon_ftp.cargar_configuracion()

    # Crear la pestaña FTP
    pestaña_ftp = ttk.Frame(notebook)
    notebook.add(pestaña_ftp, text='Carga al servidor')

    # Campos de entrada para FTP
    tk.Label(pestaña_ftp, text="Dirección IP:").grid(row=0, column=0, padx=10, pady=5, sticky='e')
    entrada_ip = tk.Entry(pestaña_ftp, width=30)
    entrada_ip.grid(row=0, column=1, padx=10, pady=5)
    entrada_ip.insert(0, parametros.get("ip", ""))

    tk.Label(pestaña_ftp, text="Puerto:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
    entrada_puerto = tk.Entry(pestaña_ftp, width=30)
    entrada_puerto.grid(row=1, column=1, padx=10, pady=5)
    entrada_puerto.insert(0, parametros.get("puerto", ""))

    tk.Label(pestaña_ftp, text="Usuario:").grid(row=2, column=0, padx=10, pady=5, sticky='e')
    entrada_usuario = tk.Entry(pestaña_ftp, width=30)
    entrada_usuario.grid(row=2, column=1, padx=10, pady=5)
    entrada_usuario.insert(0, parametros.get("usuario", ""))

    tk.Label(pestaña_ftp, text="Contraseña:").grid(row=3, column=0, padx=10, pady=5, sticky='e')
    entrada_contrasena = tk.Entry(pestaña_ftp, show="*", width=30)
    entrada_contrasena.grid(row=3, column=1, padx=10, pady=5)
    entrada_contrasena.insert(0, parametros.get("password", ""))

    tk.Label(pestaña_ftp, text="Ruta principal:").grid(row=4, column=0, padx=10, pady=5, sticky='e')
    entrada_ruta = tk.Entry(pestaña_ftp, width=30)
    entrada_ruta.grid(row=4, column=1, padx=10, pady=5)
    entrada_ruta.insert(0, parametros.get("ruta_principal", ""))

    # Cuadro de estado para SFTP
    cuadro_estado = scrolledtext.ScrolledText(pestaña_ftp, width=70, height=10, state='normal')
    cuadro_estado.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

    def ejecutar_subida():
        ip = entrada_ip.get()
        puerto = entrada_puerto.get()
        usuario = entrada_usuario.get()
        contrasena = entrada_contrasena.get()
        ruta = entrada_ruta.get()

        if not all([ip, puerto, usuario, contrasena, ruta]):
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return

        def proceso_subida():
            cuadro_estado.insert(tk.END, f"Iniciando carga de archivos...\n")
            cuadro_estado.see(tk.END)
            rcon_ftp.subir_varios_archivos_sftp(ip, puerto, usuario, contrasena, ruta, cuadro_estado)

        hilo = threading.Thread(target=proceso_subida)
        hilo.start()

    boton_subir = tk.Button(pestaña_ftp, text="Subir Archivos", command=ejecutar_subida)
    boton_subir.grid(row=4, column=3, columnspan=2, pady=20)

def crear_pestana_rcon(notebook):
    # Cargar configuración desde herramienta.ini
    parametros = rcon_ftp.cargar_configuracion()

    # Crear la pestaña RCON
    pestana_rcon = ttk.Frame(notebook)
    notebook.add(pestana_rcon, text='RCON')

    # Etiqueta y área de texto para estado RCON
    estado_label = tk.Label(pestana_rcon, text="Estado del servidor:")
    estado_label.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    cuadro_estado_rcon = scrolledtext.ScrolledText(
        pestana_rcon, width=80, height=20, state='normal', bg="black", fg="#00FF00"
    )
    cuadro_estado_rcon.grid(row=1, column=0, columnspan=3, padx=10, pady=5)

    # Etiqueta y entrada de comando
    comando_label = tk.Label(pestana_rcon, text="Enviar comando:")
    comando_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

    cuadro_comando = tk.Entry(pestana_rcon, width=60)
    cuadro_comando.grid(row=2, column=1, padx=10, pady=5, sticky="w")

    # Botones de acción
    boton_enviar = tk.Button(pestana_rcon, text="Enviar Comando")
    boton_enviar.grid(row=3, column=1, padx=10, pady=10, sticky="w")

    boton_reiniciar = tk.Button(pestana_rcon, text="Reiniciar Servidor")
    boton_reiniciar.grid(row=3, column=2, padx=10, pady=10)

    # Conectar cliente SSH
    cliente_ssh = rcon_ftp.conectar_rcon(
        parametros['ip'], parametros['puerto'], parametros['usuario'], parametros['password'], cuadro_estado_rcon
    )

    # Función para enviar comandos
    def enviar_comando():
        comando = cuadro_comando.get()
        if not cliente_ssh:
            cuadro_estado_rcon.insert(tk.END, "Error: No hay conexión SSH activa.\n")
            return
        if not comando:
            cuadro_estado_rcon.insert(tk.END, "Error: No se ha ingresado un comando.\n")
            return
        cliente_ssh.sendall((comando + "\n").encode('utf-8'))
        cuadro_comando.delete(0, tk.END)
        cuadro_estado_rcon.insert(tk.END, f"> {comando}\n")

    # Función para reiniciar el servidor
    def reiniciar_servidor():
        if not cliente_ssh:
            cuadro_estado_rcon.insert(tk.END, "Error: No hay conexión SSH activa.\n")
            return
        cliente_ssh.sendall("quit\n".encode('utf-8'))
        cuadro_estado_rcon.insert(tk.END, "Servidor reiniciado.\n")

    # Asociar funciones a botones
    boton_enviar.configure(command=enviar_comando)
    boton_reiniciar.configure(command=reiniciar_servidor)

    return pestana_rcon


def crear_interfaz():
    """
    Crea la interfaz gráfica de usuario utilizando Tkinter con tres pestañas.
    """
    ventana = tk.Tk()
    ventana.title("Herramienta hecha por Paranoid para manejo de maplist")
    ventana.geometry("1200x800")
    ventana.resizable(False, False)

    # Crear un notebook (pestañas)
    notebook = ttk.Notebook(ventana)
    notebook.pack(expand=True, fill='both')

    # Pestaña 1: Batch Processing
    pestaña_batch = ttk.Frame(notebook)
    notebook.add(pestaña_batch, text='Batch Processing')

    # Pestaña 2: Single File Processing
    pestaña_single = ttk.Frame(notebook)
    notebook.add(pestaña_single, text='Single File Processing')

    # Pestaña 3: View Entities
    pestaña_view = ttk.Frame(notebook)
    notebook.add(pestaña_view, text='View Entities')

    # Configuración de la Pestaña Batch Processing
    # Título
    titulo_batch = tk.Label(pestaña_batch, text="Procesamiento por Lotes de Entidades BSP", font=("Arial", 16))
    titulo_batch.pack(pady=10)

    # Botón para ejecutar el dump por lotes
    boton_ejecutar_batch = tk.Button(
        pestaña_batch,
        text="Ejecutar dump de entidades por lotes",
        command=lambda: parsing.ejecutar_dump_batch(text_area_batch, treeview_entidades, maps_dir, ents_dir),
        font=("Arial", 12),
        bg="#4CAF50",
        fg="white",
        padx=10,
        pady=5
    )
    boton_ejecutar_batch.pack(pady=10)

    # Área de texto para mostrar mensajes de Batch Processing
    text_area_batch = scrolledtext.ScrolledText(pestaña_batch, width=140, height=30, font=("Consolas", 10))
    text_area_batch.pack(pady=10)

    # Configuración de la Pestaña Single File Processing
    # Título
    titulo_single = tk.Label(pestaña_single, text="Procesamiento de Archivo Único de Entidades BSP", font=("Arial", 16))
    titulo_single.pack(pady=10)

    # Botón para ejecutar el dump de archivo único
    boton_ejecutar_single = tk.Button(
        pestaña_single,
        text="Ejecutar dump de entidades (Archivo Único)",
        command=lambda: parsing.ejecutar_dump_single(text_area_single, treeview_entidades, maps_dir, ents_dir),
        font=("Arial", 12),
        bg="#2196F3",
        fg="white",
        padx=10,
        pady=5
    )
    boton_ejecutar_single.pack(pady=10)

    # Área de texto para mostrar mensajes de Single File Processing
    text_area_single = scrolledtext.ScrolledText(pestaña_single, width=140, height=30, font=("Consolas", 10))
    text_area_single.pack(pady=10)

    # Configuración de la Pestaña View Entities
    # Título
    titulo_view = tk.Label(pestaña_view, text="Lista de Entidades Generadas", font=("Arial", 16))
    titulo_view.pack(pady=10)

    # Frame para Treeview y Scrollbar
    frame_tree = tk.Frame(pestaña_view)
    frame_tree.pack(pady=5, padx=20, fill='both', expand=True)

    # Treeview para listar las entidades
    columns = ("Archivo", "Estado", "Nombre del Mapa", "Nextmap Aliados", "Nextmap Nazis")
    treeview_entidades = ttk.Treeview(frame_tree, columns=columns, show='headings')
    treeview_entidades.heading("Archivo", text="Archivo")
    treeview_entidades.heading("Estado", text="Estado")
    treeview_entidades.heading("Nombre del Mapa", text="Nombre del Mapa")
    treeview_entidades.heading("Nextmap Aliados", text="Nextmap Aliados")
    treeview_entidades.heading("Nextmap Nazis", text="Nextmap Nazis")
    treeview_entidades.column("Archivo", width=200, anchor='center')
    treeview_entidades.column("Estado", width=100, anchor='center')
    treeview_entidades.column("Nombre del Mapa", width=250, anchor='center')
    treeview_entidades.column("Nextmap Aliados", width=200, anchor='center')
    treeview_entidades.column("Nextmap Nazis", width=200, anchor='center')
    treeview_entidades.pack(side='left', fill='both', expand=True)

    # Scrollbar para el Treeview
    scrollbar = ttk.Scrollbar(frame_tree, orient=tk.VERTICAL, command=treeview_entidades.yview)
    treeview_entidades.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right', fill='y')

    # Área de texto para la pestaña View Entities (para mensajes de actualización)
    text_area_view = scrolledtext.ScrolledText(pestaña_view, width=140, height=5, font=("Consolas", 10))
    text_area_view.pack(pady=10)

    # Frame para la segunda lista personalizada
    frame_custom_list = tk.Frame(pestaña_view)
    frame_custom_list.pack(pady=10, padx=20, fill='both', expand=True)

    # Título para la segunda lista
    titulo_custom_list = tk.Label(frame_custom_list, text="Lista Personalizada de Entidades", font=("Arial", 14))
    titulo_custom_list.pack(pady=5)

    # Lista personalizada (Listbox)
    custom_listbox = tk.Listbox(frame_custom_list, selectmode=tk.SINGLE, width=80, height=10, font=("Consolas", 10))
    custom_listbox.pack(side='left', fill='both', expand=True, padx=(0,10))

    # Scrollbar para la lista personalizada
    scrollbar_custom = ttk.Scrollbar(frame_custom_list, orient=tk.VERTICAL, command=custom_listbox.yview)
    custom_listbox.configure(yscrollcommand=scrollbar_custom.set)
    scrollbar_custom.pack(side='left', fill='y')

    # Frame para los botones de la segunda lista
    frame_buttons = tk.Frame(frame_custom_list)
    frame_buttons.pack(side='left', fill='y')

    # Botón para agregar elementos desde la lista principal
    boton_agregar = tk.Button(
        frame_buttons,
        text="Agregar",
        command=lambda: server_list.agregar_elemento(treeview_entidades, custom_listbox),
        font=("Arial", 12),
        bg="#4CAF50",
        fg="white",
        padx=10,
        pady=5
    )
    boton_agregar.pack(pady=5)

    # Botón para eliminar elementos de la segunda lista
    boton_eliminar = tk.Button(
        frame_buttons,
        text="Eliminar",
        command=lambda: server_list.eliminar_elemento(custom_listbox),
        font=("Arial", 12),
        bg="#f44336",
        fg="white",
        padx=10,
        pady=5
    )
    boton_eliminar.pack(pady=5)

    # Botón para subir elementos en la segunda lista
    boton_subir = tk.Button(
        frame_buttons,
        text="Subir",
        command=lambda: server_list.mover_elemento(custom_listbox, -1),
        font=("Arial", 12),
        bg="#FF9800",
        fg="white",
        padx=10,
        pady=5
    )
    boton_subir.pack(pady=5)

    # Botón para bajar elementos en la segunda lista
    boton_bajar = tk.Button(
        frame_buttons,
        text="Bajar",
        command=lambda: server_list.mover_elemento(custom_listbox, 1),
        font=("Arial", 12),
        bg="#FF9800",
        fg="white",
        padx=10,
        pady=5
    )
    boton_bajar.pack(pady=5)

    # Botón para generar entidades modificadas
    boton_generar_modificados = tk.Button(
        pestaña_view,
        text="Generar Ents Modificados",
        command=lambda: server_list.generar_ents_modificados(custom_listbox, ents_dir, os.path.join(script_dir, 'ents_modificados'), text_area_view),
        font=("Arial", 12),
        bg="#9C27B0",
        fg="white",
        padx=10,
        pady=5
    )
    boton_generar_modificados.pack(pady=10)

    # Obtener directorio donde se encuentra el script para la pestaña View Entities
    script_dir = os.path.dirname(os.path.abspath(__file__))
    maps_dir = os.path.join(script_dir, 'maps')
    ents_dir = os.path.join(script_dir, 'ents')

    # Inicializar la lista de entidades al iniciar la aplicación
    parsing.actualizar_lista_entidades(treeview_entidades, maps_dir, ents_dir, text_area_view)

    # Integrar la nueva pestaña de FTP
    crear_pestana_ftp(notebook)
    crear_pestana_rcon(notebook)

    ventana.mainloop()

if __name__ == "__main__":
    crear_interfaz()