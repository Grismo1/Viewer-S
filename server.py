import asyncio
import websockets
import json
import os
import time
import functools

print = functools.partial(print, flush=True)


print("SERVER.PY CARGADO")


# ======================================================
# DATOS CONEXIONES
# ======================================================


# websocket -> información dispositivo
dispositivos = {}


# viewer websocket -> PC seleccionada
selecciones = {}


# estados streaming
streams_activos = {}
streams_viewer = {}


# nombre PC -> cámaras
camera_lists = {}


# buffers futuros
frames_actuales = {}
ultimo_envio_frame = {}


# ======================================================
# UTILIDADES
# ======================================================


async def enviar_json(ws, datos):

    try:

        await ws.send(json.dumps(datos))

    except Exception:

        pass


async def enviar_a_pc(nombre, mensaje):

    for ws, info in list(dispositivos.items()):

        if info.get("role") == "client" and info.get("name") == nombre:

            try:

                await ws.send(mensaje)

            except Exception:

                pass

            return


async def enviar_a_viewer_de_pc(nombre, mensaje):

    muertos = []

    for viewer, pc in list(selecciones.items()):

        if pc != nombre:
            continue

        try:

            await viewer.send(mensaje)

        except Exception:

            muertos.append(viewer)

    for viewer in muertos:

        selecciones.pop(viewer, None)
        dispositivos.pop(viewer, None)

        try:

            await viewer.close()

        except:

            pass


# ======================================================
# MANEJAR CLIENTES
# ======================================================


