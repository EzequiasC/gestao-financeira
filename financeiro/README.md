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
