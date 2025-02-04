from tkinter import messagebox
import os
import tkinter as tk
import re

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
    primer_mapa = maplist_str.split()[0]
    rcon_password = 'password'

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
        f'set rcon_password "{rcon_password}"\n'
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
        f'map {primer_mapa}\n'
        'seta bots 0\n'
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