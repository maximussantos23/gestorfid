#!/usr/bin/env python3
import os
import math
import time
import csv
from datetime import datetime, date, timedelta
import mariadb
from tabulate import tabulate
from dialog import Dialog
from bancodedados import timeout_para_proximo_minuto, formatar_data, formatar_data_hora, tempo_formatado
from atualiza_custos import atualizar_reabastecimento
import subprocess
import shutil

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

tabelas = {
    "1": "produtos",
    "2": "produtos_vendidos",
    "3": "produtos_excluidos",
    "4": "custos_produto"
}

def encontrar_pendrive():
    # Lista dispositivos de bloco (lsblk -J = JSON)
    resultado = subprocess.check_output(["lsblk", "-J", "-o", "NAME,MOUNTPOINT"]).decode()
    if "/media/" in resultado or "/mnt/" in resultado:
        linhas = resultado.splitlines()
        for linha in linhas:
            if "/media/" in linha or "/mnt/" in linha:
                return linha.strip().split('"')[-2]  # pega o caminho de montagem
    return None

def copiar_para_pendrive(arquivo_origem):
    destino = encontrar_pendrive()
    if not destino:
        return None
    
    shutil.copy(arquivo_origem, destino)
    return 1

# ----------------- CUSTOS DE LOTE -----------------
def custos_exibir():
    cursor.execute("""
        SELECT id, nome, preco_lote, preco_armazenamento, dias_entrega, validade_dias
        FROM custos_produto
    """)
    produtos = cursor.fetchall()
    if not produtos:
        d.msgbox("Nenhum produto encontrado.", ok_label="Aceitar")
        return

    linhas = []
    for p in produtos:
        linhas.append([
            str(p[0]), p[1], f"R$ {p[2]:.2f}", f"R$ {p[3]:.2f}", str(p[4]), str(p[5])
        ])

    headers = ["ID", "Nome", "Custo lote", "Custo armazenamento (mensal)", "Dias entrega", "Validade (dias)"]
    texto = tabulate(linhas, headers=headers, tablefmt="fancy_grid")
    d.scrollbox(texto, height=60, width=200, title="Produto(s) encontrado(s)", exit_label="OK")

