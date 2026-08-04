import asyncio
import websockets
import json
import os
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


# nombre PC -> cámaras
camera_lists = {}


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

        if (
            info.get("role") == "client"
            and info.get("name") == nombre
        ):

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
# NUEVO FIX
# ENVIAR RESPUESTA AL VIEWER CORRECTO
# ======================================================


async def enviar_a_viewer(websocket_viewer, mensaje):

    try:

        await websocket_viewer.send(mensaje)

    except Exception:

        pass



# ======================================================
# BUSCAR VIEWER QUE CONTROLA UNA PC
# ======================================================


def obtener_viewer_de_pc(nombre_pc):

    for viewer, pc in list(selecciones.items()):

        if pc == nombre_pc:

            return viewer

    return None



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



                prefijo = mensaje[:6]



                if prefijo == b"SCREEN":

                    await enviar_a_viewer_de_pc(
                        nombre,
                        mensaje
                    )



                elif prefijo == b"CAMERA":

                    await enviar_a_viewer_de_pc(
                        nombre,
                        mensaje
                    )



                # descarga de archivos
                                # descarga de archivos binarios

                elif prefijo == b"FILE_D":


                    viewer = obtener_viewer_de_pc(
                        nombre
                    )


                    if viewer:

                        await enviar_a_viewer(
                            viewer,
                            mensaje
                        )


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


                    nombre = datos.get(
                        "name",
                        "PC"
                    )



                    # eliminar duplicados


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



                            dispositivos.pop(
                                ws,
                                None
                            )



                    dispositivos[websocket] = {


                        "role": "client",


                        "name": nombre,


                        "screen_width":
                            datos.get(
                                "screen_width",
                                1920
                            ),


                        "screen_height":
                            datos.get(
                                "screen_height",
                                1080
                            ),

                    }



                    print(
                        "CLIENTE:",
                        nombre
                    )




                # ------------------------------
                # VIEWER
                # ------------------------------


                elif role == "viewer":


                    dispositivos[websocket] = {


                        "role": "viewer"

                    }


                    print(
                        "VIEWER conectado"
                    )



            # ==================================================
            # LISTA DISPOSITIVOS
            # ==================================================


            elif tipo == "list_devices":


                lista = []



                for ws, dispositivo in dispositivos.items():


                    if dispositivo.get("role") == "client":


                        lista.append(


                            {

                                "name":
                                    dispositivo.get(
                                        "name"
                                    ),


                                "status":
                                    "online"

                            }


                        )



                await enviar_json(
                    websocket,
                    {
                        "type":
                            "device_list",

                        "devices":
                            lista
                    }
                )



            # ==================================================
            # SELECCIONAR PC
            # ==================================================


            elif tipo == "select_device":


                nombre = datos.get("name")



                info = dispositivos.get(
                    websocket
                )



                if info and info.get("role") == "viewer":



                    anterior = selecciones.get(
                        websocket
                    )



                    if anterior and anterior != nombre:


                        await enviar_a_pc(
                            anterior,
                            json.dumps(
                                {
                                    "type":
                                        "stream_stop"
                                }
                            )
                        )



                    selecciones[websocket] = nombre



                    print(
                        "PC seleccionada:",
                        nombre
                    )



                    await enviar_a_pc(
                        nombre,
                        json.dumps(
                            {
                                "type":
                                    "stream_start"
                            }
                        )
                    )



                    if nombre in camera_lists:



                        await enviar_json(

                            websocket,

                            {

                                "type":
                                    "camera_list",

                                "cameras":
                                    camera_lists[nombre]

                            }

                        )



            # ==================================================
            # CAMARAS
            # ==================================================


            elif tipo == "camera_list":



                nombre = datos.get(
                    "device"
                )



                cams = datos.get(
                    "cameras",
                    []
                )



                camera_lists[nombre] = cams



                for viewer, pc in list(selecciones.items()):



                    if pc == nombre:


                        await enviar_json(

                            viewer,

                            {

                                "type":
                                    "camera_list",

                                "cameras":
                                    cams

                            }

                        )



            elif tipo == "set_camera":



                pc = selecciones.get(
                    websocket
                )



                if pc:



                    await enviar_a_pc(

                        pc,

                        json.dumps(

                            {

                                "type":
                                    "set_camera",

                                "camera":
                                    datos.get(
                                        "camera"
                                    )

                            }

                        )

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


                info_viewer = dispositivos.get(
                    websocket
                )



                if not info_viewer:

                    continue



                if info_viewer.get("role") != "viewer":

                    continue



                pc = selecciones.get(
                    websocket
                )



                if not pc:

                    continue



                comando = datos.copy()



                if tipo == "mouse_move":



                    info_pc = None



                    for ws, info in dispositivos.items():



                        if (
                            info.get("role") == "client"
                            and info.get("name") == pc
                        ):


                            info_pc = info

                            break



                    if info_pc:



                        ancho = info_pc.get(
                            "screen_width",
                            1920
                        )


                        alto = info_pc.get(
                            "screen_height",
                            1080
                        )



                        try:


                            x = float(
                                datos.get(
                                    "x",
                                    0
                                )
                            )


                            y = float(
                                datos.get(
                                    "y",
                                    0
                                )
                            )


                        except:


                            continue



                        x = max(
                            0.0,
                            min(
                                1.0,
                                x
                            )
                        )


                        y = max(
                            0.0,
                            min(
                                1.0,
                                y
                            )
                        )



                        comando["x"] = int(
                            x * ancho
                        )


                        comando["y"] = int(
                            y * alto
                        )



                await enviar_a_pc(

                    pc,

                    json.dumps(
                        comando
                    )

                )



                        # ==================================================
            # EXPLORADOR ARCHIVOS
            # ==================================================


            elif tipo in (
                "list_files",
                "explore_folder",
                "list_drives"
            ):



                pc = selecciones.get(
                    websocket
                )



                if not pc:

                    continue




                if tipo == "list_drives":


                    await enviar_a_pc(

                        pc,

                        json.dumps(

                            {

                                "type":
                                    "list_drives"

                            }

                        )

                    )




                else:


                    ruta = datos.get(
                        "path",
                        "C:\\"
                    )



                    await enviar_a_pc(

                        pc,

                        json.dumps(

                            {

                                "type":
                                    "explore_folder",

                                "path":
                                    ruta

                            }

                        )

                    )



            # ==================================================
            # NUEVO FIX
            # SOLICITUD DESCARGA ARCHIVO
            # ==================================================


            elif tipo == "download_file":



                pc = selecciones.get(
                    websocket
                )



                if not pc:

                    continue



                ruta = datos.get(
                    "path"
                )



                if ruta:



                    await enviar_a_pc(

                        pc,

                        json.dumps(

                            {

                                "type":
                                    "download_file",

                                "path":
                                    ruta

                            }

                        )

                    )



            # ==================================================
            # RESPUESTA LISTA ARCHIVOS
            # ==================================================


            elif tipo == "file_list":



                info = dispositivos.get(
                    websocket
                )



                if info:



                    nombre = info.get(
                        "name"
                    )



                    viewer = obtener_viewer_de_pc(
                        nombre
                    )



                    if viewer:



                        await enviar_a_viewer(

                            viewer,

                            json.dumps(

                                {

                                    "type":
                                        "file_list",

                                    "path":
                                        datos.get(
                                            "path",
                                            ""
                                        ),

                                    "items":
                                        datos.get(
                                            "items",
                                            []
                                        )

                                }

                            )

                        )


                        # ==================================================
            # TRANSFERENCIA ARCHIVOS JSON
            # ==================================================


            elif tipo in (
                "FILE_START",
                "FILE_END"
            ):



                info = dispositivos.get(
                    websocket
                )



                if info:


                    nombre = info.get(
                        "name"
                    )



                    viewer = obtener_viewer_de_pc(
                        nombre
                    )



                    if viewer:


                        await enviar_a_viewer(

                            viewer,

                            json.dumps(
                                datos
                            )

                        )
                        
            # ==================================================
            # ERROR ARCHIVOS
            # ==================================================


            elif tipo == "file_error":



                info = dispositivos.get(
                    websocket
                )



                if info:



                    nombre = info.get(
                        "name"
                    )



                    viewer = obtener_viewer_de_pc(
                        nombre
                    )



                    if viewer:



                        await enviar_a_viewer(

                            viewer,

                            json.dumps(

                                {

                                    "type":
                                        "file_error",

                                    "message":
                                        datos.get(
                                            "message",
                                            "Error desconocido"
                                        )

                                }

                            )

                        )



    except websockets.ConnectionClosed:


        pass



    except Exception as error:


        print(
            "[!] Error con cliente:",
            error
        )



    # ==================================================
    # LIMPIEZA
    # ==================================================


    pc_seleccionada = selecciones.pop(
        websocket,
        None
    )



    if pc_seleccionada:



        await enviar_a_pc(

            pc_seleccionada,

            json.dumps(

                {

                    "type":
                        "stream_stop"

                }

            )

        )



    info = dispositivos.pop(
        websocket,
        None
    )



    if info:



        nombre = info.get(
            "name"
        )



        if nombre:


            camera_lists.pop(
                nombre,
                None
            )



    print(
        "[-] Desconectado"
    )



# ======================================================
# MAIN
# ======================================================


async def main():


    port = int(
        os.environ.get(
            "PORT",
            8765
        )
    )



    print(
        "SERVIDOR REMOTEVIEW INICIADO",
        port
    )



    async with websockets.serve(

        manejar_cliente,

        "0.0.0.0",

        port,

        max_size=None

    ):


        await asyncio.Future()



print(
    "========== ANTES DE ARRANCAR WEBSOCKET =========="
)



asyncio.run(main())
