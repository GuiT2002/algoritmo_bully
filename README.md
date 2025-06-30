# Algoritmo de Eleição - Algoritmo de Bully

1. Proposta do Trabalho
Este projeto consiste na implementação em Python do Algoritmo de Bully. O objetivo é simular um sistema distribuído onde múltiplos processos independentes podem se comunicar e, na ausência de um líder (coordenador), são capazes de eleger um novo de forma autônoma. O critério de eleição é o Identificador de Processo (PID), onde o processo com o maior PID assume a liderança.

O sistema demonstra conceitos de descoberta de falhas (via heartbeat), comunicação entre processos (via sockets) e tomada de decisão descentralizada.

2. Arquitetura
A arquitetura do sistema é descentralizada (peer-to-peer). Não existe uma entidade central que gerencia o estado ou a comunicação. Cada processo na rede é um nó autônomo e igualitário.

Embora a arquitetura seja descentralizada, cada processo individualmente opera com um modelo dual:

Servidor: Cada processo possui uma thread que escuta continuamente em uma porta TCP específica, aguardando mensagens de outros processos.

Cliente: Para se comunicar, um processo atua como cliente, estabelecendo conexões com os servidores dos outros processos para enviar mensagens.

3. Requisitos Funcionais e Protocolo de Mensagens
Requisitos de um Processo
Identificação: Cada processo é unicamente identificado por um ID de processo (pid) inteiro.

Descoberta de Falha: Cada processo monitora a saúde do coordenador atual através de mensagens de HEARTBEAT. Se o coordenador não responder, o processo assume uma falha.

Início de Eleição: Um processo inicia uma eleição se descobre que o coordenador falhou ou se, ao entrar na rede, não conhece nenhum coordenador.

Participação em Eleição: Um processo deve ser capaz de responder a mensagens de eleição e, se tiver um pid maior, iniciar sua própria eleição.

Liderança: Um processo deve ser capaz de se declarar o novo coordenador se vencer uma eleição e notificar todos os outros processos.

Protocolo de Mensagens
As mensagens são trocadas no formato JSON via TCP. Os seguintes tipos de mensagens são utilizados:

Tipo da Mensagem

Descrição

ELEICAO

Enviada por um processo para todos os processos com pid maior que o seu, para iniciar uma eleição.

RESPOSTA

Resposta a uma mensagem de ELEICAO, enviada por um processo de pid maior para indicar que está ativo.

COORDENADOR

Mensagem de broadcast enviada pelo vencedor da eleição para anunciar a todos que é o novo líder.

HEARTBEAT

Enviada periodicamente para o coordenador para verificar se ele ainda está ativo.


Exportar para as Planilhas
4. Comunicação entre Processos
A comunicação é realizada via Sockets TCP/IP sobre a interface de loopback (127.0.0.1).

Cada instância do processo processo.py abre um socket de servidor em uma porta única para receber conexões. A troca de mensagens é concorrente, utilizando threads para que o recebimento de uma mensagem não bloqueie a lógica principal do processo.

Diagrama de Sequência: Falha do Líder e Nova Eleição
O diagrama abaixo ilustra o fluxo de comunicação quando o Processo 1 detecta uma falha no Coordenador (Processo 4) e uma nova eleição é realizada, resultando na vitória do Processo 3.

Participantes: P1, P2, P3 (Novo Líder), P4 (Líder Antigo - Falha)

1. P1 --> P4: Envia HEARTBEAT.
2. P4 --x P1: Sem resposta (timeout).
3. P1: Detecta falha do líder e inicia eleição.
4. P1 --> P2: Envia mensagem ELEICAO.
5. P2 --> P1: Envia mensagem RESPOSTA (OK).
6. P2: Inicia sua própria eleição.
7. P2 --> P3: Envia mensagem ELEICAO.
8. P2 --> P4: Envia mensagem ELEICAO (falha).
9. P1 --> P3: Envia mensagem ELEICAO.
10. P3 --> P2: Envia mensagem RESPOSTA (OK).
11. P3 --> P1: Envia mensagem RESPOSTA (OK).
12. P3: Inicia sua própria eleição.
13. P3 --> P4: Envia mensagem ELEICAO (falha).
14. P3: Não recebe RESPOSTA de PIDs maiores. Declara-se vencedor.
15. P3 --> P1: Envia mensagem COORDENADOR.
16. P3 --> P2: Envia mensagem COORDENADOR.
5. Descrição do Serviço e Execução
O serviço é implementado integralmente no script processo.py. Para simular o sistema distribuído, múltiplas instâncias deste script são executadas, cada uma representando um nó.

