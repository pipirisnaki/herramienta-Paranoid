import os
import tkinter as tk
from tkinter import messagebox
import struct
import re
from tkinter import filedialog

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