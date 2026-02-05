# Recovery Tool

Uma ferramenta gráfica moderna para análise forense e recuperação de dados em discos físicos (Raw Drive Analysis), desenvolvida em Python com CustomTkinter.

![Status](https://img.shields.io/badge/Status-Finished-green) ![Python](https://img.shields.io/badge/Python-3.x-blue)

## Funcionalidades
- **Varredura de Baixo Nível:** Leitura direta de setores do disco (PhysicalDrive).
- **Recuperação por Assinatura:** Identifica JPG, PNG, PDF, MP4 e JSON via *magic numbers*.
- **Interface Moderna:** UI escura amigável com visualização de miniaturas em tempo real.
- **Multilíngue:** Suporte nativo para Português (BR) e Inglês (US).
- **Filtros Inteligentes:** Busca por conteúdo (strings) e filtragem por tipo de arquivo.

## Como rodar o código
Necessário privilégios de Administrador para acesso direto ao disco.

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute o arquivo:
   ```bash
   python fileRecovery.pyw
   ```

## Como compilar (Build)
Para gerar o executável standalone com ícones inclusos:
   ```bash
   pyinstaller --noconsole --onefile --collect-all customtkinter --icon=icon.ico --add-data "icon.ico;." --add-data "icon.png;." fileRecovery.pyw
   ```

## Aviso Legal
Esta ferramenta acessa discos físicos. O uso indevido pode causar perda de dados ou instabilidade.