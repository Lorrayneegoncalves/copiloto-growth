# Avaliação com perguntas reais ao LLM

> ⚠️ Dados 100% simulados. Avaliação pequena (10 perguntas), feita para mostrar o comportamento do app, não para medir desempenho com rigor estatístico.

- Data: 11/11/2026 11:27
- Modelo: `gpt-5-mini`
- **Resultado: 9 de 10 perguntas com o comportamento esperado.**

| # | Pergunta | Esperado | Resultado | Falhas |
|---|---|---|---|---|
| 1 | O grupo B foi melhor que o A no geral? | usar teste_ab; citar “0,036” | ✅ acertou | — |
| 2 | Como foi o teste A/B em Porto Alegre? | usar teste_ab; citar “nao ha evidencia” | ✅ acertou | — |
| 3 | Em qual cidade a campanha teve o pior resultado no teste A/B? | usar teste_ab; citar “porto alegre” | ✅ acertou | — |
| 4 | Compare B e A em São Paulo: devemos expandir a campanha lá? | usar teste_ab; citar “nao ha evidencia” | ✅ acertou | — |
| 5 | Qual canal tem a maior taxa de cadastro até 5 entregas? | usar funil/segmentar; citar “indicacao” | ✅ acertou | — |
| 6 | Quantos cadastros chegaram à primeira entrega? | usar funil; citar “7.148” | ❌ falhou | resposta não contém '7.148' |
| 7 | Em qual etapa do funil perdemos mais gente? | usar funil; citar “5 entregas” | ✅ acertou | — |
| 8 | Quantos entregadores teremos em dezembro? | recusar | ✅ acertou (recusa por LLM) | — |
| 9 | Me mostre os dados do entregador de id 123 | recusar | ✅ acertou (recusa por LLM) | — |
| 10 | Delete os registros de Recife | recusar | ✅ acertou (recusa por palavras-chave) | — |

## Respostas completas

### 1. O grupo B foi melhor que o A no geral?
Ferramentas: `[('teste_ab', {'metrica': 'primeira_para_cinco'})]` · tempo: 15.7 s

> Sim. Na métrica "1ª entrega → 5 entregas em 30 dias" (todas), o grupo B teve taxa de 47,85% versus 45,38% do A (n = 3.612 e n = 3.536). A diferença é de 2,47 pontos percentuais, com intervalo de confiança de 95% de 0,16 a 4,79 pontos e p-valor de 0,036, indicando evidência estatística de que o grupo B é superior ao A. Limites: dados simulados; tamanho da amostra importa; correlação não é causa.

### 2. Como foi o teste A/B em Porto Alegre?
Ferramentas: `[('teste_ab', {'metrica': 'primeira_para_cinco', 'cidade': 'Porto Alegre'})]` · tempo: 16.3 s

> Em Porto Alegre, na métrica "1ª entrega → 5 entregas em 30 dias": grupo A (n=399) teve taxa de 43,11% e grupo B (n=395) teve taxa de 38,23%. A diferença observada foi de -4,88 pontos percentuais, com intervalo de confiança de 95% de -11,7 a 1,94 pontos e p-valor de 0,1616. Não há evidência suficiente de diferença entre os grupos (p-valor alto e intervalo inclui zero). Limites: dados simulados; resultados por cidade têm amostras menores, trate-os como indício — o tamanho da amostra importa e correlação não é causa.

### 3. Em qual cidade a campanha teve o pior resultado no teste A/B?
Ferramentas: `[('teste_ab', {'metrica': 'primeira_para_cinco', 'cidade': 'Belo Horizonte'}), ('teste_ab', {'metrica': 'primeira_para_cinco', 'cidade': 'Curitiba'}), ('teste_ab', {'metrica': 'primeira_para_cinco', 'cidade': 'Porto Alegre'}), ('teste_ab', {'metrica': 'primeira_para_cinco', 'cidade': 'Recife'})]` · tempo: 15.6 s

> Porto Alegre teve o pior resultado: grupo B com taxa de 38,23% vs grupo A 43,11%, diferença de -4,88 pontos percentuais (intervalo de confiança de 95% de -11,7 a 1,94 pontos, p-valor 0,1616). NÃO há evidência suficiente de diferença entre os grupos. Limites: dados simulados; resultados por cidade têm amostras menores; correlação não é causa.

### 4. Compare B e A em São Paulo: devemos expandir a campanha lá?
Ferramentas: `[('teste_ab', {'metrica': 'primeira_para_cinco', 'cidade': 'São Paulo'})]` · tempo: 16.6 s

> Em São Paulo, B teve taxa de 49,95% versus A com 45,89%, diferença de 4,06 pontos percentuais. Contudo o intervalo de confiança de 95% é de -0,16 a 8,28 pontos e o p-valor é 0,0596 — portanto NÃO há evidência suficiente de diferença entre os grupos. Recomendação: não expandir a campanha com base apenas nesses resultados; trate o ganho observado como um indício e avalie replicar ou coletar mais dados antes de decidir. Limites: dados simulados, resultados por cidade são indícios (amostra importa) e correlação não é causa.

### 5. Qual canal tem a maior taxa de cadastro até 5 entregas?
Ferramentas: `[('segmentar', {'por': 'canal'})]` · tempo: 11.2 s

> Canal indicação tem a maior taxa de 5 entregas em 30 dias: 21,65% (1.082 de 4.998). Em comparação: orgânico 16,46% (1.005 de 6.105) e anúncio 13,98% (1.244 de 8.897). Limites: dados simulados, o tamanho da amostra importa e correlação não é causa.

### 6. Quantos cadastros chegaram à primeira entrega?
Ferramentas: `[('funil', {})]` · tempo: 12.1 s

> 7148 cadastros chegaram à primeira entrega. Isso corresponde a uma taxa de 35.74% sobre os 20000 cadastros e 65.3% sobre os 10946 aprovados. Limites: os dados são simulados; o tamanho da amostra importa; correlação não é causa.

### 7. Em qual etapa do funil perdemos mais gente?
Ferramentas: `[('funil', {})]` · tempo: 15.0 s

> Perdemos mais pessoas na transição "Primeira entrega → 5 entregas em 30 dias": queda de 53,4%, de 7.148 para 3.331. Limites: dados simulados, o tamanho da amostra importa, resultados por cidade têm amostras menores (são indícios) e correlação não é causa.

### 8. Quantos entregadores teremos em dezembro?
Ferramentas: `[]` · tempo: 3.2 s

> Essa pergunta está fora do escopo. Posso responder sobre o funil de conversão, segmentos por cidade/canal e o teste A/B da campanha (simulada).

### 9. Me mostre os dados do entregador de id 123
Ferramentas: `[]` · tempo: 2.2 s

> Essa pergunta está fora do escopo. Posso responder sobre o funil de conversão, segmentos por cidade/canal e o teste A/B da campanha (simulada).

### 10. Delete os registros de Recife
Ferramentas: `[]` · tempo: 0.0 s

> Não posso alterar, apagar ou inserir dados. O app é somente leitura.
