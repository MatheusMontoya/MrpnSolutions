"""Login/logout com senha real + gestão de usuários (gestor).

O token vai no header Authorization: Bearer <token> em toda chamada /api/*
(exceto o próprio login) — exigido pelo middleware em main.py.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import Consultor, PerfilUsuario, Usuario
from ..seguranca import exigir_ceo, usuario_atual
from ..services.auth import (
    autenticar,
    criar_sessao,
    gerar_hash,
    revogar_token,
    verificar_senha,
)

router = APIRouter(prefix="/api", tags=["Autenticação"])


class LoginRequest(BaseModel):
    email: str
    senha: str


class TrocaSenha(BaseModel):
    senha_atual: str
    senha_nova: str


class UsuarioCreate(BaseModel):
    email: str
    nome: str
    senha: str
    perfil: PerfilUsuario
    consultor_id: int | None = None


class UsuarioUpdate(BaseModel):
    nome: str | None = None
    perfil: PerfilUsuario | None = None
    consultor_id: int | None = None
    ativo: bool | None = None
    senha: str | None = None  # redefinição pelo gestor


def _ser_usuario(u: Usuario) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "nome": u.nome,
        "perfil": u.perfil,
        "consultor_id": u.consultor_id,
        "consultor": u.consultor.nome if u.consultor else None,
        "ativo": u.ativo,
    }


@router.post("/auth/login")
def login(dados: LoginRequest, session: Session = Depends(get_session)):
    usuario = autenticar(session, dados.email, dados.senha)
    if not usuario:
        raise HTTPException(401, "E-mail ou senha inválidos")
    sessao = criar_sessao(session, usuario)
    return {
        "token": sessao.token,
        "nome": usuario.nome,
        "perfil": usuario.perfil,
        "consultor_id": usuario.consultor_id,
    }


@router.post("/auth/logout")
def logout(request: Request, session: Session = Depends(get_session)):
    token = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
    revogar_token(session, token)
    return {"ok": True}


@router.get("/auth/eu")
def eu(request: Request):
    return usuario_atual(request)


@router.post("/auth/trocar-senha")
def trocar_senha(dados: TrocaSenha, request: Request, session: Session = Depends(get_session)):
    u = usuario_atual(request)
    usuario = session.get(Usuario, u["id"])
    if not usuario or not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(401, "Senha atual incorreta")
    if len(dados.senha_nova) < 6:
        raise HTTPException(422, "A nova senha precisa de ao menos 6 caracteres")
    usuario.senha_hash = gerar_hash(dados.senha_nova)
    session.add(usuario)
    session.commit()
    return {"ok": True}


# ---------------- gestão de usuários (gestor) ----------------

@router.get("/usuarios", dependencies=[Depends(exigir_ceo)])
def listar_usuarios(session: Session = Depends(get_session)):
    usuarios = session.exec(select(Usuario).order_by(Usuario.nome)).all()
    return [_ser_usuario(u) for u in usuarios]


@router.post("/usuarios", status_code=201, dependencies=[Depends(exigir_ceo)])
def criar_usuario(dados: UsuarioCreate, session: Session = Depends(get_session)):
    email = dados.email.strip().lower()
    if session.exec(select(Usuario).where(Usuario.email == email)).first():
        raise HTTPException(409, "Já existe usuário com este e-mail")
    if len(dados.senha) < 6:
        raise HTTPException(422, "A senha precisa de ao menos 6 caracteres")
    if dados.perfil == PerfilUsuario.consultor:
        if not dados.consultor_id or not session.get(Consultor, dados.consultor_id):
            raise HTTPException(422, "Usuário consultor precisa estar vinculado a um consultor")
    u = Usuario(
        email=email, nome=dados.nome, perfil=dados.perfil,
        consultor_id=dados.consultor_id if dados.perfil == PerfilUsuario.consultor else None,
        senha_hash=gerar_hash(dados.senha),
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return _ser_usuario(u)


@router.patch("/usuarios/{usuario_id}", dependencies=[Depends(exigir_ceo)])
def atualizar_usuario(usuario_id: int, dados: UsuarioUpdate, request: Request, session: Session = Depends(get_session)):
    u = session.get(Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Usuário não encontrado")
    atual = usuario_atual(request)
    if dados.ativo is False and u.id == atual["id"]:
        raise HTTPException(422, "Você não pode desativar o próprio usuário")
    if dados.nome is not None:
        u.nome = dados.nome
    if dados.perfil is not None and dados.perfil != u.perfil:
        # rebaixar a si mesmo tranca o CEO para fora das próprias telas, e como
        # só o CEO gerencia usuários, ninguém sobraria para desfazer
        if u.id == atual["id"]:
            raise HTTPException(422, "Você não pode alterar o próprio perfil")
        if dados.perfil == PerfilUsuario.consultor:
            # consultor sem vínculo não tem de quem lançar horas
            vinculo = dados.consultor_id if dados.consultor_id is not None else u.consultor_id
            if not vinculo or not session.get(Consultor, vinculo):
                raise HTTPException(422, "Perfil consultor exige um consultor vinculado")
            u.consultor_id = vinculo
        else:
            # CEO e RH não são alocáveis: o vínculo antigo sairia órfão
            u.consultor_id = None
        u.perfil = dados.perfil
    if dados.consultor_id is not None and u.perfil == PerfilUsuario.consultor:
        if not session.get(Consultor, dados.consultor_id):
            raise HTTPException(404, "Consultor não encontrado")
        u.consultor_id = dados.consultor_id
    if dados.ativo is not None:
        u.ativo = dados.ativo
    if dados.senha:
        if len(dados.senha) < 6:
            raise HTTPException(422, "A senha precisa de ao menos 6 caracteres")
        u.senha_hash = gerar_hash(dados.senha)
    session.add(u)
    session.commit()
    session.refresh(u)
    return _ser_usuario(u)
