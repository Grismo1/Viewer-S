import asyncio
import websockets
import json
import os
import time


# websocket -> información del dispositivo
dispositivos = {}


# viewer websocket -> PC seleccionada
selecciones = {}


# nombre PC -> cámaras
camera_lists = {}
frames_actuales = {}
ultimo_envio_frame = {}




async def enviar_json(ws, datos):

    try:

        await ws.send(
            json.dumps(datos)
        )

    except:

        pass







async def enviar_a_pc(nombre, mensaje):


    for ws, info in list(dispositivos.items()):


        if (
            info.get("role") == "client"
            and info.get("name") == nombre
        ):


            try:

                await ws.send(
                    mensaje
                )

            except:

                pass


            return







async def manejar_cliente(websocket):


    print(
        "[+] Cliente conectado"
    )



    try:


        async for mensaje in websocket:





                        # ==================================================
            # FRAMES BINARIOS
            # ==================================================

            if isinstance(mensaje, bytes):

                info = dispositivos.get(
                    websocket
                )


                if not info:

                    continue


                if info.get("role") != "client":

                    continue


                nombre = info.get(
                    "name"
                )


                for viewer, pc in list(selecciones.items()):

                    if pc == nombre:

                        try:

                            asyncio.create_task(
                                viewer.send(mensaje)
                            )


                        except Exception:

                            pass


                continue            # ==================================================
            # JSON
            # ==================================================


            try:


                datos = json.loads(
                    mensaje
                )


            except:


                continue




            tipo = datos.get(
                "type"
            )









            # ==================================================
            # REGISTER
            # ==================================================


            if tipo == "register":



                role = datos.get(
                    "role"
                )






                if role == "client":



                    nombre = datos.get(
                        "name",
                        "PC"
                    )






                    # eliminar duplicado


                    for ws, info in list(
                        dispositivos.items()
                    ):



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



                        "role":
                            "client",



                        "name":
                            nombre,



                        "screen_width":
                            datos.get(
                                "screen_width",
                                1920
                            ),



                        "screen_height":
                            datos.get(
                                "screen_height",
                                1080
                            )

                    }




                    print(
                        "CLIENTE:",
                        nombre
                    )









                elif role == "viewer":




                    dispositivos[websocket] = {


                        "role":
                            "viewer"

                    }



                    print(
                        "VIEWER conectado"
                    )














            # ==================================================
            # LISTA DISPOSITIVOS
            # ==================================================


            elif tipo == "list_devices":




                lista = []




                for info in dispositivos.values():



                    if info.get("role") == "client":



                        lista.append({


                            "name":
                                info["name"],


                            "status":
                                "online"


                        })






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




                nombre = datos.get(
                    "name"
                )



                info = dispositivos.get(
                    websocket
                )



                if info and info.get("role") == "viewer":




                    selecciones[websocket] = nombre





                    print(

                        "PC seleccionada:",

                        nombre

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





                for viewer, pc in list(
                    selecciones.items()
                ):



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



                        json.dumps({


                            "type":
                                "set_camera",



                            "camera":
                                datos.get(
                                    "camera"
                                )


                        })



                    )









            # ==================================================
            # CONTROL REMOTO
            # ==================================================


            elif tipo in [


                "mouse_move",

                "mouse_click",

                "mouse_scroll",

                "key_press"


            ]:





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






                # ==============================
                # MOUSE RELATIVO
                # ==============================


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


                             ancho_pc = info_pc.get(
                            "screen_width",
                              1920
                         )


                             alto_pc = info_pc.get(
                             "screen_height",
                              1080
                         )


                             x_rel = datos.get(
                              "x",
                               0
                          )


                             y_rel = datos.get(
            "y",
            0
        )


        ancho_viewer = datos.get(
            "viewer_width",
            1
        )


        alto_viewer = datos.get(
            "viewer_height",
            1
        )


        comando["x"] = int(
            x_rel *
            ancho_pc
            /
            ancho_viewer
        )


        comando["y"] = int(
            y_rel *
            alto_pc
            /
            alto_viewer
        )







        await enviar_a_pc(



                    pc,



                    json.dumps(
                        comando
                    )


                )








    except websockets.ConnectionClosed:


        pass



    except Exception as e:


        print(
            "Error:",
            e
        )







    finally:



        info = dispositivos.pop(
            websocket,
            None
        )



        selecciones.pop(
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









asyncio.run(
    main()
)