"""Redefinição de senha pela linha de comando — a saída de emergência.

Dentro do produto quem redefine senha é o CEO. Só que o CEO é a única conta que
ninguém pode socorrer: se ele perde a senha, não existe autoatendimento, não
existe outro gestor, e o sistema fica trancado com todo mundo do lado de fora.

Este comando é essa porta. Roda contra o banco de produção, exige acesso ao
DATABASE_URL (ou seja, a quem já é dono do ambiente) e derruba todas as sessões
abertas da conta — porque perder a senha e ter sido invadido se parecem muito.

    DATABASE_URL="postgresql://..." python -m app.redefinir_senha michel@mrpnachbar.com

Sem a senha nova como argumento ele pede no terminal, sem ecoar na tela e sem
deixar rastro no histórico do shell.
"""
import getpass
import sys

from sqlmodel import Session, select

from . import database  # o engine é lido na hora da chamada, não no import
from .models import Usuario
from .services.auth import gerar_hash, revogar_sessoes_do_usuario

MINIMO = 6


def redefinir(email: str, senha: str) -> str:
    """Troca a senha e encerra as sessões. Devolve o nome de quem foi alterado."""
    if len(senha) < MINIMO:
        raise SystemExit(f"A senha precisa de ao menos {MINIMO} caracteres.")

    alvo = email.strip().lower()
    with Session(database.engine) as s:
        usuario = s.exec(select(Usuario).where(Usuario.email == alvo)).first()
        if not usuario:
            raise SystemExit(f"Nenhum usuário com o e-mail {alvo}.")
        usuario.senha_hash = gerar_hash(senha)
        if not usuario.ativo:
            # conta desativada por engano é o outro jeito de se trancar para fora
            usuario.ativo = True
            print("Conta estava desativada — reativada.")
        s.add(usuario)
        s.commit()
        derrubadas = revogar_sessoes_do_usuario(s, usuario.id)
        if derrubadas:
            print(f"{derrubadas} sessão(ões) aberta(s) encerrada(s).")
        return usuario.nome


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(
            "uso: python -m app.redefinir_senha <email> [senha]\n"
            "     (sem a senha, ela é pedida no terminal sem aparecer na tela)"
        )
    email = argv[0]
    senha = argv[1] if len(argv) > 1 else getpass.getpass("Nova senha: ")
    nome = redefinir(email, senha)
    print(f"Senha de {nome} redefinida. Entre no RunRate com a nova senha.")


if __name__ == "__main__":
    main(sys.argv[1:])
