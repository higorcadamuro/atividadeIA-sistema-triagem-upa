"""
Interface de linha de comando do sistema de triagem.

Modos de uso:
  python main.py                        -> REPL interativo
  python main.py --arquivo paciente.json -> processa arquivo JSON
  python main.py --demo                 -> executa cenario demonstrativo
"""

import sys
import json

from base_conhecimento import NIVEIS_PRIORIDADE
from motor_inferencia import MotorInferencia
from desempate import ModuloDesempate
from log_auditavel import LogAuditavel


log       = LogAuditavel()
motor     = MotorInferencia(log)
desempate = ModuloDesempate()
fila      = []

def cmd_processar_arquivo(caminho):
    """Processa um paciente a partir de um arquivo JSON."""
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        print(f"  Arquivo '{caminho}' não encontrado.")
        return
    except json.JSONDecodeError as e:
        print(f"  Erro ao ler JSON: {e}")
        return

    pacientes = dados if isinstance(dados, list) else [dados]

    for paciente in pacientes:
        memoria = motor.processar_paciente(paciente)
        fila.append(memoria)
        _imprimir_resumo(memoria)


def cmd_adicionar_manual():
    """Coleta dados de um paciente via terminal e o processa."""
    print("\n  --- Novo paciente ---")
    pid   = input("  ID do paciente (ex: PAC-001): ").strip() or "PAC-MANUAL"
    idade = _ler_int("  Idade: ")
    hora  = input("  Hora de entrada (HH:MM): ").strip() or "00:00"

    gestante   = input("  Gestante? (s/n): ").strip().lower() == "s"
    deficiencia = input("  Deficiência física grave? (s/n): ").strip().lower() == "s"

    print("\n  --- Sinais vitais (Enter para pular campo) ---")
    leitura = {"hora": hora}
    leitura["pulso_presente"]     = _ler_bool("  Pulso presente? (s/n): ", padrao=True)
    leitura["respirando"]         = _ler_bool("  Respirando? (s/n): ", padrao=True)
    leitura["spo2"]               = _ler_float("  SpO2 (%): ")
    leitura["frequencia_cardiaca"]= _ler_int("  FC (bpm): ")
    leitura["glasgow"]            = _ler_int("  Glasgow (3-15): ")
    leitura["temperatura"]        = _ler_float("  Temperatura (°C): ")
    leitura["escala_dor"]         = _ler_int("  Dor (0-10): ")
    leitura["vomitos_por_hora"]   = _ler_int("  Vômitos/hora: ")

    leitura = {k: v for k, v in leitura.items() if v is not None}

    paciente = {
        "id":           pid,
        "idade":        idade,
        "gestante":     gestante,
        "deficiencia":  deficiencia,
        "hora_entrada": hora,
        "leituras":     [leitura],
    }

    memoria = motor.processar_paciente(paciente)
    fila.append(memoria)
    _imprimir_resumo(memoria)


def cmd_ver_fila(hora_consulta=None):
    """Exibe a fila de espera ordenada por prioridade."""
    if not fila:
        print("\n  Nenhum paciente na fila.")
        return

    hora_consulta = hora_consulta or _hora_atual_fake()
    ordenada = desempate.ordenar_fila(fila, hora_consulta, log)

    print("\n  " + "=" * 55)
    print(f"  FILA DE ESPERA — {hora_consulta}")
    print("  " + "=" * 55)
    print(f"  {'Pos':>3}  {'ID':<20}  {'Nível':<8}  {'Cor':<10}  {'Espera':>7}")
    print("  " + "-" * 55)

    for i, mem in enumerate(ordenada, 1):
        nivel = mem.nivel_atual or 99
        cor   = NIVEIS_PRIORIDADE[nivel]["cor"] if nivel in NIVEIS_PRIORIDADE else "?"
        espera = mem.tempo_no_nivel_atual(hora_consulta)
        print(f"  {i:>3}  {mem.id_paciente:<20}  {nivel:<8}  {cor:<10}  {espera:>5} min")

    print("  " + "=" * 55)


def cmd_log():
    log.imprimir()


def cmd_exportar():
    caminho = input("  Nome do arquivo (padrão: log_triagem.json): ").strip()
    log.exportar_json(caminho or "log_triagem.json")


