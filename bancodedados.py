#!/usr/bin/env python3
import mariadb
import os
import time
from datetime import datetime, date, timedelta
from dialog import Dialog
from tabulate import tabulate

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
    "3": "produtos_excluidos"
}

def tempo_formatado():
    agora = time.localtime()
    return time.strftime("GestorFID - %d-%m-%Y %H:%M", agora)

def timeout_para_proximo_minuto():
    tempo = tempo_formatado()
    d.set_background_title(f"{tempo}")
    agora = time.localtime()
    return 60 - agora.tm_sec

def formatar_data(data):
    if isinstance(data, (datetime, date)):
        return data.strftime("%d-%m-%Y")
    try:
        return datetime.strptime(str(data), "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return str(data)

def formatar_data_hora(data_hora):
    if isinstance(data_hora, (datetime, date)):
        return data_hora.strftime("%d-%m-%Y %H:%M:%S")
    try:
        return datetime.strptime(str(data_hora), "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y %H:%M:%S")
    except Exception:
        return str(data_hora)

def preencher_campos_vazios(prod_tuple):
    #Converte tupla em lista para poder mudar
    lst = list(prod_tuple)

    #Estrutura esperada: RSSI, ID, EPC, nome, validade, setor, distribuidor, data
    for i in range(len(lst)):
        if lst[i] is None or lst[i] == "":
            lst[i] = "-----"
    return tuple(lst)

def obter_prazo_vencimento():
    """Lê o número de dias de alerta na tabela 'vencimento' (coluna 'dias')."""
    try:
        cursor.execute("SELECT dias FROM vencimento")
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except mariadb.Error:
        return 0

def parse_data_para_date(valor):
    if not valor:
        return None
    s = str(valor)
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    return None

def em_prazo_de_vencimento(validade, dias_alerta):
    """True se vencida (delta<0) ou dentro do prazo (0<=delta<=dias_alerta)."""
    v = parse_data_para_date(validade)
    if v is None:
        return False
    delta = (v - date.today()).days
    return delta <= dias_alerta

def escolher_valor_existente(campo, titulo="Selecionar/inserir valor"):
    try:
        cursor.execute(f"""
            SELECT DISTINCT {campo} 
            FROM produtos 
            WHERE {campo} IS NOT NULL AND {campo} != ''
            ORDER BY nome
        """)
        resultados = cursor.fetchall()
    except mariadb.Error as e:
        d.msgbox(f"Erro ao buscar valores já existentes: {e}", ok_label="Aceitar")
        return None

    #Converte para lista simples
    valores = [r[0] for r in resultados]

    if not valores:
        #Se não há registros, obriga inserir novo
        code, novo_valor = d.inputbox(f"Nenhum valor encontrado. Digite o {campo}",
            ok_label="Aceitar", cancel_label="Voltar")
        return novo_valor if code == d.OK else None

    #Cria opções numeradas para menu
    opcoes = [(str(i+1), v) for i, v in enumerate(valores)]

    while True:
        timeout = timeout_para_proximo_minuto()
        code, escolhido = d.menu(
            f"Selecione {campo} já existente ou insira um novo",
            choices=opcoes,
            title=titulo,
            ok_label="Aceitar",
            extra_button=True,
            extra_label="Novo",
            cancel_label="Voltar",
            height=20,
            width=80,
            timeout=timeout
        )

        if code == d.OK: #Usar existente
            indice = int(escolhido) - 1
            return valores[indice]
        elif code == d.EXTRA: #Inserir novo
            code, novo_valor = d.inputbox(f"Digite o novo {campo}", ok_label="Aceitar", cancel_label="Voltar")
            return novo_valor if code == d.OK else None
        elif code == d.TIMEOUT:
            continue
        else:
            return None #Voltar

def obter_produtos(tabela, filtro_sql="", valores=()):
    cursor.execute(f"SELECT * FROM {tabela} {filtro_sql}", valores)
    return cursor.fetchall()

def mostrar_tabela(produtos, tabela):
    if not produtos:
        d.msgbox("Nenhum produto encontrado.", ok_label="Aceitar")
        return

    linhas = []
    for p in produtos:
        p_normalizado = preencher_campos_vazios(p)

        linha = [
            str(p_normalizado[0]),
            p_normalizado[2],
            formatar_data(p_normalizado[3]),
            p_normalizado[4],
            p_normalizado[5],
            formatar_data_hora(p_normalizado[6])
        ]
        if tabela in ("produtos_vendidos", "produtos_excluidos"):
            linha.append(formatar_data_hora(p_normalizado[7]))
            if tabela == "produtos_excluidos":
                linha.append(p_normalizado[8])

        linhas.append(linha)

    headers = ["ID", "Nome", "Validade", "Setor", "Distribuidor", "Data/hora registro"]
    if tabela == "produtos_vendidos":
        headers.append("Data venda")
    elif tabela == "produtos_excluidos":
        headers.append("Data/hora exclusão")
        headers.append("Motivo(s)")

    texto = tabulate(linhas, headers=headers, tablefmt="fancy_grid")
    d.scrollbox(texto, height=60, width=200, title="Produto(s) encontrado(s)", exit_label="OK")
    return produtos

def aplicar_filtro(tabela, retornar_resultado=False, modo="padrao", repetir=True, modo_escolhido="padrao", produtos_lidos=[], campo_ordem=None, direcao_ordem=None):
    tipo = "ativos" if tabela == "produtos" else ("vendidos" if tabela == "produtos_vendidos" else "excluídos")
    if modo == "padrao":
        titulo = f"Banco de dados - Produtos {tipo} - Ordenar"
    else:
        titulo = f"Leitura em tempo real - Leitura {modo_escolhido} - Ordenar"
    while True:
        if modo == "padrao":
            timeout = timeout_para_proximo_minuto()

            campos = {
                "1": "id",
                "2": "nome",
                "3": "setor",
                "4": "distribuidor"
            }

            #Cria uma janela do tipo lista, sendo possivel escolher vários ou nenhum filtro com ESPAÇO
            code, filtros_marcados = d.checklist(
                "Filtrar por (ESPAÇO para sel.)",
                choices=[
                    ("1", "ID", False),
                    ("2", "Nome", False),
                    ("3", "Setor", False),
                    ("4", "Distribuidor", False)
                ],
                title=f"Banco de dados - Produtos {tipo} - Filtrar",
                cancel_label="Voltar",
                ok_label="Aceitar",
                timeout=timeout
            )

            if code == d.TIMEOUT:
                continue
            if code != d.OK:
                #Se o usuário estiver alterando/excluindo, e quiser sair logo no inicio do filtro, terá que sair da função alterar_ou_excluir, para isso, retornamos VOLTAR para indicar que é para sair das duas funções e retornar para o menu de aplicações
                return "VOLTAR", None, None, None, None

        while True:
            where_clause = "" #Evita erro caso repetir = False, na formação do comando SQL
            valores = []
            if repetir==True: #Condição para mostrar menu de ordenação apenas uma vez em leitura em tempo real
                timeout = timeout_para_proximo_minuto()

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

                code, ordem_escolhida = d.menu(
                    "Ordenar por",
                    choices=escolhas_ordem,
                    title=titulo,
                    cancel_label="Voltar",
                    ok_label="Aceitar",
                    timeout=timeout
                )

                if code == d.TIMEOUT:
                    continue
                if code != d.OK:
                    if modo == "leitura_em_tempo_real":
                        return "VOLTAR", None, None, None, None
                    else:
                        break

                ordem_map = {
                    "1": ("validade", "ASC"),
                    "2": ("validade", "DESC"),
                    "3": ("nome", "ASC"),
                    "4": ("nome", "DESC"),
                    "5": ("data", "DESC"),
                    "6": ("data", "ASC"),
                    "7": ("data_exclusao", "DESC"),
                    "8": ("data_exclusao", "ASC")
                }

                #campo_ordem retorna "validade", etc. direcao_ordem retorna "ASC", "DESC".
                campo_ordem, direcao_ordem = ordem_map.get(ordem_escolhida)
                if not campo_ordem:
                    continue

                clausulas = []

                if modo == "padrao":
                    retorna = 0
                    #O for itera apenas os indices presentes em filtros_marcados
                    for indice in filtros_marcados:
                        campo = campos[indice]
                        timeout = timeout_para_proximo_minuto()
                        code, termo = d.inputbox(f"Digite o {campo.capitalize()}", cancel_label="Voltar", ok_label="Aceitar", timeout=timeout)
                        if code != d.OK:
                            retorna = 1
                            break
                        clausulas.append(f"{campo} LIKE ?")
                        valores.append(f"%{termo}%")
                    #Quando o for se encerrar, entra aqui
                    if retorna == 1:
                        continue
                    else:
                        #Isso garante que se houver ao menos uma clausula, ele cria o comando SQL. Caso não tiver, retorna uma string vazia e sql organiza apenas por ordem
                        where_clause = f"WHERE {' AND '.join(clausulas)}" if clausulas else ""

            sql = f"SELECT * FROM {tabela} {where_clause} ORDER BY {campo_ordem} {direcao_ordem}"

            tags_nao_cadastradas = []
            try:
                cursor.execute(sql, valores)
                produtos = cursor.fetchall()
            except mariadb.Error as e:
                d.msgbox(f"Erro ao executar a consulta: {e}")
                return []

            #Laço para filtrar produtos_lidos
            if modo == "leitura_em_tempo_real":
                produtos_filtrados = []
                tags_nao_cadastradas = []
                if produtos:
                    for i in produtos: #Para cada produto da tabela do database, compara com tabela de produtos lidos
                        for y in produtos_lidos:
                            if i[1] == y[2]: #Se as EPC’s forem iguais
                                produtos_filtrados.append(y)
                            if y[3] == "Tag não cadastrada" and y not in tags_nao_cadastradas:
                                tags_nao_cadastradas.append(y)
                    produtos = []
                    produtos = produtos_filtrados + tags_nao_cadastradas
                else:
                    produtos = produtos_lidos

            #Se quisermos essa tabela filtrada para alterar/excluir alguma coisa
            if retornar_resultado:
                return produtos, campo_ordem, direcao_ordem, valores, where_clause
            #Se quisermos apenas exibir ela
            else:
                mostrar_tabela(produtos, tabela)
                return []

def alterar_ou_excluir(tabela, modo="padrao", modo_escolhido="padrao", tempo=0, txt="padrao", repetir=True, produtos_lidos=[], campo_ordem=None, direcao_ordem=None):
    tipo = "ativos"
    dias_alerta_venc = obter_prazo_vencimento()
    while True:
        if modo == "padrao":
            titulo = f"Banco de dados - Produtos {tipo} - Alterar/Excluir"
        else:
            titulo = f"Leitura em tempo real - {txt}"
            if modo_escolhido == "contínua":
                titulo += f" - {str(tempo)} s"
        produtos, campo_ordem, direcao_ordem, valores, where_clause = aplicar_filtro(tabela, retornar_resultado=True, modo=modo, repetir=repetir, modo_escolhido=modo_escolhido, produtos_lidos=produtos_lidos, campo_ordem=campo_ordem, direcao_ordem=direcao_ordem)
        if produtos == "VOLTAR":
            return "VOLTAR", None

        if not produtos:
            d.msgbox("Nenhum produto encontrado.", ok_label="Aceitar")
            return "VOLTAR", None

        while True:
            cabecalho = "ID | Nome | Validade | Setor | Distribuidor"
            if modo == "leitura_em_tempo_real":
                cabecalho = "RSSI (dBm) | EPC | " + cabecalho
            else:
                cabecalho += " | Data/hora registro"

            produtos_nao_cadastrados  = []
            produtos_formatados = []
            opcoes = []

            for i, p in enumerate(produtos, start=1):
                if modo == "leitura_em_tempo_real":
                    rssi_fmt = str(p[0]).rjust(5)
                    epc_fmt = str(p[2]).ljust(24)

                    #Detectar tag não cadastrada
                    if p[3] == "Tag não cadastrada":
                        id_str = "-----"
                        nome = "Tag não cadastrada".ljust(25)
                        validade = setor = dist = "-----".ljust(10)
                        linha = f"{rssi_fmt} | {epc_fmt} | {id_str} | {nome} | {validade} | {setor} | {dist}"
                        produtos_nao_cadastrados.append(p)
                        opcoes.append((str(i), linha))
                    else:
                        #Produto cadastrado normal
                        
                        try:
                            p_normalizado = preencher_campos_vazios(p)
                            rssi, id_, epc_val, nome, validade, setor, distribuidor, data = p_normalizado
                            id_str = str(id_).rjust(5)
                            nome_fmt = nome[:25].ljust(25)
                            validade_fmt = formatar_data(validade).ljust(10)
                            setor_fmt = setor[:10].ljust(10)
                            dist_fmt = distribuidor[:15].ljust(15)
                            linha = f"{rssi_fmt} | {epc_fmt} | {id_str} | {nome_fmt} | {validade_fmt} | {setor_fmt} | {dist_fmt}"
                            produtos_formatados.append(p_normalizado)
                            validade_para_verificar = validade
                            linha_exibicao = linha
                            if em_prazo_de_vencimento(validade_para_verificar, dias_alerta_venc):
                                linha_exibicao = f"\\Z1{linha}\\Zn"  #vermelho só na exibição
                            opcoes.append((str(i), linha_exibicao))

                        except Exception as e:
                            continue
                else:
                    p = preencher_campos_vazios(p)
                    id_str = str(p[0]).rjust(5)
                    nome = p[2][:30].ljust(30)
                    validade = formatar_data(p[3]).ljust(10)
                    setor = p[4][:12].ljust(12)
                    dist = p[5][:20].ljust(20)
                    data = formatar_data_hora(p[6]).ljust(10)
                    linha = f"{id_str} | {nome} | {validade} | {setor} | {dist} | {data}"
                    produtos_formatados.append(p)
                    linha_exibicao = linha
                    validade_para_verificar = p[3]
                    if em_prazo_de_vencimento(validade_para_verificar, dias_alerta_venc):
                        linha_exibicao = f"\\Z1{linha}\\Zn"
                    opcoes.append((str(i), linha_exibicao))

            if modo_escolhido == "contínua":
                timeout_para_proximo_minuto()
                timeout=tempo #Faz com que a tabela de produtos atualize a cada tempo de ciclo escolhido em leitura em tempo real
            else:
                timeout = timeout_para_proximo_minuto()
                #Menu de escolha de produtos
            cursor.execute("SELECT * FROM vencimento")
            dias = cursor.fetchone()
            code, escolhido = d.menu(
                f"Produto(s) encontrado(s)\nPrazo p/ aviso de vencimento próx.: {dias[0]} dias\n\n{cabecalho}",
                height=30,
                width=130,
                title=titulo,
                choices=opcoes,
                ok_label="Alterar",
                cancel_label="Voltar",
                extra_button=True,
                extra_label="Excluir",
                timeout=timeout,
                colors=True
            )

            if code == d.TIMEOUT:
                if modo_escolhido == "contínua":
                    produtos_lidos = produtos_formatados + produtos_nao_cadastrados
                    return produtos_lidos, campo_ordem, direcao_ordem
                else:
                    continue
            if code != d.OK and code != d.EXTRA:
                produtos_lidos = produtos_formatados + produtos_nao_cadastrados
                return "VOLTAR", produtos_lidos

            try:
                indice = int(escolhido) - 1
                prod = produtos_formatados[indice]
            except (ValueError, IndexError):
                d.msgbox("Essa tag ainda não foi cadastrada no sistema.", ok_label="Aceitar")
                continue

            if modo == "leitura_em_tempo_real":
                rssi, *prod = prod #Tira rssi de prod para fazer a procura em SQL

            #Ação Alterar
            if code == d.OK:
                campos_editaveis = {
                    "1": "nome",
                    "2": "validade",
                    "3": "setor",
                    "4": "distribuidor"
                }

                while True:
                    timeout = timeout_para_proximo_minuto()
                    code, campo_alt = d.menu("Campo para alterar", title=f"Alterar produto ID {prod[0]}", choices=[
                        ("1", "Nome"),
                        ("2", "Validade"),
                        ("3", "Setor"),
                        ("4", "Distribuidor")
                    ], timeout=timeout, cancel_label="Voltar", ok_label="Aceitar")

                    if code == d.TIMEOUT:
                        continue
                    if code != d.OK:
                        break

                    campo_alt = campos_editaveis.get(campo_alt)

                    if campo_alt in ["nome", "setor", "distribuidor"]:
                        valor = escolher_valor_existente(campo_alt.capitalize(), titulo=f"Selecionar/inserir {campo_alt}")
                        if not valor: #Usuário cancelou
                            continue
                        valor_formatado = valor
                    elif campo_alt == "validade":
                        code, data = d.calendar("TAB para trocar o campo",title="Selecionar validade", height=3, cancel_label="Voltar", ok_label="Aceitar")
                        if code != d.OK:
                            continue
                        valor = f"{data[2]:04d}-{data[1]:02d}-{data[0]:02d}"
                        valor_formatado = formatar_data(valor)

                    confirmar = d.yesno(f"Alterar {campo_alt} do produto ID {prod[0]} para {valor_formatado}?", yes_label="Sim", no_label="Não")
                    if confirmar == d.OK:
                        cursor.execute(f"UPDATE produtos SET {campo_alt} = ? WHERE id = ?", (valor, prod[0]))
                        conn.commit()
                        d.msgbox("Produto alterado com sucesso.")
                        #Atualiza a lista inteira
                        sql = f"SELECT * FROM {tabela} {where_clause} ORDER BY {campo_ordem} {direcao_ordem}"
                        cursor.execute(sql, valores)
                        produtos_tabela = cursor.fetchall()
                        
                        if modo == "leitura_em_tempo_real":
                            produtos_nao_cadastrados = [p for p in produtos if p[3] == "Tag não cadastrada"]
                            produtos_validos = [p for p in produtos if not (p[0] is None and p[3] != "Tag não cadastrada")]

                            # Cria o mapa de RSSI só com produtos válidos
                            rssi_map = {p[1]: p[0] for p in produtos_validos}

                            # Atualiza produtos com RSSI, descartando os inválidos
                            produtos_atualizados = []
                            for linha in produtos_tabela:
                                id = linha[0]
                                rssi = rssi_map.get(id, None)
                                if rssi is None and linha[2] != "Tag não cadastrada":
                                    continue  # remove produto indesejado
                                produtos_atualizados.append((rssi,) + linha)

                            # Junta produtos não cadastrados (com RSSI que já tinham)
                            produtos = produtos_atualizados + produtos_nao_cadastrados
                        else:
                            produtos=produtos_tabela
                        break #Volta pra janela de produtos para alteração/exclusão

            #Ação Excluir
            elif code == d.EXTRA:
                while True:
                    timeout = timeout_para_proximo_minuto()
                    code, motivos = d.checklist(
                        "Motivo(s) da exclusão (ESPAÇO para sel.)",
                        choices=[
                            ("1", "Validade expirada", False),
                            ("2", "Roubado/Furtado", False),
                            ("3", "Item perdido/danificado", False),
                            ("4", "Tag perdida/danificada", False)
                        ],
                        title=f"Excluir produto ID {prod[0]}",
                        ok_label="Aceitar",
                        cancel_label="Voltar",
                        timeout=timeout
                    )

                    if code == d.TIMEOUT:
                        continue
                    if code != d.OK:
                        break

                    motivos_map = {
                        "1": "Validade expirada",
                        "2": "Roubado/Furtado",
                        "3": "Item perdido/estragado",
                        "4": "Tag perdida/estragada"
                    }
                    motivo_str = ", ".join([motivos_map[m] for m in motivos])

                    confirmar = d.yesno(f"Excluir o produto ID {prod[0]}? (IRREVERSÍVEL)", yes_label="Sim", no_label="Não")
                    if confirmar == d.OK:
                        cursor.execute("""
                            INSERT INTO produtos_excluidos 
                                (id, epc, nome, validade, setor, distribuidor, data, data_exclusao, motivo) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (prod[0], prod[1], prod[2], prod[3], prod[4], prod[5], prod[6], datetime.now(), motivo_str))
                        cursor.execute("DELETE FROM produtos WHERE id = ?", (prod[0],))
                        conn.commit()
                        d.msgbox("Produto excluído com sucesso.")
                        del produtos[indice]
                        break

def menu_tabela(tabela):
    while True:
        timeout = timeout_para_proximo_minuto()
        tipo = "ativos" if tabela == "produtos" else ("vendidos" if tabela == "produtos_vendidos" else "excluídos")

        opcoes = [
            ("1", "Exibir todos os produtos"),
            ("2", "Filtrar produto(s)")
        ]
        if tabela == "produtos":
            opcoes.append(("3", "Alterar/Excluir produto(s)"))

        code, tag = d.menu("O que quer fazer?", title=f"Banco de dados - Produtos {tipo}", choices=opcoes, timeout=timeout, cancel_label="Voltar", ok_label="Aceitar")

        if code == d.TIMEOUT:
            continue
        if code != d.OK:
            break
        elif tag == "1":
            produtos = obter_produtos(tabela)
            mostrar_tabela(produtos, tabela)
        elif tag == "2":
            aplicar_filtro(tabela)
        elif tag == "3" and tabela == "produtos":
            alterar_ou_excluir(tabela)

def menu():
    while True:
        timeout = timeout_para_proximo_minuto()
        code, opcao = d.menu("Tabela de produtos", title="Banco de dados", choices=[
            ("1", "Ativos"),
            ("2", "Vendidos"),
            ("3", "Excluídos")
        ], timeout=timeout, cancel_label="Voltar", ok_label="Aceitar")

        if code == d.TIMEOUT:
            continue
        if code != d.OK:
            return

        tabela_escolhida = tabelas.get(opcao)
        if tabela_escolhida:
            menu_tabela(tabela_escolhida)

if __name__ == "__main__":
    menu()
    cursor.close()
    conn.close()