def custos_alterar_excluir():
    while True:
        titulo_tempo = tempo_formatado()
        d.set_background_title(titulo_tempo)
        timeout = timeout_para_proximo_minuto()

        cursor.execute("""
            SELECT id, nome, preco_lote, preco_armazenamento, dias_entrega, validade_dias
            FROM custos_produto
        """)
        produtos = cursor.fetchall()

        if not produtos:
            d.msgbox("Nenhum produto cadastrado.", ok_label="Aceitar")
            return

        cabecalho = "ID | Nome | Custo lote | Custo armazenamento (mensal) | Dias entrega | Validade (dias)"
        opcoes = []
        produtos_formatados = []

        for i, p in enumerate(produtos, start=1):
            id_str = str(p[0]).rjust(5)
            nome_fmt = p[1][:30].ljust(30)
            lote_fmt = f"R$ {p[2]:.2f}".rjust(12) if p[2] else "-----".rjust(12)
            arm_fmt = f"R$ {p[3]:.2f}".rjust(12) if p[3] else "-----".rjust(12)
            entrega_fmt = str(p[4]).rjust(5) if p[4] else "-----".rjust(5)
            validade_fmt = str(p[5]).rjust(5) if p[5] else "-----".rjust(5)
            linha = f"{id_str} | {nome_fmt} | {lote_fmt} | {arm_fmt} | {entrega_fmt} | {validade_fmt}"
            produtos_formatados.append(p)
            opcoes.append((str(i), linha))

        code, escolhido = d.menu(
            f"Produto(s) encontrado(s)\n\n{cabecalho}",
            height=30,
            width=130,
            title="Gerar relatório - Custos de Lote - Alterar/Excluir custos",
            choices=opcoes,
            ok_label="Alterar",
            cancel_label="Voltar",
            extra_button=True,
            extra_label="Excluir",
            timeout=timeout
        )

        if code == d.TIMEOUT:
            continue
        if code != d.OK and code != d.EXTRA:
            return

        indice = int(escolhido) - 1
        prod = produtos_formatados[indice]

        prod_id, nome, preco_lote_atual, preco_arm_atual, dias_entrega_atual, validade_dias_atual = prod

        if code == d.OK:
            
            opcoes = [
                ("1", "Custo de lote"),
                ("2", "Custo de armazenamento"),
                ("3", "Dias para entrega"),
                ("4", "Dias até validade")
            ]

            while True:
                titulo_tempo = tempo_formatado()
                d.set_background_title(titulo_tempo)
                timeout = timeout_para_proximo_minuto()

                code, tag = d.menu(
                    f"Campo para alterar",
                    title=f"Alterar custos ID {prod_id}",
                    choices=opcoes,
                    ok_label="Aceitar",
                    cancel_label="Voltar",
                    timeout=timeout
                )
                if code == d.TIMEOUT:
                    continue
                if code != d.OK:
                    break

                if tag == "1":
                    code, novo_lote = d.inputbox("Custo de lote (R$)", init=f"{preco_lote_atual:.2f}" if preco_lote_atual else "0,00", ok_label = "Aceitar", cancel_label = "Voltar")
                    if code != d.OK:
                        continue

                if tag == "2":
                    code, nova_arm = d.inputbox("Custo de armazenagem (mensal) (R$)", init=f"{preco_arm_atual:.2f}" if preco_arm_atual else "0,00", ok_label = "Aceitar", cancel_label = "Voltar")
                    if code != d.OK:
                        continue

                if tag == "3":
                    code, novo_entrega = d.inputbox("Dias de entrega", init=str(dias_entrega_atual) if dias_entrega_atual else "0", ok_label = "Aceitar", cancel_label = "Voltar")
                    if code != d.OK:
                        continue

                if tag == "4":
                    code, nova_validade = d.inputbox("Validade em dias", init=str(validade_dias_atual) if validade_dias_atual else "0", ok_label = "Aceitar", cancel_label = "Voltar")
                    if code != d.OK:
                        continue
    
                try:
                    preco_lote = float(novo_lote.replace(",", ".").strip())
                    preco_arm = float(nova_arm.replace(",", ".").strip())
                    dias_entrega = int(novo_entrega.strip())
                    validade_dias = int(nova_validade.strip())
                except ValueError:
                    d.msgbox("Valores inválidos.", ok_label="Aceitar")
                    continue

                try:
                    cursor.execute("""
                        UPDATE custos_produto
                        SET preco_lote=?, preco_armazenamento=?, dias_entrega=?, validade_dias=?
                        WHERE id=?
                    """, (preco_lote, preco_arm, dias_entrega, validade_dias, prod_id))
                    conn.commit()
                    d.msgbox("Custos alterados com sucesso.", ok_label="OK")
                except Exception as e:
                    d.msgbox(f"Erro ao alterar produto: {e}", ok_label="OK")

        elif code == d.EXTRA:
            confirmar = d.yesno(f"Excluir o cadastro de custos do produto ID {prod_id}?", yes_label="Sim", no_label="Não")
            if confirmar == d.OK:
                try:
                    cursor.execute("DELETE FROM custos_produto WHERE id=?", (prod_id,))
                    conn.commit()
                    d.msgbox(f"Custos excluídos com sucesso.", ok_label="OK")
                except Exception as e:
                    d.msgbox(f"Erro ao excluir custos: {e}", ok_label="OK")