def cmd_demo():
    """Carrega um cenário demonstrativo."""
    pacientes_demo = [
        {
            "id": "PAC-DEMO-001",
            "idade": 67,
            "gestante": False,
            "deficiencia": False,
            "hora_entrada": "14:00",
            "leituras": [
                {
                    "hora": "14:00",
                    "consciente": True,
                    "glasgow": 15,
                    "spo2": 95,
                    "frequencia_cardiaca": 88,
                    "temperatura": 37.2,
                    "escala_dor": 3,
                    "vomitos_por_hora": 0,
                    "pulso_presente": True,
                    "respirando": True,
                },
                {
                    "hora": "14:25",
                    "glasgow": 14,
                    "spo2": 89,
                    "frequencia_cardiaca": 122,
                    "temperatura": 38.6,
                    "escala_dor": 7,
                    "vomitos_por_hora": 2,
                },
            ],
        },
        {
            "id": "PAC-DEMO-002",
            "idade": 35,
            "gestante": False,
            "deficiencia": False,
            "hora_entrada": "14:22",
            "leituras": [
                {
                    "hora": "14:22",
                    "spo2": 93,
                    "frequencia_cardiaca": 110,
                    "temperatura": 39.5,
                    "escala_dor": 6,
                    "pulso_presente": True,
                    "respirando": True,
                },
            ],
        },
    ]

    print("\n  Carregando cenário demonstrativo...")
    for p in pacientes_demo:
        memoria = motor.processar_paciente(p)
        fila.append(memoria)
        _imprimir_resumo(memoria)

    cmd_ver_fila("14:30")


MENU = """
╔══════════════════════════════════════════╗
║   SISTEMA DE TRIAGEM UPA-SUS             ║
║   Disciplina: Inteligência Artificial    ║
╠══════════════════════════════════════════╣
║  1. Processar paciente (arquivo JSON)    ║
║  2. Adicionar paciente manualmente       ║
║  3. Ver fila de espera                   ║
║  4. Exibir log auditável                 ║
║  5. Exportar log (JSON)                  ║
║  6. Modo demonstração                    ║
║  0. Sair                                 ║
╚══════════════════════════════════════════╝
"""

def repl():
    while True:
        try:
            print(MENU)
            opcao = input("  Opção: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Encerrando...")
            break

        if opcao == "0":
            print("  Encerrando sistema.")
            break
        elif opcao == "1":
            caminho = input("  Caminho do arquivo JSON: ").strip()
            cmd_processar_arquivo(caminho)
        elif opcao == "2":
            cmd_adicionar_manual()
        elif opcao == "3":
            hora = input("  Hora de consulta (HH:MM, Enter para agora): ").strip()
            cmd_ver_fila(hora or _hora_atual_fake())
        elif opcao == "4":
            cmd_log()
        elif opcao == "5":
            cmd_exportar()
        elif opcao == "6":
            cmd_demo()
        else:
            print("  Opção inválida.")


def _imprimir_resumo(memoria):
    nivel = memoria.nivel_atual
    cor   = NIVEIS_PRIORIDADE.get(nivel, {}).get("cor", "?")
    vuln  = " [VULNERÁVEL]" if memoria.vulneravel else ""
    block = " [ADMISSÕES BLOQUEADAS]" if memoria.admissoes_bloqueadas else ""
    print(f"\n  ✔ {memoria.id_paciente} → Nível {nivel} ({cor}){vuln}{block}")
    if memoria.eventos_registrados:
        print(f"    Eventos: {', '.join(e['id'] for e in memoria.eventos_registrados)}")


def _hora_atual_fake():
    for mem in reversed(fila):
        if mem.historico_leituras:
            return mem.historico_leituras[-1].get("hora", "00:00")
    return "00:00"


def _ler_int(prompt):
    val = input(prompt).strip()
    try:
        return int(val)
    except ValueError:
        return None


def _ler_float(prompt):
    val = input(prompt).strip()
    try:
        return float(val)
    except ValueError:
        return None


def _ler_bool(prompt, padrao=None):
    val = input(prompt).strip().lower()
    if val == "s":
        return True
    if val == "n":
        return False
    return padrao


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--arquivo" in args:
        idx = args.index("--arquivo")
        if idx + 1 < len(args):
            cmd_processar_arquivo(args[idx + 1])
            cmd_ver_fila()
            log.imprimir()
        else:
            print("Uso: python main.py --arquivo <caminho.json>")

    elif "--demo" in args:
        cmd_demo()
        log.imprimir()

    else:
        repl()
