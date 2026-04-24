"""Motor de inferência por encadeamento progressivo."""

from base_conhecimento import (
    NIVEIS_PRIORIDADE,
    OPERADORES,
    REGRAS_PRIMARIAS,
    REGRA_VULNERABILIDADE,
    REGRAS_SEGUNDA_ORDEM,
    CAMPOS_SINAIS_VITAIS,
    DIRECAO_PIORA,
    FC_NORMAL,
)
from log_auditavel import LogAuditavel


def hora_para_minutos(hora_str):
    """Converte uma string 'HH:MM' em minutos desde meia-noite."""
    if not hora_str:
        return 0
    try:
        partes = hora_str.strip().split(":")
        return int(partes[0]) * 60 + int(partes[1])
    except (ValueError, IndexError):
        return 0


def diferenca_minutos(hora_inicio, hora_fim):
    """Retorna a diferença em minutos entre duas strings 'HH:MM'."""
    return hora_para_minutos(hora_fim) - hora_para_minutos(hora_inicio)


def contar_sinais_piorando(leitura_atual, leitura_anterior):
    """Conta pioras clinicamente relevantes entre duas leituras."""
    count = 0
    for campo in CAMPOS_SINAIS_VITAIS:
        val_atual    = leitura_atual.get(campo)
        val_anterior = leitura_anterior.get(campo)

        if val_atual is None or val_anterior is None:
            continue

        direcao = DIRECAO_PIORA.get(campo)
        delta = val_atual - val_anterior

        if direcao == "crescente" and _variacao_relevante(campo, delta):
            count += 1
        elif direcao == "decrescente" and _variacao_relevante(campo, -delta):
            count += 1
        elif direcao == "distancia":
            if abs(val_atual - FC_NORMAL) > abs(val_anterior - FC_NORMAL):
                if _variacao_relevante(campo, abs(val_atual - val_anterior)):
                    count += 1

    return count


def _variacao_relevante(campo, delta):
    """Filtra oscilações pequenas que não devem contar como piora."""
    limiares = {
        "spo2": 3,
        "frequencia_cardiaca": 15,
        "temperatura": 0.8,
        "escala_dor": 2,
        "glasgow": 1,
        "vomitos_por_hora": 2,
    }
    return delta >= limiares.get(campo, 1)


class MemoriaDeTrabalho:
    """Estado atual e histórico de um paciente."""

    def __init__(self, paciente):
        self.id_paciente     = paciente["id"]
        self.dados_fixos     = {
            "idade":      paciente.get("idade"),
            "gestante":   paciente.get("gestante", False),
            "deficiencia": paciente.get("deficiencia", False),
        }
        self.hora_entrada         = paciente.get("hora_entrada", "00:00")
        self.nivel_atual          = None
        self.hora_entrada_nivel   = None
        self.historico_niveis     = []
        self.historico_leituras   = []
        self.alertas_sla          = 0
        self.vulneravel           = False
        self.admissoes_bloqueadas = False
        self.eventos_registrados  = []
        self.ultima_leitura_reclassificou = False

    def registrar_nivel(self, novo_nivel, hora_str):
        """Atualiza o nível sem permitir rebaixamento automático."""
        if self.nivel_atual is not None and novo_nivel > self.nivel_atual:
            return False
        if self.nivel_atual == novo_nivel:
            return False

        self.nivel_atual        = novo_nivel
        self.hora_entrada_nivel = hora_str
        self.historico_niveis.append((hora_str, novo_nivel))
        return True

    def ultima_leitura(self):
        return self.historico_leituras[-1] if self.historico_leituras else None

    def penultima_leitura(self):
        return self.historico_leituras[-2] if len(self.historico_leituras) >= 2 else None

    def tempo_no_nivel_atual(self, hora_atual):
        """Retorna quantos minutos o paciente está no nível atual."""
        if not self.hora_entrada_nivel:
            return 0
        return max(0, diferenca_minutos(self.hora_entrada_nivel, hora_atual))

    def sla_atual(self):
        if self.nivel_atual is not None:
            return NIVEIS_PRIORIDADE[self.nivel_atual]["sla_minutos"]
        return None

    def nivel_anterior(self):
        if len(self.historico_niveis) >= 2:
            return self.historico_niveis[-2][1]
        return None

    def hora_nivel_anterior(self):
        if len(self.historico_niveis) >= 2:
            return self.historico_niveis[-2][0]
        return None

    def evento_ja_disparou(self, id_evento, hora=None):
        """Verifica se um evento de segunda ordem já foi registrado."""
        for e in self.eventos_registrados:
            if e["id"] == id_evento:
                if hora is None or e["hora"] == hora:
                    return True
        return False

    def contar_eventos(self, id_evento):
        return sum(1 for e in self.eventos_registrados if e["id"] == id_evento)

