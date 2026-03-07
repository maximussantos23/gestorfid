from dialog import Dialog
import subprocess
import sys
import time

d = Dialog(dialog="dialog")

def tempo_atual():

    """
    Adquire o tempo local de agora (data e hora), segundos para assim subtrair de 60 equivalente ao tempo restante até o próximo minuto e é atribuído a timeout que será usado para definir o tempo em que a janela será atualizada, assim atualizando dinamicamente o tempo que está localizado no canto superior esquerdo da interface, juntamente com o nome do projeto

    Retorno:
        timeout(int): tempo restante para o próximo minuto
    """

    agora = time.localtime()
    segundos = agora.tm_sec
    timeout = 60 - segundos # segundos restantes para o próximo minuto
    tempo = time.strftime("%d-%m-%Y %H:%M", agora)
    d.set_background_title(f"GestorFID - {tempo}")
    return timeout

def menu():

    while True: #Cria um loop, para que seja possível atualizar a janela com return
        timeout=tempo_atual() #Atribui o retorno da função a timeout

        #Menu simples em janela com opções
        #timeout é atribuída apenas uma vez, quando a janela é criada. Se o usuário mexer na tela, o timer é resetado para 60 segundos
        code, tag = d.menu("Serviços", title="Menu principal", choices=[
            ("1", "Leitura em tempo real"),
            ("2", "Dar baixa"),
            ("3", "Nova gravação"),
            ("4", "Banco de dados"),
            ("5", "Gerar relatório"),
            ("6", "Configurações"),
            ("7", "Sair do menu")
        ], timeout=timeout, no_cancel=True, ok_label="Aceitar")

        #Tempo acabou ou usuário apertou ESC, apenas atualiza o relógio e reapresenta o menu
        if code == d.ESC or code == d.TIMEOUT:
            continue

        #Lógica para abrir os arquivos correspondentes a escolha do usuário
        if code != d.OK or tag == "7":
            break
        if tag == "1":
            subprocess.run([sys.executable, 'leitura.py'])
        elif tag == "2":
            subprocess.run([sys.executable, 'baixa.py'])
        elif tag == "3":
            subprocess.run([sys.executable, 'gravacao.py'])
        elif tag == "4":
            subprocess.run([sys.executable, 'bancodedados.py'])
        elif tag == "5":
            subprocess.run([sys.executable, 'relatorio.py'])
        elif tag == "6":
            #Configuracoes.py precisa de uma autorização sudo para alterar dados internos do rasp
            subprocess.run(["sudo", sys.executable, "configuracoes.py"])

if __name__ == "__main__":
    menu()


