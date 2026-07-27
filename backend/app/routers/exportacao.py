"""Exportação CSV — dados operacionais em formato Excel pt-BR.

Convenções: separador ';', BOM UTF-8 (Excel Windows abre acentos direito),
decimal com vírgula. Sem dependências novas — csv da stdlib em memória.
"""
import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Apontamento,
    Despesa,
    Fatura,
    Pendencia,
    Proposta,
)
from .financeiro import rentabilidade

router = APIRouter(prefix="/api/export", tags=["Exportação"])


def _num(v) -> str:
    """Número em formato pt-BR (vírgula decimal) para o Excel."""
    if v is None:
        return ""
    return f"{v:.2f}".replace(".", ",")


def _data(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _csv(nome: str, cabecalho: list[str], linhas: list[list]) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(cabecalho)
    w.writerows(linhas)
    return Response(
        content="﻿" + buf.getvalue(),  # BOM para o Excel reconhecer UTF-8
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}.csv"'},
    )


@router.get("/apontamentos.csv")
def exportar_apontamentos(session: Session = Depends(get_session)):
    linhas = []
    for ap in session.exec(select(Apontamento).order_by(Apontamento.data)).all():
        aloc = ap.alocacao
        fase = aloc.fase if aloc else None
        proj = fase.projeto if fase else None
        linhas.append([
            _data(ap.data),
            aloc.consultor.nome if aloc and aloc.consultor else "",
            proj.nome if proj else "",
            fase.nome if fase else "",
            _num(ap.horas),
            _num(aloc.taxa_hora_venda if aloc else None),
            _num(ap.horas * aloc.taxa_hora_venda if aloc else None),
            ap.descricao,
        ])
    return _csv("apontamentos", [
        "Data", "Consultor", "Projeto", "Fase", "Horas",
        "Taxa venda (R$/h)", "Receita (R$)", "Descrição",
    ], linhas)


@router.get("/faturas.csv")
def exportar_faturas(session: Session = Depends(get_session)):
    linhas = []
    for f in session.exec(select(Fatura).order_by(Fatura.competencia)).all():
        linhas.append([
            f.numero,
            f.projeto.nome if f.projeto else "",
            f.projeto.cliente.nome if f.projeto and f.projeto.cliente else "",
            f.competencia.strftime("%m/%Y"),
            _num(f.valor),
            f.status,
            _data(f.data_emissao),
            _data(f.data_vencimento),
            _data(f.data_recebimento),
        ])
    return _csv("faturas", [
        "Número", "Projeto", "Cliente", "Competência", "Valor (R$)",
        "Status", "Emissão", "Vencimento", "Recebimento",
    ], linhas)


@router.get("/despesas.csv")
def exportar_despesas(session: Session = Depends(get_session)):
    linhas = []
    for d in session.exec(select(Despesa).order_by(Despesa.data)).all():
        linhas.append([
            _data(d.data),
            d.consultor.nome if d.consultor else "",
            d.projeto.nome if d.projeto else "",
            d.tipo,
            d.descricao,
            _num(d.km),
            _num(d.valor),
            d.status,
        ])
    return _csv("despesas", [
        "Data", "Consultor", "Projeto", "Tipo", "Descrição",
        "Km", "Valor (R$)", "Status",
    ], linhas)


@router.get("/propostas.csv")
def exportar_propostas(session: Session = Depends(get_session)):
    linhas = []
    for p in session.exec(select(Proposta).order_by(Proposta.criada_em)).all():
        linhas.append([
            p.nome,
            p.cliente.nome if p.cliente else "",
            p.estagio,
            _num(p.horas_estimadas),
            _num(p.valor_estimado),
            f"{p.margem_estimada:.0%}".replace("%", "") + "%" if p.margem_estimada else "",
            f"{p.probabilidade:.0%}",
            _data(p.validade),
            _data(p.criada_em),
            _data(p.decidida_em),
        ])
    return _csv("propostas", [
        "Proposta", "Cliente", "Estágio", "Horas", "Valor (R$)",
        "Margem estimada", "Probabilidade", "Validade", "Criada em", "Decidida em",
    ], linhas)


@router.get("/pendencias.csv")
def exportar_pendencias(session: Session = Depends(get_session)):
    linhas = []
    for p in session.exec(select(Pendencia).order_by(Pendencia.criada_em)).all():
        linhas.append([
            p.titulo,
            p.projeto.nome if p.projeto else "",
            p.fase.nome if p.fase else "",
            p.responsavel.nome if p.responsavel else "",
            p.prioridade,
            p.status,
            _data(p.criada_em),
            _data(p.resolvida_em),
            p.descricao,
        ])
    return _csv("pendencias", [
        "Pendência", "Projeto", "Fase", "Responsável", "Prioridade",
        "Status", "Criada em", "Resolvida em", "Descrição",
    ], linhas)


@router.get("/rentabilidade.csv")
def exportar_rentabilidade(session: Session = Depends(get_session)):
    dados = rentabilidade(session)["ranking"]
    linhas = [[
        r["projeto"], r["cliente"], r["status"],
        _num(r["receita_realizada"]), _num(r["custo_horas"]),
        _num(r["despesas"]), _num(r["margem"]),
        f"{r['margem_pct']:.1%}".replace(".", ","),
    ] for r in dados]
    return _csv("rentabilidade", [
        "Projeto", "Cliente", "Status", "Receita realizada (R$)",
        "Custo horas (R$)", "Despesas (R$)", "Margem (R$)", "Margem %",
    ], linhas)


RECURSOS = {
    "apontamentos", "faturas", "despesas", "propostas", "pendencias", "rentabilidade",
}


@router.get("")
def listar_recursos():
    """Recursos exportáveis — o frontend monta os botões a partir daqui."""
    return {"recursos": sorted(RECURSOS)}
