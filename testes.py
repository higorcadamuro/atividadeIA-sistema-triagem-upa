"""
Suite de testes do sistema de triagem UPA-SUS.

Cobre no mínimo 10 cenários, incluindo obrigatoriamente:
  - 5 cenários de empate (T06 a T10)
  - 2 com piora progressiva ao longo do tempo (T04, T05)
  - 1 com dupla violação de SLA — regra E5 (T11)
  - 1 com paciente vulnerável e piora de temperatura — regra E4 (T12)
"""

from motor_inferencia import MotorInferencia
from desempate import ModuloDesempate
from log_auditavel import LogAuditavel


def _criar_motor():
    return MotorInferencia(LogAuditavel())


# -------------------------------------------------------------------
# Testes de classificação básica
# -------------------------------------------------------------------

def teste_T01_emergencia_nivel1():
    """Paciente sem pulso → Nível 1 (VERMELHO)."""
    motor = _criar_motor()
    pac = {
        "id": "T01", "idade": 45, "gestante": False, "deficiencia": False,
        "hora_entrada": "08:00",
        "leituras": [{"hora": "08:00", "pulso_presente": False, "respirando": True,
                      "escala_dor": 0}],
    }
    mem = motor.processar_paciente(pac)
    assert mem.nivel_atual == 1, f"Esperado nível 1, obtido {mem.nivel_atual}"


def teste_T02_nivel2_spo2_critica():
    """SpO2 < 90 % → Nível 2 (LARANJA)."""
    motor = _criar_motor()
    pac = {
        "id": "T02", "idade": 30, "gestante": False, "deficiencia": False,
        "hora_entrada": "09:00",
        "leituras": [{"hora": "09:00", "spo2": 87, "escala_dor": 3,
                      "frequencia_cardiaca": 95, "temperatura": 37.0,
                      "pulso_presente": True, "respirando": True}],
    }
    mem = motor.processar_paciente(pac)
    assert mem.nivel_atual == 2, f"Esperado nível 2, obtido {mem.nivel_atual}"


def teste_T03_nivel3_febre():
    """Febre > 39 °C sem outros critérios graves → Nível 3 (AMARELO)."""
    motor = _criar_motor()
    pac = {
        "id": "T03", "idade": 28, "gestante": False, "deficiencia": False,
        "hora_entrada": "10:00",
        "leituras": [{"hora": "10:00", "temperatura": 39.8, "escala_dor": 4,
                      "frequencia_cardiaca": 95, "spo2": 97,
                      "pulso_presente": True, "respirando": True}],
    }
    mem = motor.processar_paciente(pac)
    assert mem.nivel_atual == 3, f"Esperado nível 3, obtido {mem.nivel_atual}"


def teste_T04_piora_progressiva_nivel3_para_2():
    """
    Piora progressiva: 1ª leitura Nível 3, 2ª leitura SpO2 cai para 88 % → Nível 2.
    Verifica também que regra E1 disparou (3 → 2 em menos de 30 min).
    """
    motor = _criar_motor()
    pac = {
        "id": "T04", "idade": 40, "gestante": False, "deficiencia": False,
        "hora_entrada": "11:00",
        "leituras": [
            {"hora": "11:00", "spo2": 93, "temperatura": 39.2, "escala_dor": 5,
             "frequencia_cardiaca": 100, "pulso_presente": True, "respirando": True},
            {"hora": "11:20", "spo2": 88, "temperatura": 39.5, "escala_dor": 7,
             "frequencia_cardiaca": 118},
        ],
    }
    mem = motor.processar_paciente(pac)
    assert mem.nivel_atual == 2, f"Esperado nível 2, obtido {mem.nivel_atual}"
    ids_eventos = [e["id"] for e in mem.eventos_registrados]
    assert "E1" in ids_eventos, f"Esperado evento E1, eventos presentes: {ids_eventos}"


def teste_T05_piora_progressiva_multipla_E2():
    """
    2ª leitura com 3 sinais piorando → regra E2 dispara e eleva de Nível 3 para Nível 2.
    """
    motor = _criar_motor()
    pac = {
        "id": "T05", "idade": 50, "gestante": False, "deficiencia": False,
        "hora_entrada": "12:00",
        "leituras": [
            {"hora": "12:00", "spo2": 94, "temperatura": 38.5, "escala_dor": 5,
             "frequencia_cardiaca": 105, "glasgow": 15,
             "pulso_presente": True, "respirando": True},
            {"hora": "12:10", "spo2": 91, "temperatura": 39.8, "escala_dor": 7,
             "frequencia_cardiaca": 125, "glasgow": 14},
        ],
    }
    mem = motor.processar_paciente(pac)
    ids_eventos = [e["id"] for e in mem.eventos_registrados]
    assert "E2" in ids_eventos, f"Esperado evento E2, eventos: {ids_eventos}"
    assert mem.nivel_atual <= 2, f"Esperado nível ≤ 2 após E2, obtido {mem.nivel_atual}"