class MotorInferencia:

    def __init__(self, log=None):
        self.log = log if log is not None else LogAuditavel()

    def processar_paciente(self, paciente):
        """Processa todas as leituras de um paciente."""
        memoria  = MemoriaDeTrabalho(paciente)
        leituras = paciente.get("leituras", [])

        for leitura in leituras:
            self._processar_leitura(memoria, leitura)

        return memoria
    def _processar_leitura(self, memoria, leitura):
        hora = leitura.get("hora", memoria.hora_entrada)
        nivel_antes_leitura = memoria.nivel_atual
        memoria.historico_leituras.append(leitura)

        fatos = {}
        fatos.update(memoria.dados_fixos)
        fatos.update({k: v for k, v in leitura.items() if k != "hora"})

        nivel_base = self._avaliar_regras_primarias(fatos)

        regra_disparada = f"R{nivel_base}"
        self.log.registrar_regra(
            memoria.id_paciente, hora, regra_disparada, fatos,
            f"Nível {nivel_base} — {NIVEIS_PRIORIDADE[nivel_base]['cor']}",
            NIVEIS_PRIORIDADE[nivel_base]["descricao"],
        )

        eh_vulneravel = self._verificar_vulnerabilidade(fatos)
        memoria.vulneravel = eh_vulneravel
        fatos["eh_vulneravel"] = eh_vulneravel

        nivel_apos_vuln = nivel_base
        if eh_vulneravel:
            nivel_apos_vuln = max(
                REGRA_VULNERABILIDADE["nivel_minimo"],
                nivel_base - REGRA_VULNERABILIDADE["elevacao"],
            )
            if nivel_apos_vuln != nivel_base:
                self.log.registrar_regra(
                    memoria.id_paciente, hora, "V1", fatos,
                    f"Nível elevado de {nivel_base} para {nivel_apos_vuln}",
                    REGRA_VULNERABILIDADE["descricao"],
                )

        memoria.registrar_nivel(nivel_apos_vuln, hora)
        fatos["reclassificado_nesta_leitura"] = (
            nivel_antes_leitura is not None and nivel_apos_vuln < nivel_antes_leitura
        )
        memoria.ultima_leitura_reclassificou = fatos["reclassificado_nesta_leitura"]

        for _ in range(10):
            fatos["nivel_atual"]       = memoria.nivel_atual
            fatos["alertas_sla_total"] = memoria.alertas_sla

            novos_eventos = self._avaliar_segunda_ordem(memoria, fatos, hora)
            if not novos_eventos:
                break

        self.log.registrar_classificacao_final(
            memoria.id_paciente, hora,
            memoria.nivel_atual,
            NIVEIS_PRIORIDADE[memoria.nivel_atual]["cor"],
            NIVEIS_PRIORIDADE[memoria.nivel_atual]["descricao"],
        )
    def _avaliar_regras_primarias(self, fatos):
        """Retorna o nível mais crítico (menor número) que disparou."""
        nivel_mais_critico = None

        for regra in REGRAS_PRIMARIAS:
            if regra["conector"] == "PADRAO":
                if nivel_mais_critico is None:
                    nivel_mais_critico = regra["nivel_destino"]
                continue

            if self._avaliar_condicoes(fatos, regra["condicoes"], regra["conector"]):
                nd = regra["nivel_destino"]
                if nivel_mais_critico is None or nd < nivel_mais_critico:
                    nivel_mais_critico = nd

        return nivel_mais_critico or 5

    def _avaliar_condicoes(self, fatos, condicoes, conector):
        """Avalia uma lista de condições com AND ('E') ou OR ('OU')."""
        if not condicoes:
            return True

        resultados = []
        for cond in condicoes:
            campo    = cond["campo"]
            operador = cond["operador"]
            valor    = cond["valor"]

            if campo not in fatos or fatos[campo] is None:
                resultados.append(False)
                continue

            func = OPERADORES.get(operador)
            if func is None:
                resultados.append(False)
                continue

            try:
                resultados.append(func(fatos[campo], valor))
            except TypeError:
                resultados.append(False)

        return all(resultados) if conector == "E" else any(resultados)
    def _verificar_vulnerabilidade(self, fatos):
        """Retorna True se o paciente se enquadra nos grupos vulneráveis."""
        idade = fatos.get("idade")
        if idade is not None and idade >= REGRA_VULNERABILIDADE["limiar_idade"]:
            return True
        for campo in REGRA_VULNERABILIDADE["campos_booleanos"]:
            if fatos.get(campo) is True:
                return True
        return False
    def _avaliar_segunda_ordem(self, memoria, fatos, hora_atual):
        """Avalia as regras de segunda ordem da leitura atual."""
        eventos_novos = []

        for regra in REGRAS_SEGUNDA_ORDEM:
            if regra["id"] != "E3" and memoria.evento_ja_disparou(regra["id"], hora_atual):
                continue

            disparou, detalhes = self._verificar_regra_so(regra, memoria, fatos, hora_atual)

            if disparou:
                evento = {
                    "id":       regra["id"],
                    "hora":     hora_atual,
                    "descricao": regra["descricao"],
                    "acoes":    regra["acoes"],
                    "detalhes": detalhes,
                }
                memoria.eventos_registrados.append(evento)
                eventos_novos.append(evento)

                self.log.registrar_regra(
                    memoria.id_paciente, hora_atual, regra["id"], fatos,
                    f"Ações: {', '.join(regra['acoes'])}",
                    regra["descricao"],
                )

                self._executar_acoes(regra["acoes"], memoria, fatos, hora_atual)

        return eventos_novos

    def _verificar_regra_so(self, regra, memoria, fatos, hora_atual):
        """Verifica se uma regra de segunda ordem deve disparar neste ciclo."""
        tipo = regra["tipo"]

        if tipo == "reclassificacao_rapida":
            if len(memoria.historico_niveis) < 2:
                return False, None
            hora_ant, nivel_ant = memoria.historico_niveis[-2]
            hora_atu, nivel_atu = memoria.historico_niveis[-1]
            if nivel_ant == regra["nivel_origem"] and nivel_atu == regra["nivel_destino_esperado"]:
                delta = diferenca_minutos(hora_ant, hora_atu)
                if delta < regra["tempo_max_min"]:
                    return True, {"delta_min": delta}
            return False, None

        elif tipo == "piora_multipla":
            if fatos.get("reclassificado_nesta_leitura"):
                return False, None
            leit_atual = memoria.ultima_leitura()
            leit_ant   = memoria.penultima_leitura()
            if not leit_ant:
                return False, None
            n = contar_sinais_piorando(leit_atual, leit_ant)
            fatos["sinais_piorando_count"] = n
            if n >= regra["minimo_sinais_piora"]:
                return True, {"sinais_piorando": n}
            return False, None

        elif tipo == "violacao_sla":
            if not memoria.hora_entrada_nivel:
                return False, None
            sla          = memoria.sla_atual()
            tempo_espera = memoria.tempo_no_nivel_atual(hora_atual)
            if sla is not None and sla > 0 and tempo_espera > sla:
                if not memoria.evento_ja_disparou("E3", hora_atual):
                    return True, {"tempo_espera": tempo_espera, "sla": sla}
            return False, None

        elif tipo == "febre_vulneravel":
            if not memoria.vulneravel:
                return False, None
            leit_atual = memoria.ultima_leitura()
            leit_ant   = memoria.penultima_leitura()
            if not leit_ant:
                return False, None
            temp_atual = leit_atual.get("temperatura")
            temp_ant   = leit_ant.get("temperatura")
            if temp_atual is None or temp_ant is None:
                return False, None
            delta = temp_atual - temp_ant
            if delta > regra["delta_temperatura_min"]:
                return True, {"delta_temp": round(delta, 2)}
            return False, None

        elif tipo == "dupla_violacao_sla":
            total_e3 = memoria.contar_eventos("E3")
            if total_e3 >= regra["minimo_alertas"]:
                if not memoria.evento_ja_disparou("E5"):
                    return True, {"total_alertas_sla": total_e3}
            return False, None

        return False, None

    def _executar_acoes(self, acoes, memoria, fatos, hora_atual):
        """Aplica os efeitos das ações na memória de trabalho."""
        for acao in acoes:
            if acao == "elevar_prioridade":
                if memoria.nivel_atual and memoria.nivel_atual > 1:
                    novo = memoria.nivel_atual - 1
                    if memoria.registrar_nivel(novo, hora_atual):
                        fatos["nivel_atual"] = novo

            elif acao == "reclassificar_nivel_2":
                if memoria.registrar_nivel(2, hora_atual):
                    fatos["nivel_atual"] = 2

            elif acao == "gerar_alerta_violacao":
                memoria.alertas_sla += 1
                fatos["alertas_sla_total"] = memoria.alertas_sla

            elif acao == "bloquear_admissoes":
                memoria.admissoes_bloqueadas = True
