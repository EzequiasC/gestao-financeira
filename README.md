# Controle financeiro (Django)

## Rodar local
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver     # http://127.0.0.1:8000/admin/

## Testes
    python manage.py test

## Gastos fixos do mês (cron, todo dia 1 e também diariamente, é idempotente)
    python manage.py gerar_fixos

## Regras que os testes protegem
- Dinheiro sempre em Decimal; soma das parcelas == valor total, ao centavo.
- Datas das parcelas calculadas da data original (31/01 -> 28/02 -> 31/03).
- Fixos nunca duplicam no mês; mudar o valor do fixo não altera meses já gerados.
- Lançamentos não são apagados (admin sem delete); use "cancelar".
- mensagem_id único: webhook reenviado pela Meta não grava duas vezes.

## Próximos passos
bot (webhook WhatsApp), dashboard, Dockerfile/compose, backup.

## Bot do WhatsApp
- Endpoint único: `/bot/webhook/` (GET = verificação da Meta, POST = mensagens).
- Configure no `.env`: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN`
  (invente uma string; é o que você digita no painel da Meta ao criar o webhook),
  e `WHATSAPP_NUMEROS_AUTORIZADOS` (seu número, formato 5567999999999, sem "+"; vazio = aceita qualquer um, só para teste local).
- Sem `WHATSAPP_TOKEN` configurado, as respostas do bot só vão para o log (`[WhatsApp simulado]`) — dá para testar o fluxo sem ter conta na Meta ainda.
- Fluxo: "gasto" → escolhe categoria (número) → valor → dia (hoje/ontem/dd-mm) → à vista ou parcelado → (se parcelado, número de parcelas) → confirma (sim/não). "cancelar" reinicia a qualquer momento.
- Idempotência: cada mensagem da Meta tem um ID (`wamid`); reenvios são ignorados (tabela `MensagemRecebida`).
- Segurança: só números em `WHATSAPP_NUMEROS_AUTORIZADOS` conseguem lançar gastos pelo bot.

## Deploy no Railway
1. Suba este projeto para um repositório Git (GitHub) privado.
2. No Railway: **New Project → Deploy from GitHub repo**.
3. Adicione um banco: **New → Database → PostgreSQL** dentro do mesmo projeto. O Railway cria a variável `DATABASE_URL` sozinho e o Django já sabe usá-la.
4. Na aba **Variables** do serviço web, adicione:
   - `DJANGO_SECRET_KEY` (chave longa e aleatória — gere com `python -c "import secrets;print(secrets.token_urlsafe(50))"`)
   - `DJANGO_DEBUG=0`
   - `DJANGO_ALLOWED_HOSTS=SEU-PROJETO.up.railway.app` (o domínio aparece em Settings → Networking depois do primeiro deploy)
   - `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_NUMEROS_AUTORIZADOS` quando tiver a conta Meta pronta
5. Em **Settings → Networking**, gere um domínio público (Railway já entrega com HTTPS).
6. O deploy roda `python manage.py migrate` sozinho (ver `Procfile`, etapa `release`). Depois do primeiro deploy, crie o superusuário rodando pelo próprio Railway: aba do serviço → **Shell** (ou instale o Railway CLI e rode `railway run python manage.py createsuperuser`).
7. O webhook do WhatsApp na Meta vai ser: `https://SEU-PROJETO.up.railway.app/bot/webhook/`
