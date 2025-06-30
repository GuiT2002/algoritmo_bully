import socket
import threading
import time
import json
import argparse
from typing import Dict, Optional, Any

class Processo:
    def __init__(self, pid: int, porta: int, processos: Dict[int, tuple]):
        self.pid = pid
        self.porta = porta
        self.processos = processos
        self.host = '127.0.0.1'
        self.coordenador: Optional[int] = None
        self.em_eleicao = False
        self.lock = threading.RLock()

    def _log(self, mensagem: str):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[PID: {self.pid} | {timestamp}] {mensagem}")

    def iniciar(self):
        self._log(f"Processo iniciado na porta {self.porta}.")
        thread_servidor = threading.Thread(target=self.iniciar_servidor)
        thread_servidor.daemon = True
        thread_servidor.start()

        time.sleep(4)
        with self.lock:
            if self.coordenador is None:
                self.iniciar_eleicao()

        thread_monitor = threading.Thread(target=self.monitorar_coordenador)
        thread_monitor.daemon = True
        thread_monitor.start()

    def iniciar_servidor(self):
        servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor_socket.bind((self.host, self.porta))
        servidor_socket.listen(5)
        self._log(f"Servidor escutando em {self.host}:{self.porta}")
        while True:
            cliente_socket, _ = servidor_socket.accept()
            thread_cliente = threading.Thread(target=self.lidar_com_cliente, args=(cliente_socket,))
            thread_cliente.daemon = True
            thread_cliente.start()

    def lidar_com_cliente(self, cliente_socket: socket.socket):
        try:
            dados = cliente_socket.recv(1024)
            if not dados: return

            mensagem = json.loads(dados.decode())
            tipo_msg = mensagem.get('tipo')

            if tipo_msg == 'ELEICAO':
                remetente_pid = mensagem.get('remetente_pid')
                
                # <--- MUDANÇA CRÍTICA: Lógica de defesa do Coordenador
                with self.lock:
                    # Se eu sou o coordenador, eu anulo a eleição imediatamente.
                    if self.pid == self.coordenador:
                        self._log(f"Já sou o coordenador. Rejeitando eleição iniciada por {remetente_pid}.")
                        resposta = {'tipo': 'COORDENADOR', 'coordenador_pid': self.pid, 'remetente_pid': self.pid}
                        cliente_socket.sendall(json.dumps(resposta).encode())
                        return

                # Se não sou o coordenador, sigo o fluxo normal do Bully.
                self._log(f"[RECV] Mensagem de ELEIÇÃO do processo {remetente_pid}")
                resposta = {'tipo': 'RESPOSTA', 'remetente_pid': self.pid}
                cliente_socket.sendall(json.dumps(resposta).encode())
                self.iniciar_eleicao()

            elif tipo_msg == 'COORDENADOR':
                self.lidar_com_coordenador(mensagem.get('coordenador_pid'))
            elif tipo_msg == 'HEARTBEAT':
                cliente_socket.sendall(json.dumps({'tipo': 'HEARTBEAT_ACK'}).encode())

        except (json.JSONDecodeError, ConnectionResetError) as e:
            self._log(f"Erro de conexão/JSON ao lidar com cliente: {e}")
        finally:
            cliente_socket.close()

    def lidar_com_coordenador(self, novo_coordenador_pid: int):
        with self.lock:
            if self.coordenador != novo_coordenador_pid:
                self.coordenador = novo_coordenador_pid
                self._log(f"[INFO] Novo coordenador definido: {self.coordenador}")
            self.em_eleicao = False

    def iniciar_eleicao(self):
        with self.lock:
            if self.em_eleicao:
                return
            self.em_eleicao = True
            self._log("Iniciando eleição...")

        try:
            processos_superiores = [pid for pid in self.processos if pid > self.pid]

            if not processos_superiores:
                self.anunciar_vitoria()
                return

            respostas = 0
            for pid in processos_superiores:
                self._log(f"[SEND] Mensagem de ELEICAO para o processo {pid}")
                resposta = self.enviar_mensagem(pid, {'tipo': 'ELEICAO', 'remetente_pid': self.pid})
                
                if resposta:
                    # <--- MUDANÇA CRÍTICA: Aceita a anulação da eleição por um coordenador
                    if resposta.get('tipo') == 'COORDENADOR':
                        self._log(f"Eleição anulada. Processo {resposta.get('coordenador_pid')} já é o coordenador.")
                        self.lidar_com_coordenador(resposta.get('coordenador_pid'))
                        return # Aborta a eleição imediatamente
                    
                    if resposta.get('tipo') == 'RESPOSTA':
                        self._log(f"[RECV] Mensagem de RESPOSTA (OK) do processo {pid}")
                        respostas += 1
            
            if respostas == 0:
                self.anunciar_vitoria()
            else:
                self._log("Processos superiores estão ativos. Aguardando anúncio do novo líder.")

        finally:
            with self.lock:
                self.em_eleicao = False

    def anunciar_vitoria(self):
        with self.lock:
            if self.coordenador == self.pid and not self.em_eleicao:
                return
            self._log("[INFO] Eleição vencida! Eu sou o novo coordenador.")
            self.coordenador = self.pid
        
        mensagem = {'tipo': 'COORDENADOR', 'remetente_pid': self.pid, 'coordenador_pid': self.pid}
        for pid in self.processos:
            if pid != self.pid:
                self._log(f"[SEND] Anunciando novo COORDENADOR para o processo {pid}")
                self.enviar_mensagem(pid, mensagem)

    def monitorar_coordenador(self):
        while True:
            time.sleep(10)
            with self.lock:
                if self.em_eleicao or self.coordenador == self.pid:
                    continue
                if self.coordenador is None:
                    self.iniciar_eleicao()
                    continue

            resposta = self.enviar_mensagem(self.coordenador, {'tipo': 'HEARTBEAT', 'remetente_pid': self.pid})
            if not resposta:
                self._log(f"Coordenador {self.coordenador} não respondeu. Disparando nova eleição.")
                self.iniciar_eleicao()

    def enviar_mensagem(self, destino_pid: int, mensagem: dict) -> Optional[Dict[str, Any]]:
        if destino_pid not in self.processos: return None
        host, porta = self.processos[destino_pid]
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((host, porta))
                s.sendall(json.dumps(mensagem).encode())
                
                # Coordenador não espera resposta, apenas envia
                if mensagem.get('tipo') == 'COORDENADOR':
                     return {'tipo': 'ACK'}

                dados = s.recv(1024)
                if dados:
                    return json.loads(dados.decode())
                return None # Conexão fechada sem resposta
        except (socket.timeout, ConnectionRefusedError):
            return None
        except (json.JSONDecodeError, ConnectionResetError):
            return None

def main():
    parser = argparse.ArgumentParser(description="Implementação do Algoritmo de Bully.")
    parser.add_argument("--pid", type=int, required=True, help="ID deste processo.")
    parser.add_argument("--porta", type=int, required=True, help="Porta deste processo.")
    parser.add_argument("--processos", type=str, required=True, nargs='+', 
                        help="Lista de todos os processos no formato pid:host:porta")
    
    args = parser.parse_args()
    mapa_processos = {int(p.split(':')[0]): (p.split(':')[1], int(p.split(':')[2])) for p in args.processos}

    processo = Processo(args.pid, args.porta, mapa_processos)
    processo.iniciar()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[PID: {args.pid}] Processo encerrado.")
            break

if __name__ == "__main__":
    main()