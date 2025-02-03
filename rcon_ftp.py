import configparser
import re
import paramiko
import tkinter as tk
import os
import threading

def conectar_rcon(ip, puerto, usuario, contrasena, cuadro_estado):
    try:
        transport = paramiko.Transport((ip, int(puerto)))
        transport.connect(username=usuario, password=contrasena)
        client = transport.open_session()
        client.get_pty()
        client.invoke_shell()

        def recibir_datos():
            # Expresión regular para eliminar códigos ANSI
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            # Eliminar caracteres no imprimibles como \b y \r
            control_chars = re.compile(r'[\b\r]')

            while True:
                try:
                    datos = client.recv(1024).decode('utf-8')
                    if datos:
                        # Eliminar códigos ANSI y caracteres de control
                        texto_limpio = ansi_escape.sub('', datos)
                        texto_limpio = control_chars.sub('', texto_limpio)
                        cuadro_estado.insert(tk.END, texto_limpio)
                        cuadro_estado.see(tk.END)
                except Exception as e:
                    cuadro_estado.insert(tk.END, f"Error al recibir datos: {e}\n")
                    cuadro_estado.see(tk.END)
                    break

        threading.Thread(target=recibir_datos, daemon=True).start()

        # Enviar el comando inicial automáticamente
        client.sendall("screen -r 172293.q2server\n".encode('utf-8'))

        return client
    except Exception as e:
        cuadro_estado.insert(tk.END, f"Error al conectar al servidor SSH: {e}\n")
        cuadro_estado.see(tk.END)
        return None
    
def cargar_configuracion():
    config = configparser.ConfigParser()
    parametros = {
        "ip": "",
        "puerto": "",
        "usuario": "",
        "password": "",
        "ruta_principal": ""
    }

    # Determinar la ruta del archivo herramienta.ini relativa al script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "herramienta.ini")

    if os.path.exists(config_path):
        try:
            config.read(config_path)
            parametros.update({
                "ip": config.get("DEFAULT", "ip", fallback=""),
                "puerto": config.get("DEFAULT", "puerto", fallback=""),
                "usuario": config.get("DEFAULT", "usuario", fallback=""),
                "password": config.get("DEFAULT", "password", fallback=""),
                "ruta_principal": config.get("DEFAULT", "ruta_principal", fallback="")
            })
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
    else:
        print(f"Archivo {config_path} no encontrado.")

    return parametros

def subir_archivo_sftp(ip, puerto, usuario, contrasena, ruta, archivo, cuadro_estado):
    try:
        cuadro_estado.insert(tk.END, f"Conectando al servidor SFTP {ip}:{puerto}...\n")
        cuadro_estado.see(tk.END)
        try:
            transport = paramiko.Transport((ip, int(puerto)))
            transport.connect(username=usuario, password=contrasena)
            cuadro_estado.insert(tk.END, "Conexión y autenticación exitosa.\n")
        except Exception as e:
            cuadro_estado.insert(tk.END, f"Error al conectar o autenticar: {e}\n")
            cuadro_estado.see(tk.END)
            return f"Error al conectar o autenticar: {e}"

        sftp = paramiko.SFTPClient.from_transport(transport)

        try:
            cuadro_estado.insert(tk.END, f"Ruta actual antes del cambio: {sftp.getcwd()}\n")
            cuadro_estado.insert(tk.END, f"Cambiando al directorio: {ruta}...\n")
            cuadro_estado.see(tk.END)
            sftp.chdir(ruta)
            cuadro_estado.insert(tk.END, "Cambio de directorio exitoso.\n")
        except Exception as e:
            cuadro_estado.insert(tk.END, f"Error al cambiar de directorio: {e}\n")
            cuadro_estado.see(tk.END)
            transport.close()
            return f"Error al cambiar de directorio: {e}"

        try:
            cuadro_estado.insert(tk.END, f"Subiendo archivo: {archivo}...\n")
            cuadro_estado.see(tk.END)
            sftp.put(archivo, os.path.basename(archivo))
            cuadro_estado.insert(tk.END, "Archivo subido exitosamente.\n")
        except Exception as e:
            cuadro_estado.insert(tk.END, f"Error al subir el archivo: {e}\n")
            cuadro_estado.see(tk.END)
            transport.close()
            return f"Error al subir el archivo: {e}"

        transport.close()
        return f"Archivo '{archivo}' subido exitosamente a {ruta}."
    except Exception as e:
        cuadro_estado.insert(tk.END, f"Error inesperado: {e}\n")
        cuadro_estado.see(tk.END)
        return f"Error inesperado: {e}"

def subir_varios_archivos_sftp(ip, puerto, usuario, contrasena, base_ruta, cuadro_estado):
    try:
        cuadro_estado.insert(tk.END, f"Conectando al servidor SFTP {ip}:{puerto}...\n")
        cuadro_estado.see(tk.END)
        try:
            transport = paramiko.Transport((ip, int(puerto)))
            transport.connect(username=usuario, password=contrasena)
            cuadro_estado.insert(tk.END, "Conexión y autenticación exitosa.\n")
        except Exception as e:
            cuadro_estado.insert(tk.END, f"Error al conectar o autenticar: {e}\n")
            cuadro_estado.see(tk.END)
            return f"Error al conectar o autenticar: {e}"

        sftp = paramiko.SFTPClient.from_transport(transport)

        try:
            cuadro_estado.insert(tk.END, f"Cambiando al directorio base: {base_ruta}...\n")
            sftp.chdir(base_ruta)
            cuadro_estado.insert(tk.END, "Cambio de directorio exitoso.\n")
        except FileNotFoundError:
            cuadro_estado.insert(tk.END, f"Directorio no encontrado en el servidor, creando: {base_ruta}...\n")
            sftp.mkdir(base_ruta)
            sftp.chdir(base_ruta)

        # Subir maplist.txt y server.cfg
        script_dir = os.path.dirname(os.path.abspath(__file__))
        archivos_a_subir = [
            os.path.join(script_dir, "maplist.txt"),
            os.path.join(script_dir, "server.cfg")
        ]

        for archivo in archivos_a_subir:
            try:
                cuadro_estado.insert(tk.END, f"Subiendo archivo: {archivo}...\n")
                sftp.put(archivo, os.path.basename(archivo))
                cuadro_estado.insert(tk.END, f"Archivo {os.path.basename(archivo)} subido exitosamente.\n")
            except Exception as e:
                cuadro_estado.insert(tk.END, f"Error al subir {os.path.basename(archivo)}: {e}\n")

        # Subir todos los archivos en ./ents_modificados al directorio 'ents'
        ents_local_dir = os.path.join(script_dir, "ents_modificados")
        ents_remote_dir = "ents"
        try:
            cuadro_estado.insert(tk.END, f"Cambiando al directorio remoto: {ents_remote_dir}...\n")
            sftp.chdir(ents_remote_dir)
        except FileNotFoundError:
            cuadro_estado.insert(tk.END, f"Directorio remoto no encontrado, creando: {ents_remote_dir}...\n")
            sftp.mkdir(ents_remote_dir)
            sftp.chdir(ents_remote_dir)

        for root, _, files in os.walk(ents_local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                cuadro_estado.insert(tk.END, f"Subiendo archivo: {local_path}...\n")
                sftp.put(local_path, file)
                cuadro_estado.insert(tk.END, f"Archivo {file} subido exitosamente.\n")

        transport.close()
        cuadro_estado.insert(tk.END, "Todos los archivos se subieron exitosamente.\n")
    except Exception as e:
        cuadro_estado.insert(tk.END, f"Error inesperado: {e}\n")
        cuadro_estado.see(tk.END)