Como Executar
Abra um terminal para cada processo que deseja simular.

Utilize o seguinte comando para iniciar cada processo, substituindo os valores apropriados. A lista de --processos deve ser idêntica para todas as instâncias.

Bash

python processo.py --pid <ID_DO_PROCESSO> --porta <PORTA_DO_PROCESSO> --processos <LISTA_DE_TODOS_OS_PROCESSOS>
Exemplo com 3 processos:
Terminal 1:

Bash

python processo.py --pid 1 --porta 5001 --processos 1:127.0.0.1:5001 2:127.0.0.1:5002 3:127.0.0.1:5003
Terminal 2:

Bash

python processo.py --pid 2 --porta 5002 --processos 1:127.0.0.1:5001 2:127.0.0.1:5002 3:127.0.0.1:5003
Terminal 3:

Bash

python processo.py --pid 3 --porta 5003 --processos 1:127.0.0.1:5001 2:127.0.0.1:5002 3:127.0.0.1:5003
6. Demonstrações de Código
Definição e Inicialização dos Processos
O main do script utiliza argparse para receber os parâmetros do processo e de toda a rede, inicializando uma instância da classe Processo.

Python

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
Envio de Mensagens
A função enviar_mensagem encapsula a lógica de cliente: criar um socket, conectar-se a um par, serializar e enviar a mensagem em JSON, e aguardar uma resposta.

Python

def enviar_mensagem(self, destino_pid: int, mensagem: dict) -> Optional[Dict[str, Any]]:
    if destino_pid not in self.processos: return None
    host, porta = self.processos[destino_pid]
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((host, porta))
            s.sendall(json.dumps(mensagem).encode())
            
            if mensagem.get('tipo') in ['ELEICAO', 'HEARTBEAT']:
                dados = s.recv(1024)
                if dados:
                    return json.loads(dados.decode())
            return {'tipo': 'ACK'}
    except (socket.timeout, ConnectionRefusedError):
        return None
    except (json.JSONDecodeError, ConnectionResetError):
        return None
Recepção e Tratamento de Mensagens
A função lidar_com_cliente é executada em uma thread para cada conexão recebida. Ela decodifica a mensagem JSON e, com base no tipo, direciona para a ação apropriada, como defender a posição de coordenador ou responder a uma eleição.

Python

def lidar_com_cliente(self, cliente_socket: socket.socket):
    try:
        dados = cliente_socket.recv(1024)
        if not dados: return

        mensagem = json.loads(dados.decode())
        tipo_msg = mensagem.get('tipo')

        if tipo_msg == 'ELEICAO':
            remetente_pid = mensagem.get('remetente_pid')
            with self.lock:
                if self.pid == self.coordenador:
                    self._log(f"Já sou o coordenador. Rejeitando eleição iniciada por {remetente_pid}.")
                    resposta = {'tipo': 'COORDENADOR', 'coordenador_pid': self.pid, 'remetente_pid': self.pid}
                    cliente_socket.sendall(json.dumps(resposta).encode())
                    return

            self._log(f"[RECV] Mensagem de ELEIÇÃO do processo {remetente_pid}")
            resposta = {'tipo': 'RESPOSTA', 'remetente_pid': self.pid}
            cliente_socket.sendall(json.dumps(resposta).encode())
            self.iniciar_eleicao()

        elif tipo_msg == 'COORDENADOR':
            self.lidar_com_coordenador(mensagem.get('coordenador_pid'))
        # ...
    finally:
        cliente_socket.close()