def custos_cadastrar():
    cursor.execute("""
        SELECT id, epc, nome, validade, setor, distribuidor, data, data_venda 
        FROM produtos_vendidos
    """)
    vendidos = cursor.fetchall()

    if not vendidos:
        d.msgbox("Nenhum produto vendido encontrado.", ok_label="Aceitar")
        return

    nomes_unicos = {}
    for p in vendidos:
        chave = (p[2], p[3])  # nome + validade
        cursor.execute(
            "SELECT id FROM custos_produto WHERE nome=? AND validade_dias=?",
            (p[2], (p[3] - p[6].date()).days if p[3] else None)  # calcular validade em dias se precisar
        )
        if cursor.fetchone():
            continue
        if chave not in nomes_unicos:
            nomes_unicos[chave] = p

    produtos_unicos = list(nomes_unicos.values())


    produtos_unicos = list(nomes_unicos.values())
    if not produtos_unicos:
        d.msgbox("Todos os produtos já possuem custos cadastrados.", ok_label="Aceitar")
        return

    while True:
        titulo_tempo = tempo_formatado()
        d.set_background_title(titulo_tempo)
        timeout = timeout_para_proximo_minuto()
        cabecalho = "ID | Nome | Validade | Setor | Distribuidor | Data/hora venda"

        opcoes = []
        produtos_formatados = []

        for i, p in enumerate(produtos_unicos, start=1):
            id_str = str(p[0]).rjust(5)
            nome_fmt = p[2][:25].ljust(25)
            validade_fmt = formatar_data(p[3]).ljust(10) if p[3] else "-----".ljust(10)
            setor_fmt = p[4][:12].ljust(12) if p[4] else "-----".ljust(12)
            dist_fmt = p[5][:20].ljust(20) if p[5] else "-----".ljust(20)
            data_venda_fmt = formatar_data_hora(p[7]) if p[7] else "-----"
            linha = f"{id_str} | {nome_fmt} | {validade_fmt} | {setor_fmt} | {dist_fmt} | {data_venda_fmt}"
            produtos_formatados.append(p)
            opcoes.append((str(i), linha))

        code, escolhido = d.menu(
            f"Produto(s) vendido(s) (ainda sem custos)\n\n{cabecalho}",
            height=30,
            width=130,
            title="Gerar relatório - Custos de Lote - Cadastrar custos",
            choices=opcoes,
            ok_label="Cadastrar",
            cancel_label="Voltar",
            timeout=timeout
        )

        if code == d.TIMEOUT:
            continue
        if code != d.OK:
            return

        try:
            indice = int(escolhido) - 1
            prod = produtos_formatados[indice]
        except (ValueError, IndexError):
            d.msgbox("Seleção inválida.", ok_label="Aceitar")
            continue

        id = prod[0]
        nome = prod[2]

        while True:
            code, lote = d.inputbox(f"Custo de lote (R$)", title = f"ID {id}", init="0,00", ok_label = "Aceitar", cancel_label = "Voltar")
            if code != d.OK:
                break
            code, armazenagem = d.inputbox(f"Custo de armazenagem mensal (R$)", title = f"ID {id}", init="0,00", ok_label = "Aceitar", cancel_label = "Voltar")
            if code != d.OK:
                break
            code, dias_entrega = d.inputbox(f"Dias de entrega", title = f"ID {id}", init="0", ok_label = "Aceitar", cancel_label = "Voltar")
            if code != d.OK:
                break
            code, validade_dias = d.inputbox(f"Validade em dias", title = f"ID {id}", init="0", ok_label = "Aceitar", cancel_label = "Voltar")
            if code != d.OK:
                break

            try:
                preco_lote = float(lote.replace(",", ".").strip())
                preco_armazenamento = float(armazenagem.replace(",", ".").strip())
                dias_entrega = int(dias_entrega.strip())
                validade_dias = int(validade_dias.strip())
            except ValueError:
                d.msgbox("Valor(es) inválidos.", ok_label="Aceitar")
                continue

            if preco_armazenamento <= 0:
                d.msgbox("Preço de armazenagem precisa ser maior que 0.", title = f"ID {id} - AVISO", ok_label="OK")
                continue

            try:
                cursor.execute("""
                    INSERT INTO custos_produto (nome, preco_lote, preco_armazenamento, dias_entrega, validade_dias)
                    VALUES (?, ?, ?, ?, ?)
                """, (nome, preco_lote, preco_armazenamento, dias_entrega, validade_dias))
                conn.commit()
                d.msgbox(f"Custos de '{nome}' cadastrados com sucesso.", ok_label="OK")
                produtos_unicos = [p for p in produtos_unicos if p[2] != nome]
                break
            except Exception as e:
                d.msgbox(f"Erro ao cadastrar '{nome}': {e}", ok_label="OK")
                break

        if not produtos_unicos:
            d.msgbox("Todos os produtos já possuem custos cadastrados.", ok_label="Aceitar")
            return

