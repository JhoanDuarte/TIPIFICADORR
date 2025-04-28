# tunnel.py
from pyngrok import ngrok

# Abre túnel HTTP apuntando al puerto 1010
http_tunnel = ngrok.connect(1010, "http")
print("Public URL:", http_tunnel.public_url)

# Mantiene el túnel abierto hasta que pares el script
input("Presiona Enter para cerrar el túnel...\n")
