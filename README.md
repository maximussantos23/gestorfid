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

O software foi desenvolvido em **Python 3**, utilizando comunicação **UART serial** para interação com o módulo RFID R200 e **MariaDB** para persistência das informações.

### Principais funções

- Leitura em tempo real de tags RFID
- Cadastro e gravação de novos produtos em etiquetas EPC Gen2
- Consulta e gerenciamento do banco de dados
- Baixa automática de produtos
- Geração de relatórios de estoque
- Monitoramento de validade e escassez de itens

## Requisitos do Sistema



## Instalação



## Execução

