#!/usr/bin/env python3

import os
import time
import requests
import logging
from dotenv import load_dotenv
from colorama import init, Fore
from transmission_rpc import Client

# Inicializar colorama
init()

# Cargar variables de entorno
load_dotenv()

# Configurar logging
if os.getenv('DEBUG_MODE') == '1':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    # Configurar también logging para requests en modo no debug
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

class CustomLogger:
    @staticmethod
    def error(message):
        print(f"{Fore.RED}{message}{Fore.RESET}")
        logging.error(message)

    @staticmethod
    def warning(message):
        print(f"{Fore.YELLOW}{message}{Fore.RESET}")
        logging.warning(message)

    @staticmethod
    def debug(message):
        if os.getenv('DEBUG_MODE') == '1':
            print(f"{Fore.GREEN}{message}{Fore.RESET}")
        logging.debug(message)

    @staticmethod
    def info(message):
        print(message)
        logging.info(message)

logger = CustomLogger()

class TorrentController:
    def __init__(self):
        self.client_type = os.getenv('CLIENTE_TORRENT', '').lower()
        self.host = os.getenv('CLIENTE_TORRENT_IP')
        self.port = os.getenv('CLIENTE_TORRENT_PORT')
        self.username = os.getenv('CLIENTE_TORRENT_USER')
        self.password = os.getenv('CLIENTE_TORRENT_PASSWORD')
        self.session = None

    def connect(self):
        if self.client_type == 'qbittorrent':
            return self._connect_qbittorrent()
        elif self.client_type == 'transmission':
            return self._connect_transmission()
        else:
            raise ValueError("Cliente de torrent no soportado")

    def _connect_qbittorrent(self):
        try:
            self.session = requests.Session()
            login_url = f"http://{self.host}:{self.port}/api/v2/auth/login"
            logger.debug(f"Intentando conectar a qBittorrent en {login_url}")
            response = self.session.post(
                login_url,
                data={'username': self.username, 'password': self.password}
            )
            if response.status_code == 200:
                logger.info("Conectado a qBittorrent exitosamente")
                return True
            else:
                logger.error(f"Error al conectar con qBittorrent. Código de estado: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error de conexión con qBittorrent: {str(e)}")
            return False

    def _connect_transmission(self):
        try:
            logger.debug(f"Intentando conectar a Transmission en {self.host}:{self.port}")
            self.session = Client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password
            )
            logger.info("Conectado a Transmission exitosamente")
            return True
        except Exception as e:
            logger.error(f"Error de conexión con Transmission: {str(e)}")
            return False

    def toggle_speed_limit(self, enable=True):
        logger.debug(f"Intentando {'activar' if enable else 'desactivar'} límite de velocidad")
        if self.client_type == 'qbittorrent':
            return self._toggle_qbittorrent_speed_limit(enable)
        elif self.client_type == 'transmission':
            return self._toggle_transmission_speed_limit(enable)

    def _toggle_qbittorrent_speed_limit(self, enable):
        try:
            url = f"http://{self.host}:{self.port}/api/v2/transfer/speedLimitsMode"
            current_mode = self.session.get(
                f"http://{self.host}:{self.port}/api/v2/transfer/speedLimitsMode"
            ).json()
            logger.debug(f"Estado actual del límite de velocidad: {current_mode}")
            
            if (enable and not current_mode) or (not enable and current_mode):
                toggle_url = f"http://{self.host}:{self.port}/api/v2/transfer/toggleSpeedLimitsMode"
                logger.debug(f"Cambiando límite de velocidad usando {toggle_url}")
                response = self.session.post(toggle_url)
                if response.status_code == 200:
                    logger.info(f"Límite de velocidad {'activado' if enable else 'desactivado'}")
                    return True
            return True
        except Exception as e:
            logger.error(f"Error al cambiar límite de velocidad en qBittorrent: {str(e)}")
            return False

    def _toggle_transmission_speed_limit(self, enable):
        try:
            logger.info(f"Cambiando límite de velocidad en Transmission a: {'activado' if enable else 'desactivado'}")
            
            # Obtener la sesión actual y sus campos
            session = self.session.get_session()
            
            # Cambiar la velocidad alternativa
            self.session.set_session(
                alt_speed_enabled=enable,
                alt_speed_down=1000,  # 1000 KB/s cuando está limitado
                alt_speed_up=100      # 100 KB/s cuando está limitado
            )
            
            # Verificar que el cambio se realizó correctamente
            new_session = self.session.get_session()
            logger.debug(f"Nueva configuración de la sesión aplicada")
            
            return True
        except Exception as e:
            logger.error(f"Error al cambiar límite de velocidad en Transmission: {str(e)}")
            return False

class TautulliMonitor:
    def __init__(self):
        self.api_key = os.getenv('TAUTULLI_API_KEY')
        self.host = os.getenv('TAUTULLI_IP')
        self.port = os.getenv('TAUTULLI_PORT')
        logger.debug(f"Inicializando monitor de Tautulli en {self.host}:{self.port}")

    def check_active_streams(self):
        try:
            url = f"http://{self.host}:{self.port}/api/v2"
            params = {
                'apikey': self.api_key,
                'cmd': 'get_activity'
            }
            logger.debug("Consultando actividad en Tautulli")
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                stream_count = int(data.get('response', {}).get('data', {}).get('stream_count', 0))
                logger.debug(f"Número de streams activos: {stream_count}")
                return stream_count > 0
            return False
        except Exception as e:
            logger.error(f"Error al verificar streams en Tautulli: {str(e)}")
            return False

def main():
    wait_time = int(os.getenv('WAIT_TIME', 10))
    wait_check = int(os.getenv('WAIT_CHECK', 20))
    
    torrent_controller = TorrentController()
    tautulli_monitor = TautulliMonitor()
    
    if not torrent_controller.connect():
        return

    last_active = False
    no_stream_time = 0

    while True:
        try:
            current_active = tautulli_monitor.check_active_streams()
            
            if current_active and not last_active:
                logger.info("Detectada reproducción activa")
                torrent_controller.toggle_speed_limit(True)
                no_stream_time = 0
            elif not current_active and last_active:
                no_stream_time = time.time()
            elif not current_active and no_stream_time > 0:
                if time.time() - no_stream_time >= wait_time:
                    logger.info("No hay reproducciones activas")
                    torrent_controller.toggle_speed_limit(False)
                    no_stream_time = 0
            
            last_active = current_active
            time.sleep(wait_check)
            
        except KeyboardInterrupt:
            logger.info("Deteniendo el script...")
            break
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            time.sleep(wait_check)

if __name__ == "__main__":
    main()
