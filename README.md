# Cloud Book Reader

Leitor de livros EPUB com integração Google Cloud.

## Funcionalidades

- **Upload de EPUB** — Arraste e solte ou selecione arquivos EPUB
- **Leitor responsivo** — Interface limpa com navegação por capítulos
- **Sumário automático** — Extrai capítulos e metadados do EPUB
- **Text-to-Speech** — Leitura em voz alta via Google Cloud TTS (7 idiomas)
- **Cloud Storage** — Armazena livros no Google Cloud Storage (opcional)
- **Tema claro/escuro** — Alternância com detecção automática
- **Controle de fonte** — Ajuste de tamanho da fonte para leitura confortável
- **Navegação por teclado** — Setas esquerda/direita para capítulos

## Requisitos

- Python 3.10+
- Conta Google Cloud (opcional, para TTS e Storage)

## Instalação

```bash
# Clonar repositório
git clone <repo-url>
cd ANTONIO87

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais
```

## Configuração Google Cloud (opcional)

1. Crie um projeto no [Google Cloud Console](https://console.cloud.google.com)
2. Ative as APIs:
   - Cloud Text-to-Speech API
   - Cloud Storage API
3. Crie uma chave de conta de serviço (JSON)
4. Configure no `.env`:

```
GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json
GOOGLE_CLOUD_PROJECT=your-project-id
GCS_BUCKET_NAME=your-bucket-name
```

> **Nota:** A aplicação funciona sem credenciais Google Cloud — o upload e leitura de EPUB funcionam localmente. O TTS e Storage requerem configuração.

## Executar

```bash
python app.py
```

Acesse: http://localhost:5000

## Produção

```bash
gunicorn app:app --bind 0.0.0.0:8080
```

## Estrutura

```
├── app.py              # Servidor Flask + lógica Google Cloud
├── requirements.txt    # Dependências Python
├── templates/
│   └── index.html      # Template principal
├── static/
│   ├── css/style.css   # Estilos (tema claro/escuro)
│   └── js/app.js       # Frontend (upload, leitor, TTS)
├── .env.example        # Exemplo de configuração
└── README.md
```
