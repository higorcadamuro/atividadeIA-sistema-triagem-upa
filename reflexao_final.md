# Reflexao sobre o criterio de desempate

O criterio adotado prioriza primeiro o nivel de risco e, dentro do mesmo nivel, aplica uma pontuacao baseada em tres fatores: proximidade ou violacao do SLA, quantidade de sinais vitais piorando na ultima leitura e vulnerabilidade. Empates residuais sao resolvidos pelo tempo absoluto no nivel e, em ultimo caso, pelo ID do paciente. Nenhum fator depende de genero, raca, origem ou renda.

## Comportamento com 40 pacientes no Nivel 3

Com 40 pacientes simultaneos no Nivel 3, o sistema se comporta como um particionador progressivo do grupo. Primeiro separa quem ja violou o SLA dos 30 min, depois quem esta entre 80% e 100%, depois entre 60% e 80%, e assim por diante. Na pratica, o criterio gera subfilas por faixa de risco temporal, e dentro de cada faixa a piora recente e o tempo absoluto desempatam. Pacientes estaveis que chegaram cedo sao chamados antes de recem-chegados estaveis, o que reduz o risco de inanicao. Pacientes com piora recente furam a subfila da faixa deles e sobem, mesmo tendo chegado depois.

A fragilidade desse comportamento aparece quando varios pacientes caem na mesma faixa de SLA com estados clinicos parecidos. Com 40 pacientes, isso e comum: uma boa parte vai estar na faixa de 60% a 80% sem piora evidente. O desempate cai entao para tempo no nivel e depois para ID. Isso e deterministico e auditavel, mas nao e clinicamente rico, porque o sistema nao enxerga queixa subjetiva, dor localizada ou historico de doenca de base.

## Onde o criterio falha

Ele falha em tres pontos principais. Primeiro, oscilacoes pequenas nao contam como piora por causa do filtro de variacao relevante. Isso evita ruido, mas pode mascarar deterioracoes lentas que so aparecem apos varias leituras. Segundo, o bonus de vulnerabilidade e apenas um ponto e pode ser superado por um unico sinal piorando em outro paciente. Isso e coerente com o argumento clinico, mas pode parecer contraintuitivo para quem atua na UPA. Terceiro, o sistema depende da qualidade do monitoramento: se uma leitura atrasa, o desempate reflete o atraso da coleta, nao o quadro real do paciente.

## Perfis variados e ausencia de vies sistematico

Os testes cobrem idades entre 25 e 62 anos e incluem gestantes (T12) e nao gestantes. O campo deficiencia passa pelo mesmo caminho da regra V1 usada para gestante e para idade acima de 60, entao o comportamento verificado nesses dois ramos se estende por simetria para pessoa com deficiencia. Os atributos proibidos pelo enunciado, como genero, raca, origem e renda, nao sao sequer lidos pelo sistema, porque nao existem no dicionario de entrada. A vulnerabilidade entra apenas como regra institucional do SUS (Resolucao 2017) e vale um ponto na pontuacao, enquanto piora clinica vale tres pontos por sinal. Ao trocar idade ou status de gestante mantendo os sinais vitais identicos, a fila so muda se o paciente cruzar o limiar de vulnerabilidade, e essa mudanca esta em regra publica, nao em inferencia oculta. Em uso real seria necessario auditar os logs continuamente, porque ausencia de vies no design nao garante ausencia de vies na pratica.
