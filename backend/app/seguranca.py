"""Guardas de RBAC. O middleware de autenticação (main.py) valida o token e
pendura o usuário em request.state; as dependências daqui só checam o perfil.

Nos testes unitários os routers são chamados como funções (sem middleware) —
as guardas são exercitadas pelos testes de API via TestClient.
"""
from fastapi import HTTPException, Request

from .models import PerfilUsuario


def usuario_atual(request: Request) -> dict:
    u = getattr(request.state, "usuario", None)
    if not u:
        raise HTTPException(401, "Não autenticado")
    return u


def exigir_ceo(request: Request) -> dict:
    """Financeiro, comercial, projetos, configurações: visão completa do negócio."""
    u = usuario_atual(request)
    if u["perfil"] != PerfilUsuario.ceo:
        raise HTTPException(403, "Apenas o CEO pode acessar este recurso")
    return u


def exigir_gestao(request: Request) -> dict:
    """CEO ou RH: aprovações (horas, despesas, ausências, alocações) e equipe."""
    u = usuario_atual(request)
    if u["perfil"] not in (PerfilUsuario.ceo, PerfilUsuario.rh):
        raise HTTPException(403, "Apenas CEO ou RH podem acessar este recurso")
    return u


def eh_gestao(u: dict) -> bool:
    return u["perfil"] in (PerfilUsuario.ceo, PerfilUsuario.rh)


def exigir_dono(request: Request, consultor_id: int | None) -> dict:
    """Barra escalação HORIZONTAL: um consultor só alcança a própria linha.

    As guardas acima decidem QUAL ROTA cada perfil abre; esta decide QUAL LINHA.
    Sem ela, `/consultores/2/agenda` respondia 200 para a consultora de id 1 —
    era assim que horas e custo de colega vazavam. Gestão passa direto.
    """
    u = usuario_atual(request)
    if eh_gestao(u):
        return u
    if consultor_id is None or u.get("consultor_id") != consultor_id:
        raise HTTPException(403, "Você só pode acessar os seus próprios dados")
    return u

def consultor_do_filtro(request: Request, pedido: int | None) -> int | None:
    """Resolve POR QUEM filtrar uma listagem.

    Gestão filtra por quem quiser (ou por ninguém, vendo tudo). Consultor tem o
    filtro FORÇADO para si — o valor que ele mandar no query string é ignorado,
    então não existe como pedir a lista de outro nem como sondar ids alheios.
    """
    u = usuario_atual(request)
    if eh_gestao(u):
        return pedido
    return u.get("consultor_id")
