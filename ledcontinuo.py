from gpiozero import LED
import mariadb, time
from bancodedados import obter_produtos, em_prazo_de_vencimento

led = LED(17)
led_estado = None  # None, 'estatico', 'piscando'

while True:
    try:
        config = {
            'user': 'usuario',
            'password': 'senha123',
            'host': 'localhost',
            'database': 'estoque'
        }

    except mariadb.Error as e:
        print(f"Erro ao conectar ao MariaDB: {e}")
        exit(1)

    try:
        conn = mariadb.connect(**config)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM produtos")
        produtos = cursor.fetchall()
        cursor.execute("SELECT dias FROM vencimento LIMIT 1")
        prazo = cursor.fetchone()[0] or 0

        item_vencido = any(em_prazo_de_vencimento(p[3], prazo) for p in produtos)

        if item_vencido:
            if led_estado != 'piscando':
                led.blink(on_time=1, off_time=1, n=None)
                led_estado = 'piscando'
        else:
            if led_estado != 'estatico':
                led.on()
                led_estado = 'estatico'

        conn.close()

    except Exception as e:
        print(f"[ERRO LED] {e}")

    time.sleep(1)


