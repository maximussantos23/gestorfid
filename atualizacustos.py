import mariadb
import time
import math
from datetime import datetime, timedelta

config = {
    'user': 'usuario',
    'password': 'senha123',
    'host': 'localhost',
    'database': 'estoque'
}

def atualizar_reabastecimento():
    try:
        conn = mariadb.connect(**config)
        cursor = conn.cursor()

        MARGEM = 14
        hoje = datetime.now().date()

        cursor.execute("SELECT id, nome FROM custos_produto")
        produtos_custos = cursor.fetchall()

        for prod_id, nome in produtos_custos:
            # Pega os dias para analise
            cursor.execute("""
                SELECT dias_analise FROM vencimento
            """)
            dias_analise = int(cursor.fetchone()[0])            

            # Custos e lead time
            cursor.execute("""
                SELECT preco_lote, preco_armazenamento, dias_entrega, validade_dias
                FROM custos_produto
                WHERE id=?
            """, (prod_id,))
            dados = cursor.fetchone()
            if not dados:
                continue

            preco_lote, preco_armazenamento, dias_entrega, validade_dias = dados














            # Vendas nos últimos X dias
            data_inicio = hoje - timedelta(days=dias_analise)
            cursor.execute("""
                SELECT COUNT(*) FROM produtos_vendidos
                WHERE nome=? AND data_venda >= ?
            """, (nome, data_inicio))
            vendidos = cursor.fetchone()[0]

            demanda = round(vendidos / dias_analise, 2) if dias_analise else 0

            # Estoque atual
            cursor.execute("SELECT COUNT(*) FROM produtos WHERE nome=?", (nome,))
            estoque = cursor.fetchone()[0]

            # Q* de Wilson
            preco_armazenamento_ajustado = preco_armazenamento * dias_analise / 30
            demanda_total = demanda * dias_analise
            Q = math.sqrt((2 * float(demanda_total) * float(preco_lote)) / float(preco_armazenamento_ajustado)) if preco_armazenamento_ajustado else 0

            # Limite por validade
            max_validade = demanda * (validade_dias - MARGEM)
            Q_final = min(Q, max_validade)

            # Ajuste pelo estoque
            Q_pedido = max(0, Q_final - estoque)

            # Datas
            dias_ate_termino = estoque / demanda if demanda else 0
            data_termino = hoje + timedelta(days=dias_ate_termino)
            data_pedido = data_termino - timedelta(days=dias_entrega)

            cursor.execute("""
                UPDATE custos_produto
                SET vendidos=?, demanda=?, estoque=?, termino=?, encomenda=?, Q_pedido=?, Q_final=?
                WHERE id=?
            """, (vendidos, demanda, estoque, data_termino, data_pedido, Q_pedido, Q_final, prod_id))

        conn.commit()
        cursor.close()
        conn.close()

    except mariadb.Error as e:
        print(f"Erro no banco: {e}")

def menu():
    while True:
        atualizar_reabastecimento()
        time.sleep(10)

if __name__ == "__main__":
    menu()


