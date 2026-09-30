from datetime import date

from core.models import Categoria, Lancamento, Origem
from core.services import criar_compra_parcelada

from . import parsing
from .models import Conversa

AJUDA = 'Oi! Digite "gasto" para lançar uma despesa, ou "cancelar" para recomeçar.'


def _lista_categorias() -> list[Categoria]:
    return list(Categoria.objects.filter(ativa=True).order_by("nome"))


def _menu_categorias() -> str:
    linhas = [f"{i}. {c.nome}" for i, c in enumerate(_lista_categorias(), 1)]
    return "Qual o tipo de gasto?\n" + "\n".join(linhas)


def _resumo(dados: dict) -> str:
    cat = Categoria.objects.get(pk=dados["categoria_id"])
    forma = "à vista" if dados["forma"] == "avista" else f"parcelado em {dados['num_parcelas']}x"
    return (f'{cat.nome}, R$ {dados["valor"]}, {dados["data"]}, {forma}.\n'
            'Confirma? (sim / não)')


def processar_mensagem(telefone: str, texto: str) -> str:
    """Motor da conversa: recebe o texto digitado, avança o estado guardado no banco
    e devolve a resposta a enviar. Sem efeitos colaterais de rede aqui."""
    conversa, _ = Conversa.objects.get_or_create(telefone=telefone)
    texto = (texto or "").strip()
    E = Conversa.Estado

    if texto.lower() in ("cancelar", "reiniciar"):
        conversa.reiniciar()
        conversa.save()
        return "Ok, cancelei. Digite “gasto” quando quiser lançar outro."

    if conversa.estado == E.INICIO:
        if texto.lower() not in ("gasto", "novo", "lançar", "lancar"):
            return AJUDA
        if not _lista_categorias():
            return "Ainda não há categorias cadastradas. Cadastre uma no site antes de usar o bot."
        conversa.estado = E.CATEGORIA
        conversa.save()
        return _menu_categorias()

    if conversa.estado == E.CATEGORIA:
        cats = _lista_categorias()
        if not texto.isdigit() or not (1 <= int(texto) <= len(cats)):
            return "Não entendi. " + _menu_categorias()
        conversa.dados["categoria_id"] = cats[int(texto) - 1].id
        conversa.estado = E.VALOR
        conversa.save()
        return "Qual o valor? (ex: 49,90)"

    if conversa.estado == E.VALOR:
        valor = parsing.parse_valor(texto)
        if valor is None:
            return "Valor inválido. Digite só o número, ex: 49,90"
        conversa.dados["valor"] = str(valor)
        conversa.estado = E.DIA
        conversa.save()
        return "Qual o dia? (hoje, ontem ou dd/mm)"

    if conversa.estado == E.DIA:
        dia = parsing.parse_dia(texto)
        if dia is None:
            return "Não entendi a data. Digite “hoje”, “ontem” ou dd/mm."
        conversa.dados["data"] = dia.isoformat()
        conversa.estado = E.FORMA
        conversa.save()
        return "Foi à vista ou parcelado?\n1. À vista\n2. Parcelado"

    if conversa.estado == E.FORMA:
        forma = parsing.parse_forma(texto)
        if forma is None:
            return "Responda 1 para à vista ou 2 para parcelado."
        conversa.dados["forma"] = forma
        if forma == "parcelado":
            conversa.estado = E.PARCELAS
            conversa.save()
            return "Em quantas parcelas?"
        conversa.estado = E.CONFIRMAR
        conversa.save()
        return _resumo(conversa.dados)

    if conversa.estado == E.PARCELAS:
        n = parsing.parse_num_parcelas(texto)
        if n is None:
            return "Digite um número de parcelas entre 2 e 120."
        conversa.dados["num_parcelas"] = n
        conversa.estado = E.CONFIRMAR
        conversa.save()
        return _resumo(conversa.dados)

    if conversa.estado == E.CONFIRMAR:
        if texto.lower() in ("sim", "s", "confirmar", "ok"):
            resposta = _gravar(conversa, telefone)
            conversa.reiniciar()
            conversa.save()
            return resposta
        if texto.lower() in ("não", "nao", "n"):
            conversa.reiniciar()
            conversa.save()
            return "Ok, não lancei nada. Digite “gasto” para tentar de novo."
        return "Responda “sim” para confirmar ou “não” para cancelar."

    conversa.reiniciar()
    conversa.save()
    return AJUDA


def _gravar(conversa: Conversa, telefone: str) -> str:
    d = conversa.dados
    categoria = Categoria.objects.get(pk=d["categoria_id"])
    data = date.fromisoformat(d["data"])  # guardado como texto no JSON da conversa
    if d["forma"] == "avista":
        Lancamento.objects.create(
            data=data, valor=d["valor"], categoria=categoria,
            descricao=categoria.nome, forma=Lancamento.Forma.AVISTA,
            status=Lancamento.Status.PAGO, origem=Origem.WHATSAPP,
        )
        return f"Lançado: {categoria.nome}, R$ {d['valor']}. ✅"
    criar_compra_parcelada(
        descricao=categoria.nome, valor_total=d["valor"], num_parcelas=d["num_parcelas"],
        primeira_data=data, categoria=categoria, origem=Origem.WHATSAPP,
    )
    return f"Lançado: {categoria.nome}, R$ {d['valor']} em {d['num_parcelas']}x. ✅"