# ----------------- MODELO DE REABASTECIMENTO -----------------
def modelo_reabastecimento():
    try:
        conn = mariadb.connect(**config)
        cursor = conn.cursor()

        # Atualiza os cálculos antes de exibir
        atualizar_reabastecimento()
        
        # Pega os dias para analise
        cursor.execute("""
            SELECT dias_analise FROM vencimento
        """)
        dias_analise = int(cursor.fetchone()[0])

        # Pega todos os dados já calculados
        cursor.execute("""
            SELECT nome, vendidos, demanda, estoque, termino, encomenda, Q_pedido, Q_final
            FROM custos_produto
        """)
        produtos = cursor.fetchall()
        if not produtos:
            d.msgbox("Nenhum dado encontrado em custos_produto.", ok_label="OK")
            return

        texto = "REABASTECIMENTO\n\n"
        for nome, vendidos, demanda, estoque, data_termino, data_pedido, Q_pedido, Q_final in produtos:
            texto += f"Produto: {nome}\n"
            texto += f"  → Período analisado: {dias_analise} dias\n"
            texto += f"  → Vendidos: {vendidos} un.\n"
            texto += f"  → Demanda diária: {demanda:.2f} un/dia\n"
            texto += f"  → Estoque atual: {estoque} un.\n"
            texto += f"  → Lote ideal (Q*): {Q_final:.0f} un.\n"
            texto += f"  → Pedido recomendado: {Q_pedido:.0f} un.\n"
            texto += f"  → Data término estoque: {formatar_data(data_termino)}\n"
            texto += f"  → Data do pedido: {formatar_data(data_pedido)}\n\n"

        d.scrollbox(texto.strip(), exit_label="OK", width=120, height=30)
        cursor.close()
        conn.close()

    except mariadb.Error as e:
        print(f"Erro no banco: {e}")