# -------------------------------------------------------------------
# Testes de desempate — cenários obrigatórios (E1-E5 do enunciado)
# -------------------------------------------------------------------

def teste_T06_empate_mesma_hora_sem_vulneravel():
    """
    Cenário 1 do enunciado: dois pacientes no Nível 3, chegaram com < 1 min
    de diferença, nenhum vulnerável.
    Critério esperado: tempo de espera (se iguais, ID alfanumérico).
    """
    motor    = _criar_motor()
    desempa  = ModuloDesempate()

    pac_a = motor.processar_paciente({
        "id": "T06-A", "idade": 30, "gestante": False, "deficiencia": False,
        "hora_entrada": "13:00",
        "leituras": [{"hora": "13:00", "temperatura": 39.5, "escala_dor": 5,
                      "frequencia_cardiaca": 100, "spo2": 94,
                      "pulso_presente": True, "respirando": True}],
    })
    pac_b = motor.processar_paciente({
        "id": "T06-B", "idade": 25, "gestante": False, "deficiencia": False,
        "hora_entrada": "13:00",
        "leituras": [{"hora": "13:00", "temperatura": 39.3, "escala_dor": 5,
                      "frequencia_cardiaca": 98, "spo2": 95,
                      "pulso_presente": True, "respirando": True}],
    })

    assert pac_a.nivel_atual == 3 and pac_b.nivel_atual == 3, "Ambos devem ser Nível 3"

    resultado = desempa.explicar_desempate(pac_a, pac_b, "13:00")
    # Pontuações iguais, tempo igual → ID decide: T06-A < T06-B
    assert resultado["vencedor"] == "T06-A", (
        f"Esperado T06-A (ID menor), obtido {resultado['vencedor']}"
    )
    assert "ID" in resultado["criterio"] or "tempo" in resultado["criterio"], (
        f"Critério inesperado: {resultado['criterio']}"
    )


def teste_T07_empate_piora_vs_estavel():
    """
    Cenário 2 do enunciado: A estável há 25 min, B com 2 sinais piorando há 5 min.
    Esperado: B tem prioridade (piora rápida supera proximidade moderada de SLA).
    """
    motor   = _criar_motor()
    desempa = ModuloDesempate()

    # Paciente A: Nível 3 há 25 min, estável
    pac_a = motor.processar_paciente({
        "id": "T07-A", "idade": 40, "gestante": False, "deficiencia": False,
        "hora_entrada": "13:00",
        "leituras": [
            {"hora": "13:00", "temperatura": 39.5, "escala_dor": 6,
             "frequencia_cardiaca": 105, "spo2": 93,
             "pulso_presente": True, "respirando": True},
            {"hora": "13:25", "temperatura": 39.5, "escala_dor": 6,
             "frequencia_cardiaca": 105, "spo2": 93},   # sem alteração
        ],
    })

    # Paciente B: Nível 3 há 5 min, dois sinais pioraram
    pac_b = motor.processar_paciente({
        "id": "T07-B", "idade": 35, "gestante": False, "deficiencia": False,
        "hora_entrada": "13:20",
        "leituras": [
            {"hora": "13:20", "temperatura": 38.8, "escala_dor": 5,
             "frequencia_cardiaca": 100, "spo2": 94,
             "pulso_presente": True, "respirando": True},
            {"hora": "13:25", "temperatura": 39.9, "escala_dor": 7,
             "frequencia_cardiaca": 128, "spo2": 92},   # 3 sinais pioraram
        ],
    })

    # Ambos devem estar no Nível 3 (ou B elevado por E2 — nesse caso teste não aplica)
    if pac_b.nivel_atual < pac_a.nivel_atual:
        # E2 elevou B, que já tem prioridade por nível — comportamento correto
        return

    assert pac_a.nivel_atual == 3 and pac_b.nivel_atual == 3

    # Em 13:25: A tem 25 min (83 % do SLA 30min → +5 pts), B tem 5 min + 3 sinais piora
    resultado = desempa.explicar_desempate(pac_a, pac_b, "13:25")
    pts_a = resultado["pontuacoes"]["T07-A"]["pontos"]
    pts_b = resultado["pontuacoes"]["T07-B"]["pontos"]
    assert pts_b > pts_a, (
        f"Esperado B com mais pontos, A={pts_a}, B={pts_b}"
    )
    assert resultado["vencedor"] == "T07-B", (
        f"Esperado T07-B, obtido {resultado['vencedor']}"
    )


