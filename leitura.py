#!/usr/bin/env python3
import serial
import time
import mariadb
from dialog import Dialog
from bancodedados import timeout_para_proximo_minuto, tempo_formatado, alterar_ou_excluir

config = {
    'user': 'usuario',
    'password': 'senha123',
    'host': 'localhost',
    'database': 'estoque'
}
try:
    conn = mariadb.connect(**config)
    cursor = conn.cursor()
except mariadb.Error as e:
    print(f"Erro ao conectar ao MariaDB: {e}")
    exit(1)

d = Dialog(dialog="dialog")

def ler_tags_do_r200(serial_port):
    
    """
    Função responsável pela filtragem do protocolo recebido pela porta serial do Raspberry Pi via UART (24 bytes), separando potência (em dBm) de EPC (12 bytes). É tratado como parâmetro o direcionamento para a porta serial utilizada (string) e criada uma lista para armazenamento das tags interpretadas. Através do de um tempo delimitado, é feito várias leituras, ignorando tags já lidas armazenadas em epc e rssi, e salvando apenas tags únicas. Retorna a lista de tuplas (tags)
    """ 

    tags = []
    inicio = time.time()

    #Tempo escolhido para ciclo
    while time.time() - inicio < 0.05:
        if serial_port.in_waiting == 0: #Se não encontrou nada, 0.1 s e tenta denovo
            continue

        try:
            data = serial_port.read_until(b'\xDD') #Lê até o final do comando recebido
            #Tag inválida
            print(data.hex().upper())

             
            if len(data) != 24:
                continue

            raw_rssi = data[5]
            rssi = raw_rssi - 230 if raw_rssi > 128 else -raw_rssi #Adquirir rssi
            epc_bytes = data[8:20] #Localização da EPC

            epc = epc_bytes.hex().upper() #Deixa epc em hexadecimal e maiusculo
            if (epc, rssi) not in tags:
                tags.append((epc, rssi))

        except Exception as e:
            d.msgbox(f"[ERRO]: {e}")
            continue
    return tags

def leitura_em_tempo_real(modo_escolhido, tempo, repetir=True, produtos_formatados=None, repetir_unica=5):

    """
    Função responsável pela criação do direcionamento da porta serial ttyS0 (ou serial0), envio de protocolos de funcionamento do leitor, definindo região, potência e frequência. 
    """

    try:
        leitor = serial.Serial(
            '/dev/serial0',
             baudrate=115200, bytesize=serial.EIGHTBITS,
             parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
             timeout=1, xonxoff=False, rtscts=False, dsrdtr=False
        )

        if not leitor.is_open:
            leitor.open()
        leitor.reset_input_buffer()
        leitor.write(bytes.fromhex("AA00070001020ADD")) #Região (USA)
        time.sleep(0.05)
        leitor.reset_input_buffer()
        leitor.write(bytes.fromhex("AA00AB00011AC6DD")) #Frequência = 915,25 MHz
        time.sleep(0.05)
        leitor.reset_input_buffer()
        leitor.write(bytes.fromhex("AA00B6000209928FDD")) #Potência = 24,5 dBm
        time.sleep(0.05)

    except Exception as e:
        d.msgbox(f"Erro ao conectar com o leitor: {e}")
        return

    try:
        epcs_lidos = []  #EPCs únicos já exibidos ao longo do ciclo
        produtos_lidos = [] #Produtos que já foram lidos ao longo da sessão
        campo_ordem=None
        direcao_ordem=None
        epcs_rssis = []

        if produtos_formatados:
            produtos_lidos = produtos_formatados
            for p in produtos_lidos:
                epcs_lidos.append(p[2])

        while True:
            titulo_tempo = tempo_formatado()
            d.set_background_title(titulo_tempo)
            timeout=timeout_para_proximo_minuto()
            txt = "Leitura contínua" if modo_escolhido == "contínua" else "Leitura única"
            # for para repetidas leituras por ciclo
            for i in range(1, repetir_unica + 1):
                leitor.reset_input_buffer()
                leitor.write(bytes.fromhex("AA0022000022DD"))
                time.sleep(0.05)
                epcs_rssi = ler_tags_do_r200(leitor) #Novo ciclo
                for epc, rssi in epcs_rssi: #Para as tags armazenadas durante o ciclo
                    if epc in epcs_lidos: #Se já tiver inclusa em epcs_lidos, continua
                        continue
                    #-------------------ACHOU TAG NOVA-------------------
                    cursor.execute("SELECT * FROM produtos WHERE epc = ?", (epc,)) 