def configurar_relatorio_custos():
    while True:
        titulo_tempo = tempo_formatado()
        d.set_background_title(titulo_tempo)
        timeout = timeout_para_proximo_minuto()

        # Seleção de colunas
        cursor.execute("SHOW COLUMNS FROM custos_produto")
        colunas = [c[0] for c in cursor.fetchall()]

        choices = [(str(i + 1), col.replace("_", " ").capitalize(), 1) for i, col in enumerate(colunas)]
        code, colunas_idx = d.checklist(
            "Campos personalizáveis (ESPAÇO para desm.)",
            choices=choices,
            title="Gerar Relatório - Configuração de relatório - Custos de Lote",
            ok_label="Aceitar",
            cancel_label="Voltar",
            timeout=timeout,
            width=70,
            height=20
        )
        if code == d.TIMEOUT:
            continue
        if code != d.OK or not colunas_idx:
            return

        colunas_sel = [colunas[int(i) - 1] for i in colunas_idx]

        # ========= FILTRO =========
        campos_filtro = {
            "1": "id",
            "2": "nome"
        }
        while True:
            code, filtros_marcados = d.checklist(
                "Filtrar por (ESPAÇO para selecionar)",
                choices=[("1", "ID", False), ("2", "Nome", False)],
                title="Gerar relatório - Custos de Lote - Filtrar",
                ok_label="Aceitar",
                cancel_label="Voltar",
                timeout=timeout
            )
            if code == d.TIMEOUT:
                continue
            if code != d.OK:
                break
            
            clausulas = []
            valores = []
            retorna = 0

            for indice in filtros_marcados:
                campo = campos_filtro[indice]
                code, termo = d.inputbox(f"Digite o {campo.capitalize()}", ok_label="Aceitar", cancel_label="Voltar")
                if code != d.OK:
                    retorna = 1
                    break

                clausulas.append(f"{campo} LIKE ?")
                valores.append(f"%{termo}%")
            
            if retorna == 1:
                continue

            where_clause = f"WHERE {' AND '.join(clausulas)}" if clausulas else ""

            # ========= ORDENAR =========
            escolhas_ordem = [
                ("1", "Nome A-Z"),
                ("2", "Nome Z-A"),
                ("3", "Mais vendidos"),
                ("4", "Menos vendidos"),
                ("5", "Maior demanda"),
                ("6", "Menor demanda"),
                ("7", "Maior estoque"),
                ("8", "Menor estoque"),
                ("9", "Data término próxima"),
                ("10", "Data término distante"),
                ("11", "Data encomenda próxima"),
                ("12", "Data encomenda distante")
            ]
            while True:
                code, ordem_escolhida = d.menu(
                    "Ordenar por",
                    choices=escolhas_ordem,
                    title="Relatório - Custos de Produto - Ordenar",
                    ok_label="Aceitar",
                    cancel_label="Voltar",
                    width=70,
                    height=20,
                    timeout=timeout
                )
                if code == d.TIMEOUT:
                    continue
                if code != d.OK:
                    break

                ordem_map = {
                    "1": ("nome", "ASC"),
                    "2": ("nome", "DESC"),
                    "3": ("vendidos", "DESC"),
                    "4": ("vendidos", "ASC"),
                    "5": ("demanda", "DESC"),
                    "6": ("demanda", "ASC"),
                    "7": ("estoque", "DESC"),
                    "8": ("estoque", "ASC"),
                    "9": ("termino", "ASC"),
                    "10": ("termino", "DESC"),
                    "11": ("encomenda", "ASC"),
                    "12": ("encomenda", "DESC")
                }
                campo_ordem, direcao_ordem = ordem_map.get(ordem_escolhida, ("id", "ASC"))

                # ========= EXECUTAR QUERY =========
                sql = f"SELECT {', '.join(colunas_sel)} FROM custos_produto {where_clause} ORDER BY {campo_ordem} {direcao_ordem}"
                cursor.execute(sql, valores)
                dados = cursor.fetchall()

                # ========= FORMATAR =========
                dados_fmt = []
                for linha in dados:
                    linha_fmt = []
                    for idx, valor in enumerate(linha):
                        nome_coluna = colunas_sel[idx]
                        if nome_coluna in ("preco_lote", "preco_armazenamento") and valor is not None:
                            linha_fmt.append(f"R$ {valor:.2f}")
                        elif isinstance(valor, datetime):
                            linha_fmt.append(formatar_data_hora(valor))
                        elif isinstance(valor, date):
                            linha_fmt.append(formatar_data(valor))
                        else:
                            linha_fmt.append(valor)
                    dados_fmt.append(linha_fmt)

                headers_fmt = [col.replace("_", " ").capitalize() for col in colunas_sel]

                # ========= OPÇÕES =========
                while True:
                    titulo_tempo = tempo_formatado()
                    d.set_background_title(titulo_tempo)
                    timeout = timeout_para_proximo_minuto()

                    code, acao = d.menu(
                        "Opções",
                        choices=[("1", "Pré-visualização"), ("2", "Gerar CSV")],
                        title="Gerar Relatório - Custos de Produto",
                        ok_label="Aceitar",
                        cancel_label="Voltar",
                        timeout=timeout
                    )
                    if code == d.TIMEOUT:
                        continue
                    if code != d.OK:
                        break

                    if acao == "1":
                        texto = tabulate(dados_fmt, headers=headers_fmt, tablefmt="fancy_grid")
                        d.scrollbox(texto, width=200, height=60, title="Pré-visualização", exit_label="OK")
                    else:
                        with open("relatorio.csv", "w", newline="", encoding="utf-8") as f:
                            writer = csv.writer(f)
                            writer.writerow(headers_fmt)
                            writer.writerows(dados_fmt)

                        
                        d.msgbox("Relatório CSV gerado com sucesso: relatorio.csv", ok_label="OK")
                        return

