import sys
import struct
import os
import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
import re

# Definiciones similares a las de C
MAGIC = 0x50534249  # 'PSBI' en big endian, equivalente a 'IBSP' en little endian
HEADERLEN = 4 * 40   # 160 bytes
ENTITIES = 0         # Índice del lump de entidades

class BSPFile:
    """
    Clase para manejar la lectura y procesamiento de archivos BSP.
    """
    def __init__(self, filename):
        self.filename = filename
        self.pos = 0
        self.offsets = []
        self.lengths = []
        self.entities = b''

    def read_int(self, data):
        """
        Lee un entero de 4 bytes en formato little endian desde 'data' en la posición actual 'pos'.
        """
        if self.pos + 4 > len(data):
            raise ValueError("Intento de leer más allá del final de los datos")
        i = struct.unpack_from('<I', data, self.pos)[0]
        self.pos += 4
        return i

    def parse(self):
        """
        Lee y analiza el archivo BSP, extrayendo los offsets y lengths de los lumps.
        """
        try:
            with open(self.filename, 'rb') as f:
                header = f.read(HEADERLEN)
                if len(header) < HEADERLEN:
                    return f"Error: Header demasiado corto en {self.filename}"

                self.pos = 0
                check = self.read_int(header)
                version = self.read_int(header)

                if check != MAGIC:
                    return f"Archivo BSP inválido: {self.filename}"

                # Leer 19 lumps (offsets y lengths) y ajustar los offsets restando HEADERLEN
                self.offsets = []
                self.lengths = []
                for i in range(19):
                    offset = self.read_int(header) - HEADERLEN  # Ajuste aquí
                    length = self.read_int(header)
                    self.offsets.append(offset)
                    self.lengths.append(length)
                    # Puedes descomentar la siguiente línea para depuración
                    # print(f"Lump {i}: Offset={offset}, Length={length}")

                # Leer el lump de entidades
                entities_offset = self.offsets[ENTITIES] + HEADERLEN  # Esto ahora apunta al offset correcto
                entities_length = self.lengths[ENTITIES]
                # print(f"Entities Lump: Offset={entities_offset}, Length={entities_length}")

                f.seek(entities_offset)
                self.entities = f.read(entities_length)
                if len(self.entities) < entities_length:
                    return f"Error: Lump de entidades demasiado corto en {self.filename}"

                return "Parseo exitoso."
        except FileNotFoundError:
            return f"Archivo no encontrado: {self.filename}"
        except Exception as e:
            return f"Error al leer {self.filename}: {e}"

    def save_entities_to_ent(self, output_dir):
        """
        Guarda las entidades decodificadas en un archivo .ent con el mismo nombre base que el .bsp.
        Por ejemplo, 'dust.bsp' se guarda como 'dust.ent' en 'output_dir'.
        """
        try:
            # Encontrar el primer byte nulo para cortar la cadena (opcional)
            null_byte_index = self.entities.find(b'\x00')
            if null_byte_index != -1:
                entities_clean = self.entities[:null_byte_index]
            else:
                entities_clean = self.entities

            # Decodificar solo hasta el primer byte nulo
            entities_str = entities_clean.decode('utf-8', errors='replace')

            # Obtener el nombre base sin extensión
            base_name = os.path.splitext(os.path.basename(self.filename))[0]
            ent_filename = f"{base_name}.ent"
            # Definir la ruta completa para el archivo .ent en output_dir
            ent_filepath = os.path.join(output_dir, ent_filename)

            with open(ent_filepath, 'w', encoding='utf-8') as ent_file:
                ent_file.write(entities_str)

            return f"Entidades guardadas en: {ent_filepath}"
        except Exception as e:
            return f"Error al guardar entidades en {self.filename}: {e}"