def teste_T08_empate_vulneravel_vs_piora_clinica():
    """
    Cenário 3 do enunciado: A (62 anos, Nível 3 por vulnerabilidade, 28 min aguardando)
    vs B (35 anos, Nível 3 clínico, SpO2 caiu 3 pontos).
    Esperado: A tem prioridade (28/30 = 93 % do SLA supera 1 sinal de piora).
    """
    motor   = _criar_motor()
    desempa = ModuloDesempate()

    # A: 62 anos, chegou às 13:00 classificado como Nível 3 por vulnerabilidade
    pac_a = motor.processar_paciente({
        "id": "T08-A", "idade": 62, "gestante": False, "deficiencia": False,
        "hora_entrada": "13:00",
        "leituras": [
            {"hora": "13:00", "escala_dor": 3, "temperatura": 37.5,
             "frequencia_cardiaca": 88, "spo2": 96,
             "pulso_presente": True, "respirando": True},
        ],
    })

    # B: 35 anos, chegou às 13:23, SpO2 caiu de 95 para 92
    pac_b = motor.processar_paciente({
        "id": "T08-B", "idade": 35, "gestante": False, "deficiencia": False,
        "hora_entrada": "13:23",
        "leituras": [
            {"hora": "13:23", "escala_dor": 6, "temperatura": 38.0,
             "frequencia_cardiaca": 100, "spo2": 95,
             "pulso_presente": True, "respirando": True},
            {"hora": "13:28", "escala_dor": 6, "temperatura": 38.1,
             "frequencia_cardiaca": 102, "spo2": 92},  # SpO2 caiu
        ],
    })

    assert pac_a.vulneravel, "Paciente A deveria ser marcado como vulnerável"

    # Consultamos a fila em 13:28
    resultado = desempa.explicar_desempate(pac_a, pac_b, "13:28")
    assert resultado["vencedor"] == "T08-A", (
        f"Esperado T08-A (SLA quase vencido), obtido {resultado['vencedor']}. "
        f"Pontuações: {resultado['pontuacoes']}"
    )


def teste_T09_empate_violacao_sla_iminente():
    """
    Cenário 4 do enunciado: dois pacientes no Nível 3, ambos a 2 min de violar o SLA.
    O sistema deve alertar os dois (ausência de inação) e ordenar por pontuação/ID.
    """
    motor   = _criar_motor()
    desempa = ModuloDesempate()

    pac_a = motor.processar_paciente({
        "id": "T09-A", "idade": 30, "gestante": False, "deficiencia": False,
        "hora_entrada": "10:00",
        "leituras": [
            {"hora": "10:00", "temperatura": 39.2, "escala_dor": 5,
             "frequencia_cardiaca": 105, "spo2": 94,
             "pulso_presente": True, "respirando": True},
            # Leitura em 10:28 → 28 min no Nível 3, SLA = 30 min
            {"hora": "10:28", "temperatura": 39.3, "escala_dor": 5,
             "frequencia_cardiaca": 106, "spo2": 94},
        ],
    })

    pac_b = motor.processar_paciente({
        "id": "T09-B", "idade": 25, "gestante": False, "deficiencia": False,
        "hora_entrada": "10:00",
        "leituras": [
            {"hora": "10:00", "temperatura": 39.0, "escala_dor": 5,
             "frequencia_cardiaca": 100, "spo2": 95,
             "pulso_presente": True, "respirando": True},
            {"hora": "10:28", "temperatura": 39.1, "escala_dor": 5,
             "frequencia_cardiaca": 101, "spo2": 95},
        ],
    })

    # Ambos devem estar em Nível 3 com ~93 % do SLA consumido
    pontos_a, espera_a, _ = desempa.calcular_pontuacao(pac_a, "10:28")
    pontos_b, espera_b, _ = desempa.calcular_pontuacao(pac_b, "10:28")

    # Ambos devem ter pontuação de SLA iminente (> 80 %)
    assert pontos_a >= 5 and pontos_b >= 5, (
        f"Esperado pontuação de SLA iminente para ambos. A={pontos_a}, B={pontos_b}"
    )

    # O sistema ordena deterministicamente (T09-A < T09-B por ID)
    fila_local = desempa.ordenar_fila([pac_a, pac_b], "10:28")
    assert fila_local[0].id_paciente == "T09-A", (
        f"Esperado T09-A primeiro (ID menor com pontuação igual), "
        f"obtido {fila_local[0].id_paciente}"
    )