# ----------------- RELATÓRIOS CSV -----------------
def configurar_relatorio():
    while True:
        titulo_tempo = tempo_formatado()
        d.set_background_title(titulo_tempo)
        timeout = timeout_para_proximo_minuto()
        code, tabela_sel = d.menu(
            "Tabelas",
            title="Gerar relatório - Configuração de relatório",
            choices=[
                ("1", "Produtos"),
                ("2", "Produtos Vendidos"),
                ("3", "Produtos Excluídos"),
                ("4", "Custos de Lote")
            ],
            ok_label="Aceitar",
            cancel_label="Voltar",
            timeout=timeout
        )
        if code == d.TIMEOUT:
            continue
        if code != d.OK:
            return

        tabela = tabelas.get(tabela_sel)

        if not tabela:
            return

        if tabela == "custos_produto":
            configurar_relatorio_custos()
            return

        cursor.execute(f"SHOW COLUMNS FROM {tabela}")
        colunas = [c[0] for c in cursor.fetchall()]

        while True:
            titulo_tempo = tempo_formatado()
            d.set_background_title(titulo_tempo)
            timeout = timeout_para_proximo_minuto()

            choices = [
                (str(i + 1), col.replace("_", " ").capitalize(), 1)
                for i, col in enumerate(colunas)
            ]
            tabela_fmt = tabela.replace("_", " ").title()
            if tabela_fmt == "Custos Produto":
                tabela_fmt = "Custos de Lote"

            code, colunas_idx = d.checklist(
                "Campos personalizáveis (ESPAÇO para desm.)",
                choices=choices,
                title=f"Gerar relatório - Configuração de relatório - {tabela_fmt}",
                ok_label="Aceitar",
                cancel_label="Voltar",
                timeout=timeout,
                width=70,
                height=20
            )

            if code == d.TIMEOUT:
                continue
            if code != d.OK or not colunas_idx:
                break

            colunas_sel = [colunas[int(i) - 1] for i in colunas_idx]

            # ========= FILTRO FIXO ==========
            campos_filtro = {
                "1": "id",
                "2": "nome",
                "3": "setor",
                "4": "distribuidor"
            }

            while True:
                code, filtros_marcados = d.checklist(
                    "Filtrar por (ESPAÇO para sel.)",
                    choices=[
                        ("1", "ID", False),
                        ("2", "Nome", False),
                        ("3", "Setor", False),
                        ("4", "Distribuidor", False)
                    ],
                    title=f"Gerar relatório - {tabela_fmt} - Filtrar",
                    cancel_label="Voltar",
                    ok_label="Aceitar",
                timeout=timeout
                )
                if code == d.TIMEOUT:
                    continue
                if code != d.OK:
                    break

                clausulas = []
                valores = []
                for indice in filtros_marcados:
                    campo = campos_filtro[indice]
                    code, termo = d.inputbox(
                        f"Digite o {campo.capitalize()}",
                        cancel_label="Voltar",
                        ok_label="Aceitar",
                        timeout=timeout
                    )
                    if code != d.OK:
                        continue
                    clausulas.append(f"{campo} LIKE ?")
                    valores.append(f"%{termo}%")

                where_clause = f"WHERE {' AND '.join(clausulas)}" if clausulas else ""

                # ========= ORDENAÇÃO ==========
                escolhas_ordem = [
                    ("1", "Validade mais próxima"),
                    ("2", "Validade mais longa"),
                    ("3", "Ordem alfabética A-Z"),
                    ("4", "Ordem alfabética Z-A"),
                    ("5", "Registro mais próximo"),
                    ("6", "Registro mais longo")
                ]
                if tabela == "produtos_excluidos":
                    escolhas_ordem += [
                        ("7", "Exclusão mais próxima"),
                        ("8", "Exclusão mais longa")
                    ]
            
                while True:
                    code, ordem_escolhida = d.menu(
                        "Ordenar por",
                        choices=escolhas_ordem,
                        title=f"Gerar relatório - {tabela_fmt} - Ordenar",
                        cancel_label="Voltar",
                        ok_label="Aceitar",
                        timeout=timeout
                    )
                    if code == d.TIMEOUT:
                        continue
                    if code != d.OK:
                        break

                    ordem_map = {
                        "1": ("validade", "ASC"),
                        "2": ("validade", "DESC"),
                        "3": ("nome", "ASC"),
                        "4": ("nome", "DESC"),
                        "5": ("data", "DESC"),
                        "6": ("data", "ASC"),
                        "7": ("data_exclusao", "DESC") if tabela == "produtos_excluidos" else None,
                        "8": ("data_exclusao", "ASC") if tabela == "produtos_excluidos" else None
                    }
                    campo_ordem, direcao_ordem = ordem_map.get(ordem_escolhida, ("id", "ASC"))

                    sql = f"SELECT {', '.join(colunas_sel)} FROM {tabela} {where_clause} ORDER BY {campo_ordem} {direcao_ordem}"
                    cursor.execute(sql, valores)
                    dados = cursor.fetchall()

                    # ========= FORMATAR ==========
                    dados_fmt = []
                    for linha in dados:
                        linha_fmt = []
                        for idx, valor in enumerate(linha):
                            nome_coluna = colunas_sel[idx]
                            if nome_coluna in ("preco_lote", "preco_armazenamento") and valor is not None:
                                linha_fmt.append(f"R$ {valor:.2f}")
                            elif isinstance(valor, datetime):
                                linha_fmt.append(formatar_data_hora(valor))
                            elif isinstance(valor, date):
                                linha_fmt.append(formatar_data(valor))
                            else:
                                linha_fmt.append(valor)
                        dados_fmt.append(linha_fmt)

                    headers_fmt = [col.replace("_", " ").capitalize() for col in colunas_sel]

                    # ========= OPÇÕES ==========
                    while True:
                        titulo_tempo = tempo_formatado()
                        d.set_background_title(titulo_tempo)
                        timeout = timeout_para_proximo_minuto()

                        code, acao = d.menu(
                            "Opções",
                            choices=[("1", "Pré-visualização"), ("2", "Gerar CSV")],
                            title=f"Gerar relatório - {tabela_fmt}",
                            ok_label="Aceitar",
                            cancel_label="Voltar",
                            timeout=timeout
                        )
                        if code == d.TIMEOUT:
                            continue
                        if code != d.OK:
                            break

                        if acao == "1":
                            texto = tabulate(dados_fmt, headers=headers_fmt, tablefmt="fancy_grid")
                            d.scrollbox(texto, width=200, height=60, title="Pré-visualização", exit_label="OK")
                        else:
                            with open("relatorio.csv", "w", newline="", encoding="utf-8") as f:
                                writer = csv.writer(f)
                                writer.writerow(headers_fmt)
                                writer.writerows(dados_fmt)

                            resultado = copiar_para_pendrive("/home/maximus/relatorio.csv")

                            if resultado:
                                d.msgbox("Relatório CSV gerado e transferido com sucesso: relatorio.csv", ok_label="OK")
                            else:
                                d.msgbox("Relatório CSV gerado com sucesso: relatorio.csv", ok_label="OK")
                            return

