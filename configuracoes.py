#!/usr/bin/env python3
import dialog
import subprocess
import os
import re
import time
import mariadb

d = dialog.Dialog(dialog="dialog")
CONFIG_DIR = "/etc/gestorfid"
WPA_SUPPLICANT = "/etc/wpa_supplicant/wpa_supplicant.conf"

config = {
    'user': 'usuario',
    'password': 'senha123',
    'host': 'localhost',
    'database': 'estoque'
}
os.makedirs(CONFIG_DIR, exist_ok=True)

def ssid_atual():
    try:
        result = subprocess.run(
            ["wpa_cli", "-i", "wlan0", "status"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("ssid="):
                return line.split("=", 1)[1]
        return "(desconectado)"
    except Exception:
        return "(erro)"

def alterar_senha():
    usuario = os.getenv("SUDO_USER") or os.getenv("USER")

    #Primeiro input
    code, nova_senha = d.inputbox(f"Nova senha do usuário '{usuario}'", title=f"Configurações - Senha", ok_label="Aceitar",cancel_label="Voltar")
    if not nova_senha:
        d.msgbox("Valor inválido.", ok_label="Aceitar")
        return
    if code != d.OK:
        return

    #Segundo input (confirmação)
    code, confirma_senha = d.inputbox("Confirme a nova senha", title="Configurações - Senha",ok_label="Aceitar",cancel_label="Voltar")
    if not confirma_senha:
        d.msgbox("Valor inválido.", ok_label="Aceitar")
        return
    if code != d.OK:
        return

    if nova_senha != confirma_senha:
        d.msgbox("As senhas não coincidem. Tente novamente.", ok_label="Aceitar")
        return  #volta ao menu sem alterar

    try:
        entrada = f"{usuario}:{nova_senha}"
        subprocess.run(["chpasswd"], input=entrada.encode(), check=True)

        conn = mariadb.connect(**config)
        cursor = conn.cursor()
        cursor.execute("UPDATE vencimento SET senha = NULL")
        cursor.execute("UPDATE vencimento SET senha = ?", (nova_senha,))
        conn.commit()
        cursor.close()
        conn.close()

        d.msgbox(f"Senha do usuário '{usuario}' alterada com sucesso!")
    except subprocess.CalledProcessError:
        d.msgbox("Erro ao alterar senha.")
    except mariadb.Error as e:
        d.msgbox(f"Erro ao salvar senha no banco: {e}")

def configurar_rede():
    code, ssid = d.inputbox("Nome da rede (SSID)", title="Configurações - Conectar Wi-Fi", ok_label="Aceitar", cancel_label="Voltar")
    if code != d.OK:
        return
    if not ssid:
        d.msgbox("Valor inválido.", ok_label="Aceitar")
        return

    code, psk = d.inputbox("Senha da rede", title="Configurações - Conectar Wi-Fi", ok_label="Aceitar", cancel_label="Voltar")
    if code != d.OK:
        return
    if not psk:
        d.msgbox("Valor inválido.", ok_label="Aceitar")
        return

    if ssid and psk:
        try:
            # Escreve no wpa_supplicant
            with open(WPA_SUPPLICANT, "w") as f:
                f.write(
                    f'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n'
                    f'update_config=1\n'
                    f'country=BR\n\n'
                    f'network={{\n'
                    f'    ssid="{ssid}"\n'
                    f'    psk="{psk}"\n'
                    f'}}\n'
                )

            # Recarrega config
            subprocess.run(["wpa_cli", "-i", "wlan0", "reconfigure"], check=True)

            # Aguarda conexão até 10s
            conectado = False
            for i in range(10):
                time.sleep(1)
                result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
                ssid_atual = result.stdout.strip()
                if ssid_atual == ssid:
                    conectado = True
                    break

            if conectado:
                d.msgbox(f"Conectado com sucesso à rede: {ssid}")
            else:
                d.msgbox(f"Não foi possível conectar à rede '{ssid}'. Verifique SSID e senha.")

        except Exception as e:
            d.msgbox(f"Erro ao configurar rede: {e}", ok_label="Aceitar")

def ajustar_data_hora():
    #Verifica se há internet (ping rápido no Google DNS)
    tem_internet = subprocess.run(
        ["ping", "-c", "1", "-W", "1", "8.8.8.8"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0

    if tem_internet:
        d.msgbox("O Raspberry está conectado à internet.\n"
                 "O ajuste manual de data/hora não é permitido.",
                 title="Configurações - Ajustar data",
                 ok_label="Aceitar")
        return

    #Seleciona data pelo calendário
    code, data = d.calendar("TAB para trocar o campo", 
        title="Configurações - Ajustar data",
        ok_label="Aceitar", cancel_label="Voltar", height=4)
    if code != d.OK:
        return

    #data já vem como lista [dia, mês, ano]
    dia, mes, ano = data
    data_txt = f"{dia}-{mes}-{ano}"
    data_formatada = f"{ano}-{mes}-{dia}"

    #Seleciona hora pelo timebox
    code, hora = d.timebox("Horas:Minutos:Segundos", 
        title="Ajustar hora",
        ok_label="Aceitar", cancel_label="Voltar")
    if code != d.OK:
        return

    #Hora vem como lista [HH, MM, SS]
    hh, mm, ss = hora
    hora_formatada = f"{hh}:{mm}:{ss}"

    try:
        subprocess.run(["date", "-s", f"{data_formatada} {hora_formatada}"], check=True)
        d.msgbox(f"Data/hora ajustadas para: {data_txt} {hora_formatada}")
    except subprocess.CalledProcessError:
        d.msgbox("Erro ao ajustar data/hora.")

def definir_prazo_vencimento():
    code, prazo = d.inputbox("Prazo de aviso para vencimento (em dias)", title="Configurações - Prazo",ok_label="Aceitar",cancel_label="Voltar")
    if code != d.OK:
        return
    if prazo and prazo.isdigit():
        try:
            conn = mariadb.connect(**config)
            cursor = conn.cursor()

            #Exclui valor antigo
            cursor.execute("UPDATE vencimento SET dias = NULL")
            cursor.execute("UPDATE vencimento SET dias = ?", (prazo,))
            conn.commit()

            cursor.close()
            conn.close()

            d.msgbox(f"Prazo definido: {prazo} dias")
        except mariadb.Error as e:
            d.msgbox(f"Erro ao salvar no banco: {e}")
    else:
        d.msgbox("Valor inválido.", ok_label="Aceitar")

def dias_analise():
    code, dias = d.inputbox("Dias de análise de reabastecimento", title="Configurações - Dias de análise",ok_label="Aceitar",cancel_label="Voltar")
    if code != d.OK:
        return
    if dias and dias.isdigit():
        try:
            conn = mariadb.connect(**config)
            cursor = conn.cursor()

            #Exclui valor antigo
            cursor.execute("UPDATE vencimento SET dias_analise = NULL")
            cursor.execute("UPDATE vencimento SET dias_analise = ?", (dias,))
            conn.commit()

            cursor.close()
            conn.close()

            d.msgbox(f"Dias definidos: {dias} dias")
        except mariadb.Error as e:
            d.msgbox(f"Erro ao salvar no banco: {e}")
    else:
        d.msgbox("Valor inválido.", ok_label="Aceitar")

def menu():
    while True:
        conn = mariadb.connect(**config)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM vencimento")
        dias_senha = cursor.fetchone()
        rede = ssid_atual()

        agora = time.localtime()
        tempo = time.strftime("%d-%m-%Y %H:%M", agora)
        segundos = agora.tm_sec
        timeout = 60 - segundos

        d.set_background_title(f"GestorFID - {tempo}")

        code, tag = d.menu("Opções", title="Configurações", choices=[
            ("1", f"Alterar senha: {dias_senha[1]}"),
            ("2", f"Configurar rede Wi-Fi: {rede}"),
            ("3", "Ajustar data e hora"),
            ("4", f"Prazo de aviso para vencimento: {dias_senha[0]} dias"),
            ("5", f"Dias de análise de reabastecimento: {dias_senha[2]} dias")
        ], timeout=timeout, ok_label="Aceitar", cancel_label="Voltar")

        if code == d.TIMEOUT:
            continue
        if code != d.OK:
            break

        elif tag == "1":
            alterar_senha()
        elif tag == "2":
            configurar_rede()
        elif tag == "3":
            ajustar_data_hora()
        elif tag == "4":
            definir_prazo_vencimento()
        elif tag == "5":
            dias_analise()

if __name__ == "__main__":
    menu()




