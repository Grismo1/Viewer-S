import asyncio
import websockets
import json
import os

clientes = set()

dispositivos = {}


async def manejar_cliente(websocket):

    clientes.add(websocket)

    print(f"[+] Cliente conectado")
    print(f"Conexiones activas: {len(clientes)}")

    try:

        async for mensaje in websocket:

            datos = json.loads(mensaje)
            print("MENSAJE:")
            print(datos)
            
            if datos["type"] == "register":

                if datos["role"] == "client":

                    dispositivos[websocket] = {
                        "role": "client",
                        "name": datos["name"]
                    }

                    print()
                    print("========== CLIENTE ==========")
                    print("Nombre:", datos["name"])
                    print("=============================")


                elif datos["role"] == "viewer":

                    dispositivos[websocket] = {
                        "role": "viewer"
                    }

                    print()
                    print("========== VIEWER ==========")
                    print("Viewer registrado")
                    print("=============================")



            elif datos["type"] == "screen":

                print(
                    "Recibida captura:",
                    len(datos["image"]),
                    "bytes"
                )

                mensaje = json.dumps({
                    "type": "screen",
                    "image": datos["image"]
                })


                for dispositivo, info in dispositivos.items():

                    if info["role"] == "viewer":

                        await dispositivo.send(mensaje)



            elif datos["type"] == "ping":

                info = dispositivos.get(websocket)

                if info:

                    if info["role"] == "client":
                        print(f"PING <- {info['name']}")

                    else:
                        print("PING <- VIEWER")



            elif datos["type"] == "list_devices":

                lista = []

                for dispositivo in dispositivos.values():

                    if dispositivo["role"] == "client":

                        lista.append({
                            "name": dispositivo["name"],
                            "status": "online"
                        })


                respuesta = {
                    "type": "device_list",
                    "devices": lista
                }

                await websocket.send(json.dumps(respuesta))


    except websockets.ConnectionClosed:
        pass


    finally:

        if websocket in dispositivos:
            del dispositivos[websocket]

        clientes.remove(websocket)

        print("[-] Cliente desconectado")
        print(f"Conexiones activas: {len(clientes)}")



async def main():

    print("===================================")
    print(" SERVIDOR REMOTEVIEW INICIADO ")
    print(" Puerto: 8765")
    print("===================================")
    
    PORT = int(os.environ.get("PORT", 8765))
     
    async with websockets.serve(
        manejar_cliente,
        "0.0.0.0",
        PORT
        
    ):

        await asyncio.Future()



asyncio.run(main())