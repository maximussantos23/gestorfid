#!/usr/bin/env python3
import mariadb
from dialog import Dialog
from datetime import datetime
from bancodedados import tempo_formatado, formatar_data
from leitura import leitura_em_tempo_real
import time

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
    print(f"Erro ao conectar: {e}")
    exit(1)

d = Dialog(dialog="dialog")

def menu():
    while True:
        titulo_tempo = tempo_formatado()
        d.set_background_title(titulo_tempo)

        d.infobox("Aproxime a tag da antena...", title = "Dar Baixa")
        time.sleep(2)
        rssi_epc = leitura_em_tempo_real("dar_baixa", 0.05, None, None, 5)
        if not rssi_epc:
            d.msgbox("Tag muito distante. Tente novamente.")
            return
        elif rssi_epc == "NAO_DETECTOU":
            return

        try:
            #Busca produto
            cursor.execute("SELECT * FROM produtos WHERE epc = ?", (rssi_epc[1],))
            produto = cursor.fetchone()

            if not produto:
                d.msgbox("Tag não cadastrada.", title = "Dar Baixa")
                return
 
            confirmar = d.yesno(
                f"Registrar produto como vendido?\n- - - - - - - - - - - - - - - -\nID: {produto[0]}\nNome: {produto[2]}\nValidade: {formatar_data(produto[3])}\nSetor: {produto[4]}\nDistribuidor: {produto[5]}\n- - - - - - - - - - - - - - - -", height=12, width=35, yes_label="Sim", no_label="Não", title = "Dar Baixa")
            if confirmar == d.OK:

                #Inserir em produtos_vendidos
                cursor.execute("""
                    INSERT INTO produtos_vendidos
                    (id, epc, nome, validade, setor, distribuidor, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    produto[0], produto[1], produto[2], produto[3],
                    produto[4], produto[5], produto[6]
                ))

                #Deletar da tabela original
                cursor.execute("DELETE FROM produtos WHERE epc = ?", (rssi_epc[1],))
                conn.commit()

                d.msgbox("Venda registrada com sucesso e produto removido de ativos.")
            return

        except Exception as e:
            d.msgbox(f"Erro: {e}")
            return

if __name__ == "__main__":
    menu()
    cursor.close()
    conn.close()