# ----------------- MENU PRINCIPAL -----------------
def menu():
    while True:
        titulo_tempo = tempo_formatado()
        d.set_background_title(titulo_tempo)
        timeout = timeout_para_proximo_minuto()
        code, sel = d.menu(
            "Opções",
            title="Gerar relatório",
            choices=[("1", "Custos de Lote"), ("2", "Modelo de reabastecimento"), ("3", "Configuração de relatório (CSV)")],
            ok_label="Aceitar",
            cancel_label="Voltar",
            timeout=timeout
        )
        if code == d.TIMEOUT:
            continue
        if code != d.OK:
            break

        if sel == "1":
            while True:
                titulo_tempo = tempo_formatado()
                d.set_background_title(titulo_tempo)
                timeout = timeout_para_proximo_minuto()

                code, tag = d.menu(
                    "Escolha uma opção",
                    title="Gerar relatório - Custos de Lote",
                    choices=[("1", "Exibir custos"), ("2", "Alterar/Excluir custos"), ("3", "Cadastrar custos")],
                    ok_label="Aceitar",
                    cancel_label="Voltar",
                    timeout=timeout
                )
                if code == d.TIMEOUT:
                    continue
                if code != d.OK:
                    break
                if tag == "1":
                    custos_exibir()
                elif tag == "2":
                    custos_alterar_excluir()
                elif tag == "3":
                    custos_cadastrar()

        elif sel == "2":
            modelo_reabastecimento()
        elif sel == "3":
            configurar_relatorio()

if __name__ == "__main__":
    menu()
    cursor.close()
    conn.close()




