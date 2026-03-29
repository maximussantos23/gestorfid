# GestorFID 

Projeto de pesquisa 2025 - Trabalho de Conclusão do Curso Técnico em Eletrônica  
(FETLSVC - Novo Hamburgo/RS)

Autores:

- Mateus Ramires Hörlle
- Maximus Matheus Rosa Santos

Tecnologias: Python, SQL, Raspberry Pi, RFID, EPC Gen2

## Contexto

- Num estabelecimento comercial, sistemas de PDV normalmente utilizam códigos de barras para realizar leituras de produtos e registrar pagamentos;
- Esse sistema pode ser limitado em relação ao monitoramento em tempo real de produtos, especialmente para prazos de validade e escassez de itens;
- Ao integrar um sistema RFID (Identificação por Radiofrequência), é possível não apenas garantir esse monitoramento, mas também a individualização analítica de cada produto.

## Projeto

Hardware utilizado:

- Raspberry Pi 3 (Debian 12 "Bookworm") - Servidor local
- Leitor RFID R200 (módulo UHF serial)
- Antena cerâmica UHF FA-305A 5.5 dBi
- Tags RFID Wet Inlay NXP U8

## Middleware

O middleware é responsável por intermediar a comunicação entre o leitor RFID, o banco de dados e a interface de operação do sistema. Ele executa no Raspberry Pi e realiza o processamento das leituras das tags, gerenciamento de dados e controle das operações do sistema.

O software foi desenvolvido em Python 3, utilizando comunicação UART serial para interação com o módulo RFID R200 e MariaDB para persistência das informações. Possui seis serviços principais de operação.

### Serviços

- Leitura em tempo real
- Dar baixa
- Nova gravação
- Banco de dados
- Gerar relatório
- Configurações

### Principais funções

- Leitura em tempo real de tags RFID
- Cadastro e gravação de novos produtos em etiquetas EPC Gen2
- Consulta e gerenciamento do banco de dados
- Baixa automática de produtos
- Geração de relatórios de estoque
- Monitoramento de validade e escassez de itens

## Ambientes suportados

### Produção (recomendado)
- Raspberry Pi (Debian-based)
- Integração completa com leitor RFID

### Desenvolvimento
- Ubuntu (nativo)
- WSL (Windows Subsystem for Linux)

Observação:
Em Ubuntu/WSL, funcionalidades dependentes de hardware (como leitura RFID) podem não funcionar ou exigir adaptação.

### Dependências do sistema
- sudo apt update
- sudo apt install dialog python3-venv python3-pip mariadb-server -y
- sudo apt install libmariadb-dev
- sudo apt install mariadb-server

### Instalação

- python3 -m venv venv
  
- source venv/bin/activate

- pip install -r requirements.txt

- mysqldump -u root -p --database estoque > schema.sql

#### Setup do banco de dados (MariaDB)

##### 1. Iniciar o serviço
- sudo service mariadb start

##### 2. Criar banco e usuário (Exemplo)
- sudo mysql -e "
CREATE DATABASE estoque;
CREATE USER 'usuario'@'localhost' IDENTIFIED BY 'senha123';
GRANT ALL PRIVILEGES ON estoque.* TO 'usuario'@'localhost';
FLUSH PRIVILEGES;
"

##### 3. Importar schema
- mysql -u usuario -p estoque < database/schema.sql

## Execução

Na primeira execução, caso no Raspberry Pi, é necessário inserir manualmente a rede em Configurações.
Somente após, será possível utilizar por conexão remota (SSH) em rede local.

Senha padrão de inicialização por SSH: 123456

## Relatório

- https://docs.google.com/document/d/1XaPjWHtfMITkK5YDtYTN7xeungY4HFr7ofbHfELuuNM/edit?usp=sharing