def parse_ent_file(ent_path):
    """
    Analiza un archivo .ent y extrae:
    - nombre_del_mapa
    - nextmap_aliados
    - nextmap_nazis
    """
    try:
        with open(ent_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Dividir el contenido en bloques
        blocks = re.findall(r'\{([^}]*)\}', content, re.DOTALL)

        nombre_del_mapa = "N/A"
        nextmap_aliados = "N/A"
        nextmap_nazis = "N/A"

        for block in blocks:
            entity = {}
            matches = re.findall(r'"([^"]+)"\s+"([^"]+)"', block)
            for key, value in matches:
                entity[key] = value
            classname = entity.get("classname", "")
            if classname == "worldspawn":
                nombre_del_mapa = entity.get("message", "N/A")
            elif classname == "info_team_start":
                message = entity.get("message", "")
                nextmap = entity.get("nextmap", "N/A")
                if message.lower() == "allies":
                    nextmap_aliados = nextmap
                elif message.lower() == "axis":
                    nextmap_nazis = nextmap

        return nombre_del_mapa, nextmap_aliados, nextmap_nazis

    except Exception as e:
        return "Error al parsear", "Error al parsear", "Error al parsear"

def ejecutar_dump_batch(text_area, treeview_entidades, maps_dir, ents_dir):
    """
    Función que se ejecuta al presionar el botón de Batch Processing.
    Procesa todos los archivos .bsp en 'maps' y guarda los .ent en 'ents'.
    """
    # Limpiar el área de texto
    text_area.delete('1.0', tk.END)

    # Verificar que el directorio 'maps' existe
    if not os.path.isdir(maps_dir):
        message = f"Directorio 'maps' no encontrado en: {maps_dir}"
        text_area.insert(tk.END, message + "\n")
        messagebox.showerror("Error", message)
        return

    # Crear el directorio 'ents' si no existe
    os.makedirs(ents_dir, exist_ok=True)

    # Listar todos los archivos .bsp en 'maps'
    bsp_files = [f for f in os.listdir(maps_dir) if f.lower().endswith('.bsp')]

    if not bsp_files:
        message = f"No se encontraron archivos .bsp en el directorio 'maps': {maps_dir}"
        text_area.insert(tk.END, message + "\n")
        messagebox.showwarning("Advertencia", message)
        return

    # Procesar cada archivo .bsp
    for bsp_file in bsp_files:
        bsp_path = os.path.join(maps_dir, bsp_file)
        message = f"Procesando: {bsp_path}"
        text_area.insert(tk.END, message + "\n")
        bsp = BSPFile(bsp_path)
        parse_result = bsp.parse()
        text_area.insert(tk.END, f"Parseo: {parse_result}\n")
        if parse_result == "Parseo exitoso.":
            save_result = bsp.save_entities_to_ent(ents_dir)
            text_area.insert(tk.END, f"{save_result}\n")
        else:
            text_area.insert(tk.END, f"No se pudo procesar: {bsp_file}\n")
        text_area.insert(tk.END, '-' * 60 + "\n")

    # Actualizar la lista de entidades después del procesamiento por lotes
    actualizar_lista_entidades(treeview_entidades, maps_dir, ents_dir, text_area)

    messagebox.showinfo("Completado", "Dump de entidades por lotes completado.")

def ejecutar_dump_single(text_area, treeview_entidades, maps_dir, ents_dir):
    """
    Función que se ejecuta al presionar el botón de Single File Processing.
    Permite seleccionar un archivo .bsp y procesa solo ese archivo.
    """
    # Limpiar el área de texto
    text_area.delete('1.0', tk.END)

    # Abrir un diálogo para seleccionar el archivo .bsp
    archivo_bsp = filedialog.askopenfilename(
        title="Selecciona un archivo .bsp",
        filetypes=[("Archivos BSP", "*.bsp")],
        initialdir=maps_dir
    )

    if not archivo_bsp:
        # El usuario canceló la selección
        return

    # Verificar que el archivo seleccionado exista
    if not os.path.isfile(archivo_bsp):
        message = f"Archivo no encontrado: {archivo_bsp}"
        text_area.insert(tk.END, message + "\n")
        messagebox.showerror("Error", message)
        return

    # Procesar el archivo seleccionado
    bsp = BSPFile(archivo_bsp)
    parse_result = bsp.parse()
    text_area.insert(tk.END, f"Parseo: {parse_result}\n")
    if parse_result == "Parseo exitoso.":
        save_result = bsp.save_entities_to_ent(ents_dir)
        text_area.insert(tk.END, f"{save_result}\n")
    else:
        text_area.insert(tk.END, f"No se pudo procesar: {archivo_bsp}\n")
    text_area.insert(tk.END, '-' * 60 + "\n")

    # Actualizar la lista de entidades después del procesamiento de un archivo único
    actualizar_lista_entidades(treeview_entidades, maps_dir, ents_dir, text_area)

    messagebox.showinfo("Completado", "Dump de entidades completado.")

def generar_maplist_txt(entidades, script_dir, text_area):
    """
    Genera el archivo maplist.txt en el directorio raíz del script con la lista de mapas proporcionada.
    """
    maplist_path = os.path.join(script_dir, 'maplist.txt')

    # Definir el contenido fijo del maplist.txt
    header = (
        "; This maplist is NOT used at default.\n"
        "; The maximum amount of maps for maplist is 64.\n"
        "; If you want to start using it, type:\n"
        ";\n"
        ";       sv maplist maplist.ini [option]\n"
        ";       at the console.\n"
        ";\n"
        "; Where option = 0 (play maps in sequence) or \n"
        ";                1 (pick random maps).\n"
        ";\n"
        "; You can then use \"sv maplist start\"\n"
        ";\n"
        "; Use:\n"
        "; \"sv maplist help\" for a full list of available commands;\n"
        "; \"sv maplist next\" to move to next map;\n"
        "; \"sv maplist off\" to stop map rotations ;\n"
        "[maplist]\n"
    )

    footer = (
        "###\n"
        "; Make sure you have [maplist] at the beginning of the list and ### at the end.\n"
    )

    try:
        with open(maplist_path, 'w', encoding='utf-8') as file:
            file.write(header)
            for map_name in entidades:
                file.write(f"{map_name}\n")
            file.write(footer)

        # Informar al usuario
        text_area.insert(tk.END, f"Generado: {maplist_path}\n")
    except Exception as e:
        message = f"Error al generar maplist.txt: {e}"
        text_area.insert(tk.END, message + "\n")

def generar_server_cfg(entidades, script_dir, text_area):
    """
    Genera el archivo server.cfg en el directorio raíz del script con la configuración especificada,
    reemplazando la línea 'set sv_maplist' con la lista de mapas personalizada.
    """
    server_cfg_path = os.path.join(script_dir, 'server.cfg')

    # Crear la lista de mapas separados por espacios
    maplist_str = ' '.join(entidades)

    # Definir el contenido fijo del server.cfg con el maplist personalizado
    server_cfg_content = (
        'set game dday\n'
        'set gamedir dday\n'
        'set hostname "MR D-Day server by paranoid"\n'
        'set website "http://www.mr.cl" s\n'
        'set deathmatch 1\n'
        'set timelimit 0\n'
        'set maxclients 24\n'
        'set public 1\n'
        'setmaster master.q2servers.com satan.idsoftware.com q2master.planetquake.com\n'
        '//set password "mypass"\n'
        'set rcon_password "mrinvicto"\n'
        'set observer_password "sapo"\n'
        'sv maplist maplist.txt 0\n'
        'sv maplist start\n'
        'set RI 3\n'
        'set level_wait 5\n'
        'set team_kill 1\n'
        'set invuln_medic 0\n'
        'set death_msg 1\n'
        'set easter_egg 0\n'
        'set arty_delay 10\n'
        'set arty_time 60\n'
        'set arty_max 1\n'
        'set invuln_spawn 2\n'
        'set spawn_camp_check 1\n'
        'set spawn_camp_time 2\n'
        'set flood_msgs 10\n'
        'set flood_persecond 10\n'
        'set flood_waitdelay 10\n'
        f'set sv_maplist "{maplist_str}"\n'
        'map dust\n'
        'seta bots 1\n'
        'sv_allow_map 2\n'
        'set allow_download 1\n'
        'set exbattleinfo 5\n'
    )

    try:
        with open(server_cfg_path, 'w', encoding='utf-8') as file:
            file.write(server_cfg_content)

        # Informar al usuario
        text_area.insert(tk.END, f"Generado: {server_cfg_path}\n")
    except Exception as e:
        message = f"Error al generar server.cfg: {e}"
        text_area.insert(tk.END, message + "\n")

def generar_ents_modificados(custom_listbox, ents_dir, output_dir, text_area):
    """
    Genera nuevos archivos .ent con el campo 'nextmap' actualizado según la lista personalizada
    y crea un archivo maplist.txt y server.cfg en el directorio raíz del script.
    """
    entidades = custom_listbox.get(0, tk.END)
    if not entidades:
        messagebox.showwarning("Advertencia", "La lista personalizada está vacía.")
        return

    # Crear el directorio 'ents_modificados' si no existe
    os.makedirs(output_dir, exist_ok=True)

    # Obtener el directorio raíz del script (donde se encuentra el archivo Python)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    total = len(entidades)
    for i, entidad in enumerate(entidades):
        # Determinar el nuevo 'nextmap'
        nuevo_nextmap = entidades[(i + 1) % total]

        # Ruta del archivo .ent original
        ent_original_path = os.path.join(ents_dir, f"{entidad}.ent")
        if not os.path.isfile(ent_original_path):
            message = f"Archivo .ent no encontrado: {ent_original_path}"
            text_area.insert(tk.END, message + "\n")
            continue

        try:
            # Leer el contenido original
            with open(ent_original_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Definir una función para modificar o agregar 'nextmap' en los bloques correspondientes
            def modificar_nextmap(match):
                block_content = match.group(1)
                # Verificar si el bloque tiene 'classname' 'info_team_start'
                if '"classname" "info_team_start"' in block_content:
                    # Buscar si ya tiene 'nextmap'
                    if re.search(r'"nextmap"\s+"[^"]+"', block_content):
                        # Reemplazar el valor de 'nextmap'
                        block_content = re.sub(r'("nextmap"\s+")([^"]+)(")', f'\\1{nuevo_nextmap}\\3', block_content, count=1)
                    else:
                        # Agregar el campo 'nextmap' antes del cierre del bloque sin espacios adicionales
                        block_content = block_content.rstrip() + f'\n"nextmap" "{nuevo_nextmap}"'
                    # Asegurar que el cierre de la llave esté en una nueva línea
                    return f'{{{block_content}\n}}'
                else:
                    return match.group(0)  # No modificar bloques que no correspondan

            # Aplicar la modificación a todos los bloques
            nuevo_content = re.sub(r'\{([^}]*)\}', modificar_nextmap, content, flags=re.DOTALL)

            # Eliminar saltos de línea innecesarios: reemplazar múltiples saltos de línea por uno solo
            # Esto evita que se agreguen líneas en blanco extra
            nuevo_content = re.sub(r'\n\s*\n', '\n', nuevo_content)

            # Guardar el nuevo contenido en el directorio 'ents_modificados'
            ent_modificado_path = os.path.join(output_dir, f"{entidad}.ent")
            with open(ent_modificado_path, 'w', encoding='utf-8') as file:
                file.write(nuevo_content)

            # Informar al usuario
            text_area.insert(tk.END, f"Generado: {ent_modificado_path}\n")
        except Exception as e:
            message = f"Error al modificar {ent_original_path}: {e}"
            text_area.insert(tk.END, message + "\n")

    # Después de modificar los archivos .ent, generar maplist.txt y server.cfg
    generar_maplist_txt(entidades, script_dir, text_area)
    generar_server_cfg(entidades, script_dir, text_area)

    text_area.insert(tk.END, '-' * 60 + "\n")
    messagebox.showinfo("Completado", "Generación de entidades modificadas, maplist.txt y server.cfg completada.")

def actualizar_lista_entidades(treeview, maps_dir, ents_dir, text_area):
    """
    Actualiza la lista de entidades en la tercera pestaña.
    Lista todos los archivos .bsp en 'maps' y verifica si su correspondiente .ent existe en 'ents'.
    Muestra solo el nombre sin la extensión .ent y añade información adicional.
    """
    # Limpiar el Treeview
    for item in treeview.get_children():
        treeview.delete(item)

    # Listar todos los archivos .bsp en 'maps'
    bsp_files = [f for f in os.listdir(maps_dir) if f.lower().endswith('.bsp')]

    for bsp_file in bsp_files:
        base_name = os.path.splitext(bsp_file)[0]
        ent_filename = f"{base_name}.ent"
        ent_path = os.path.join(ents_dir, ent_filename)
        if os.path.isfile(ent_path):
            status = "Generado"
            # Extraer información adicional del archivo .ent
            nombre_del_mapa, nextmap_aliados, nextmap_nazis = parse_ent_file(ent_path)
        else:
            status = "No Generado"
            nombre_del_mapa = "N/A"
            nextmap_aliados = "N/A"
            nextmap_nazis = "N/A"
        # Insertar en el Treeview sin la extensión .ent
        treeview.insert('', 'end', values=(base_name, status, nombre_del_mapa, nextmap_aliados, nextmap_nazis))

    # Mostrar mensaje en el área de texto
    text_area.insert(tk.END, "Lista de entidades actualizada.\n")

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
        command=lambda: ejecutar_dump_batch(text_area_batch, treeview_entidades, maps_dir, ents_dir),
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
        command=lambda: ejecutar_dump_single(text_area_single, treeview_entidades, maps_dir, ents_dir),
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
        command=lambda: agregar_elemento(treeview_entidades, custom_listbox),
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
        command=lambda: eliminar_elemento(custom_listbox),
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
        command=lambda: mover_elemento(custom_listbox, -1),
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
        command=lambda: mover_elemento(custom_listbox, 1),
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
        command=lambda: generar_ents_modificados(custom_listbox, ents_dir, os.path.join(script_dir, 'ents_modificados'), text_area_view),
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
    actualizar_lista_entidades(treeview_entidades, maps_dir, ents_dir, text_area_view)

    ventana.mainloop()

def agregar_elemento(treeview, custom_listbox):
    """
    Agrega el elemento seleccionado en el Treeview a la lista personalizada.
    """
    selected_item = treeview.selection()
    if not selected_item:
        messagebox.showwarning("Advertencia", "Selecciona una entidad para agregar.")
        return
    for item in selected_item:
        valores = treeview.item(item, 'values')
        archivo = valores[0]
        # Evitar duplicados
        existing_items = custom_listbox.get(0, tk.END)
        if archivo not in existing_items:
            custom_listbox.insert(tk.END, archivo)
        else:
            messagebox.showinfo("Información", f"'{archivo}' ya está en la lista.")

def eliminar_elemento(custom_listbox):
    """
    Elimina el elemento seleccionado de la lista personalizada.
    """
    selected_indices = custom_listbox.curselection()
    if not selected_indices:
        messagebox.showwarning("Advertencia", "Selecciona un elemento para eliminar.")
        return
    for index in reversed(selected_indices):
        custom_listbox.delete(index)

def mover_elemento(custom_listbox, direccion):
    """
    Mueve el elemento seleccionado en la lista personalizada hacia arriba o hacia abajo.
    :param custom_listbox: Listbox que contiene los elementos.
    :param direccion: -1 para subir, 1 para bajar.
    """
    seleccion = custom_listbox.curselection()
    if not seleccion:
        messagebox.showwarning("Advertencia", "Selecciona un elemento para mover.")
        return

    index = seleccion[0]
    nueva_pos = index + direccion

    if nueva_pos < 0 or nueva_pos >= custom_listbox.size():
        return  # No hacer nada si está en los límites

    # Obtener el texto del elemento seleccionado
    elemento = custom_listbox.get(index)

    # Eliminar el elemento de su posición actual
    custom_listbox.delete(index)

    # Insertar el elemento en la nueva posición
    custom_listbox.insert(nueva_pos, elemento)

    # Seleccionar el elemento nuevamente
    custom_listbox.select_set(nueva_pos)
    custom_listbox.activate(nueva_pos)

def generar_maplist_txt(entidades, script_dir, text_area):
    """
    Genera el archivo maplist.txt en el directorio raíz del script con la lista de mapas proporcionada.
    """
    maplist_path = os.path.join(script_dir, 'maplist.txt')

    # Definir el contenido fijo del maplist.txt
    header = (
        "; This maplist is NOT used at default.\n"
        "; The maximum amount of maps for maplist is 64.\n"
        "; If you want to start using it, type:\n"
        ";\n"
        ";       sv maplist maplist.ini [option]\n"
        ";       at the console.\n"
        ";\n"
        "; Where option = 0 (play maps in sequence) or \n"
        ";                1 (pick random maps).\n"
        ";\n"
        "; You can then use \"sv maplist start\"\n"
        ";\n"
        "; Use:\n"
        "; \"sv maplist help\" for a full list of available commands;\n"
        "; \"sv maplist next\" to move to next map;\n"
        "; \"sv maplist off\" to stop map rotations ;\n"
        "[maplist]\n"
    )

    footer = (
        "###\n"
        "; Make sure you have [maplist] at the beginning of the list and ### at the end.\n"
    )

    try:
        with open(maplist_path, 'w', encoding='utf-8') as file:
            file.write(header)
            for map_name in entidades:
                file.write(f"{map_name}\n")
            file.write(footer)

        # Informar al usuario
        text_area.insert(tk.END, f"Generado: {maplist_path}\n")
    except Exception as e:
        message = f"Error al generar maplist.txt: {e}"
        text_area.insert(tk.END, message + "\n")

def generar_server_cfg(entidades, script_dir, text_area):
    """
    Genera el archivo server.cfg en el directorio raíz del script con la configuración especificada,
    reemplazando la línea 'set sv_maplist' con la lista de mapas personalizada.
    """
    server_cfg_path = os.path.join(script_dir, 'server.cfg')

    # Crear la lista de mapas separados por espacios
    maplist_str = ' '.join(entidades)

    # Definir el contenido fijo del server.cfg con el maplist personalizado
    server_cfg_content = (
        'set game dday\n'
        'set gamedir dday\n'
        'set hostname "MR D-Day server by paranoid"\n'
        'set website "http://www.mr.cl" s\n'
        'set deathmatch 1\n'
        'set timelimit 0\n'
        'set maxclients 24\n'
        'set public 1\n'
        'setmaster master.q2servers.com satan.idsoftware.com q2master.planetquake.com\n'
        '//set password "mypass"\n'
        'set rcon_password "mrinvicto"\n'
        'set observer_password "sapo"\n'
        'sv maplist maplist.txt 0\n'
        'sv maplist start\n'
        'set RI 3\n'
        'set level_wait 5\n'
        'set team_kill 1\n'
        'set invuln_medic 0\n'
        'set death_msg 1\n'
        'set easter_egg 0\n'
        'set arty_delay 10\n'
        'set arty_time 60\n'
        'set arty_max 1\n'
        'set invuln_spawn 2\n'
        'set spawn_camp_check 1\n'
        'set spawn_camp_time 2\n'
        'set flood_msgs 10\n'
        'set flood_persecond 10\n'
        'set flood_waitdelay 10\n'
        f'set sv_maplist "{maplist_str}"\n'
        'map dust\n'
        'seta bots 1\n'
        'sv_allow_map 2\n'
        'set allow_download 1\n'
        'set exbattleinfo 5\n'
    )

    try:
        with open(server_cfg_path, 'w', encoding='utf-8') as file:
            file.write(server_cfg_content)

        # Informar al usuario
        text_area.insert(tk.END, f"Generado: {server_cfg_path}\n")
    except Exception as e:
        message = f"Error al generar server.cfg: {e}"
        text_area.insert(tk.END, message + "\n")

def generar_ents_modificados(custom_listbox, ents_dir, output_dir, text_area):
    """
    Genera nuevos archivos .ent con el campo 'nextmap' actualizado según la lista personalizada
    y crea un archivo maplist.txt y server.cfg en el directorio raíz del script.
    """
    entidades = custom_listbox.get(0, tk.END)
    if not entidades:
        messagebox.showwarning("Advertencia", "La lista personalizada está vacía.")
        return

    # Crear el directorio 'ents_modificados' si no existe
    os.makedirs(output_dir, exist_ok=True)

    # Obtener el directorio raíz del script (donde se encuentra el archivo Python)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    total = len(entidades)
    for i, entidad in enumerate(entidades):
        # Determinar el nuevo 'nextmap'
        nuevo_nextmap = entidades[(i + 1) % total]

        # Ruta del archivo .ent original
        ent_original_path = os.path.join(ents_dir, f"{entidad}.ent")
        if not os.path.isfile(ent_original_path):
            message = f"Archivo .ent no encontrado: {ent_original_path}"
            text_area.insert(tk.END, message + "\n")
            continue

        try:
            # Leer el contenido original
            with open(ent_original_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Definir una función para modificar o agregar 'nextmap' en los bloques correspondientes
            def modificar_nextmap(match):
                block_content = match.group(1)
                # Verificar si el bloque tiene 'classname' 'info_team_start'
                if '"classname" "info_team_start"' in block_content:
                    # Buscar si ya tiene 'nextmap'
                    if re.search(r'"nextmap"\s+"[^"]+"', block_content):
                        # Reemplazar el valor de 'nextmap'
                        block_content = re.sub(r'("nextmap"\s+")([^"]+)(")', f'\\1{nuevo_nextmap}\\3', block_content, count=1)
                    else:
                        # Agregar el campo 'nextmap' antes del cierre del bloque sin espacios adicionales
                        block_content = block_content.rstrip() + f'\n"nextmap" "{nuevo_nextmap}"'
                    # Asegurar que el cierre de la llave esté en una nueva línea
                    return f'{{{block_content}\n}}'
                else:
                    return match.group(0)  # No modificar bloques que no correspondan

            # Aplicar la modificación a todos los bloques
            nuevo_content = re.sub(r'\{([^}]*)\}', modificar_nextmap, content, flags=re.DOTALL)

            # Eliminar saltos de línea innecesarios: reemplazar múltiples saltos de línea por uno solo
            # Esto evita que se agreguen líneas en blanco extra
            nuevo_content = re.sub(r'\n\s*\n', '\n', nuevo_content)

            # Guardar el nuevo contenido en el directorio 'ents_modificados'
            ent_modificado_path = os.path.join(output_dir, f"{entidad}.ent")
            with open(ent_modificado_path, 'w', encoding='utf-8') as file:
                file.write(nuevo_content)

            # Informar al usuario
            text_area.insert(tk.END, f"Generado: {ent_modificado_path}\n")
        except Exception as e:
            message = f"Error al modificar {ent_original_path}: {e}"
            text_area.insert(tk.END, message + "\n")

    # Después de modificar los archivos .ent, generar maplist.txt y server.cfg
    generar_maplist_txt(entidades, script_dir, text_area)
    generar_server_cfg(entidades, script_dir, text_area)

    text_area.insert(tk.END, '-' * 60 + "\n")
    messagebox.showinfo("Completado", "Generación de entidades modificadas, maplist.txt y server.cfg completada.")

def actualizar_lista_entidades(treeview, maps_dir, ents_dir, text_area):
    """
    Actualiza la lista de entidades en la tercera pestaña.
    Lista todos los archivos .bsp en 'maps' y verifica si su correspondiente .ent existe en 'ents'.
    Muestra solo el nombre sin la extensión .ent y añade información adicional.
    """
    # Limpiar el Treeview
    for item in treeview.get_children():
        treeview.delete(item)

    # Listar todos los archivos .bsp en 'maps'
    bsp_files = [f for f in os.listdir(maps_dir) if f.lower().endswith('.bsp')]

    for bsp_file in bsp_files:
        base_name = os.path.splitext(bsp_file)[0]
        ent_filename = f"{base_name}.ent"
        ent_path = os.path.join(ents_dir, ent_filename)
        if os.path.isfile(ent_path):
            status = "Generado"
            # Extraer información adicional del archivo .ent
            nombre_del_mapa, nextmap_aliados, nextmap_nazis = parse_ent_file(ent_path)
        else:
            status = "No Generado"
            nombre_del_mapa = "N/A"
            nextmap_aliados = "N/A"
            nextmap_nazis = "N/A"
        # Insertar en el Treeview sin la extensión .ent
        treeview.insert('', 'end', values=(base_name, status, nombre_del_mapa, nextmap_aliados, nextmap_nazis))

    # Mostrar mensaje en el área de texto
    text_area.insert(tk.END, "Lista de entidades actualizada.\n")

def mover_elemento(custom_listbox, direccion):
    """
    Mueve el elemento seleccionado en la lista personalizada hacia arriba o hacia abajo.
    :param custom_listbox: Listbox que contiene los elementos.
    :param direccion: -1 para subir, 1 para bajar.
    """
    seleccion = custom_listbox.curselection()
    if not seleccion:
        messagebox.showwarning("Advertencia", "Selecciona un elemento para mover.")
        return

    index = seleccion[0]
    nueva_pos = index + direccion

    if nueva_pos < 0 or nueva_pos >= custom_listbox.size():
        return  # No hacer nada si está en los límites

    # Obtener el texto del elemento seleccionado
    elemento = custom_listbox.get(index)

    # Eliminar el elemento de su posición actual
    custom_listbox.delete(index)

    # Insertar el elemento en la nueva posición
    custom_listbox.insert(nueva_pos, elemento)

    # Seleccionar el elemento nuevamente
    custom_listbox.select_set(nueva_pos)
    custom_listbox.activate(nueva_pos)

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
        command=lambda: ejecutar_dump_batch(text_area_batch, treeview_entidades, maps_dir, ents_dir),
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
        command=lambda: ejecutar_dump_single(text_area_single, treeview_entidades, maps_dir, ents_dir),
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
        command=lambda: agregar_elemento(treeview_entidades, custom_listbox),
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
        command=lambda: eliminar_elemento(custom_listbox),
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
        command=lambda: mover_elemento(custom_listbox, -1),
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
        command=lambda: mover_elemento(custom_listbox, 1),
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
        command=lambda: generar_ents_modificados(custom_listbox, ents_dir, os.path.join(script_dir, 'ents_modificados'), text_area_view),
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
    actualizar_lista_entidades(treeview_entidades, maps_dir, ents_dir, text_area_view)

    ventana.mainloop()

def agregar_elemento(treeview, custom_listbox):
    """
    Agrega el elemento seleccionado en el Treeview a la lista personalizada.
    """
    selected_item = treeview.selection()
    if not selected_item:
        messagebox.showwarning("Advertencia", "Selecciona una entidad para agregar.")
        return
    for item in selected_item:
        valores = treeview.item(item, 'values')
        archivo = valores[0]
        # Evitar duplicados
        existing_items = custom_listbox.get(0, tk.END)
        if archivo not in existing_items:
            custom_listbox.insert(tk.END, archivo)
        else:
            messagebox.showinfo("Información", f"'{archivo}' ya está en la lista.")

def eliminar_elemento(custom_listbox):
    """
    Elimina el elemento seleccionado de la lista personalizada.
    """
    selected_indices = custom_listbox.curselection()
    if not selected_indices:
        messagebox.showwarning("Advertencia", "Selecciona un elemento para eliminar.")
        return
    for index in reversed(selected_indices):
        custom_listbox.delete(index)

def mover_elemento(custom_listbox, direccion):
    """
    Mueve el elemento seleccionado en la lista personalizada hacia arriba o hacia abajo.
    :param custom_listbox: Listbox que contiene los elementos.
    :param direccion: -1 para subir, 1 para bajar.
    """
    seleccion = custom_listbox.curselection()
    if not seleccion:
        messagebox.showwarning("Advertencia", "Selecciona un elemento para mover.")
        return

    index = seleccion[0]
    nueva_pos = index + direccion

    if nueva_pos < 0 or nueva_pos >= custom_listbox.size():
        return  # No hacer nada si está en los límites

    # Obtener el texto del elemento seleccionado
    elemento = custom_listbox.get(index)

    # Eliminar el elemento de su posición actual
    custom_listbox.delete(index)

    # Insertar el elemento en la nueva posición
    custom_listbox.insert(nueva_pos, elemento)

    # Seleccionar el elemento nuevamente
    custom_listbox.select_set(nueva_pos)
    custom_listbox.activate(nueva_pos)

def generar_maplist_txt(entidades, script_dir, text_area):
    """
    Genera el archivo maplist.txt en el directorio raíz del script con la lista de mapas proporcionada.
    """
    maplist_path = os.path.join(script_dir, 'maplist.txt')

    # Definir el contenido fijo del maplist.txt
    header = (
        "; This maplist is NOT used at default.\n"
        "; The maximum amount of maps for maplist is 64.\n"
        "; If you want to start using it, type:\n"
        ";\n"
        ";       sv maplist maplist.ini [option]\n"
        ";       at the console.\n"
        ";\n"
        "; Where option = 0 (play maps in sequence) or \n"
        ";                1 (pick random maps).\n"
        ";\n"
        "; You can then use \"sv maplist start\"\n"
        ";\n"
        "; Use:\n"
        "; \"sv maplist help\" for a full list of available commands;\n"
        "; \"sv maplist next\" to move to next map;\n"
        "; \"sv maplist off\" to stop map rotations ;\n"
        "[maplist]\n"
    )

    footer = (
        "###\n"
        "; Make sure you have [maplist] at the beginning of the list and ### at the end.\n"
    )

    try:
        with open(maplist_path, 'w', encoding='utf-8') as file:
            file.write(header)
            for map_name in entidades:
                file.write(f"{map_name}\n")
            file.write(footer)

        # Informar al usuario
        text_area.insert(tk.END, f"Generado: {maplist_path}\n")
    except Exception as e:
        message = f"Error al generar maplist.txt: {e}"
        text_area.insert(tk.END, message + "\n")

def generar_server_cfg(entidades, script_dir, text_area):
    """
    Genera el archivo server.cfg en el directorio raíz del script con la configuración especificada,
    reemplazando la línea 'set sv_maplist' con la lista de mapas personalizada.
    """
    server_cfg_path = os.path.join(script_dir, 'server.cfg')

    # Crear la lista de mapas separados por espacios
    maplist_str = ' '.join(entidades)

    # Definir el contenido fijo del server.cfg con el maplist personalizado
    server_cfg_content = (
        'set game dday\n'
        'set gamedir dday\n'
        'set hostname "MR D-Day server by paranoid"\n'
        'set website "http://www.mr.cl" s\n'
        'set deathmatch 1\n'
        'set timelimit 0\n'
        'set maxclients 24\n'
        'set public 1\n'
        'setmaster master.q2servers.com satan.idsoftware.com q2master.planetquake.com\n'
        '//set password "mypass"\n'
        'set rcon_password "mrinvicto"\n'
        'set observer_password "sapo"\n'
        'sv maplist maplist.txt 0\n'
        'sv maplist start\n'
        'set RI 3\n'
        'set level_wait 5\n'
        'set team_kill 1\n'
        'set invuln_medic 0\n'
        'set death_msg 1\n'
        'set easter_egg 0\n'
        'set arty_delay 10\n'
        'set arty_time 60\n'
        'set arty_max 1\n'
        'set invuln_spawn 2\n'
        'set spawn_camp_check 1\n'
        'set spawn_camp_time 2\n'
        'set flood_msgs 10\n'
        'set flood_persecond 10\n'
        'set flood_waitdelay 10\n'
        f'set sv_maplist "{maplist_str}"\n'
        'map dust\n'
        'seta bots 1\n'
        'sv_allow_map 2\n'
        'set allow_download 1\n'
        'set exbattleinfo 5\n'
    )

    try:
        with open(server_cfg_path, 'w', encoding='utf-8') as file:
            file.write(server_cfg_content)

        # Informar al usuario
        text_area.insert(tk.END, f"Generado: {server_cfg_path}\n")
    except Exception as e:
        message = f"Error al generar server.cfg: {e}"
        text_area.insert(tk.END, message + "\n")

def generar_ents_modificados(custom_listbox, ents_dir, output_dir, text_area):
    """
    Genera nuevos archivos .ent con el campo 'nextmap' actualizado según la lista personalizada
    y crea un archivo maplist.txt y server.cfg en el directorio raíz del script.
    """
    entidades = custom_listbox.get(0, tk.END)
    if not entidades:
        messagebox.showwarning("Advertencia", "La lista personalizada está vacía.")
        return

    # Crear el directorio 'ents_modificados' si no existe
    os.makedirs(output_dir, exist_ok=True)

    # Obtener el directorio raíz del script (donde se encuentra el archivo Python)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    total = len(entidades)
    for i, entidad in enumerate(entidades):
        # Determinar el nuevo 'nextmap'
        nuevo_nextmap = entidades[(i + 1) % total]

        # Ruta del archivo .ent original
        ent_original_path = os.path.join(ents_dir, f"{entidad}.ent")
        if not os.path.isfile(ent_original_path):
            message = f"Archivo .ent no encontrado: {ent_original_path}"
            text_area.insert(tk.END, message + "\n")
            continue

        try:
            # Leer el contenido original
            with open(ent_original_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Definir una función para modificar o agregar 'nextmap' en los bloques correspondientes
            def modificar_nextmap(match):
                block_content = match.group(1)
                # Verificar si el bloque tiene 'classname' 'info_team_start'
                if '"classname" "info_team_start"' in block_content:
                    # Buscar si ya tiene 'nextmap'
                    if re.search(r'"nextmap"\s+"[^"]+"', block_content):
                        # Reemplazar el valor de 'nextmap'
                        block_content = re.sub(r'("nextmap"\s+")([^"]+)(")', f'\\1{nuevo_nextmap}\\3', block_content, count=1)
                    else:
                        # Agregar el campo 'nextmap' antes del cierre del bloque sin espacios adicionales
                        block_content = block_content.rstrip() + f'\n"nextmap" "{nuevo_nextmap}"'
                    # Asegurar que el cierre de la llave esté en una nueva línea
                    return f'{{{block_content}\n}}'
                else:
                    return match.group(0)  # No modificar bloques que no correspondan

            # Aplicar la modificación a todos los bloques
            nuevo_content = re.sub(r'\{([^}]*)\}', modificar_nextmap, content, flags=re.DOTALL)

            # Eliminar saltos de línea innecesarios: reemplazar múltiples saltos de línea por uno solo
            # Esto evita que se agreguen líneas en blanco extra
            nuevo_content = re.sub(r'\n\s*\n', '\n', nuevo_content)

            # Guardar el nuevo contenido en el directorio 'ents_modificados'
            ent_modificado_path = os.path.join(output_dir, f"{entidad}.ent")
            with open(ent_modificado_path, 'w', encoding='utf-8') as file:
                file.write(nuevo_content)

            # Informar al usuario
            text_area.insert(tk.END, f"Generado: {ent_modificado_path}\n")
        except Exception as e:
            message = f"Error al modificar {ent_original_path}: {e}"
            text_area.insert(tk.END, message + "\n")

    # Después de modificar los archivos .ent, generar maplist.txt y server.cfg
    generar_maplist_txt(entidades, script_dir, text_area)
    generar_server_cfg(entidades, script_dir, text_area)

    text_area.insert(tk.END, '-' * 60 + "\n")
    messagebox.showinfo("Completado", "Generación de entidades modificadas, maplist.txt y server.cfg completada.")

def actualizar_lista_entidades(treeview, maps_dir, ents_dir, text_area):
    """
    Actualiza la lista de entidades en la tercera pestaña.
    Lista todos los archivos .bsp en 'maps' y verifica si su correspondiente .ent existe en 'ents'.
    Muestra solo el nombre sin la extensión .ent y añade información adicional.
    """
    # Limpiar el Treeview
    for item in treeview.get_children():
        treeview.delete(item)

    # Listar todos los archivos .bsp en 'maps'
    bsp_files = [f for f in os.listdir(maps_dir) if f.lower().endswith('.bsp')]

    for bsp_file in bsp_files:
        base_name = os.path.splitext(bsp_file)[0]
        ent_filename = f"{base_name}.ent"
        ent_path = os.path.join(ents_dir, ent_filename)
        if os.path.isfile(ent_path):
            status = "Generado"
            # Extraer información adicional del archivo .ent
            nombre_del_mapa, nextmap_aliados, nextmap_nazis = parse_ent_file(ent_path)
        else:
            status = "No Generado"
            nombre_del_mapa = "N/A"
            nextmap_aliados = "N/A"
            nextmap_nazis = "N/A"
        # Insertar en el Treeview sin la extensión .ent
        treeview.insert('', 'end', values=(base_name, status, nombre_del_mapa, nextmap_aliados, nextmap_nazis))

    # Mostrar mensaje en el área de texto
    text_area.insert(tk.END, "Lista de entidades actualizada.\n")

def mover_elemento(custom_listbox, direccion):
    """
    Mueve el elemento seleccionado en la lista personalizada hacia arriba o hacia abajo.
    :param custom_listbox: Listbox que contiene los elementos.
    :param direccion: -1 para subir, 1 para bajar.
    """
    seleccion = custom_listbox.curselection()
    if not seleccion:
        messagebox.showwarning("Advertencia", "Selecciona un elemento para mover.")
        return

    index = seleccion[0]
    nueva_pos = index + direccion

    if nueva_pos < 0 or nueva_pos >= custom_listbox.size():
        return  # No hacer nada si está en los límites

    # Obtener el texto del elemento seleccionado
    elemento = custom_listbox.get(index)

    # Eliminar el elemento de su posición actual
    custom_listbox.delete(index)

    # Insertar el elemento en la nueva posición
    custom_listbox.insert(nueva_pos, elemento)

    # Seleccionar el elemento nuevamente
    custom_listbox.select_set(nueva_pos)
    custom_listbox.activate(nueva_pos)

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
        command=lambda: ejecutar_dump_batch(text_area_batch, treeview_entidades, maps_dir, ents_dir),
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
        command=lambda: ejecutar_dump_single(text_area_single, treeview_entidades, maps_dir, ents_dir),
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
        command=lambda: agregar_elemento(treeview_entidades, custom_listbox),
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
        command=lambda: eliminar_elemento(custom_listbox),
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
        command=lambda: mover_elemento(custom_listbox, -1),
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
        command=lambda: mover_elemento(custom_listbox, 1),
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
        command=lambda: generar_ents_modificados(custom_listbox, ents_dir, os.path.join(script_dir, 'ents_modificados'), text_area_view),
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
    actualizar_lista_entidades(treeview_entidades, maps_dir, ents_dir, text_area_view)

    ventana.mainloop()

def agregar_elemento(treeview, custom_listbox):
    """
    Agrega el elemento seleccionado en el Treeview a la lista personalizada.
    """
    selected_item = treeview.selection()
    if not selected_item:
        messagebox.showwarning("Advertencia", "Selecciona una entidad para agregar.")
        return
    for item in selected_item:
        valores = treeview.item(item, 'values')
        archivo = valores[0]
        # Evitar duplicados
        existing_items = custom_listbox.get(0, tk.END)
        if archivo not in existing_items:
            custom_listbox.insert(tk.END, archivo)
        else:
            messagebox.showinfo("Información", f"'{archivo}' ya está en la lista.")

def eliminar_elemento(custom_listbox):
    """
    Elimina el elemento seleccionado de la lista personalizada.
    """
    selected_indices = custom_listbox.curselection()
    if not selected_indices:
        messagebox.showwarning("Advertencia", "Selecciona un elemento para eliminar.")
        return
    for index in reversed(selected_indices):
        custom_listbox.delete(index)

def mover_elemento(custom_listbox, direccion):
    """
    Mueve el elemento seleccionado en la lista personalizada hacia arriba o hacia abajo.
    :param custom_listbox: Listbox que contiene los elementos.
    :param direccion: -1 para subir, 1 para bajar.
    """
    seleccion = custom_listbox.curselection()
    if not seleccion:
        messagebox.showwarning("Advertencia", "Selecciona un elemento para mover.")
        return

    index = seleccion[0]
    nueva_pos = index + direccion

    if nueva_pos < 0 or nueva_pos >= custom_listbox.size():
        return  # No hacer nada si está en los límites

    # Obtener el texto del elemento seleccionado
    elemento = custom_listbox.get(index)

    # Eliminar el elemento de su posición actual
    custom_listbox.delete(index)

    # Insertar el elemento en la nueva posición
    custom_listbox.insert(nueva_pos, elemento)

    # Seleccionar el elemento nuevamente
    custom_listbox.select_set(nueva_pos)
    custom_listbox.activate(nueva_pos)

def generar_maplist_txt(entidades, script_dir, text_area):
    """
    Genera el archivo maplist.txt en el directorio raíz del script con la lista de mapas proporcionada.
    """
    maplist_path = os.path.join(script_dir, 'maplist.txt')

    # Definir el contenido fijo del maplist.txt
    header = (
        "; This maplist is NOT used at default.\n"
        "; The maximum amount of maps for maplist is 64.\n"
        "; If you want to start using it, type:\n"
        ";\n"
        ";       sv maplist maplist.ini [option]\n"
        ";       at the console.\n"
        ";\n"
        "; Where option = 0 (play maps in sequence) or \n"
        ";                1 (pick random maps).\n"
        ";\n"
        "; You can then use \"sv maplist start\"\n"
        ";\n"
        "; Use:\n"
        "; \"sv maplist help\" for a full list of available commands;\n"
        "; \"sv maplist next\" to move to next map;\n"
        "; \"sv maplist off\" to stop map rotations ;\n"
        "[maplist]\n"
    )

    footer = (
        "###\n"
        "; Make sure you have [maplist] at the beginning of the list and ### at the end.\n"
    )

    try:
        with open(maplist_path, 'w', encoding='utf-8') as file:
            file.write(header)
            for map_name in entidades:
                file.write(f"{map_name}\n")
            file.write(footer)

        # Informar al usuario
        text_area.insert(tk.END, f"Generado: {maplist_path}\n")
    except Exception as e:
        message = f"Error al generar maplist.txt: {e}"
        text_area.insert(tk.END, message + "\n")

def generar_server_cfg(entidades, script_dir, text_area):
    """
    Genera el archivo server.cfg en el directorio raíz del script con la configuración especificada,
    reemplazando la línea 'set sv_maplist' con la lista de mapas personalizada.
    """
    server_cfg_path = os.path.join(script_dir, 'server.cfg')

    # Crear la lista de mapas separados por espacios
    maplist_str = ' '.join(entidades)

    # Definir el contenido fijo del server.cfg con el maplist personalizado
    server_cfg_content = (
        'set game dday\n'
        'set gamedir dday\n'
        'set hostname "MR D-Day server by paranoid"\n'
        'set website "http://www.mr.cl" s\n'
        'set deathmatch 1\n'
        'set timelimit 0\n'
        'set maxclients 24\n'
        'set public 1\n'
        'setmaster master.q2servers.com satan.idsoftware.com q2master.planetquake.com\n'
        '//set password "mypass"\n'
        'set rcon_password "mrinvicto"\n'
        'set observer_password "sapo"\n'
        'sv maplist maplist.txt 0\n'
        'sv maplist start\n'
        'set RI 3\n'
        'set level_wait 5\n'
        'set team_kill 1\n'
        'set invuln_medic 0\n'
        'set death_msg 1\n'
        'set easter_egg 0\n'
        'set arty_delay 10\n'
        'set arty_time 60\n'
        'set arty_max 1\n'
        'set invuln_spawn 2\n'
        'set spawn_camp_check 1\n'
        'set spawn_camp_time 2\n'
        'set flood_msgs 10\n'
        'set flood_persecond 10\n'
        'set flood_waitdelay 10\n'
        f'set sv_maplist "{maplist_str}"\n'
        'map dust\n'
        'seta bots 1\n'
        'sv_allow_map 2\n'
        'set allow_download 1\n'
        'set exbattleinfo 5\n'
    )

    try:
        with open(server_cfg_path, 'w', encoding='utf-8') as file:
            file.write(server_cfg_content)

        # Informar al usuario
        text_area.insert(tk.END, f"Generado: {server_cfg_path}\n")
    except Exception as e:
        message = f"Error al generar server.cfg: {e}"
        text_area.insert(tk.END, message + "\n")

def generar_ents_modificados(custom_listbox, ents_dir, output_dir, text_area):
    """
    Genera nuevos archivos .ent con el campo 'nextmap' actualizado según la lista personalizada
    y crea un archivo maplist.txt y server.cfg en el directorio raíz del script.
    """
    entidades = custom_listbox.get(0, tk.END)
    if not entidades:
        messagebox.showwarning("Advertencia", "La lista personalizada está vacía.")
        return

    # Crear el directorio 'ents_modificados' si no existe
    os.makedirs(output_dir, exist_ok=True)

    # Obtener el directorio raíz del script (donde se encuentra el archivo Python)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    total = len(entidades)
    for i, entidad in enumerate(entidades):
        # Determinar el nuevo 'nextmap'
        nuevo_nextmap = entidades[(i + 1) % total]

        # Ruta del archivo .ent original
        ent_original_path = os.path.join(ents_dir, f"{entidad}.ent")
        if not os.path.isfile(ent_original_path):
            message = f"Archivo .ent no encontrado: {ent_original_path}"
            text_area.insert(tk.END, message + "\n")
            continue

        try:
            # Leer el contenido original
            with open(ent_original_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Definir una función para modificar o agregar 'nextmap' en los bloques correspondientes
            def modificar_nextmap(match):
                block_content = match.group(1)
                # Verificar si el bloque tiene 'classname' 'info_team_start'
                if '"classname" "info_team_start"' in block_content:
                    # Buscar si ya tiene 'nextmap'
                    if re.search(r'"nextmap"\s+"[^"]+"', block_content):
                        # Reemplazar el valor de 'nextmap'
                        block_content = re.sub(r'("nextmap"\s+")([^"]+)(")', f'\\1{nuevo_nextmap}\\3', block_content, count=1)
                    else:
                        # Agregar el campo 'nextmap' antes del cierre del bloque sin espacios adicionales
                        block_content = block_content.rstrip() + f'\n"nextmap" "{nuevo_nextmap}"'
                    # Asegurar que el cierre de la llave esté en una nueva línea
                    return f'{{{block_content}\n}}'
                else:
                    return match.group(0)  # No modificar bloques que no correspondan

            # Aplicar la modificación a todos los bloques
            nuevo_content = re.sub(r'\{([^}]*)\}', modificar_nextmap, content, flags=re.DOTALL)

            # Eliminar saltos de línea innecesarios: reemplazar múltiples saltos de línea por uno solo
            # Esto evita que se agreguen líneas en blanco extra
            nuevo_content = re.sub(r'\n\s*\n', '\n', nuevo_content)

            # Guardar el nuevo contenido en el directorio 'ents_modificados'
            ent_modificado_path = os.path.join(output_dir, f"{entidad}.ent")
            with open(ent_modificado_path, 'w', encoding='utf-8') as file:
                file.write(nuevo_content)

            # Informar al usuario
            text_area.insert(tk.END, f"Generado: {ent_modificado_path}\n")
        except Exception as e:
            message = f"Error al modificar {ent_original_path}: {e}"
            text_area.insert(tk.END, message + "\n")

    # Después de modificar los archivos .ent, generar maplist.txt y server.cfg
    generar_maplist_txt(entidades, script_dir, text_area)
    generar_server_cfg(entidades, script_dir, text_area)

    text_area.insert(tk.END, '-' * 60 + "\n")
    messagebox.showinfo("Completado", "Generación de entidades modificadas, maplist.txt y server.cfg completada.")

def actualizar_lista_entidades(treeview, maps_dir, ents_dir, text_area):
    """
    Actualiza la lista de entidades en la tercera pestaña.
    Lista todos los archivos .bsp en 'maps' y verifica si su correspondiente .ent existe en 'ents'.
    Muestra solo el nombre sin la extensión .ent y añade información adicional.
    """
    # Limpiar el Treeview
    for item in treeview.get_children():
        treeview.delete(item)

    # Listar todos los archivos .bsp en 'maps'
    bsp_files = [f for f in os.listdir(maps_dir) if f.lower().endswith('.bsp')]

    for bsp_file in bsp_files:
        base_name = os.path.splitext(bsp_file)[0]
        ent_filename = f"{base_name}.ent"
        ent_path = os.path.join(ents_dir, ent_filename)
        if os.path.isfile(ent_path):
            status = "Generado"
            # Extraer información adicional del archivo .ent
            nombre_del_mapa, nextmap_aliados, nextmap_nazis = parse_ent_file(ent_path)
        else:
            status = "No Generado"
            nombre_del_mapa = "N/A"
            nextmap_aliados = "N/A"
            nextmap_nazis = "N/A"
        # Insertar en el Treeview sin la extensión .ent
        treeview.insert('', 'end', values=(base_name, status, nombre_del_mapa, nextmap_aliados, nextmap_nazis))

    # Mostrar mensaje en el área de texto
    text_area.insert(tk.END, "Lista de entidades actualizada.\n")

if __name__ == "__main__":
    crear_interfaz()
