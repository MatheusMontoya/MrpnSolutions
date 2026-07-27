"""Regras de criação de projeto: as 6 fases Activate nascem automaticamente,
já com as atividades/entregáveis padrão e o Quality Gate de cada fase."""
from datetime import date, timedelta

from sqlmodel import Session

from ..models import (
    DURACAO_DEFAULT_SEMANAS,
    FASES_ACTIVATE,
    Atividade,
    Fase,
    ItemGate,
    ModeloProjeto,
    Projeto,
)
from .templates_activate import ATIVIDADES_PADRAO, GATES_PADRAO


def _conteudo_da_fase(nome: str, modelo: ModeloProjeto | None):
    """Entregas e gate da fase: do modelo escolhido, ou dos templates Activate."""
    if modelo is not None:
        atividades = [a.titulo for a in modelo.atividades if a.fase == nome]
        gates = [(g.codigo, g.pergunta, g.risco) for g in modelo.itens_gate if g.fase == nome]
        return atividades, gates
    return (
        ATIVIDADES_PADRAO.get(nome, []),
        GATES_PADRAO.get(nome, []),
    )


def criar_projeto_com_fases(
    session: Session, projeto: Projeto, modelo: ModeloProjeto | None = None
) -> Projeto:
    """Persiste o projeto e gera as 6 fases Activate em sequência, com datas
    estimadas a partir das durações default (editáveis depois). Cada fase nasce
    com as atividades e o Quality Gate do MODELO escolhido (ou do template
    Activate padrão, quando nenhum modelo é passado)."""
    if modelo is not None:
        projeto.modelo_id = modelo.id
    session.add(projeto)
    session.flush()  # garante projeto.id

    inicio = projeto.data_inicio
    for ordem, nome in enumerate(FASES_ACTIVATE):
        semanas = DURACAO_DEFAULT_SEMANAS[nome]
        fim = inicio + timedelta(weeks=semanas) - timedelta(days=1)
        fase = Fase(
            projeto_id=projeto.id,
            nome=nome,
            ordem=ordem,
            data_inicio_prevista=inicio,
            data_fim_prevista=fim,
            baseline_inicio=inicio,  # linha de base fotografada na criação
            baseline_fim=fim,
        )
        session.add(fase)
        session.flush()  # garante fase.id para atividades e gate

        atividades, gates = _conteudo_da_fase(nome, modelo)
        for i, titulo in enumerate(atividades):
            session.add(Atividade(fase_id=fase.id, titulo=titulo, ordem=i))
        for codigo, pergunta, risco in gates:
            session.add(ItemGate(fase_id=fase.id, codigo=codigo, pergunta=pergunta, risco=risco))

        inicio = fim + timedelta(days=1)

    session.commit()
    session.refresh(projeto)
    return projeto


def criar_modelo_padrao(session: Session) -> ModeloProjeto:
    """Materializa os templates do SAP Activate como o modelo padrão editável."""
    from ..models import ModeloAtividade, ModeloItemGate

    modelo = ModeloProjeto(
        nome="Implantação SAP Activate (padrão)",
        descricao="Entregas e Quality Gates adaptados dos aceleradores oficiais do SAP Activate.",
        padrao=True,
    )
    session.add(modelo)
    session.flush()
    for fase, titulos in ATIVIDADES_PADRAO.items():
        for i, titulo in enumerate(titulos):
            session.add(ModeloAtividade(modelo_id=modelo.id, fase=fase, titulo=titulo, ordem=i))
    for fase, gates in GATES_PADRAO.items():
        for codigo, pergunta, risco in gates:
            session.add(ModeloItemGate(modelo_id=modelo.id, fase=fase, codigo=codigo, pergunta=pergunta, risco=risco))
    session.commit()
    session.refresh(modelo)
    return modelo


def fase_atual(projeto: Projeto, hoje: date) -> Fase | None:
    """Fase corrente: a que contém a data de hoje; antes do início retorna a
    primeira, depois do fim retorna a última."""
    if not projeto.fases:
        return None
    fases = sorted(projeto.fases, key=lambda f: f.ordem)
    for f in fases:
        if f.data_inicio_prevista <= hoje <= f.data_fim_prevista:
            return f
    if hoje < fases[0].data_inicio_prevista:
        return fases[0]
    return fases[-1]
