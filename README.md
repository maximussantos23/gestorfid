# GestorFID
Projeto de pesquisa 2025 - Trabalho de conclusão do curso técnico de eletrônica (FETLSVC - NH/RS)

Autores:

Maximus R. Santos
Mateus R. Hörlle

Python, SQL, Raspberry Pi, RFID, EPC Gen2

# Contexto
 
- Num estabelecimento, o sistema PDV utilizado normalmente se utiliza de código de barras para se efetuar exames e pagamentos;
- Esse sistema pode ser limitado com relação a monitoramento em tempo real de produtos, em específico, para prazos de validade e escassez de itens;
- Ao integrarmos um sistema RFID (Identificação por Radiofrequência) podemos, não só garantir esse tipo de monitoramento, mas individualização analítica de cada produto.

# Projeto

- Raspberry Pi 3 Debian 12 "Bookworm" (Servidor local);
- Leitor RFID R200 (Módulo UHF-serial);
- Antena Cerâmica UHF FA-305A 5,5 dBi;
- Tags RFID Wet Inlay NXP U8.

# Middleware

- O middleware é responsável por intermediar a comunicação entre o leitor RFID, o banco de dados e a interface de operação do sistema. Ele executa no Raspberry Pi e realiza o processamento das leituras das tags, gerenciamento de dados e controle das operações do sistema.
- O software foi desenvolvido em Python 3, utilizando comunicação UART serial para interação com o módulo RFID R200 e MariaDB para persistência das informações.

Principais Funções:

- Leitura em tempo real de tags RFID;
- Cadastro e gravação de novos produtos em etiquetas EPC Gen2;
- Consulta e gerenciamento do banco de dados;
- Baixa automática de produtos;
- Geração de relatórios de estoque;
- Monitoramento de validade e escassez de itens.