def teste_T10_empate_apos_reclassificacao():
    """
    Cenário 5 do enunciado: A recém-reclassificado de Nível 4 para Nível 3 (0 min);
    B já está no Nível 3 há 15 min.
    Esperado: B tem prioridade (mais tempo no nível → prevenção de inanição).
    """
    motor   = _criar_motor()
    desempa = ModuloDesempate()

    # B: Nível 3 há 15 min
    pac_b = motor.processar_paciente({
        "id": "T10-B", "idade": 35, "gestante": False, "deficiencia": False,
        "hora_entrada": "14:00",
        "leituras": [
            {"hora": "14:00", "temperatura": 39.2, "escala_dor": 5,
             "frequencia_cardiaca": 105, "spo2": 94,
             "pulso_presente": True, "respirando": True},
        ],
    })

    # A: classificado como Nível 4 mas piora e é elevado para Nível 3 às 14:15
    pac_a = motor.processar_paciente({
        "id": "T10-A", "idade": 40, "gestante": False, "deficiencia": False,
        "hora_entrada": "14:10",
        "leituras": [
            {"hora": "14:10", "escala_dor": 2, "temperatura": 37.5,
             "frequencia_cardiaca": 80, "spo2": 97,
             "pulso_presente": True, "respirando": True},
            {"hora": "14:15", "escala_dor": 5, "temperatura": 39.5,
             "frequencia_cardiaca": 110, "spo2": 94},
        ],
    })

    assert pac_b.nivel_atual == 3, f"B deveria ser Nível 3, obtido {pac_b.nivel_atual}"
    assert pac_a.nivel_atual == 3, f"A deveria ser Nível 3, obtido {pac_a.nivel_atual}"

    resultado = desempa.explicar_desempate(pac_a, pac_b, "14:15")
    assert resultado["vencedor"] == "T10-B", (
        f"Esperado T10-B (mais tempo no nível), obtido {resultado['vencedor']}. "
        f"Detalhes: {resultado}"
    )


# -------------------------------------------------------------------
# Testes de regras de segunda ordem obrigatórias
# -------------------------------------------------------------------

def teste_T11_dupla_violacao_sla_E5():
    """
    Paciente viola o SLA em duas leituras consecutivas → regra E5 dispara
    (bloquear admissões + protocolo de sobrecarga).
    """
    motor = _criar_motor()
    pac = {
        "id": "T11", "idade": 45, "gestante": False, "deficiencia": False,
        "hora_entrada": "08:00",
        "leituras": [
            {"hora": "08:00", "temperatura": 39.5, "escala_dor": 6,
             "frequencia_cardiaca": 110, "spo2": 93,
             "pulso_presente": True, "respirando": True},
            # 35 min depois → violação SLA (Nível 3, SLA = 30 min) → E3 dispara
            {"hora": "08:35", "temperatura": 39.6, "escala_dor": 6,
             "frequencia_cardiaca": 111, "spo2": 93},
            # 70 min depois → segunda violação → E3 + E5
            {"hora": "09:10", "temperatura": 39.7, "escala_dor": 6,
             "frequencia_cardiaca": 112, "spo2": 93},
        ],
    }
    mem = motor.processar_paciente(pac)
    ids_eventos = [e["id"] for e in mem.eventos_registrados]
    assert "E3" in ids_eventos, f"Esperado E3, eventos: {ids_eventos}"
    assert "E5" in ids_eventos, f"Esperado E5, eventos: {ids_eventos}"
    assert mem.admissoes_bloqueadas, "Esperado admissoes_bloqueadas = True após E5"


