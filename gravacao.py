#!/usr/bin/env python3
import mariadb
from dialog import Dialog
from datetime import datetime
from bancodedados import tempo_formatado, formatar_data, timeout_para_proximo_minuto, escolher_valor_existente
from leitura import leitura_em_tempo_real
import time
import sys

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
    sys.exit(1)

d = Dialog(dialog="dialog")

def monta_preview(campos):
    #Gera string de pré-visualização curta dos campos preenchidos
    partes = []
    for chave, rotulo in [("nome", "Nome"), ("validade", "Validade"), ("setor", "Setor"), ("distribuidor", "Distribuidor")]:
        valor = campos.get(chave)
        if valor:
            if chave == "validade":
                partes.append(f"{rotulo}: {formatar_data(valor)}")
            else:
                partes.append(f"{rotulo}: {valor}")
        else:
            partes.append(f"{rotulo}: <vazio>")
    return "\n".join(partes)

def menu():
    while True:
        titulo_base = "Nova gravação"
        while True:
            titulo_tempo = tempo_formatado()
            d.set_background_title(titulo_tempo)
            timeout = timeout_para_proximo_minuto()

            d.infobox("Aproxime a tag da antena...", title=titulo_base)
            time.sleep(2)
            rssi_epc = leitura_em_tempo_real("dar_baixa", 0.05, None, None, 5)
            if not rssi_epc:
                d.msgbox("Tag muito distante. Tente novamente.")
                return
            elif rssi_epc == "NAO_DETECTOU":
                return

            epc = rssi_epc[1]
            try:
                cursor.execute("SELECT * FROM produtos WHERE epc = %s", (epc,))
                produto_existente = cursor.fetchone()
            except Exception as e:
                d.msgbox(f"Erro ao consultar o banco: {e}")
                return

            if produto_existente:
                d.msgbox("Tag já cadastrada.", title="Nova gravação")
                return

            #Começa coleta de campos
            campos = {
                "nome": None,
                "validade": None,
                "setor": None,
                "distribuidor": None
            }
            mapa_campos = {
                "1": "nome",
                "2": "validade",
                "3": "setor",
                "4": "distribuidor"
            }

            while True:
                timeout = timeout_para_proximo_minuto()
                titulo_tempo = tempo_formatado()
                d.set_background_title(titulo_tempo)
                titulo_menu = "Nova gravação"
                choices = [("1", "Cópia de cadastrado"), ("2", "Campos individuais")]
                code, tag = d.menu(f"Tag detectada: {epc}\n\nOpções de cadastro",
                    title=titulo_menu, choices=choices,
                    ok_label="Aceitar", cancel_label="Voltar",
                    extra_button=False,
                    timeout=timeout)

                if code == d.TIMEOUT:
                    continue
                if code != d.OK:
                    return

                if tag == "1":  #=== CÓPIA DE CADASTRADO ===
                    try:
                        cursor.execute("""
                            SELECT p.id, p.nome, p.validade, p.setor, p.distribuidor
                            FROM produtos p
                            JOIN (
                                SELECT nome, validade, MAX(id) AS id_mais_recente
                                FROM produtos
                                GROUP BY nome, validade
                            ) ult
                            ON p.id = ult.id_mais_recente
                            ORDER BY p.nome, p.validade DESC
                        """)
                        produtos_existentes = cursor.fetchall()
                    except Exception as e:
                        d.msgbox(f"Erro ao consultar produtos: {e}")
                        return

                    if not produtos_existentes:
                        d.msgbox("Nenhum produto encontrado.")
                        continue

                    #=== FORMATA MENU COM COLUNAS FIXAS ===
                    choices_copy = []
                    for i, p in enumerate(produtos_existentes, start = 1):
                        _id, nome, validade, setor, distribuidor = p

                        nome_fmt = (nome or "").ljust(40)[:40]
                        validade_fmt = validade.strftime("%d-%m-%Y") if validade else " " * 10

                        texto = f"{nome_fmt} | {validade_fmt}"
                        choices_copy.append((str(i), texto))

                    while True:
                        timeout = timeout_para_proximo_minuto()
                        titulo_tempo = tempo_formatado()
                        d.set_background_title(titulo_tempo)

                        code, tag_prod = d.menu("Escolha um produto para copiar\n\nNome | Validade",
                            title=titulo_menu + " - Cópia de cadastrado",
                            choices=choices_copy,
                            ok_label="Aceitar", cancel_label="Voltar",
                            height=20, width=80, timeout=timeout)

                        if code == d.TIMEOUT:
                            continue
                        if code != d.OK:
                            break

                        escolhido = produtos_existentes[int(tag_prod) - 1]
                        _id, nome, validade, setor, distribuidor = escolhido

                        confirmar = d.yesno(f"Confirmar cópia?\n- - - - - - - - - - - - - - - - - - - - - - - - -\n"
                            f"Nome: {nome}\n"
                            f"Validade: {formatar_data(validade) if validade else 's/ validade'}\n"
                            f"Setor: {setor or '-'}\n"
                            f"Distribuidor: {distribuidor or '-'}\n- - - - - - - - - - - - - - - - - - - - - - - - -",
                            title=titulo_menu + " - Cópia de cadastrado",
                            yes_label="Sim", no_label="Não", height=11, width=53)

                        if confirmar != d.OK:
                            break

                        try:
                            cursor.execute("""
                                INSERT INTO produtos (epc, nome, validade, setor, distribuidor)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (epc, nome, validade, setor, distribuidor))
                            conn.commit()
                            d.msgbox("Produto cadastrado com sucesso.", title="Nova Gravação")
                        except Exception as e:
                            d.msgbox(f"Erro ao inserir no banco: {e}")
                        return

                elif tag == "2":  # === CAMPOS INDIVIDUAIS ===
                    while True:
                        timeout = timeout_para_proximo_minuto()
                        titulo_tempo = tempo_formatado()
                        d.set_background_title(titulo_tempo)
                        titulo_menu = "Nova gravação - Campos individuais"
                        preview = monta_preview(campos)
                        choices = [("1", "Nome"), ("2", "Validade"), ("3", "Setor"), ("4", "Distribuidor")]
                        code, tag = d.menu(f"Campos de produto\n- - - - - - - - - - - - - - - - - - - - - - - - -\n{preview}\n- - - - - - - - - - - - - - - - - - - - - - - - -", title=titulo_menu, choices=choices,
                            ok_label="Aceitar", cancel_label="Voltar",
                            extra_button=True, extra_label="Cadastrar",
                            height = 17, timeout=timeout)

                        if code == d.TIMEOUT:
                            continue
                        elif code != d.OK and code != d.EXTRA:
                            break
                        elif code == d.EXTRA:
                            code = d.yesno("Confirmar cadastro?", title=titulo_menu, yes_label="Sim", no_label="Não")
                            if code == d.OK:
                                try:
                                    cursor.execute("""
                                        INSERT INTO produtos
                                        (epc, nome, validade, setor, distribuidor)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (
                                        epc,
                                        campos["nome"],
                                        campos["validade"],
                                        campos["setor"],
                                        campos["distribuidor"]
                                    ))
                                    conn.commit()
                                    d.msgbox("Produto cadastrado com sucesso.", 
title="Sucesso")
                                except Exception as e:
                                    d.msgbox(f"Erro ao inserir no banco: {e}")
                                return
                            else:
                                continue #volta ao menu de campos

                        #Se chegou aqui, escolheu um campo para editar
                        campo_alt = mapa_campos.get(tag)

                        if campo_alt in ["nome", "setor", "distribuidor"]:
                            campo = escolher_valor_existente(campo_alt.capitalize(), titulo=f"Selecionar/inserir {campo_alt}")
                            if not campo: #Usuário cancelou
                                continue
                            campos[campo_alt] = campo.strip()
                        elif campo_alt == "validade":
                            code, data = d.calendar("TAB para alterar campo",title="Selecionar validade", height=3, cancel_label="Voltar", ok_label="Aceitar")
                            if code != d.OK:
                                continue
                            valor = f"{data[2]:04d}-{data[1]:02d}-{data[0]:02d}"
                            campos["validade"] = valor
                
                    #fim do loop de campos

        #Fim do try/while de leitura de EPC
        break  #Sair do while principal

if __name__ == "__main__":
    menu()
    cursor.close()
    conn.close()