async def manejar_cliente(websocket):

    print("[+] NUEVA CONEXION")

    try:

        async for mensaje in websocket:

            # ==================================================
            # BINARIOS
            # ==================================================

            if isinstance(mensaje, bytes):

                info = dispositivos.get(websocket)

                if not info:

                    continue

                if info.get("role") != "client":

                    continue

                nombre = info.get("name")

                # identificar tipo de binario

                prefijo = mensaje[:6]

                # pantalla

                if prefijo == b"SCREEN":

                    await enviar_a_viewer_de_pc(nombre, mensaje)

                # cámara

                elif prefijo == b"CAMERA":

                    await enviar_a_viewer_de_pc(nombre, mensaje)

                # archivos futuros

                elif prefijo.startswith(b"FILE"):

                    await enviar_a_viewer_de_pc(nombre, mensaje)

                continue
                # ==================================================
            # JSON
            # ==================================================

            try:

                datos = json.loads(mensaje)

            except Exception:

                continue

            tipo = datos.get("type")

            # ==================================================
            # REGISTER
            # ==================================================

            if tipo == "register":

                print("REGISTER RECIBIDO:", datos)

                role = datos.get("role")

                # ------------------------------
                # CLIENTE REMOTO
                # ------------------------------

                if role == "client":

                    nombre = datos.get("name", "PC")

                    # eliminar duplicado

                    for ws, info in list(dispositivos.items()):

                        if (
                            info.get("role") == "client"
                            and info.get("name") == nombre
                            and ws != websocket
                        ):

                            try:

                                await ws.close()

                            except:

                                pass

                            dispositivos.pop(ws, None)

                    dispositivos[websocket] = {
                        "role": "client",
                        "name": nombre,
                        "screen_width": datos.get("screen_width", 1920),
                        "screen_height": datos.get("screen_height", 1080),
                    }

                    print("CLIENTE:", nombre)

                # ------------------------------
                # VIEWER
                # ------------------------------

                elif role == "viewer":

                    dispositivos[websocket] = {"role": "viewer"}

                    print("VIEWER conectado")

            # ==================================================
            # LISTA DISPOSITIVOS
            # ==================================================

            elif tipo == "list_devices":

                lista = []

                for ws, dispositivo in dispositivos.items():

                    if dispositivo.get("role") == "client":

                        lista.append(
                            {"name": dispositivo.get("name"), "status": "online"}
                        )

                await enviar_json(websocket, {"type": "device_list", "devices": lista})

            # ==================================================
            # SELECCIONAR PC
            # ==================================================

            elif tipo == "select_device":

                nombre = datos.get("name")

                info = dispositivos.get(websocket)

                if info and info.get("role") == "viewer":

                    anterior = selecciones.get(websocket)

                    if anterior and anterior != nombre:

                        await enviar_a_pc(anterior, json.dumps({"type": "stream_stop"}))

                    selecciones[websocket] = nombre

                    print("PC seleccionada:", nombre)

                    await enviar_a_pc(nombre, json.dumps({"type": "stream_start"}))

                    if nombre in camera_lists:

                        await enviar_json(
                            websocket,
                            {"type": "camera_list", "cameras": camera_lists[nombre]},
                        )

            # ==================================================
            # CAMARAS
            # ==================================================

            elif tipo == "camera_list":

                nombre = datos.get("device")

                cams = datos.get("cameras", [])

                camera_lists[nombre] = cams

                for viewer, pc in list(selecciones.items()):

                    if pc == nombre:

                        await enviar_json(
                            viewer, {"type": "camera_list", "cameras": cams}
                        )

            elif tipo == "set_camera":

                pc = selecciones.get(websocket)

                if pc:

                    await enviar_a_pc(
                        pc,
                        json.dumps(
                            {"type": "set_camera", "camera": datos.get("camera")}
                        ),
                    )
                    # ==================================================
            # CONTROL REMOTO
            # ==================================================

            elif tipo in (
                "mouse_move",
                "mouse_click",
                "mouse_double_click",
                "mouse_scroll",
                "key_press",
            ):

                info_viewer = dispositivos.get(websocket)

                if not info_viewer:

                    continue

                if info_viewer.get("role") != "viewer":

                    continue

                pc = selecciones.get(websocket)

                if not pc:

                    continue

                comando = datos.copy()

                if tipo == "mouse_move":

                    info_pc = None

                    for ws, info in dispositivos.items():

                        if info.get("role") == "client" and info.get("name") == pc:

                            info_pc = info

                            break

                    if info_pc:

                        ancho_pc = info_pc.get("screen_width", 1920)

                        alto_pc = info_pc.get("screen_height", 1080)

                        try:

                            x_rel = float(datos.get("x", 0))

                            y_rel = float(datos.get("y", 0))

                        except:

                            continue

                        x_rel = max(0.0, min(1.0, x_rel))

                        y_rel = max(0.0, min(1.0, y_rel))

                        comando["x"] = int(x_rel * ancho_pc)

                        comando["y"] = int(y_rel * alto_pc)

                await enviar_a_pc(pc, json.dumps(comando))

            # ==================================================
            # ARCHIVOS
            # ==================================================

            elif tipo == "list_files":

                pc = selecciones.get(websocket)

                if not pc:

                    continue

                ruta = datos.get("path", "C:\\")

                await enviar_a_pc(pc, json.dumps({"type": "list_files", "path": ruta}))

            # respuesta del cliente con lista archivos

            elif tipo == "file_list":

                nombre = None

                info = dispositivos.get(websocket)

                if info:

                    nombre = info.get("name")

                if nombre:

                    await enviar_a_viewer_de_pc(
                        nombre,
                        json.dumps(
                            {
                                "type": "file_list",
                                "path": datos.get("path", ""),
                                "items": datos.get("items", []),
                            }
                        ),
                    )

            # error archivos

            elif tipo == "file_error":

                nombre = None

                info = dispositivos.get(websocket)

                if info:

                    nombre = info.get("name")

                if nombre:

                    await enviar_a_viewer_de_pc(
                        nombre,
                        json.dumps(
                            {
                                "type": "file_error",
                                "message": datos.get("message", "Error desconocido"),
                            }
                        ),
                    )

    except websockets.ConnectionClosed:

        pass

    except Exception as error:

        print("[!] Error con cliente:", error)

    # ==================================================
    # LIMPIEZA DESCONEXION
    # ==================================================

    pc_seleccionada = selecciones.pop(websocket, None)

    if pc_seleccionada:

        await enviar_a_pc(pc_seleccionada, json.dumps({"type": "stream_stop"}))

    info = dispositivos.pop(websocket, None)

    if info:

        nombre = info.get("name")

        if nombre:

            camera_lists.pop(nombre, None)

    print("[-] Desconectado")


# ======================================================
# MAIN
# ======================================================


async def main():

    port = int(os.environ.get("PORT", 8765))

    print("SERVIDOR REMOTEVIEW INICIADO", port)

    async with websockets.serve(manejar_cliente, "0.0.0.0", port, max_size=None):

        await asyncio.Future()


print("========== ANTES DE ARRANCAR WEBSOCKET ==========")


asyncio.run(main())
