"""Regras de desempate para pacientes no mesmo nível."""

from motor_inferencia import contar_sinais_piorando


class ModuloDesempate:
    PONTOS_SLA_VIOLADO   = 10
    PONTOS_SLA_80        = 5
    PONTOS_SLA_60        = 2
    PONTOS_SINAL_PIORA   = 3
    PONTOS_VULNERAVEL    = 1

    def calcular_pontuacao(self, memoria, hora_atual):
        """Retorna pontos, espera e detalhes usados no desempate."""
        pontos    = 0
        detalhes  = []
        sla       = memoria.sla_atual()
        espera    = memoria.tempo_no_nivel_atual(hora_atual)

        if sla is not None and sla > 0:
            proporcao = espera / sla
            if proporcao > 1.0:
                pontos += self.PONTOS_SLA_VIOLADO
                detalhes.append(f"SLA violado (+{self.PONTOS_SLA_VIOLADO})")
            elif proporcao > 0.8:
                pontos += self.PONTOS_SLA_80
                detalhes.append(f"SLA {proporcao:.0%} atingido (+{self.PONTOS_SLA_80})")
            elif proporcao > 0.6:
                pontos += self.PONTOS_SLA_60
                detalhes.append(f"SLA {proporcao:.0%} atingido (+{self.PONTOS_SLA_60})")
        elif sla == 0:
            pontos += self.PONTOS_SLA_VIOLADO
            detalhes.append(f"Nível 1 emergência (+{self.PONTOS_SLA_VIOLADO})")

        leit_atual = memoria.ultima_leitura()
        leit_ant   = memoria.penultima_leitura()
        sinais_piora = 0
        if leit_atual and leit_ant and not memoria.ultima_leitura_reclassificou:
            sinais_piora = contar_sinais_piorando(leit_atual, leit_ant)
        if sinais_piora > 0:
            pts_piora = sinais_piora * self.PONTOS_SINAL_PIORA
            pontos   += pts_piora
            detalhes.append(f"{sinais_piora} sinal(is) piorando (+{pts_piora})")

        if memoria.vulneravel:
            pontos  += self.PONTOS_VULNERAVEL
            detalhes.append(f"Paciente vulnerável (+{self.PONTOS_VULNERAVEL})")

        return pontos, espera, detalhes

    def ordenar_fila(self, memorias, hora_atual, log=None):
        """Ordena a fila por nível, pontuação, espera e ID."""
        def chave(mem):
            nivel  = mem.nivel_atual if mem.nivel_atual is not None else 99
            pontos, espera, _ = self.calcular_pontuacao(mem, hora_atual)
            return (nivel, -pontos, -espera, mem.id_paciente)

        fila_ordenada = sorted(memorias, key=chave)

        if log:
            for i in range(len(fila_ordenada) - 1):
                a = fila_ordenada[i]
                b = fila_ordenada[i + 1]
                if a.nivel_atual == b.nivel_atual:
                    resultado = self.explicar_desempate(a, b, hora_atual)
                    log.registrar_desempate(
                        resultado["vencedor"],
                        resultado["perdedor"],
                        hora_atual,
                        resultado["criterio"],
                        resultado["pontuacoes"],
                    )

        return fila_ordenada

    def explicar_desempate(self, mem_a, mem_b, hora_atual):
        """Compara dois pacientes do mesmo nível."""
        pontos_a, espera_a, det_a = self.calcular_pontuacao(mem_a, hora_atual)
        pontos_b, espera_b, det_b = self.calcular_pontuacao(mem_b, hora_atual)

        if pontos_a != pontos_b:
            vencedor  = mem_a if pontos_a > pontos_b else mem_b
            perdedor  = mem_b if pontos_a > pontos_b else mem_a
            criterio  = f"pontuação de desempate ({pontos_a} pts vs {pontos_b} pts)"

        elif espera_a != espera_b:
            vencedor  = mem_a if espera_a > espera_b else mem_b
            perdedor  = mem_b if espera_a > espera_b else mem_a
            criterio  = (f"tempo de espera no nível ({espera_a} min vs {espera_b} min)"
                         " — prevenção de inanição")

        else:
            vencedor  = mem_a if mem_a.id_paciente <= mem_b.id_paciente else mem_b
            perdedor  = mem_b if mem_a.id_paciente <= mem_b.id_paciente else mem_a
            criterio  = f"ID do paciente (critério determinístico final)"

        return {
            "vencedor": vencedor.id_paciente,
            "perdedor": perdedor.id_paciente,
            "criterio": criterio,
            "pontuacoes": {
                mem_a.id_paciente: {
                    "pontos":       pontos_a,
                    "tempo_espera": espera_a,
                    "detalhes":     det_a,
                },
                mem_b.id_paciente: {
                    "pontos":       pontos_b,
                    "tempo_espera": espera_b,
                    "detalhes":     det_b,
                },
            },
        }
