# Google Cloud Book Reader — WaveNet & Neural2

Leitor de livros TXT com vozes neurais premium do Google Cloud.  
**$300 de crédito grátis por 90 dias** para novas contas.

## Configuração Google Cloud (uma vez)

### 1. Criar conta gratuita
1. Acesse https://console.cloud.google.com
2. Entre com sua conta Google
3. Aceite os termos → ganhe **$300 de crédito grátis**

### 2. Ativar a API
1. No Console, busque **"Cloud Text-to-Speech API"**
2. Clique **Ativar**

### 3. Criar chave de serviço
1. Vá em **IAM & Admin > Service Accounts**
2. Clique **Create Service Account** → nome: `book-reader` → **Done**
3. Clique no service account → **Keys** → **Add Key** → **JSON**
4. Salve o arquivo JSON no Desktop

### 4. Configurar o app
```bash
cd gcloud-reader
cp .env.example .env
```

Edite o `.env` e coloque o caminho do arquivo JSON:
```
GOOGLE_APPLICATION_CREDENTIALS=/Users/renato/Desktop/book-reader-xxxxx.json
```

## Instalação e execução

```bash
cd ~/Desktop/antonio87/gcloud-reader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse: http://127.0.0.1:5002

## 24 vozes neurais disponíveis

- **PT-BR:** 3 WaveNet + 3 Neural2 (femininas e masculinas)
- **PT-PT:** 4 WaveNet
- **EN-US:** 3 Neural2
- **EN-GB:** 2 Neural2
- **ES:** 2 Neural2
- **FR:** 2 Neural2
- **IT/DE/JA:** Neural2

## Custo com $300 grátis

| Tipo de voz | Preço/1M chars | Páginas com $300 |
|-------------|---------------|-----------------|
| WaveNet | $16/1M chars | ~6.250 páginas |
| Neural2 | $16/1M chars | ~6.250 páginas |

**~6.250 páginas grátis = ~20 livros inteiros**
