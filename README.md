# Sistema de Triagem UPA-SUS

Trabalho da disciplina de Inteligencia Artificial (J903 - 2026).
Sistema com encadeamento progressivo para triagem em UPA.

## O que o sistema faz

- recebe os dados do paciente (perfil + leituras de sinais vitais);
- classifica o nivel de urgencia de 1 a 5 (Manchester adaptado para o SUS);
- aplica a regra de grupos vulneraveis (Resolucao SUS 2017);
- reage a piora ao longo do tempo usando as regras E1 a E5;
- ordena a fila com um criterio de desempate auditavel;
- registra tudo em um log explicavel.

## Como rodar

Nao precisa instalar nada alem do Python.

### Modo demonstrativo

```bash
python main.py --demo
```

Roda com pacientes de exemplo e mostra o log no final.
E o jeito mais rapido de ver o sistema funcionando.

### Modo interativo

```bash
python main.py
```

Abre um menu no terminal com as opcoes do sistema.

Resumo das opcoes:

- `1` processa paciente a partir de um arquivo JSON;
- `2` digita um paciente manualmente pelo terminal;
- `3` mostra a fila de espera atual;
- `4` mostra o log completo;
- `5` exporta o log em JSON;
- `6` roda o modo demonstrativo;
- `0` sai do programa.

### Processar arquivo JSON

```bash
python main.py --arquivo paciente.json
```

Aceita um unico paciente ou uma lista de pacientes em um so arquivo.

### Suite de testes

```bash
python testes.py --verbose
```

Resultado esperado:

```text
Resultado: 14/14 testes aprovados
```

## Como entender a saida

Niveis do Protocolo de Manchester adaptado:

- Nivel 1 (VERMELHO) - emergencia, atendimento imediato
- Nivel 2 (LARANJA)  - muito urgente, ate 10 min
- Nivel 3 (AMARELO)  - urgente, ate 30 min
- Nivel 4 (VERDE)    - pouco urgente, ate 60 min
- Nivel 5 (AZUL)     - nao urgente, ate 120 min

Na fila, quem estiver na posicao 1 e atendido primeiro.

O log mostra, para cada paciente:

- a regra que disparou;
- os fatos usados na decisao;
- a conclusao gerada;
- e, nos empates, o criterio aplicado em texto legivel.

## Formato de entrada

```python
paciente = {
    "id": "PAC-2026-001",
    "idade": 67,
    "gestante": False,
    "deficiencia": False,
    "hora_entrada": "14:00",
    "leituras": [
        {
            "hora": "14:00",
            "glasgow": 15,
            "spo2": 95,
            "frequencia_cardiaca": 88,
            "temperatura": 37.2,
            "escala_dor": 3,
            "vomitos_por_hora": 0,
            "pulso_presente": True,
            "respirando": True
        },
        {
            "hora": "14:25",
            "glasgow": 14,
            "spo2": 89,
            "frequencia_cardiaca": 122,
            "temperatura": 38.6,
            "escala_dor": 7,
            "vomitos_por_hora": 2
        }
    ]
}
```

Campos ausentes sao tratados sem lancar excecao.

## Arquivos do projeto

- `base_conhecimento.py` - regras primarias (R1-R5), vulnerabilidade (V1) e segunda ordem (E1-E5), todas como dados;
- `motor_inferencia.py` - motor de forward chaining e memoria de trabalho;
- `desempate.py` - criterio de desempate entre pacientes no mesmo nivel;
- `log_auditavel.py` - registro das inferencias e dos desempates;
- `main.py` - interface CLI e REPL;
- `testes.py` - suite com 14 cenarios, incluindo os 5 de empate, E4 e E5;
- `reflexao_final.md` - reflexao pedida no enunciado;
- `README_entrega.md` - descricao tecnica da entrega.

## Restricoes respeitadas

- Python puro, sem biblioteca de machine learning;
- regras representadas como dados (sem blocos if-elif);
- motor em arquivo separado da base de conhecimento;
- sinais vitais ausentes tratados sem excecao;
- nenhum rebaixamento automatico de prioridade.