#Procura por produto com epc nova
                    prod = cursor.fetchone() #Guarda todos os registros do produto em prod
                    if prod: #Se encontrou o produto com epc registrada
                        produtos_lidos.append((rssi, *prod)) #Insere em produtos_lidos com registros armazenados
                    else: #Se não encontrou o produto com epc registrada
                        produtos_lidos.append((rssi, None, epc, "Tag não cadastrada", None, None, None, None)) #RSSI, ID, EPC, NOME, VALIDADE, SETOR, DISTRIBUIDOR, DATA
                    epcs_lidos.append(epc) #Tag já foi lida

                if i < repetir_unica:
                    continue

                if produtos_lidos: #Se tiver alguma tag armazenada ao longo da sessão
                    if modo_escolhido != "dar_baixa":
      
                        feedback = alterar_ou_excluir("produtos", "leitura_em_tempo_real", modo_escolhido, tempo, txt, repetir, produtos_lidos, campo_ordem, direcao_ordem) #Chama função para exibir produtos em tabela e poder ordená-los, alterá-los e excluí-los
                        if feedback[0] == "VOLTAR": #Se quiser voltar
                            produtos_lidos = feedback[1]
                            return produtos_lidos
                        else:
                            produtos_lidos, campo_ordem, direcao_ordem = feedback #Faz backup de produtos
                            repetir=False #Nao pode repetir o menu de ordenação

                    #----------LÓGICA DE PROXIMIDADE POR POT----------
                    else:
                        if not epcs_rssi and not epcs_lidos:
                            break
                        epcs_rssis+=epcs_rssi
                        if i == 5:
                            rssis=[]
                            mais_perto=[]
                            for p in epcs_rssis:
                                rssis.append(p[1])
                            rssis.sort(reverse=True)  #Do maior para o menor
                            try:
                                if rssis[0] > -15:
                                    mais_perto.append(rssis[0])
                                else:
                                    return []
                            except:
                                return []
                            for p in epcs_rssis:
                                if p[1] == mais_perto[0]:
                                    mais_perto.append(p[0]) #[rssi, epc]

                            return mais_perto

            if not epcs_rssi and not epcs_lidos:
                d.msgbox("Nenhuma tag foi detectada.", ok_label="Aceitar")
                return "NAO_DETECTOU"

            if modo_escolhido == "contínua":
                time.sleep(tempo)

    finally: #Sempre encerrar a conexão com o leitor após o final
        try:
            if leitor and leitor.is_open:
                try:
                    leitor.flush()
                except Exception as e:
                    d.msgbox(f"[AVISO] Erro ao fazer flush: {e}")
                try:
                    leitor.write(bytes.fromhex("AA0028000028DD"))  # Parar leitura segura
                    time.sleep(0.05)
                except Exception as e:
                    d.msgbox(f"[AVISO] Erro ao enviar comando de parada: {e}")
                try:
                    leitor.close()
                except Exception as e:
                    d.msgbox(f"[AVISO] Erro ao fechar porta serial: {e}")
        except Exception as e:
            d.msgbox(f"[AVISO]: {e}")

def menu():
    modos = {
        "1": "única",
        "2": "contínua"
    }
    produtos_formatados=[]

    while True:
        if produtos_formatados == "NAO_DETECTOU":
            produtos_formatados = []

        repetir=True #Repetir o menu de ordem
        titulo_tempo = tempo_formatado()
        d.set_background_title(titulo_tempo)
        timeout=timeout_para_proximo_minuto()

        code, modo = d.menu("Modos de leitura", title="Leitura em tempo real", choices=[
            ("1", "Única"),
            ("2", "Contínua")
        ], timeout=timeout, ok_label="Aceitar", cancel_label="Voltar")

        if code == d.TIMEOUT:
            continue
        if code != d.OK:
            return

        modo_escolhido = modos.get(modo)
        tempo = 0.05 #Ciclo de leitura padrão para leitura única
        if modo_escolhido == "contínua": #Input de tempo de ciclo (em segundos)
            while True:
                code, tempo_str = d.inputbox("Tempo de ciclo (segundos)", ok_label="Aceitar", cancel_label="Voltar")
                if code != d.OK:
                    break
                if tempo_str.isdigit() and int(tempo_str) > 0:
                    tempo = int(tempo_str)
                    break
                else: #Se nao for inteiro positivo, tenta denovo
                    d.msgbox("Digite um número inteiro positivo.")
                    continue
        produtos_formatados = leitura_em_tempo_real(modo_escolhido, tempo, repetir, produtos_formatados, repetir_unica=5)

if __name__ == "__main__":
    menu()





