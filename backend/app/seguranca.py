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
