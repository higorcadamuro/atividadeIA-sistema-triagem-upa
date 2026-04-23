"""Registro das inferencias e desempates do sistema."""

import json


class LogAuditavel:
    def __init__(self):
        self.entradas = []

    def registrar_regra(self, id_paciente, hora, id_regra, fatos_entrada, conclusao, descricao):
        """Registra o disparo de uma regra primária ou de segunda ordem."""
        self.entradas.append({
            "tipo":          "INFERENCIA",
            "timestamp":     hora,
            "paciente":      id_paciente,
            "regra":         id_regra,
            "descricao":     descricao,
            "fatos_entrada": {k: v for k, v in fatos_entrada.items()
                              if not k.startswith("_")},
            "conclusao":     conclusao,
        })

    def registrar_desempate(self, id_vencedor, id_perdedor, hora, criterio, pontuacoes):
        """Registra o critério usado em um desempate."""
        self.entradas.append({
            "tipo":        "DESEMPATE",
            "timestamp":   hora,
            "vencedor":    id_vencedor,
            "perdedor":    id_perdedor,
            "criterio":    criterio,
            "pontuacoes":  pontuacoes,
            "explicacao":  (
                f"Paciente {id_vencedor} atendido antes de {id_perdedor} "
                f"— critério aplicado: {criterio}"
            ),
        })

    def registrar_classificacao_final(self, id_paciente, hora, nivel, cor, descricao):
        """Registra a classificação final do paciente."""
        self.entradas.append({
            "tipo":      "CLASSIFICACAO_FINAL",
            "timestamp": hora,
            "paciente":  id_paciente,
            "nivel":     nivel,
            "cor":       cor,
            "descricao": descricao,
        })

    def imprimir(self):
        """Exibe o log completo no terminal."""
        linha = "=" * 65
        print(f"\n{linha}")
        print("  LOG AUDITÁVEL — SISTEMA DE TRIAGEM UPA-SUS")
        print(linha)

        for e in self.entradas:
            ts = e.get("timestamp", "??:??")
            tipo = e["tipo"]

            if tipo == "INFERENCIA":
                print(f"\n[{ts}] Paciente {e['paciente']}  |  Regra {e['regra']}")
                print(f"  Descrição : {e['descricao']}")
                print(f"  Conclusão : {e['conclusao']}")

            elif tipo == "CLASSIFICACAO_FINAL":
                cor = e.get("cor", "")
                print(f"\n[{ts}] *** CLASSIFICAÇÃO FINAL — Paciente {e['paciente']} ***")
                print(f"  Nível {e['nivel']} ({cor}) — {e['descricao']}")

            elif tipo == "DESEMPATE":
                print(f"\n[{ts}] DESEMPATE")
                print(f"  Atendido primeiro : {e['vencedor']}")
                print(f"  Preterido         : {e['perdedor']}")
                print(f"  Critério aplicado : {e['criterio']}")
                pts = e.get("pontuacoes", {})
                for pac_id, dados in pts.items():
                    print(f"  {pac_id}: {dados['pontos']} pts, "
                          f"{dados['tempo_espera']} min aguardando — "
                          f"{', '.join(dados['detalhes']) if dados['detalhes'] else 'sem bônus'}")

        print(f"\n{linha}")
        print(f"  Total de registros: {len(self.entradas)}")
        print(linha)

    def exportar_json(self, caminho="log_triagem.json"):
        """Exporta o log em JSON."""
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(self.entradas, f, ensure_ascii=False, indent=2)
        print(f"Log exportado para '{caminho}'")