def teste_T12_vulneravel_febre_E4():
    """
    Paciente vulnerável (gestante) com temperatura subindo > 1 °C → E4 dispara
    e reclassifica diretamente para Nível 2.
    """
    motor = _criar_motor()
    pac = {
        "id": "T12", "idade": 28, "gestante": True, "deficiencia": False,
        "hora_entrada": "10:00",
        "leituras": [
            {"hora": "10:00", "temperatura": 38.2, "escala_dor": 3,
             "frequencia_cardiaca": 90, "spo2": 97,
             "pulso_presente": True, "respirando": True},
            # Temperatura sobe 1.5 °C — E4 deve disparar
            {"hora": "10:20", "temperatura": 39.7, "escala_dor": 4,
             "frequencia_cardiaca": 95, "spo2": 96},
        ],
    }
    mem = motor.processar_paciente(pac)
    assert mem.vulneravel, "Gestante deve ser marcada como vulnerável"
    ids_eventos = [e["id"] for e in mem.eventos_registrados]
    assert "E4" in ids_eventos, f"Esperado E4, eventos: {ids_eventos}"
    assert mem.nivel_atual == 2, (
        f"Esperado Nível 2 após E4, obtido {mem.nivel_atual}"
    )


def teste_T13_sem_rebaixamento():
    """
    Garante que o sistema nunca rebaixa automaticamente um nível de prioridade.
    Paciente começa em Nível 2 — leitura posterior com sinais menos críticos
    não deve reduzir para Nível 3.
    """
    motor = _criar_motor()
    pac = {
        "id": "T13", "idade": 30, "gestante": False, "deficiencia": False,
        "hora_entrada": "15:00",
        "leituras": [
            {"hora": "15:00", "spo2": 87, "escala_dor": 9,
             "frequencia_cardiaca": 155, "temperatura": 37.0,
             "pulso_presente": True, "respirando": True},
            # Sinais melhoram na 2ª leitura — nível NÃO deve cair
            {"hora": "15:30", "spo2": 95, "escala_dor": 4,
             "frequencia_cardiaca": 90, "temperatura": 37.2},
        ],
    }
    mem = motor.processar_paciente(pac)
    assert mem.nivel_atual == 2, (
        f"Nível não deve rebaixar automaticamente. Obtido: {mem.nivel_atual}"
    )


def teste_T14_campos_ausentes_gracioso():
    """
    Leitura com quase todos os campos ausentes não deve lançar exceção.
    O sistema deve classificar como Nível 5 (padrão) sem erro.
    """
    motor = _criar_motor()
    pac = {
        "id": "T14", "idade": 25, "gestante": False, "deficiencia": False,
        "hora_entrada": "16:00",
        "leituras": [{"hora": "16:00"}],   # sem nenhum sinal vital
    }
    try:
        mem = motor.processar_paciente(pac)
        assert mem.nivel_atual == 5, f"Esperado Nível 5 (padrão), obtido {mem.nivel_atual}"
    except Exception as e:
        assert False, f"Sistema lançou exceção com campos ausentes: {e}"


# -------------------------------------------------------------------
# Runner
# -------------------------------------------------------------------

TODOS_OS_TESTES = [
    teste_T01_emergencia_nivel1,
    teste_T02_nivel2_spo2_critica,
    teste_T03_nivel3_febre,
    teste_T04_piora_progressiva_nivel3_para_2,
    teste_T05_piora_progressiva_multipla_E2,
    teste_T06_empate_mesma_hora_sem_vulneravel,
    teste_T07_empate_piora_vs_estavel,
    teste_T08_empate_vulneravel_vs_piora_clinica,
    teste_T09_empate_violacao_sla_iminente,
    teste_T10_empate_apos_reclassificacao,
    teste_T11_dupla_violacao_sla_E5,
    teste_T12_vulneravel_febre_E4,
    teste_T13_sem_rebaixamento,
    teste_T14_campos_ausentes_gracioso,
]


def executar_testes(verbose=False):
    aprovados = 0
    reprovados = 0

    print("\n" + "=" * 60)
    print("  SUITE DE TESTES — SISTEMA DE TRIAGEM UPA-SUS")
    print("=" * 60)

    for teste in TODOS_OS_TESTES:
        nome = teste.__name__.replace("teste_", "")
        try:
            teste()
            print(f"  [OK]   {nome}")
            aprovados += 1
        except AssertionError as e:
            print(f"  [FAIL] {nome}")
            if verbose:
                print(f"         → {e}")
            reprovados += 1
        except Exception as e:
            print(f"  [ERR]  {nome}")
            if verbose:
                print(f"         → {type(e).__name__}: {e}")
            reprovados += 1

    total = aprovados + reprovados
    print("=" * 60)
    print(f"  Resultado: {aprovados}/{total} testes aprovados")
    if reprovados > 0:
        print(f"  {reprovados} teste(s) falharam. Execute com --verbose para detalhes.")
    print("=" * 60)
    return reprovados == 0


if __name__ == "__main__":
    import sys
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    ok = executar_testes(verbose=verbose)
    sys.exit(0 if ok else 1)
