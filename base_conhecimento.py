"""Base de conhecimento do sistema."""

# SLAs do Protocolo de Manchester adaptados no enunciado.
NIVEIS_PRIORIDADE = {
    1: {"cor": "VERMELHO", "descricao": "Emergência",     "sla_minutos": 0},
    2: {"cor": "LARANJA",  "descricao": "Muito urgente",  "sla_minutos": 10},
    3: {"cor": "AMARELO",  "descricao": "Urgente",        "sla_minutos": 30},
    4: {"cor": "VERDE",    "descricao": "Pouco urgente",  "sla_minutos": 60},
    5: {"cor": "AZUL",     "descricao": "Não urgente",    "sla_minutos": 120},
}

# Operadores usados na avaliação das condições.
OPERADORES = {
    "lt":  lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt":  lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "eq":  lambda a, b: a == b,
    "ne":  lambda a, b: a != b,
}

# Regras primárias.
REGRAS_PRIMARIAS = [
    {
        "id": "R1",
        "nivel_destino": 1,
        "descricao": "Emergência: PCR, apneia ou ausência de pulso confirmada",
        "conector": "OU",
        "condicoes": [
            {"campo": "pulso_presente", "operador": "eq", "valor": False},
            {"campo": "respirando",     "operador": "eq", "valor": False},
        ],
    },
    {
        "id": "R2",
        "nivel_destino": 2,
        "descricao": "Muito urgente: SpO2 < 90%, dor >= 8/10, Glasgow < 14 ou FC extrema",
        "conector": "OU",
        "condicoes": [
            {"campo": "spo2",                "operador": "lt",  "valor": 90},
            {"campo": "escala_dor",          "operador": "gte", "valor": 8},
            {"campo": "glasgow",             "operador": "lt",  "valor": 14},
            {"campo": "frequencia_cardiaca", "operador": "gt",  "valor": 150},
            {"campo": "frequencia_cardiaca", "operador": "lt",  "valor": 40},
        ],
    },
    {
        "id": "R3",
        "nivel_destino": 3,
        "descricao": "Urgente: febre > 39 °C, dor 5-7/10, vômitos > 3/h ou FC alterada",
        "conector": "OU",
        "condicoes": [
            {"campo": "temperatura",         "operador": "gt",  "valor": 39.0},
            {"campo": "escala_dor",          "operador": "gte", "valor": 5},
            {"campo": "vomitos_por_hora",    "operador": "gt",  "valor": 3},
            {"campo": "frequencia_cardiaca", "operador": "gte", "valor": 120},
            {"campo": "frequencia_cardiaca", "operador": "lte", "valor": 50},
        ],
    },
    {
        "id": "R4",
        "nivel_destino": 4,
        "descricao": "Pouco urgente: dor leve (1-4/10) com sinais estáveis",
        "conector": "E",
        "condicoes": [
            {"campo": "escala_dor", "operador": "gte", "valor": 1},
            {"campo": "escala_dor", "operador": "lte", "valor": 4},
        ],
    },
    {
        "id": "R5",
        "nivel_destino": 5,
        "descricao": "Não urgente: sem dor relevante ou caso administrativo",
        "conector": "PADRAO",
        "condicoes": [],
    },
]

# Regra dos grupos vulneráveis.
REGRA_VULNERABILIDADE = {
    "id": "V1",
    "descricao": "Paciente vulnerável — elevação de um nível de prioridade (Res. SUS 2017)",
    "limiar_idade": 60,
    "campos_booleanos": ["gestante", "deficiencia"],
    "elevacao": 1,
    "nivel_minimo": 1,
}

# Regras de segunda ordem.
REGRAS_SEGUNDA_ORDEM = [
    {
        "id": "E1",
        "descricao": "Reclassificação de Nível 3 para Nível 2 em menos de 30 minutos",
        "tipo": "reclassificacao_rapida",
        "nivel_origem": 3,
        "nivel_destino_esperado": 2,
        "tempo_max_min": 30,
        "acoes": ["registrar_evento_critico", "notificar_medico"],
    },
    {
        "id": "E2",
        "descricao": "Dois ou mais sinais vitais pioraram simultaneamente na última leitura",
        "tipo": "piora_multipla",
        "minimo_sinais_piora": 2,
        "acoes": ["elevar_prioridade", "agendar_leitura_5min"],
    },
    {
        "id": "E3",
        "descricao": "Paciente aguarda além do SLA do nível atual",
        "tipo": "violacao_sla",
        "acoes": ["gerar_alerta_violacao", "escalar_supervisor"],
    },
    {
        "id": "E4",
        "descricao": "Paciente vulnerável com temperatura subindo mais de 1 °C desde a leitura anterior",
        "tipo": "febre_vulneravel",
        "delta_temperatura_min": 1.0,
        "acoes": ["reclassificar_nivel_2"],
    },
    {
        "id": "E5",
        "descricao": "Dois alertas de violação de SLA para o mesmo paciente — protocolo de sobrecarga",
        "tipo": "dupla_violacao_sla",
        "minimo_alertas": 2,
        "acoes": ["bloquear_admissoes", "protocolo_sobrecarga"],
    },
]

# Sinais usados na regra E2.
CAMPOS_SINAIS_VITAIS = [
    "spo2",
    "frequencia_cardiaca",
    "temperatura",
    "escala_dor",
    "glasgow",
    "vomitos_por_hora",
]

# Direção de piora por sinal.
DIRECAO_PIORA = {
    "spo2":                "decrescente",
    "frequencia_cardiaca": "distancia",
    "temperatura":         "crescente",
    "escala_dor":          "crescente",
    "glasgow":             "decrescente",
    "vomitos_por_hora":    "crescente",
}

FC_NORMAL = 75
