# Trabalho Prático de Sistemas Distribuídos: Algoritmo de Eleição Bully

Grupo: Guilherme Trajano, Ítalo Silva e Maurício Ronzani

## 1. Descrição da Proposta

Este trabalho implementa o **Algoritmo de Eleição de Líder de Bully** em um sistema distribuído simulado. A aplicação foi desenvolvida em Python 3 e demonstra como um conjunto de processos autônomos pode eleger um novo processo coordenador quando o líder atual falha ou quando um novo processo de maior prioridade entra no sistema.

A arquitetura é **descentralizada (peer-to-peer)**, onde cada processo é um nó independente que se comunica com os outros através de Sockets TCP/IP em uma rede local (`localhost`). Cada nó é executado como uma instância separada de um mesmo script, diferenciado por argumentos de linha de comando.

## 2. Requisitos Funcionais e Mensagens

Cada processo no sistema é um nó funcional que atua tanto enviando requisições quanto respondendo a elas.

### Identificação dos Processos

-   **Process ID (PID):** Cada processo é unicamente identificado por um ID inteiro. O PID determina a "força" do processo no algoritmo de eleição (quanto maior o PID, maior a prioridade).
-   **Endereço:** Cada processo possui um endereço de `host:porta` onde escuta por conexões.

### Tipos de Mensagens

A comunicação é feita através de mensagens no formato JSON. Os tipos de mensagens trocadas são:

-   **`ELEICAO`**: Enviada por um processo para todos os outros com PID superior ao seu para iniciar uma eleição.
    -   Exemplo: `{'tipo': 'ELEICAO', 'remetente_pid': 1}`
-   **`RESPOSTA`** (OK): Enviada em resposta a uma mensagem `ELEICAO` por um processo de PID superior, indicando que ele está ativo e irá assumir o processo de eleição.
    -   Exemplo: `{'tipo': 'RESPOSTA', 'remetente_pid': 2}`
-   **`COORDENADOR`**: Enviada pelo processo que venceu a eleição para todos os outros processos, anunciando-se como o novo líder. Esta mensagem também é usada por um coordenador estabelecido para anular uma eleição iniciada por um processo de PID inferior.
    -   Exemplo: `{'tipo': 'COORDENADOR', 'coordenador_pid': 4, 'remetente_pid': 4}`
-   **`HEARTBEAT`**: Enviada periodicamente por processos não-coordenadores para o líder atual para verificar se ele ainda está ativo.
    -   Exemplo: `{'tipo': 'HEARTBEAT', 'remetente_pid': 1}`
-   **`HEARTBEAT_ACK`**: Resposta enviada pelo coordenador para confirmar que está ativo.
    -   Exemplo: `{'tipo': 'HEARTBEAT_ACK'}`

## 3. Arquitetura e Comunicação

O sistema simula uma arquitetura peer-to-peer. Não existe um servidor central; cada processo é um par que executa a mesma lógica e pode tanto iniciar comunicação (atuando como cliente) quanto receber comunicação (atuando como servidor).

-   **Modelo de Threads:**
    1.  **Thread Principal:** Inicia o processo e os demais threads.
    2.  **Thread de Servidor:** Roda em um loop infinito, escutando na porta designada pelo processo. A cada nova conexão, uma nova thread de curta duração é criada para lidar com a mensagem recebida, evitando que o servidor bloqueie.
    3.  **Thread de Monitoramento:** Roda em um loop, enviando `HEARTBEAT`s para o coordenador em intervalos regulares para detecção de falhas.


## 4. Execução da Aplicação

### Requisitos

-   Python 3.x

### Como Executar

1.  Abra um terminal para cada processo que deseja simular na rede.
2.  Execute o script `processo.py` em cada terminal, fornecendo os argumentos necessários.

**Argumentos de Linha de Comando:**

-   `--pid`: O ID único do processo.
-   `--porta`: A porta de rede para o processo.
-   `--processos`: A lista completa de todos os processos na rede, no formato `pid:host:porta`.

**Exemplo para uma rede com 3 processos:**

-   **Terminal 1 (Processo 1):**
    ```bash
    python processo.py --pid 1 --porta 5001 --processos 1:127.0.0.1:5001 2:127.0.0.1:5002 3:127.0.0.1:5003
    ```
-   **Terminal 2 (Processo 2):**
    ```bash
    python processo.py --pid 2 --porta 5002 --processos 1:127.0.0.1:5001 2:127.0.0.1:5002 3:127.0.0.1:5003
    ```
-   **Terminal 3 (Processo 3):**
    ```bash
    python processo.py --pid 3 --porta 5003 --processos 1:127.0.0.1:5001 2:127.0.0.1:5002 3:127.0.0.1:5003
    ```

### Como Testar a Lógica de Eleição

1.  **Eleição Inicial:** Inicie todos os processos. Observe nos logs que o processo com o maior PID (no exemplo, P3) vencerá a eleição inicial e se anunciará como coordenador.
2.  **Falha do Coordenador:** Encerre o processo coordenador (P3) pressionando `Ctrl + C` em seu terminal.
3.  **Nova Eleição:** Observe os logs dos processos restantes (P1 e P2). Após um tempo (10 segundos, o intervalo do heartbeat), eles detectarão a falha do líder e iniciarão uma nova eleição.
4.  **Novo Líder:** O processo com o maior PID entre os remanescentes (P2) vencerá a eleição e se anunciará como o novo coordenador.
5.  **Retorno do Processo "Bully":** Reinicie o processo P3. Ao entrar na rede, ele iniciará uma eleição, "intimidará" o líder atual (P2) e retomará sua posição como coordenador.

## 5. Demonstrações do Código-Fonte

### Definição dos Processos via Argumentos

O ponto de entrada da aplicação utiliza a biblioteca `argparse` para configurar cada processo de forma única.

```python
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
Envio de Mensagens (Ação de Cliente)
A função enviar_mensagem encapsula a lógica de se conectar a outro processo e enviar uma mensagem, tratando timeouts e erros de conexão.

Python

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
```

### Recepção e Tratamento de Mensagens (Ação de Servidor)
A função lidar_com_cliente é executada em uma thread para cada conexão recebida. Ela decodifica a mensagem e age de acordo com seu tipo. O trecho abaixo mostra a lógica crucial de como um Coordenador defende sua posição.

```Python

def lidar_com_cliente(self, cliente_socket: socket.socket):
    try:
        dados = cliente_socket.recv(1024)
        if not dados: return

        mensagem = json.loads(dados.decode())
        tipo_msg = mensagem.get('tipo')

        if tipo_msg == 'ELEICAO':
            remetente_pid = mensagem.get('remetente_pid')
            
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

        # ... outros tipos de mensagem ...
    
    finally:
        cliente_socket.close()
```
